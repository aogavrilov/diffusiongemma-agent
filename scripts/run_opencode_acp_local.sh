#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export OPENCODE_CONFIG="${OPENCODE_MCP_CONFIG:-$DG_ROOT/configs/opencode.dg-mcp.json}"
exec "$DG_ROOT/scripts/run_opencode_local.sh" acp "$@"
