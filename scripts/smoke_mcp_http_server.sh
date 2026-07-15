#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$DG_ROOT/.venv/bin/python"
PORT="${DG_MCP_HTTP_SMOKE_PORT:-18765}"
URL="http://127.0.0.1:$PORT/mcp"
LOG="$(mktemp /tmp/dg-mcp-http-smoke.XXXXXX.log)"

cleanup() {
  if [[ -n "${server_pid:-}" ]]; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

test -x "$PYTHON"
bash -n "$DG_ROOT/scripts/run_mcp_http_server.sh"

"$DG_ROOT/scripts/run_mcp_http_server.sh" --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
server_pid=$!

for _ in $(seq 1 80); do
  http_code="$(curl -sS -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || true)"
  if [[ "$http_code" == "200" || "$http_code" == "400" || "$http_code" == "405" || "$http_code" == "406" ]]; then
    break
  fi
  if ! kill -0 "$server_pid" >/dev/null 2>&1; then
    echo "MCP HTTP server exited early" >&2
    cat "$LOG" >&2 || true
    exit 1
  fi
  sleep 0.25
done

DG_MCP_HTTP_URL="$URL" "$PYTHON" - <<'PY'
import anyio
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> None:
    async with streamablehttp_client(os.environ["DG_MCP_HTTP_URL"]) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            required = {"dg_status", "dg_context", "dg_session", "dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline"}
            missing = sorted(required - names)
            if missing:
                raise SystemExit(f"missing tools: {missing}")


anyio.run(main)
PY

"$DG_ROOT/scripts/dg_agent.sh" mcp-http -- --help-local >/tmp/dg-mcp-http-help.txt 2>&1
grep -F "streamable HTTP" /tmp/dg-mcp-http-help.txt >/dev/null

echo "DG MCP HTTP smoke passed."
