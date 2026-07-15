#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_DIR="$DG_ROOT/.tools/uv"
UV_BIN="$UV_DIR/bin/uv"
UV_EXE="$UV_DIR/bin/uv.exe"
UNAME="$(uname -s 2>/dev/null || true)"

if [[ "$UNAME" == Linux* ]]; then
  if [[ ! -x "$UV_BIN" ]]; then
    mkdir -p "$UV_DIR/bin"
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$UV_DIR/bin" sh
  fi
  "$UV_BIN" --version
  exit 0
fi

if [[ ! -x "$UV_BIN" && ! -x "$UV_EXE" ]]; then
  mkdir -p "$UV_DIR/bin"
  curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$UV_DIR/bin" sh
fi

if [[ -x "$UV_BIN" ]]; then
  "$UV_BIN" --version
else
  "$UV_EXE" --version
fi
