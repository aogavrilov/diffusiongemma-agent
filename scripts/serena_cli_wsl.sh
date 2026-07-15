#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${DG_SERENA_WSL_PYTHON:-/root/diffusiongemma-agent/.venv-wsl/bin/python}"
OVERLAY="${DG_SERENA_OVERLAY:-$DG_ROOT/.venv-serena/Lib/site-packages}"
RUN_CWD="${DG_SERENA_WSL_CWD:-$DG_ROOT}"

cd "$RUN_CWD"
export DG_SERENA_STUB_OPTIONAL_NATIVE="${DG_SERENA_STUB_OPTIONAL_NATIVE:-1}"
export DG_SERENA_OVERLAY="$OVERLAY"
export PATH="$DG_ROOT/scripts/wsl-bin:$DG_ROOT/.tools/pyright/node_modules/.bin:$PATH"

exec "$PYTHON_BIN" "$DG_ROOT/scripts/serena_cli.py" "$@"
