#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="$DG_ROOT/.tools/uv/bin/uv"
TOOL_DIR="$DG_ROOT/.tools/external-agents/uv-tools"
TOOL_BIN_DIR="$DG_ROOT/.tools/external-agents/bin"
OPENHANDS_BIN="$TOOL_BIN_DIR/openhands"

if [[ ! -x "$UV_BIN" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh" >/tmp/dg-uv-install.log
fi

mkdir -p "$TOOL_DIR" "$TOOL_BIN_DIR"
if [[ ! -x "$OPENHANDS_BIN" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  UV_TOOL_DIR="$TOOL_DIR" UV_TOOL_BIN_DIR="$TOOL_BIN_DIR" "$UV_BIN" tool install openhands --python 3.12 --force
fi

"$OPENHANDS_BIN" --help >/tmp/dg-openhands-help.txt
echo "$OPENHANDS_BIN"
