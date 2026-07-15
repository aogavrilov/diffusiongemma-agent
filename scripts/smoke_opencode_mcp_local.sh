#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${OS:-}" == "Windows_NT" ]] && command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
  win_script="$(cygpath -am "$0")"
  wsl_script="$(wsl.exe wslpath -a "$win_script" | sed 's/\r$//')"
  exec env MSYS2_ARG_CONV_EXCL='*' wsl.exe bash "$wsl_script"
fi

OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/.bin/opencode"
CONFIG="$DG_ROOT/configs/opencode.dg-mcp.json"
if [[ -x "$DG_ROOT/.tools/node-linux/bin/node" ]]; then
  export PATH="$DG_ROOT/.tools/node-linux/bin:$PATH"
fi

test -x "$OPENCODE_BIN"
python3 -m json.tool "$CONFIG" >/dev/null
grep -F '"mcp"' "$CONFIG" >/dev/null
grep -F '"dg_agent"' "$CONFIG" >/dev/null
grep -F '"repomix"' "$CONFIG" >/dev/null
grep -F 'run_mcp_server.sh' "$CONFIG" >/dev/null
grep -F 'run_repomix_mcp.sh' "$CONFIG" >/dev/null
if grep -F '"mcpServers"' "$CONFIG" >/dev/null; then
  echo "opencode.dg-mcp.json uses obsolete mcpServers key" >&2
  exit 1
fi

resolved="$(OPENCODE_CONFIG="$CONFIG" "$DG_ROOT/scripts/run_opencode_local.sh" debug config)"
grep -F '"mcp"' <<<"$resolved" >/dev/null
grep -F '"type": "local"' <<<"$resolved" >/dev/null
grep -F '"environment"' <<<"$resolved" >/dev/null

linux_payload="$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode"
opencode_payload="$DG_ROOT/.tools/opencode/node_modules/opencode-ai/bin/opencode.exe"
if [[ ! -x "$linux_payload" ]] && command -v file >/dev/null 2>&1 && file "$opencode_payload" | grep -F "PE32" >/dev/null; then
  echo "OpenCode MCP live list skipped: installed OpenCode payload is Windows PE; install opencode-linux-x64 for WSL MCP process spawning."
  echo "OpenCode MCP config smoke passed."
  exit 0
fi

list_out="$(timeout 60s env OPENCODE_CONFIG="$CONFIG" "$DG_ROOT/scripts/run_opencode_local.sh" mcp list 2>&1)"
grep -F 'dg_agent' <<<"$list_out" >/dev/null
grep -F 'repomix' <<<"$list_out" >/dev/null
grep -F 'connected' <<<"$list_out" >/dev/null
if grep -F 'failed' <<<"$list_out" >/dev/null; then
  echo "$list_out" >&2
  exit 1
fi

echo "OpenCode MCP smoke passed."
