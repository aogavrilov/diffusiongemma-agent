#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-llamaindex.XXXXXX)"
trap 'rm -rf "$TMP_REPO"' EXIT

echo "hello" >"$TMP_REPO/README.md"

test -s "$DG_ROOT/configs/client_profiles/llamaindex.dg.json"
python3 -m json.tool "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" >/dev/null
python3 -m py_compile "$DG_ROOT/scripts/dg_llamaindex_runner.py"

"$DG_ROOT/scripts/dg_llamaindex_runner.py" \
  --repo "$TMP_REPO" \
  --config "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" \
  --dry-run \
  --json >/tmp/dg-llamaindex-dry.json

python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/dg-llamaindex-dry.json").read_text(encoding="utf-8"))
assert data["llm_class"] == "llama_index.llms.openai_like.OpenAILike", data
assert data["agent_workflow_class"] == "llama_index.core.agent.workflow.AgentWorkflow", data
assert data["agent_class"] == "llama_index.core.agent.workflow.ReActAgent", data
assert data["function_agent_class"] == "llama_index.core.agent.workflow.FunctionAgent", data
assert data["selected_agent_class"] == "ReActAgent", data
assert data["llm_kwargs"]["api_base"] == "http://127.0.0.1:4100/v1", data
assert data["llm_kwargs"]["model"] == "diffusiongemma-local", data
assert data["llm_kwargs"]["is_function_calling_model"] is False, data
assert data["tools"] == ["list_files", "read_file", "search_repo"], data
PY

"$DG_ROOT/scripts/run_llamaindex_local.sh" --help-local >/tmp/dg-llamaindex-help.txt
grep -F "LlamaIndex" /tmp/dg-llamaindex-help.txt

echo "LlamaIndex local profile smoke passed."
