#!/usr/bin/env bash
set -euo pipefail

export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$PWD}"

cd "$(dirname "$0")/.."

if [[ -n "${DG_AGENT_PYTHON:-}" && -x "${DG_AGENT_PYTHON}" ]]; then
  exec "${DG_AGENT_PYTHON}" scripts/dg_agent.py "$@"
fi

# WSL must not fall through to the Windows .exe below: doing so makes the
# supervisor launch the Linux Aider runner through Windows process semantics.
if [[ "$(uname -s 2>/dev/null || true)" == "Linux" ]]; then
  WSL_AGENT_PYTHON="${DG_WSL_AGENT_PYTHON:-/root/diffusiongemma-agent/.venv-wsl/bin/python}"
  if [[ -x "${WSL_AGENT_PYTHON}" ]]; then
    export DG_AGENT_PYTHON="${WSL_AGENT_PYTHON}"
    exec "${WSL_AGENT_PYTHON}" scripts/dg_agent.py "$@"
  fi
fi

if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python scripts/dg_agent.py "$@"
fi

if [[ -x .venv/Scripts/python.exe ]]; then
  exec .venv/Scripts/python.exe scripts/dg_agent.py "$@"
fi

if command -v python >/dev/null 2>&1 && python -c 'import sys' >/dev/null 2>&1; then
  exec python scripts/dg_agent.py "$@"
fi

exec python3 scripts/dg_agent.py "$@"
