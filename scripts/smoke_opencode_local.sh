#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/.bin/opencode"
if [[ "$(uname -s 2>/dev/null || true)" == Linux* && -x "$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode" ]]; then
  OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode"
fi
CONFIG="$DG_ROOT/configs/opencode.dg.json"
PYTHON_CMD=()

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import json' >/dev/null 2>&1; then
    PYTHON_CMD=("$candidate")
    break
  fi
done
if [[ "${#PYTHON_CMD[@]}" -eq 0 ]] && command -v py >/dev/null 2>&1 && py -3 -c 'import json' >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
fi
if [[ "${#PYTHON_CMD[@]}" -eq 0 ]]; then
  echo "Python with the stdlib json module is required for OpenCode smoke." >&2
  exit 1
fi

test -x "$OPENCODE_BIN"
"${PYTHON_CMD[@]}" -m json.tool "$CONFIG" >/dev/null
grep -F '"diffusiongemma-local"' "$CONFIG" >/dev/null
grep -F '"baseURL": "http://127.0.0.1:8090/v1"' "$CONFIG" >/dev/null

"$DG_ROOT/scripts/install_opencode_local.sh" >/tmp/dg-opencode-version.txt
grep -E '^1\.17\.20$' /tmp/dg-opencode-version.txt

resolved="$(OPENCODE_CONFIG="$CONFIG" "$DG_ROOT/scripts/run_opencode_local.sh" debug config)"
grep -F '"diffusiongemma-local"' <<<"$resolved" >/dev/null
grep -F '"baseURL": "http://127.0.0.1:8090/v1"' <<<"$resolved" >/dev/null

"$DG_ROOT/scripts/dg_agent.sh" opencode -- --version >/tmp/dg-opencode-dg-version.txt
grep -E '^1\.17\.20$' /tmp/dg-opencode-dg-version.txt

echo "OpenCode provider smoke passed."
