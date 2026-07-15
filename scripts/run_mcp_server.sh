#!/usr/bin/env bash
set -euo pipefail

export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$PWD}"

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(uname -s 2>/dev/null || true)" != Linux* ]] && command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
  win_root="$(cygpath -am "$DG_ROOT")"
  wsl_root="$(wsl.exe wslpath -a "$win_root" | sed 's/\r$//')"
  export MSYS2_ARG_CONV_EXCL='*'
  export MSYS_NO_PATHCONV=1
  quoted_args=()
  for arg in "$@"; do
    [[ -n "$arg" ]] && quoted_args+=("$(printf '%q' "$arg")")
  done
  exec wsl.exe bash -lc "cd $(printf '%q' "$wsl_root") && exec ./scripts/run_mcp_server.sh ${quoted_args[*]}"
fi

if [[ $# -gt 0 ]]; then
  filtered_args=()
  for arg in "$@"; do
    [[ -n "$arg" ]] && filtered_args+=("$arg")
  done
  set -- "${filtered_args[@]}"
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "--help-local" ]]; then
  cat <<'EOF'
Runs the local DiffusionGemma MCP stdio server.

Usage:
  scripts/run_mcp_server.sh
  scripts/run_mcp_server.sh --list-tools
  scripts/run_mcp_server.sh --legacy

The server exposes tools around the existing reliable DG agent commands:
  dg_status, dg_context, dg_rag_context, dg_rag_answer, dg_repo_pack, dg_preflight,
  dg_plan, dg_task, dg_session, dg_verify, dg_capabilities,
  dg_client_smoke, dg_client_report
EOF
  exit 0
fi

if [[ "$(uname -s 2>/dev/null || true)" == Linux* ]]; then
  PYTHON="${DG_AGENT_PYTHON:-}"
  if [[ -z "$PYTHON" || ! -x "$PYTHON" || "$PYTHON" == *.exe || "$PYTHON" == *:\/* ]]; then
    if [[ -x "/root/diffusiongemma-agent/.venv-wsl/bin/python" ]]; then
      PYTHON="/root/diffusiongemma-agent/.venv-wsl/bin/python"
    elif [[ -x "$DG_ROOT/.venv/bin/python" ]]; then
      PYTHON="$DG_ROOT/.venv/bin/python"
    else
      PYTHON="python3"
    fi
  fi
else
  PYTHON="${DG_AGENT_PYTHON:-$DG_ROOT/.venv/bin/python}"
  if [[ ! -x "$PYTHON" && -x "$DG_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$DG_ROOT/.venv/Scripts/python.exe"
  fi
  if [[ ! -x "$PYTHON" ]]; then
    PYTHON="python3"
  fi
fi

if [[ "${1:-}" == "--legacy" ]]; then
  shift
  exec "$PYTHON" "$DG_ROOT/scripts/dg_mcp_server.py" "$@"
fi

if [[ "${DG_MCP_LEGACY:-0}" == "1" ]]; then
  exec "$PYTHON" "$DG_ROOT/scripts/dg_mcp_server.py" "$@"
fi

exec "$PYTHON" "$DG_ROOT/scripts/dg_mcp_sdk_server.py" "$@"
