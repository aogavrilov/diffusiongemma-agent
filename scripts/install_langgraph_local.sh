#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="$DG_ROOT/.tools/uv/bin/uv"
VENV="$DG_ROOT/.venv-langgraph"
PYTHON="$VENV/bin/python"
PYTHON_WIN="$VENV/Scripts/python.exe"
VENV_WSL="$DG_ROOT/.venv-langgraph-wsl"
PYTHON_WSL="$VENV_WSL/bin/python"
WHEELHOUSE="$DG_ROOT/.wheelhouse/langgraph-wsl-cp314"
UNAME="$(uname -s 2>/dev/null || true)"

win_to_wsl_path() {
  local value="$1"
  value="${value//\\//}"
  if [[ "$value" =~ ^([A-Za-z]):/(.*)$ ]]; then
    local drive
    drive="$(printf '%s' "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')"
    printf '/mnt/%s/%s' "$drive" "${BASH_REMATCH[2]}"
  else
    printf '%s' "$value"
  fi
}

if [[ "$UNAME" != Linux* ]] && command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1 && [[ -d "$WHEELHOUSE" ]]; then
  export MSYS2_ARG_CONV_EXCL='*'
  export MSYS_NO_PATHCONV=1
  win_root="$(cygpath -am "$DG_ROOT")"
  wsl_root="$(win_to_wsl_path "$win_root")"
  exec wsl.exe bash -lc "cd $(printf '%q' "$wsl_root") && exec ./scripts/install_langgraph_local.sh"
fi

if [[ "$UNAME" == Linux* ]]; then
  if [[ -d "$WHEELHOUSE" ]]; then
    if [[ ! -x "$PYTHON_WSL" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
      python3 -m venv "$VENV_WSL"
    fi
    "$PYTHON_WSL" -m pip install --no-index --find-links "$WHEELHOUSE" "langgraph" "langchain" "langchain-openai"
    PYTHON="$PYTHON_WSL"
  elif [[ ! -x "$UV_BIN" ]]; then
    "$DG_ROOT/scripts/install_uv_local.sh" >/tmp/dg-uv-install.log

    if [[ ! -x "$PYTHON" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
      "$UV_BIN" venv "$VENV" --python 3.12
    fi

    "$UV_BIN" pip install --python "$PYTHON" "langgraph" "langchain" "langchain-openai"
  fi
else
  if [[ ! -x "$PYTHON_WIN" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
    python -m venv "$VENV"
  fi
  "$PYTHON_WIN" -m pip install "langgraph" "langchain" "langchain-openai"
  PYTHON="$PYTHON_WIN"
fi

"$PYTHON" - <<'PY'
from langchain_openai import ChatOpenAI

try:
    from langchain.agents import create_agent as agent_factory
except ImportError:
    from langgraph.prebuilt import create_react_agent as agent_factory

print("langgraph ready")
print(ChatOpenAI.__name__)
print(agent_factory.__name__)
PY
