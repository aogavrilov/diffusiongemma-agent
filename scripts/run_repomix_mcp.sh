#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$DG_ROOT/.tools/node-linux/bin/node" ]]; then
  export PATH="$DG_ROOT/.tools/node-linux/bin:$PATH"
elif [[ -x "$DG_ROOT/.tools/node/bin/node" ]]; then
  export PATH="$DG_ROOT/.tools/node/bin:$PATH"
fi

if [[ -x "$DG_ROOT/.tools/repomix/node_modules/.bin/repomix" ]]; then
  exec "$DG_ROOT/.tools/repomix/node_modules/.bin/repomix" --mcp
fi

if command -v npx >/dev/null 2>&1; then
  exec npx --yes repomix --mcp
fi

echo "npx is required for Repomix MCP." >&2
exit 1
