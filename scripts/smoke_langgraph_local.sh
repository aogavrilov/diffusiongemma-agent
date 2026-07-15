#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-langgraph.XXXXXX)"
PYTHON_CMD=()

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import json' >/dev/null 2>&1; then
    PYTHON_CMD=("$candidate")
    break
  fi
done
if [[ "${#PYTHON_CMD[@]}" -eq 0 ]] && command -v py >/dev/null 2>&1 && py -3 -c 'import json' >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
fi
if [[ "${#PYTHON_CMD[@]}" -eq 0 ]]; then
  echo "Python with the stdlib json module is required for LangGraph smoke." >&2
  exit 1
fi

host_path() {
  if [[ "$(uname -s 2>/dev/null || true)" != Linux* ]] && command -v cygpath >/dev/null 2>&1; then
    cygpath -aw "$1"
  else
    printf '%s' "$1"
  fi
}

cleanup() {
  echo "DG LangGraph smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/install_langgraph_local.sh"
test -x "$DG_ROOT/scripts/run_langgraph_local.sh"
test -x "$DG_ROOT/scripts/dg_langgraph_runner.py"
bash -n "$DG_ROOT/scripts/install_langgraph_local.sh" "$DG_ROOT/scripts/run_langgraph_local.sh"
"${PYTHON_CMD[@]}" -m py_compile "$DG_ROOT/scripts/dg_langgraph_runner.py"
"${PYTHON_CMD[@]}" -m json.tool "$DG_ROOT/configs/client_profiles/langgraph.dg.json" >/dev/null

"$DG_ROOT/scripts/install_langgraph_local.sh" >/tmp/dg-langgraph-install.txt
grep -F "langgraph ready" /tmp/dg-langgraph-install.txt
grep -F "ChatOpenAI" /tmp/dg-langgraph-install.txt
grep -E "create_(agent|react_agent)" /tmp/dg-langgraph-install.txt

"$DG_ROOT/scripts/run_langgraph_local.sh" --help-local >/tmp/dg-langgraph-help.txt
grep -F "LangGraph/LangChain" /tmp/dg-langgraph-help.txt

"$DG_ROOT/scripts/run_langgraph_local.sh" --repo "$TMP_REPO" --smoke-import >/tmp/dg-langgraph-import.txt
grep -F "langgraph import ok" /tmp/dg-langgraph-import.txt
grep -F "ChatOpenAI" /tmp/dg-langgraph-import.txt

"$DG_ROOT/scripts/run_langgraph_local.sh" --repo "$TMP_REPO" --dry-run --json >/tmp/dg-langgraph-dry.json
"${PYTHON_CMD[@]}" - "$(host_path /tmp/dg-langgraph-dry.json)" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["model_class"].endswith("ChatOpenAI"), data
assert data["model_kwargs"]["base_url"] == "http://127.0.0.1:4100/v1", data
assert data["model_kwargs"]["model"] == "diffusiongemma-local", data
assert data["agent_factory"].endswith(("create_agent", "create_react_agent")), data
PY

"$DG_ROOT/scripts/dg_agent.sh" langgraph -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-langgraph-dg-dry.json
grep -F "ChatOpenAI" /tmp/dg-langgraph-dg-dry.json
grep -F "diffusiongemma-local" /tmp/dg-langgraph-dg-dry.json

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-langgraph-workspace.json
test -s "$TMP_REPO/.dg-agent/langgraph.dg.json"
"${PYTHON_CMD[@]}" -m json.tool "$(host_path "$TMP_REPO/.dg-agent/langgraph.dg.json")" >/dev/null
test -x "$TMP_REPO/.dg-agent/bin/langgraph"
bash -n "$TMP_REPO/.dg-agent/bin/langgraph"
"$TMP_REPO/.dg-agent/bin/langgraph" --smoke-import >/tmp/dg-langgraph-workspace-import.txt
grep -F "langgraph import ok" /tmp/dg-langgraph-workspace-import.txt

echo "DG LangGraph smoke passed."
