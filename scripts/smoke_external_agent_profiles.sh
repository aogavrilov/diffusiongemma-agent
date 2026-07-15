#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-external-agent-smoke.XXXXXX)"

cleanup() {
  echo "DG external agent smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-external-workspace.json

for script in run_openhands_local.sh run_qwen_code_local.sh run_autogen_local.sh run_smolagents_local.sh run_langgraph_local.sh run_crewai_local.sh run_open_interpreter_local.sh run_llamaindex_local.sh run_haystack_local.sh run_swe_agent_local.sh run_mini_swe_agent_local.sh; do
  test -x "$DG_ROOT/scripts/$script"
  bash -n "$DG_ROOT/scripts/$script"
  "$DG_ROOT/scripts/$script" --help-local >/tmp/dg-$script.help
done

for script in install_uv_local.sh install_openhands_local.sh install_qwen_code_local.sh install_autogen_local.sh install_smolagents_local.sh install_langgraph_local.sh install_crewai_local.sh install_open_interpreter_local.sh install_llamaindex_local.sh install_haystack_local.sh install_swe_agent_local.sh install_mini_swe_agent_local.sh; do
  test -x "$DG_ROOT/scripts/$script"
  bash -n "$DG_ROOT/scripts/$script"
done

grep -F "OpenHands" /tmp/dg-run_openhands_local.sh.help
grep -F "Qwen Code" /tmp/dg-run_qwen_code_local.sh.help
grep -F "AutoGen AgentChat" /tmp/dg-run_autogen_local.sh.help
grep -F "smolagents CodeAgent" /tmp/dg-run_smolagents_local.sh.help
grep -F "LangGraph/LangChain" /tmp/dg-run_langgraph_local.sh.help
grep -F "CrewAI" /tmp/dg-run_crewai_local.sh.help
grep -F "Open Interpreter" /tmp/dg-run_open_interpreter_local.sh.help
grep -F "LlamaIndex" /tmp/dg-run_llamaindex_local.sh.help
grep -F "Haystack BM25 RAG" /tmp/dg-run_haystack_local.sh.help
grep -F "SWE-agent" /tmp/dg-run_swe_agent_local.sh.help
grep -F "mini-swe-agent" /tmp/dg-run_mini_swe_agent_local.sh.help

"$DG_ROOT/scripts/dg_agent.sh" openhands -- --repo "$TMP_REPO" --task "inspect calc.py" --dry-run >/tmp/dg-openhands-dry.txt
"$DG_ROOT/scripts/dg_agent.sh" qwen-code -- --repo "$TMP_REPO" --dry-run -- --help >/tmp/dg-qwen-code-dry.txt
"$DG_ROOT/scripts/dg_agent.sh" autogen -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-autogen-dry.json
"$DG_ROOT/scripts/dg_agent.sh" smolagents -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-smolagents-dry.json
"$DG_ROOT/scripts/dg_agent.sh" langgraph -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-langgraph-dry.json
"$DG_ROOT/scripts/dg_agent.sh" crewai -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-crewai-dry.json
"$DG_ROOT/scripts/dg_agent.sh" open-interpreter -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-open-interpreter-dry.json
"$DG_ROOT/scripts/dg_agent.sh" llamaindex -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-llamaindex-dry.json
"$DG_ROOT/scripts/dg_agent.sh" haystack -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-haystack-dry.json
"$DG_ROOT/scripts/dg_agent.sh" swe-agent -- --repo "$TMP_REPO" --task "inspect calc.py" --dry-run >/tmp/dg-swe-dry.txt
"$DG_ROOT/scripts/dg_agent.sh" mini-swe-agent -- --repo "$TMP_REPO" --task "inspect calc.py" --dry-run >/tmp/dg-mini-swe-dry.txt
"$DG_ROOT/scripts/dg_agent.sh" mini-swe-run \
  --repo "$TMP_REPO" \
  --task "Inspect calc.py without changing files." \
  --out-dir "$TMP_REPO/.dg-agent/mini-swe-runs" \
  --dry-run \
  --json >/tmp/dg-external-mini-swe-run.json

grep -E "litellm_proxy/diffusiongemma-local|command:" /tmp/dg-openhands-dry.txt
grep -E "diffusiongemma-local|qwen-code.mcp.json|command:" /tmp/dg-qwen-code-dry.txt
grep -E "diffusiongemma-local|OpenAIChatCompletionClient|command" /tmp/dg-autogen-dry.json
grep -E "diffusiongemma-local|CodeAgent|command" /tmp/dg-smolagents-dry.json
grep -E "diffusiongemma-local|ChatOpenAI|command" /tmp/dg-langgraph-dry.json
grep -E "openai/diffusiongemma-local|crewai.Crew|command" /tmp/dg-crewai-dry.json
grep -E "openai/diffusiongemma-local|interpreter.interpreter|command" /tmp/dg-open-interpreter-dry.json
grep -E "diffusiongemma-local|OpenAILike|AgentWorkflow|ReActAgent|command" /tmp/dg-llamaindex-dry.json
grep -E "diffusiongemma-local|OpenAIChatGenerator|InMemoryBM25Retriever|command" /tmp/dg-haystack-dry.json
grep -E "openai/diffusiongemma-local|swe-agent.dg.yaml|command:" /tmp/dg-swe-dry.txt
grep -E "mini-swe-agent.dg.yaml|command:" /tmp/dg-mini-swe-dry.txt
if [[ -x "$DG_ROOT/.tools/external-agents/bin/mini" ]]; then
  grep -F "$DG_ROOT/.tools/external-agents/bin/mini" /tmp/dg-mini-swe-dry.txt
fi
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-external-mini-swe-run.json").read_text(encoding="utf-8"))
assert data["status"] == "dry-run", data
assert data["repo"].startswith("/tmp/dg-external-agent-smoke."), data
assert data["run_dir"].endswith(".dg-agent/mini-swe-runs"), data
assert data["command_file"].endswith("command.sh"), data
assert Path(data["run_dir"], "report.json").exists(), data
assert Path(data["command_file"]).exists(), data
PY

for launcher in openhands qwen-code autogen smolagents langgraph crewai open-interpreter llamaindex haystack swe-agent mini-swe-agent; do
  test -x ".dg-agent/bin/$launcher"
  bash -n ".dg-agent/bin/$launcher"
  ".dg-agent/bin/$launcher" --help-local >/tmp/dg-workspace-$launcher.help
done
for launcher in mini-swe-run mini-swe-runs; do
  test -x ".dg-agent/bin/$launcher"
  bash -n ".dg-agent/bin/$launcher"
  ".dg-agent/bin/$launcher" --help >/tmp/dg-workspace-$launcher.help
done

grep -F "OpenHands" /tmp/dg-workspace-openhands.help
grep -F "Qwen Code" /tmp/dg-workspace-qwen-code.help
grep -F "AutoGen AgentChat" /tmp/dg-workspace-autogen.help
grep -F "smolagents CodeAgent" /tmp/dg-workspace-smolagents.help
grep -F "LangGraph/LangChain" /tmp/dg-workspace-langgraph.help
grep -F "CrewAI" /tmp/dg-workspace-crewai.help
grep -F "Open Interpreter" /tmp/dg-workspace-open-interpreter.help
grep -F "LlamaIndex" /tmp/dg-workspace-llamaindex.help
grep -F "Haystack BM25 RAG" /tmp/dg-workspace-haystack.help
grep -F "SWE-agent" /tmp/dg-workspace-swe-agent.help
grep -F "mini-swe-agent" /tmp/dg-workspace-mini-swe-agent.help
".dg-agent/bin/mini-swe-runs" list --root "$TMP_REPO/.dg-agent/mini-swe-runs" --json >/tmp/dg-external-mini-swe-runs-list.json
".dg-agent/bin/mini-swe-runs" show --root "$TMP_REPO/.dg-agent/mini-swe-runs" --latest --json >/tmp/dg-external-mini-swe-runs-show.json
".dg-agent/bin/mini-swe-runs" artifact command --root "$TMP_REPO/.dg-agent/mini-swe-runs" --latest --path-only >/tmp/dg-external-mini-swe-command-path.txt
python3 - <<'PY'
import json
from pathlib import Path

listed = json.loads(Path("/tmp/dg-external-mini-swe-runs-list.json").read_text(encoding="utf-8"))
shown = json.loads(Path("/tmp/dg-external-mini-swe-runs-show.json").read_text(encoding="utf-8"))
command_path = Path("/tmp/dg-external-mini-swe-command-path.txt").read_text(encoding="utf-8").strip()
assert len(listed["runs"]) == 1, listed
assert listed["runs"][0]["status"] == "dry-run", listed
assert shown["status"] == "dry-run", shown
assert command_path.endswith("command.sh"), command_path
assert Path(command_path).exists(), command_path
PY

echo "DG external agent profiles smoke passed."
