#!/usr/bin/env bash
set -euo pipefail

export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$PWD}"

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "--help-local" ]]; then
  cat <<'EOF'
Runs the local DiffusionGemma MCP server over streamable HTTP.

Usage:
  scripts/run_mcp_http_server.sh --port 8765
  scripts/run_mcp_http_server.sh --host 127.0.0.1 --port 8765 --path /mcp

Endpoint:
  http://127.0.0.1:8765/mcp

This uses the official modelcontextprotocol Python SDK FastMCP streamable-http
transport and exposes the same tools/resources/prompts as run_mcp_server.sh.
EOF
  exit 0
fi

PYTHON="${DG_AGENT_PYTHON:-$DG_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

exec "$PYTHON" "$DG_ROOT/scripts/dg_mcp_sdk_server.py" --http "$@"
