#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_CMD="${PYTHON:-python}"

bash -n "$DG_ROOT/scripts/run_stack_watchdog.sh"
"$DG_ROOT/scripts/run_stack_watchdog.sh" --help-local >/tmp/dg-stack-watchdog-help.txt
grep -F "Watch and recover" /tmp/dg-stack-watchdog-help.txt

"$DG_ROOT/scripts/run_stack_watchdog.sh" status --json >/tmp/dg-stack-watchdog-status.json
"$PY_CMD" -m json.tool /tmp/dg-stack-watchdog-status.json >/dev/null
grep -F '"backend"' /tmp/dg-stack-watchdog-status.json
grep -F '"proxy"' /tmp/dg-stack-watchdog-status.json
grep -F '"litellm"' /tmp/dg-stack-watchdog-status.json

"$DG_ROOT/scripts/run_stack_watchdog.sh" ensure --json --wait-timeout 5 >/tmp/dg-stack-watchdog-ensure.json
"$PY_CMD" -m json.tool /tmp/dg-stack-watchdog-ensure.json >/dev/null
grep -F '"ok": true' /tmp/dg-stack-watchdog-ensure.json

echo "DG stack watchdog smoke passed."
