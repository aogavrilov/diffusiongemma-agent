#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${DG_AGENT_PYTHON:-/root/diffusiongemma-agent/.venv-wsl/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "DG_AGENT_PYTHON is not executable: $PYTHON_BIN" >&2
  exit 2
fi

export DG_AIDER_BACKEND_BASE="${DG_AIDER_BACKEND_BASE:-http://127.0.0.1:4100/v1}"
export DG_AIDER_BACKEND_MODEL="${DG_AIDER_BACKEND_MODEL:-diffusiongemma-26b-a4b-it-iq3m-fullgpu}"
export DG_AIDER_PROXY_HOST="${DG_AIDER_PROXY_HOST:-127.0.0.1}"
export DG_AIDER_PROXY_PORT="${DG_AIDER_PROXY_PORT:-8090}"
export DG_AGENT_PYTHON="$PYTHON_BIN"

exec "$PYTHON_BIN" "$DG_ROOT/scripts/aider_dg_proxy.py"
