#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$DG_ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$DG_ROOT/.venv"
  PYTHON="$DG_ROOT/.venv/bin/python"
fi

"$PYTHON" -m pip install --upgrade 'mcp>=1.12,<2'
"$PYTHON" - <<'PY'
import importlib.metadata

print("mcp", importlib.metadata.version("mcp"))
PY
