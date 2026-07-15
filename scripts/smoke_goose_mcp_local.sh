#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d /tmp/dg-goose-mcp-home.XXXXXX)"

cleanup() {
  rm -rf "$TMP_HOME"
}
trap cleanup EXIT

grep -F "dg_agent:" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "enabled: true" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "type: stdio" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_mcp_server.sh" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "serena:" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_serena_mcp.sh" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "timeout: 300" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"

"$DG_ROOT/scripts/run_goose_mcp_local.sh" --help-local | grep -F "Serena semantic"

DG_GOOSE_MCP_HOME="$TMP_HOME" "$DG_ROOT/scripts/run_goose_mcp_local.sh" info -v >/tmp/dg-goose-mcp-info.txt
grep -F "Config yaml:" /tmp/dg-goose-mcp-info.txt
grep -F "$TMP_HOME/.config/goose/config.yaml" /tmp/dg-goose-mcp-info.txt
grep -F "dg_agent:" /tmp/dg-goose-mcp-info.txt
grep -F "serena:" /tmp/dg-goose-mcp-info.txt
grep -F "type: stdio" /tmp/dg-goose-mcp-info.txt
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_mcp_server.sh" /tmp/dg-goose-mcp-info.txt
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_serena_mcp.sh" /tmp/dg-goose-mcp-info.txt

test -s "$TMP_HOME/.config/goose/config.yaml"
cmp -s "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml" "$TMP_HOME/.config/goose/config.yaml"

echo "Goose MCP local profile smoke passed."
