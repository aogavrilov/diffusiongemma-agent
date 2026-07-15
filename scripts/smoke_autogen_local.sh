#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-autogen.XXXXXX)"

cleanup() {
  echo "DG AutoGen smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/install_autogen_local.sh"
test -x "$DG_ROOT/scripts/run_autogen_local.sh"
test -x "$DG_ROOT/scripts/dg_autogen_runner.py"
bash -n "$DG_ROOT/scripts/install_autogen_local.sh" "$DG_ROOT/scripts/run_autogen_local.sh"
python3 -m py_compile "$DG_ROOT/scripts/dg_autogen_runner.py"
python3 -m json.tool "$DG_ROOT/configs/client_profiles/autogen.dg.json" >/dev/null

"$DG_ROOT/scripts/install_autogen_local.sh" >/tmp/dg-autogen-install.txt
grep -F "autogen-agentchat ready" /tmp/dg-autogen-install.txt
grep -F "AssistantAgent" /tmp/dg-autogen-install.txt
grep -F "OpenAIChatCompletionClient" /tmp/dg-autogen-install.txt

"$DG_ROOT/scripts/run_autogen_local.sh" --help-local >/tmp/dg-autogen-help.txt
grep -F "AutoGen AgentChat" /tmp/dg-autogen-help.txt

"$DG_ROOT/scripts/run_autogen_local.sh" --repo "$TMP_REPO" --smoke-import >/tmp/dg-autogen-import.txt
grep -F "autogen import ok" /tmp/dg-autogen-import.txt
grep -F "OpenAIChatCompletionClient" /tmp/dg-autogen-import.txt

"$DG_ROOT/scripts/run_autogen_local.sh" --repo "$TMP_REPO" --dry-run --json >/tmp/dg-autogen-dry.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-autogen-dry.json").read_text(encoding="utf-8"))
assert data["model_client"].endswith("OpenAIChatCompletionClient"), data
assert data["model_kwargs"]["base_url"] == "http://127.0.0.1:4100/v1", data
assert data["model_kwargs"]["model"] == "diffusiongemma-local", data
assert data["model_kwargs"]["model_info"]["function_calling"] is False, data
PY

"$DG_ROOT/scripts/dg_agent.sh" autogen -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-autogen-dg-dry.json
grep -F "OpenAIChatCompletionClient" /tmp/dg-autogen-dg-dry.json
grep -F "diffusiongemma-local" /tmp/dg-autogen-dg-dry.json

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-autogen-workspace.json
test -s "$TMP_REPO/.dg-agent/autogen.dg.json"
python3 -m json.tool "$TMP_REPO/.dg-agent/autogen.dg.json" >/dev/null
test -x "$TMP_REPO/.dg-agent/bin/autogen"
bash -n "$TMP_REPO/.dg-agent/bin/autogen"
"$TMP_REPO/.dg-agent/bin/autogen" --smoke-import >/tmp/dg-autogen-workspace-import.txt
grep -F "autogen import ok" /tmp/dg-autogen-workspace-import.txt

echo "DG AutoGen smoke passed."
