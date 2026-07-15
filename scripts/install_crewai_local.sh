#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="$DG_ROOT/.tools/uv/bin/uv"
VENV="$DG_ROOT/.venv-crewai"
PYTHON="$VENV/bin/python"

if [[ ! -x "$UV_BIN" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh" >/tmp/dg-uv-install.log
fi

if [[ ! -x "$PYTHON" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  "$UV_BIN" venv "$VENV" --python 3.12
fi

"$UV_BIN" pip install --python "$PYTHON" "crewai"

"$PYTHON" - <<'PY'
from crewai import Agent, Crew, LLM, Task

print("crewai ready")
print(Agent.__name__)
print(Task.__name__)
print(Crew.__name__)
print(LLM.__name__)
PY
