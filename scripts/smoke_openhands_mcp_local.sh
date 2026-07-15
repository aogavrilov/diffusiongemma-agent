#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-openhands-mcp.XXXXXX)"

cleanup() {
  echo "DG OpenHands MCP smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-openhands-mcp-workspace.json

test -x "$DG_ROOT/scripts/run_openhands_mcp_setup.sh"
bash -n "$DG_ROOT/scripts/run_openhands_mcp_setup.sh"
"$DG_ROOT/scripts/run_openhands_mcp_setup.sh" --help-local >/tmp/dg-openhands-mcp-help.txt
"$DG_ROOT/scripts/run_openhands_mcp_setup.sh" --repo "$TMP_REPO" --dry-run >/tmp/dg-openhands-mcp-dry.txt

grep -F "Configure OpenHands MCP servers" /tmp/dg-openhands-mcp-help.txt
grep -F "diffusiongemma-local-agent" /tmp/dg-openhands-mcp-dry.txt
grep -F "repomix" /tmp/dg-openhands-mcp-dry.txt
grep -F "serena" /tmp/dg-openhands-mcp-dry.txt
grep -F "$TMP_REPO/.dg-agent/openhands-persistence/mcp.json" /tmp/dg-openhands-mcp-dry.txt

"$DG_ROOT/scripts/run_openhands_mcp_setup.sh" --repo "$TMP_REPO" --reset >/tmp/dg-openhands-mcp-setup.txt

CONFIG="$TMP_REPO/.dg-agent/openhands-persistence/mcp.json"
test -s "$CONFIG"
CONFIG="$CONFIG" TMP_REPO="$TMP_REPO" DG_ROOT="$DG_ROOT" python3 - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["CONFIG"]).read_text(encoding="utf-8"))
servers = config["mcpServers"]
assert set(servers) == {"diffusiongemma-local-agent", "repomix", "serena"}, servers

dg = servers["diffusiongemma-local-agent"]
assert dg["transport"] == "stdio", dg
assert dg["command"] == f'{os.environ["DG_ROOT"]}/scripts/run_mcp_server.sh', dg
assert dg["args"] == [], dg
assert dg["env"]["DG_MCP_REPO"] == os.environ["TMP_REPO"], dg
assert dg["env"]["DG_AGENT_CALLER_CWD"] == os.environ["TMP_REPO"], dg
assert dg["enabled"] is True, dg

repomix = servers["repomix"]
assert repomix["transport"] == "stdio", repomix
assert repomix["command"] == f'{os.environ["DG_ROOT"]}/scripts/run_repomix_mcp.sh', repomix
assert repomix["args"] == [], repomix
assert repomix["enabled"] is True, repomix

serena = servers["serena"]
assert serena["transport"] == "stdio", serena
assert serena["command"] == f'{os.environ["DG_ROOT"]}/scripts/run_serena_mcp.sh', serena
assert serena["args"] == ["--project", os.environ["TMP_REPO"]], serena
assert serena["enabled"] is True, serena
PY

OPENHANDS_BIN="${OPENHANDS_BIN:-$DG_ROOT/.tools/external-agents/bin/openhands}"
OPENHANDS_PERSISTENCE_DIR="$TMP_REPO/.dg-agent/openhands-persistence" \
OPENHANDS_SUPPRESS_BANNER=1 \
PYTHONWARNINGS=ignore \
"$OPENHANDS_BIN" mcp list >/tmp/dg-openhands-mcp-list.txt
grep -F "diffusiongemma-local-agent" /tmp/dg-openhands-mcp-list.txt
grep -F "repomix" /tmp/dg-openhands-mcp-list.txt
grep -F "serena" /tmp/dg-openhands-mcp-list.txt

for server in diffusiongemma-local-agent repomix serena; do
  OPENHANDS_PERSISTENCE_DIR="$TMP_REPO/.dg-agent/openhands-persistence" \
  OPENHANDS_SUPPRESS_BANNER=1 \
  PYTHONWARNINGS=ignore \
  "$OPENHANDS_BIN" mcp get "$server" >/tmp/dg-openhands-mcp-get-"$server".txt
  grep -F "MCP server '$server'" /tmp/dg-openhands-mcp-get-"$server".txt
done

"$DG_ROOT/scripts/dg_agent.sh" openhands-mcp -- --repo "$TMP_REPO" --dry-run >/tmp/dg-openhands-mcp-dg-dry.txt
grep -F "diffusiongemma-local-agent" /tmp/dg-openhands-mcp-dg-dry.txt
grep -F "serena" /tmp/dg-openhands-mcp-dg-dry.txt

test -x "$TMP_REPO/.dg-agent/bin/openhands-mcp"
bash -n "$TMP_REPO/.dg-agent/bin/openhands-mcp"
"$TMP_REPO/.dg-agent/bin/openhands-mcp" --reset >/tmp/dg-openhands-mcp-workspace-setup.txt
test -s "$CONFIG"

echo "DG OpenHands MCP smoke passed."
