#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOOSE_BIN="$DG_ROOT/.tools/goose/bin/goose"
GOOSE_HOME="${DG_GOOSE_MCP_HOME:-$DG_ROOT/.tools/goose-dg-mcp-home}"
GOOSE_CONFIG_DIR="$GOOSE_HOME/.config/goose"

if [[ "${1:-}" == "--help-local" ]]; then
  cat <<'EOF'
Runs Goose with the local DiffusionGemma OpenAI-compatible proxy and the
DiffusionGemma MCP tool server plus Serena semantic/LSP MCP mounted as Goose
stdio extensions.

Usage:
  scripts/run_goose_mcp_local.sh info -v
  scripts/run_goose_mcp_local.sh run --no-session --no-profile --max-turns 1 --text "..."
  scripts/run_goose_mcp_local.sh --acp
  scripts/run_goose_mcp_local.sh --serve --port 3294

The launcher uses an isolated Goose HOME by default:
  .tools/goose-dg-mcp-home
EOF
  exit 0
fi

MODE="passthrough"
if [[ "${1:-}" == "--acp" ]]; then
  MODE="acp"
  shift
elif [[ "${1:-}" == "--serve" ]]; then
  MODE="serve"
  shift
fi

if [[ ! -x "$GOOSE_BIN" ]]; then
  "$DG_ROOT/scripts/install_goose_local.sh" >/tmp/dg-goose-install.log
fi

if command -v curl >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:8090/healthz >/dev/null || {
    echo "Aider-compatible proxy is not healthy at http://127.0.0.1:8090/healthz" >&2
    exit 2
  }
fi

mkdir -p "$GOOSE_CONFIG_DIR"
cp "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml" "$GOOSE_CONFIG_DIR/config.yaml"

export HOME="$GOOSE_HOME"
export GOOSE_PROVIDER="${GOOSE_PROVIDER:-openai}"
export GOOSE_MODEL="${GOOSE_MODEL:-diffusiongemma-26b-a4b-it-iq4xs-aider-local}"
export OPENAI_HOST="${OPENAI_HOST:-http://127.0.0.1:8090}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"

if [[ "$MODE" == "acp" ]]; then
  exec "$GOOSE_BIN" acp "$@"
fi

if [[ "$MODE" == "serve" ]]; then
  exec "$GOOSE_BIN" serve "$@"
fi

exec "$GOOSE_BIN" "$@"
