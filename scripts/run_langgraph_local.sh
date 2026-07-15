#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

if [[ "$UNAME" != Linux* ]] && command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1 && [[ -d "$DG_ROOT/.venv-langgraph-wsl" ]]; then
  export MSYS2_ARG_CONV_EXCL='*'
  export MSYS_NO_PATHCONV=1
  win_root="$(cygpath -am "$DG_ROOT")"
  wsl_root="$(win_to_wsl_path "$win_root")"
  mapped_args=()
  path_next=0
  for arg in "$@"; do
    if [[ "$path_next" == 1 ]]; then
      if [[ "$arg" == /mnt/* ]]; then
        mapped_args+=("$arg")
      else
        win_arg="$(cygpath -am "$arg" 2>/dev/null || printf '%s' "$arg")"
        mapped_args+=("$(win_to_wsl_path "$win_arg")")
      fi
      path_next=0
      continue
    fi
    mapped_args+=("$arg")
    if [[ "$arg" == "--repo" || "$arg" == "--config" ]]; then
      path_next=1
    fi
  done
  quoted_args=()
  for arg in "${mapped_args[@]}"; do
    [[ -n "$arg" ]] && quoted_args+=("$(printf '%q' "$arg")")
  done
  exec wsl.exe bash -lc "cd $(printf '%q' "$wsl_root") && exec ./scripts/run_langgraph_local.sh ${quoted_args[*]}"
fi

PYTHON="$DG_ROOT/.venv-langgraph/bin/python"
if [[ "$UNAME" == Linux* && -x "$DG_ROOT/.venv-langgraph-wsl/bin/python" ]]; then
  PYTHON="$DG_ROOT/.venv-langgraph-wsl/bin/python"
elif [[ ! -x "$PYTHON" && -x "$DG_ROOT/.venv-langgraph/Scripts/python.exe" ]]; then
  PYTHON="$DG_ROOT/.venv-langgraph/Scripts/python.exe"
fi
REPO=""
CONFIG=""
HELP_LOCAL=0

usage() {
  cat <<'EOF'
Runs LangGraph/LangChain agent factory against the local DiffusionGemma profile.

Usage:
  scripts/run_langgraph_local.sh [--repo PATH] [--config PATH] [--dry-run|--smoke-import|--task TEXT]

Default config:
  configs/client_profiles/langgraph.dg.json

Examples:
  scripts/run_langgraph_local.sh --repo /repo --dry-run
  scripts/run_langgraph_local.sh --repo /repo --smoke-import
  scripts/run_langgraph_local.sh --repo /repo --task "Summarize this repo"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --config)
      CONFIG="$2"
      shift 2
      ;;
    --help-local)
      HELP_LOCAL=1
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$HELP_LOCAL" == "1" ]]; then
  usage
  exit 0
fi

if [[ -z "$REPO" ]]; then
  REPO="$PWD"
fi
REPO="$(cd "$REPO" && pwd)"

if [[ ! -x "$PYTHON" ]]; then
  "$DG_ROOT/scripts/install_langgraph_local.sh" >/tmp/dg-langgraph-install.log
fi

if [[ -z "$CONFIG" ]]; then
  if [[ -s "$REPO/.dg-agent/langgraph.dg.json" ]]; then
    CONFIG="$REPO/.dg-agent/langgraph.dg.json"
  else
    CONFIG="$DG_ROOT/configs/client_profiles/langgraph.dg.json"
  fi
fi

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:4100/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
export LANGGRAPH_MODEL="${LANGGRAPH_MODEL:-diffusiongemma-local}"
export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$REPO}"

exec "$PYTHON" "$DG_ROOT/scripts/dg_langgraph_runner.py" --repo "$REPO" --config "$CONFIG" "$@"
