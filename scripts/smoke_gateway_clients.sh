#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${DG_GATEWAY_CLIENTS_PORT:-4100}"
MODELS_URL="http://127.0.0.1:$PORT/v1/models"
LOG_OUT="/tmp/dg-gateway-clients-litellm.out"
LOG_ERR="/tmp/dg-gateway-clients-litellm.err"
started_pid=""

cleanup() {
  if [[ -n "$started_pid" ]]; then
    kill "$started_pid" 2>/dev/null || true
    wait "$started_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if ! curl -fsS --max-time 2 "$MODELS_URL" >/tmp/dg-gateway-client-models.json 2>/dev/null; then
  LITELLM_PORT="$PORT" "$DG_ROOT/scripts/run_litellm_gateway.sh" >"$LOG_OUT" 2>"$LOG_ERR" &
  started_pid=$!
  ready=0
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 2 "$MODELS_URL" >/tmp/dg-gateway-client-models.json 2>/dev/null; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" != "1" ]]; then
    echo "LiteLLM gateway did not become ready on port $PORT" >&2
    tail -n 120 "$LOG_ERR" >&2 || true
    tail -n 120 "$LOG_OUT" >&2 || true
    exit 1
  fi
fi

python3 - "$DG_ROOT" "$PORT" <<'PY'
import json
import re
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
port = sys.argv[2]
base_url = f"http://127.0.0.1:{port}/v1"
model = "diffusiongemma-local"

models = json.loads(Path("/tmp/dg-gateway-client-models.json").read_text(encoding="utf-8"))
ids = [item.get("id") for item in models.get("data", []) if isinstance(item, dict)]
assert model in ids, models

profile = json.loads((root / "configs/client_profiles/openai-compatible.local.json").read_text(encoding="utf-8"))
assert profile["base_url"] == base_url, profile
assert profile["api_key"] == "dummy", profile
assert profile["model"] == model, profile
assert profile["clients"]["continue"]["apiBase"] == base_url, profile
assert profile["clients"]["cline"]["base_url"] == base_url, profile
assert profile["clients"]["roo_code"]["base_url"] == base_url, profile
assert profile["clients"]["openhands"]["base_url"] == f"http://127.0.0.1:{port}", profile
assert profile["clients"]["openhands"]["model"] == "litellm_proxy/diffusiongemma-local", profile
assert profile["clients"]["autogen"]["base_url"] == base_url, profile
assert profile["clients"]["autogen"]["model_client"].endswith("OpenAIChatCompletionClient"), profile
assert profile["clients"]["smolagents"]["base_url"] == base_url, profile
assert profile["clients"]["smolagents"]["agent"] == "smolagents.CodeAgent", profile
assert profile["clients"]["smolagents"]["model_class"].endswith("OpenAIModel"), profile
assert profile["clients"]["langgraph"]["base_url"] == base_url, profile
assert profile["clients"]["langgraph"]["agent_factory"].endswith("create_agent"), profile
assert profile["clients"]["langgraph"]["model_class"].endswith("ChatOpenAI"), profile
assert profile["clients"]["crewai"]["base_url"] == base_url, profile
assert profile["clients"]["crewai"]["classes"]["crew"] == "crewai.Crew", profile
assert profile["clients"]["crewai"]["model"] == "openai/diffusiongemma-local", profile
assert profile["clients"]["open_interpreter"]["base_url"] == base_url, profile
assert profile["clients"]["open_interpreter"]["agent"] == "interpreter.interpreter", profile
assert profile["clients"]["open_interpreter"]["model"] == "openai/diffusiongemma-local", profile
assert profile["clients"]["open_interpreter"]["auto_run"] is False, profile
assert profile["clients"]["llamaindex"]["base_url"] == base_url, profile
assert profile["clients"]["llamaindex"]["model"] == "diffusiongemma-local", profile
assert profile["clients"]["llamaindex"]["llm_class"] == "llama_index.llms.openai_like.OpenAILike", profile
assert profile["clients"]["llamaindex"]["agent_workflow_class"] == "llama_index.core.agent.workflow.AgentWorkflow", profile
assert profile["clients"]["llamaindex"]["agent_class"] == "llama_index.core.agent.workflow.ReActAgent", profile
assert profile["clients"]["llamaindex"]["function_agent_class"] == "llama_index.core.agent.workflow.FunctionAgent", profile
assert profile["clients"]["llamaindex"]["is_function_calling_model"] is False, profile
assert profile["clients"]["llamaindex"]["tools"] == ["list_files", "read_file", "search_repo"], profile
assert profile["clients"]["haystack"]["base_url"] == base_url, profile
assert profile["clients"]["haystack"]["model"] == "diffusiongemma-local", profile
assert profile["clients"]["haystack"]["document_store"] == "haystack.document_stores.in_memory.InMemoryDocumentStore", profile
assert profile["clients"]["haystack"]["retriever"] == "haystack.components.retrievers.in_memory.InMemoryBM25Retriever", profile
assert profile["clients"]["haystack"]["generator"] == "haystack.components.generators.chat.OpenAIChatGenerator", profile
assert profile["clients"]["haystack"]["top_k"] == 4, profile
assert profile["clients"]["swe_agent"]["base_url"] == base_url, profile
assert profile["clients"]["swe_agent"]["model"] == "openai/diffusiongemma-local", profile
assert profile["clients"]["mini_swe_agent"]["config"].endswith("mini-swe-agent.dg.yaml"), profile

env = (root / "configs/client_profiles/openai.env").read_text(encoding="utf-8")
assert f"OPENAI_BASE_URL={base_url}" in env, env
assert "OPENAI_API_KEY=dummy" in env, env
assert f"OPENAI_MODEL={model}" in env, env
assert f"LLM_BASE_URL=http://127.0.0.1:{port}" in env, env
assert "LLM_MODEL=litellm_proxy/diffusiongemma-local" in env, env
assert "AUTOGEN_MODEL=diffusiongemma-local" in env, env
assert "SMOLAGENTS_MODEL=diffusiongemma-local" in env, env
assert "LANGGRAPH_MODEL=diffusiongemma-local" in env, env
assert "CREWAI_MODEL=openai/diffusiongemma-local" in env, env
assert "OPEN_INTERPRETER_MODEL=openai/diffusiongemma-local" in env, env
assert "LLAMAINDEX_MODEL=diffusiongemma-local" in env, env
assert "HAYSTACK_MODEL=diffusiongemma-local" in env, env
assert "SWE_AGENT_MODEL=openai/diffusiongemma-local" in env, env

continue_yaml = (root / "configs/client_profiles/continue.config.yaml").read_text(encoding="utf-8")
lines = {line.strip() for line in continue_yaml.splitlines()}
required = {
    "schema: v1",
    "provider: openai",
    f"model: {model}",
    f"apiBase: {base_url}",
    "apiKey: dummy",
}
for needle in required:
    assert needle in lines, needle

openhands = (root / "configs/client_profiles/openhands.dg.toml").read_text(encoding="utf-8")
assert 'model = "litellm_proxy/diffusiongemma-local"' in openhands, openhands
assert f'base_url = "http://127.0.0.1:{port}"' in openhands, openhands
assert "drop_params = true" in openhands, openhands

swe = (root / "configs/client_profiles/swe-agent.dg.yaml").read_text(encoding="utf-8")
assert "name: openai/diffusiongemma-local" in swe, swe
assert f"api_base: {base_url}" in swe, swe
assert "type: thought_action" in swe, swe

mini = (root / "configs/client_profiles/mini-swe-agent.dg.yaml").read_text(encoding="utf-8")
assert "model_name: openai/diffusiongemma-local" in mini, mini
assert "cost_tracking: ignore_errors" in mini, mini
assert f"api_base: {base_url}" in mini, mini
mini_profile = yaml.safe_load(mini)
assert set(["agent", "environment", "model"]).issubset(mini_profile), mini_profile
assert "model" not in mini_profile["agent"], mini_profile
assert "environment" not in mini_profile["agent"], mini_profile
assert mini_profile["model"]["model_name"] == "openai/diffusiongemma-local", mini_profile
assert mini_profile["model"]["model_class"] == "litellm_textbased", mini_profile
assert "format_error_template" in mini_profile["model"], mini_profile
assert mini_profile["model"]["model_kwargs"]["api_base"] == base_url, mini_profile
assert mini_profile["environment"]["timeout"] == 480, mini_profile
assert mini_profile["environment"]["env"]["PAGER"] == "cat", mini_profile

registry = json.loads((root / "configs/client_profiles/litellm-local-model-registry.json").read_text(encoding="utf-8"))
assert registry["diffusiongemma-local"]["max_input_tokens"] == 768, registry
assert registry["openai/diffusiongemma-local"]["litellm_provider"] == "openai", registry
PY

echo "Gateway client profiles smoke passed."
