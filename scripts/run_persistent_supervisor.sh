#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${DG_PERSISTENT_SUPERVISOR_PYTHON:-${DG_AGENT_PYTHON:-$DG_ROOT/.venv-wsl/bin/python}}"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

exec "$PYTHON" "$DG_ROOT/scripts/dg_persistent_supervisor.py" "$@"
