#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-smolagents.XXXXXX)"

cleanup() {
  echo "DG smolagents smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/install_smolagents_local.sh"
test -x "$DG_ROOT/scripts/run_smolagents_local.sh"
test -x "$DG_ROOT/scripts/dg_smolagents_runner.py"
bash -n "$DG_ROOT/scripts/install_smolagents_local.sh" "$DG_ROOT/scripts/run_smolagents_local.sh"
python3 -m py_compile "$DG_ROOT/scripts/dg_smolagents_runner.py"
python3 -m json.tool "$DG_ROOT/configs/client_profiles/smolagents.dg.json" >/dev/null

"$DG_ROOT/scripts/install_smolagents_local.sh" >/tmp/dg-smolagents-install.txt
grep -F "smolagents ready" /tmp/dg-smolagents-install.txt
grep -F "CodeAgent" /tmp/dg-smolagents-install.txt
grep -E "OpenAI(Model|ServerModel)" /tmp/dg-smolagents-install.txt

"$DG_ROOT/scripts/run_smolagents_local.sh" --help-local >/tmp/dg-smolagents-help.txt
grep -F "smolagents CodeAgent" /tmp/dg-smolagents-help.txt

"$DG_ROOT/scripts/run_smolagents_local.sh" --repo "$TMP_REPO" --smoke-import >/tmp/dg-smolagents-import.txt
grep -F "smolagents import ok" /tmp/dg-smolagents-import.txt
grep -F "CodeAgent" /tmp/dg-smolagents-import.txt

"$DG_ROOT/scripts/run_smolagents_local.sh" --repo "$TMP_REPO" --dry-run --json >/tmp/dg-smolagents-dry.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-smolagents-dry.json").read_text(encoding="utf-8"))
assert data["agent"].endswith("CodeAgent"), data
assert data["model_class"].endswith("OpenAIModel"), data
assert data["model_kwargs"]["api_base"] == "http://127.0.0.1:4100/v1", data
assert data["model_kwargs"]["model_id"] == "diffusiongemma-local", data
assert data["max_steps"] == 2, data
PY

"$DG_ROOT/scripts/dg_agent.sh" smolagents -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-smolagents-dg-dry.json
grep -F "CodeAgent" /tmp/dg-smolagents-dg-dry.json
grep -F "diffusiongemma-local" /tmp/dg-smolagents-dg-dry.json

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-smolagents-workspace.json
test -s "$TMP_REPO/.dg-agent/smolagents.dg.json"
python3 -m json.tool "$TMP_REPO/.dg-agent/smolagents.dg.json" >/dev/null
test -x "$TMP_REPO/.dg-agent/bin/smolagents"
bash -n "$TMP_REPO/.dg-agent/bin/smolagents"
"$TMP_REPO/.dg-agent/bin/smolagents" --smoke-import >/tmp/dg-smolagents-workspace-import.txt
grep -F "smolagents import ok" /tmp/dg-smolagents-workspace-import.txt

echo "DG smolagents smoke passed."
