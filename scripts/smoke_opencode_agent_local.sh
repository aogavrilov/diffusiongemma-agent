#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$DG_ROOT/configs/opencode.dg-agent.json"

test -x "$DG_ROOT/.tools/opencode/node_modules/.bin/opencode"
test -x "$DG_ROOT/scripts/run_opencode_agent_local.sh"
bash -n "$DG_ROOT/scripts/run_opencode_agent_local.sh"
python3 -m json.tool "$CONFIG" >/dev/null

grep -F '"bash": true' "$CONFIG" >/dev/null
grep -F '"default_agent": "dg_delegate"' "$CONFIG" >/dev/null
grep -F 'verified local DG workflow' "$CONFIG" >/dev/null

resolved="$(OPENCODE_CONFIG="$CONFIG" "$DG_ROOT/scripts/run_opencode_agent_local.sh" debug config)"
grep -F '"diffusiongemma-local"' <<<"$resolved" >/dev/null
grep -F '"default_agent": "dg_delegate"' <<<"$resolved" >/dev/null

version="$("$DG_ROOT/scripts/run_opencode_agent_local.sh" --version)"
grep -E '^1\.17\.20$' <<<"$version" >/dev/null

echo "OpenCode compact delegate profile smoke passed."
