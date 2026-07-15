#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${DG_AGENT_PYTHON:-$DG_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
  if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
    PYTHON="$(command -v python)"
  else
    PYTHON="$(command -v python3 || command -v python)"
  fi
fi

exec "$PYTHON" "$DG_ROOT/scripts/dg_supervisor_agent.py" "$@"
