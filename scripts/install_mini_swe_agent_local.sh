#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="$DG_ROOT/.tools/uv/bin/uv"
TOOL_DIR="$DG_ROOT/.tools/external-agents/uv-tools"
TOOL_BIN_DIR="$DG_ROOT/.tools/external-agents/bin"
MINI_GLOBAL_CONFIG_DIR="$DG_ROOT/.tools/external-agents/mini-swe-config"
MINI_BIN="$TOOL_BIN_DIR/mini"

if [[ ! -x "$UV_BIN" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh" >/tmp/dg-uv-install.log
fi

mkdir -p "$TOOL_DIR" "$TOOL_BIN_DIR"
if [[ ! -x "$MINI_BIN" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  UV_TOOL_DIR="$TOOL_DIR" UV_TOOL_BIN_DIR="$TOOL_BIN_DIR" "$UV_BIN" tool install mini-swe-agent --python 3.12 --force
fi

"$MINI_BIN" --help >/tmp/dg-mini-swe-agent-help.txt
mkdir -p "$MINI_GLOBAL_CONFIG_DIR"
cat >"$MINI_GLOBAL_CONFIG_DIR/.env" <<'EOF'
MSWEA_CONFIGURED=true
MSWEA_MODEL_NAME=openai/diffusiongemma-local
OPENAI_API_KEY=dummy
OPENAI_BASE_URL=http://127.0.0.1:4100/v1
EOF
echo "$MINI_BIN"
