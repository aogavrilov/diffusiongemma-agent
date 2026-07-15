#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-crewai.XXXXXX)"

cleanup() {
  echo "DG CrewAI smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/install_crewai_local.sh"
test -x "$DG_ROOT/scripts/run_crewai_local.sh"
test -x "$DG_ROOT/scripts/dg_crewai_runner.py"
bash -n "$DG_ROOT/scripts/install_crewai_local.sh" "$DG_ROOT/scripts/run_crewai_local.sh"
python3 -m py_compile "$DG_ROOT/scripts/dg_crewai_runner.py"
python3 -m json.tool "$DG_ROOT/configs/client_profiles/crewai.dg.json" >/dev/null

"$DG_ROOT/scripts/install_crewai_local.sh" >/tmp/dg-crewai-install.txt
grep -F "crewai ready" /tmp/dg-crewai-install.txt
grep -F "Agent" /tmp/dg-crewai-install.txt
grep -F "Task" /tmp/dg-crewai-install.txt
grep -F "Crew" /tmp/dg-crewai-install.txt
grep -F "LLM" /tmp/dg-crewai-install.txt

"$DG_ROOT/scripts/run_crewai_local.sh" --help-local >/tmp/dg-crewai-help.txt
grep -F "CrewAI" /tmp/dg-crewai-help.txt

"$DG_ROOT/scripts/run_crewai_local.sh" --repo "$TMP_REPO" --smoke-import >/tmp/dg-crewai-import.txt
grep -F "crewai import ok" /tmp/dg-crewai-import.txt
grep -F "Agent" /tmp/dg-crewai-import.txt
grep -F "LLM" /tmp/dg-crewai-import.txt

"$DG_ROOT/scripts/run_crewai_local.sh" --repo "$TMP_REPO" --dry-run --json >/tmp/dg-crewai-dry.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-crewai-dry.json").read_text(encoding="utf-8"))
assert data["classes"]["crew"] == "crewai.Crew", data
assert data["classes"]["llm"] == "crewai.LLM", data
assert data["llm_kwargs"]["base_url"] == "http://127.0.0.1:4100/v1", data
assert data["llm_kwargs"]["model"] == "openai/diffusiongemma-local", data
PY

"$DG_ROOT/scripts/dg_agent.sh" crewai -- --repo "$TMP_REPO" --dry-run --json >/tmp/dg-crewai-dg-dry.json
grep -F "crewai.Crew" /tmp/dg-crewai-dg-dry.json
grep -F "openai/diffusiongemma-local" /tmp/dg-crewai-dg-dry.json

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-crewai-workspace.json
test -s "$TMP_REPO/.dg-agent/crewai.dg.json"
python3 -m json.tool "$TMP_REPO/.dg-agent/crewai.dg.json" >/dev/null
test -x "$TMP_REPO/.dg-agent/bin/crewai"
bash -n "$TMP_REPO/.dg-agent/bin/crewai"
"$TMP_REPO/.dg-agent/bin/crewai" --smoke-import >/tmp/dg-crewai-workspace-import.txt
grep -F "crewai import ok" /tmp/dg-crewai-workspace-import.txt

echo "DG CrewAI smoke passed."
