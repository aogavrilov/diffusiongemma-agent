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
bash -n "$DG_ROOT/scripts/run_opencode_acp_local.sh"
python3 -m json.tool "$CONFIG" >/dev/null

resolved="$(OPENCODE_CONFIG="$CONFIG" "$DG_ROOT/scripts/run_opencode_local.sh" debug config)"
grep -F '"mcp"' <<<"$resolved" >/dev/null
grep -F '"dg_agent"' <<<"$resolved" >/dev/null
grep -F '"repomix"' <<<"$resolved" >/dev/null

help_out="$("$DG_ROOT/scripts/dg_agent.sh" opencode-acp -- --help 2>&1)"
grep -F 'opencode acp' <<<"$help_out" >/dev/null
grep -F 'start ACP' <<<"$help_out" >/dev/null
grep -F -- '--cwd' <<<"$help_out" >/dev/null
grep -F -- '--port' <<<"$help_out" >/dev/null

echo "OpenCode ACP smoke passed."
