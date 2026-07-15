#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/.bin/opencode"
if [[ "$(uname -s 2>/dev/null || true)" == Linux* && -x "$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode" ]]; then
  OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode"
fi
CONFIG="$DG_ROOT/configs/opencode.dg.json"

test -x "$OPENCODE_BIN"
help_out="$(OPENCODE_CONFIG="$CONFIG" "$OPENCODE_BIN" run --help 2>&1)"
grep -F "run opencode with a message" <<<"$help_out" >/dev/null
grep -F -- "--model" <<<"$help_out" >/dev/null
grep -F -- "--agent" <<<"$help_out" >/dev/null

echo "OpenCode run fallback smoke passed."
