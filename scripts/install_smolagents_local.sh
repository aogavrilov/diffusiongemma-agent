#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="$DG_ROOT/.tools/uv/bin/uv"
VENV="$DG_ROOT/.venv-smolagents"
PYTHON="$VENV/bin/python"

if [[ ! -x "$UV_BIN" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh" >/tmp/dg-uv-install.log
fi

if [[ ! -x "$PYTHON" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  "$UV_BIN" venv "$VENV" --python 3.12
fi

"$UV_BIN" pip install --python "$PYTHON" "smolagents[toolkit]" "openai"

"$PYTHON" - <<'PY'
from smolagents import CodeAgent

try:
    from smolagents import OpenAIModel as ModelClass
except ImportError:
    from smolagents import OpenAIServerModel as ModelClass

print("smolagents ready")
print(CodeAgent.__name__)
print(ModelClass.__name__)
PY
