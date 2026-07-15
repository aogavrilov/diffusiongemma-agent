#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-openhands-acp.XXXXXX)"

cleanup() {
  echo "DG OpenHands ACP smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-openhands-acp-workspace.json

test -x "$DG_ROOT/scripts/run_openhands_acp_local.sh"
bash -n "$DG_ROOT/scripts/run_openhands_acp_local.sh"
"$DG_ROOT/scripts/run_openhands_acp_local.sh" --help-local >/tmp/dg-openhands-acp-help.txt
"$DG_ROOT/scripts/run_openhands_acp_local.sh" --repo "$TMP_REPO" --dry-run >/tmp/dg-openhands-acp-dry.txt
"$DG_ROOT/scripts/run_openhands_acp_local.sh" --repo "$TMP_REPO" -- --help >/tmp/dg-openhands-acp-upstream-help.txt

grep -F "OpenHands as an ACP stdio agent server" /tmp/dg-openhands-acp-help.txt
grep -F "openhands" /tmp/dg-openhands-acp-dry.txt
grep -F " acp " /tmp/dg-openhands-acp-dry.txt
grep -F -- "--override-with-envs" /tmp/dg-openhands-acp-dry.txt
grep -F "litellm_proxy/diffusiongemma-local" /tmp/dg-openhands-acp-dry.txt
grep -F "usage: openhands acp" /tmp/dg-openhands-acp-upstream-help.txt

"$DG_ROOT/scripts/dg_agent.sh" openhands-acp -- --repo "$TMP_REPO" --dry-run >/tmp/dg-openhands-acp-dg-dry.txt
grep -F " acp " /tmp/dg-openhands-acp-dg-dry.txt
grep -F -- "--override-with-envs" /tmp/dg-openhands-acp-dg-dry.txt

test -x "$TMP_REPO/.dg-agent/bin/openhands-acp"
bash -n "$TMP_REPO/.dg-agent/bin/openhands-acp"
"$TMP_REPO/.dg-agent/bin/openhands-acp" --dry-run >/tmp/dg-openhands-acp-workspace-dry.txt
grep -F " acp " /tmp/dg-openhands-acp-workspace-dry.txt
grep -F -- "--override-with-envs" /tmp/dg-openhands-acp-workspace-dry.txt

"$DG_ROOT/scripts/dg_agent.sh" agent-bridge \
  --repo "$TMP_REPO" \
  --server openhands-acp \
  --no-init \
  --json >/tmp/dg-openhands-acp-bridge.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-openhands-acp-bridge.json").read_text(encoding="utf-8"))
assert data["status"] == "ready", data
assert data["server"] == "openhands-acp", data
assert data["connect"]["transport"] == "stdio", data
assert data["connect"]["profile"] == "openhands_acp", data
assert "openhands-acp" in data["command"], data
PY

echo "DG OpenHands ACP smoke passed."
