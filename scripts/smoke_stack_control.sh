#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_CMD="${PYTHON:-python}"

"$DG_ROOT/scripts/dg_agent.sh" status --json >/tmp/dg-stack-control-status.json
"$PY_CMD" -m json.tool /tmp/dg-stack-control-status.json >/dev/null
grep -F '"status": "watchdog"' /tmp/dg-stack-control-status.json
grep -F '"backend"' /tmp/dg-stack-control-status.json

"$DG_ROOT/scripts/dg_agent.sh" up --json --wait-timeout 5 >/tmp/dg-stack-control-up.json
"$PY_CMD" -m json.tool /tmp/dg-stack-control-up.json >/dev/null
grep -F '"ok": true' /tmp/dg-stack-control-up.json

"$DG_ROOT/scripts/dg_agent.sh" watchdog -- status --json >/tmp/dg-stack-control-watchdog.json
"$PY_CMD" -m json.tool /tmp/dg-stack-control-watchdog.json >/dev/null
grep -F '"proxy"' /tmp/dg-stack-control-watchdog.json

echo "DG stack-control smoke passed."
