#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${DG_OPENCODE_VERSION:-1.17.20}"
PREFIX="$DG_ROOT/.tools/opencode"
BIN="$PREFIX/node_modules/.bin/opencode"
LINUX_BIN="$PREFIX/node_modules/opencode-linux-x64/bin/opencode"
WIN_INSTALL="$DG_ROOT/scripts/install_opencode_windows.ps1"

if [[ "$(uname -s 2>/dev/null || true)" == Linux* && -x "$LINUX_BIN" && "${DG_REFRESH_EXTERNAL_AGENT:-0}" != "1" ]]; then
  "$LINUX_BIN" --version
  exit 0
fi

if [[ -x "$BIN" && "${DG_REFRESH_EXTERNAL_AGENT:-0}" != "1" ]]; then
  "$BIN" --version
  exit 0
fi

case "$(uname -s 2>/dev/null || true)" in
  Linux*)
    node_path_entries=()
    if [[ -x "$DG_ROOT/.tools/node-linux/bin/node" ]]; then
      node_path_entries+=("$DG_ROOT/.tools/node-linux/bin")
    fi
    if [[ -x "$DG_ROOT/.tools/node/bin/node" ]]; then
      node_path_entries+=("$DG_ROOT/.tools/node/bin")
    fi
    if ((${#node_path_entries[@]})); then
      export PATH="$(IFS=:; echo "${node_path_entries[*]}"):$PATH"
    fi
    if ! command -v npm >/dev/null 2>&1; then
      echo "npm is required to install OpenCode." >&2
      exit 1
    fi
    npm install --prefix "$PREFIX" --no-audit --no-fund --ignore-scripts "opencode-ai@$VERSION"
    npm install --prefix "$PREFIX" --no-audit --no-fund --ignore-scripts "opencode-linux-x64@$VERSION" || true
    node "$PREFIX/node_modules/opencode-ai/postinstall.mjs"
    if [[ -x "$LINUX_BIN" ]]; then
      "$LINUX_BIN" --version
    else
      "$BIN" --version
    fi
    ;;
  *)
    if command -v powershell.exe >/dev/null 2>&1 && [[ -f "$WIN_INSTALL" ]]; then
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WIN_INSTALL" -Version "$VERSION"
    elif command -v powershell >/dev/null 2>&1 && [[ -f "$WIN_INSTALL" ]]; then
      powershell -NoProfile -ExecutionPolicy Bypass -File "$WIN_INSTALL" -Version "$VERSION"
    else
      echo "PowerShell installer is required to install OpenCode on this host." >&2
      exit 1
    fi
    ;;
esac
