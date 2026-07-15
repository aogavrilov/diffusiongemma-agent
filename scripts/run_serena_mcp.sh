#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  DG_ROOT="$(cygpath -au "$DG_ROOT")"
fi

usage() {
  cat <<EOF
Run upstream Serena as an MCP server for semantic/LSP code tools.

Usage:
  scripts/run_serena_mcp.sh [serena start-mcp-server options]

Checks:
  scripts/run_serena_mcp.sh --version
  scripts/run_serena_mcp.sh --check-installed

Defaults:
  --project-from-cwd
  --context claude-code
  --enable-web-dashboard false
  --open-web-dashboard false
  --enable-gui-log-window false

Useful:
  scripts/run_serena_mcp.sh --help-local
  scripts/run_serena_mcp.sh --transport streamable-http --port 9121

Install:
  scripts/install_serena_local.sh
EOF
}

try_serena_cli() {
  local version
  version="$("$@" --version </dev/null 2>&1)" || return 1
  SERENA_CMD=("$@")
  SERENA_VERSION="$version"
  return 0
}

try_wsl_serena_cli() {
  command -v wsl.exe >/dev/null 2>&1 || return 1
  command -v cygpath >/dev/null 2>&1 || return 1
  local win_root wsl_root win_cwd wsl_cwd
  win_root="$(cygpath -am "$DG_ROOT")"
  wsl_root="$(wsl.exe wslpath -a "$win_root" | sed 's/\r$//')"
  win_cwd="$(cygpath -am "$PWD")"
  wsl_cwd="$(wsl.exe wslpath -a "$win_cwd" | sed 's/\r$//')"
  wsl_cwd="${DG_SERENA_WSL_CWD:-$wsl_cwd}"
  [[ -n "$wsl_root" ]] || return 1
  try_serena_cli env MSYS2_ARG_CONV_EXCL='*' DG_SERENA_WSL_CWD="$wsl_cwd" wsl.exe bash "$wsl_root/scripts/serena_cli_wsl.sh"
}

try_linux_serena_cli() {
  [[ "$(uname -s 2>/dev/null || true)" == Linux* ]] || return 1
  [[ -x "$DG_ROOT/scripts/serena_cli_wsl.sh" ]] || return 1
  try_serena_cli env DG_SERENA_WSL_CWD="${DG_SERENA_WSL_CWD:-$PWD}" "$DG_ROOT/scripts/serena_cli_wsl.sh"
}

resolve_serena_cli() {
  SERENA_CMD=()
  if [[ -n "${DG_SERENA_BIN:-}" ]]; then
    try_serena_cli "$DG_SERENA_BIN" && return 0
  fi
  if try_linux_serena_cli; then
    return 0
  fi
  if try_wsl_serena_cli; then
    return 0
  fi
  if [[ -x "$DG_ROOT/.tools/uv-tools/bin/serena" ]]; then
    try_serena_cli "$DG_ROOT/.tools/uv-tools/bin/serena" && return 0
  fi
  if [[ -x "$DG_ROOT/.venv-serena/bin/python" ]]; then
    try_serena_cli "$DG_ROOT/.venv-serena/bin/python" "$DG_ROOT/scripts/serena_cli.py" && return 0
  fi
  if [[ -x "$DG_ROOT/.venv-serena/Scripts/python.exe" ]]; then
    try_serena_cli "$DG_ROOT/.venv-serena/Scripts/python.exe" "$DG_ROOT/scripts/serena_cli.py" && return 0
  fi
  if [[ -x "$DG_ROOT/.tools/uv-tools/bin/serena.exe" ]]; then
    try_serena_cli "$DG_ROOT/.tools/uv-tools/bin/serena.exe" && return 0
  fi
  return 1
}

if [[ "${1:-}" == "--help-local" ]]; then
  usage
  exit 0
fi

if ! resolve_serena_cli; then
  echo "Serena is not installed or cannot be executed by the current policy." >&2
  echo "Run: $DG_ROOT/scripts/install_serena_local.sh" >&2
  exit 2
fi

if [[ "${1:-}" == "--version" ]]; then
  printf '%s\n' "$SERENA_VERSION"
  exit 0
fi

if [[ "${1:-}" == "--check-installed" ]]; then
  printf '%s\n' "$SERENA_VERSION"
  printf 'Serena command:'
  printf ' %q' "${SERENA_CMD[@]}"
  printf '\n'
  exit 0
fi

has_project_flag=0
has_context_flag=0
has_dashboard_flag=0
has_open_dashboard_flag=0
has_gui_flag=0

for arg in "$@"; do
  case "$arg" in
    --project|--project=*|--project-file|--project-file=*|--project-from-cwd)
      has_project_flag=1
      ;;
    --context|--context=*)
      has_context_flag=1
      ;;
    --enable-web-dashboard|--enable-web-dashboard=*)
      has_dashboard_flag=1
      ;;
    --open-web-dashboard|--open-web-dashboard=*)
      has_open_dashboard_flag=1
      ;;
    --enable-gui-log-window|--enable-gui-log-window=*)
      has_gui_flag=1
      ;;
  esac
done

args=(start-mcp-server)
if [[ "$has_project_flag" == "0" ]]; then
  args+=(--project-from-cwd)
fi
if [[ "$has_context_flag" == "0" ]]; then
  args+=(--context claude-code)
fi
if [[ "$has_dashboard_flag" == "0" ]]; then
  args+=(--enable-web-dashboard false)
fi
if [[ "$has_open_dashboard_flag" == "0" ]]; then
  args+=(--open-web-dashboard false)
fi
if [[ "$has_gui_flag" == "0" ]]; then
  args+=(--enable-gui-log-window false)
fi
args+=("$@")

exec "${SERENA_CMD[@]}" "${args[@]}"
