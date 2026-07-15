#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d /tmp/dg-goose-acp-home.XXXXXX)"

cleanup() {
  rm -rf "$TMP_HOME"
}
trap cleanup EXIT

"$DG_ROOT/scripts/run_goose_mcp_local.sh" --help-local | grep -F -- "--acp"
"$DG_ROOT/scripts/run_goose_mcp_local.sh" --help-local | grep -F -- "--serve"

DG_GOOSE_MCP_HOME="$TMP_HOME" "$DG_ROOT/scripts/run_goose_mcp_local.sh" --acp --help >/tmp/dg-goose-acp-help.txt
grep -F "Run goose as an ACP agent server on stdio" /tmp/dg-goose-acp-help.txt

DG_GOOSE_MCP_HOME="$TMP_HOME" "$DG_ROOT/scripts/run_goose_mcp_local.sh" --serve --help >/tmp/dg-goose-serve-help.txt
grep -F "Start ACP server over HTTP and WebSocket" /tmp/dg-goose-serve-help.txt
grep -F -- "--port" /tmp/dg-goose-serve-help.txt

DG_GOOSE_MCP_HOME="$TMP_HOME" "$DG_ROOT/scripts/dg_agent.sh" goose-acp -- --help >/tmp/dg-agent-goose-acp-help.txt
grep -F "Run goose as an ACP agent server on stdio" /tmp/dg-agent-goose-acp-help.txt

DG_GOOSE_MCP_HOME="$TMP_HOME" "$DG_ROOT/scripts/dg_agent.sh" goose-serve -- --help >/tmp/dg-agent-goose-serve-help.txt
grep -F "Start ACP server over HTTP and WebSocket" /tmp/dg-agent-goose-serve-help.txt

test -s "$TMP_HOME/.config/goose/config.yaml"
grep -F "dg_agent:" "$TMP_HOME/.config/goose/config.yaml"
grep -F "serena:" "$TMP_HOME/.config/goose/config.yaml"

echo "Goose ACP local launchers smoke passed."
