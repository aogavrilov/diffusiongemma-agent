#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV="$DG_ROOT/.tools/uv/bin/uv"
VENV="$DG_ROOT/.venv-open-interpreter"

if [[ ! -x "$UV" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh"
fi

"$UV" venv "$VENV"
"$UV" pip install --python "$VENV/bin/python" open-interpreter

"$VENV/bin/python" - <<'PY'
from interpreter import interpreter
print("open-interpreter ready")
print(type(interpreter).__name__)
PY
