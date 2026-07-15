#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_DIR="$DG_ROOT/.tools/node"
NODE_LINUX_DIR="$DG_ROOT/.tools/node-linux"
NODE_WIN_DIR="$DG_ROOT/.tools/node-v22.17.1-win-x64"
QWEN_BIN="$DG_ROOT/.tools/qwen-code/node_modules/.bin/qwen"
REPO=""
DRY_RUN=0
HELP_LOCAL=0
WITH_MCP=1
MCP_CONFIG=""

usage() {
  cat <<'EOF'
Runs Qwen Code against the local DiffusionGemma LiteLLM/OpenAI-compatible profile.

Usage:
  scripts/run_qwen_code_local.sh [--repo PATH] [--no-mcp] [--mcp-config PATH] [--dry-run] -- [qwen args]

Defaults:
  repo: current directory
  model: diffusiongemma-local
  base URL: http://127.0.0.1:4100/v1
  MCP config: configs/client_profiles/qwen-code.mcp.json

Examples:
  scripts/run_qwen_code_local.sh --repo /repo --dry-run
  scripts/run_qwen_code_local.sh --repo /repo -- -p "Summarize this repo" --approval-mode plan
  scripts/run_qwen_code_local.sh --repo /repo -- --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-mcp)
      WITH_MCP=0
      shift
      ;;
    --mcp-config)
      MCP_CONFIG="$2"
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

if [[ ! -x "$QWEN_BIN" ]]; then
  "$DG_ROOT/scripts/install_qwen_code_local.sh" >/tmp/dg-qwen-code-install.log
fi

node_path_entries=()
case "$(uname -s)" in
  Linux*)
    if [[ -x "$NODE_LINUX_DIR/bin/node" ]]; then
      node_path_entries+=("$NODE_LINUX_DIR/bin")
    fi
    ;;
esac
if [[ -x "$NODE_DIR/bin/node" ]]; then
  node_path_entries+=("$NODE_DIR/bin")
fi
if [[ -x "$NODE_WIN_DIR/node.exe" ]]; then
  node_path_entries+=("$NODE_WIN_DIR")
fi
if ((${#node_path_entries[@]})); then
  export PATH="$(IFS=:; echo "${node_path_entries[*]}"):$DG_ROOT/.tools/qwen-code/node_modules/.bin:$PATH"
else
  export PATH="$DG_ROOT/.tools/qwen-code/node_modules/.bin:$PATH"
fi

if [[ -z "$MCP_CONFIG" ]]; then
  if [[ -s "$REPO/.dg-agent/qwen-code.mcp.json" ]]; then
    MCP_CONFIG="$REPO/.dg-agent/qwen-code.mcp.json"
  else
    MCP_CONFIG="$DG_ROOT/configs/client_profiles/qwen-code.mcp.json"
  fi
fi

OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:4100/v1}"
OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
OPENAI_MODEL="${OPENAI_MODEL:-diffusiongemma-local}"

cmd=(
  "$QWEN_BIN"
  --auth-type openai
  --model "$OPENAI_MODEL"
  --openai-api-key "$OPENAI_API_KEY"
  --openai-base-url "$OPENAI_BASE_URL"
  --telemetry=false
)

if [[ "$WITH_MCP" == "1" ]]; then
  cmd+=(
    --mcp-config "$MCP_CONFIG"
    --allowed-mcp-server-names diffusiongemma-local-agent
    --allowed-mcp-server-names repomix
    --allowed-mcp-server-names serena
  )
fi

cmd+=("$@")

if [[ "$DRY_RUN" == "1" ]]; then
  echo "repo: $REPO"
  echo "qwen: $QWEN_BIN"
  echo "openai_base_url: $OPENAI_BASE_URL"
  echo "openai_model: $OPENAI_MODEL"
  echo "mcp_config: $MCP_CONFIG"
  printf 'command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
  exit 0
fi

export OPENAI_BASE_URL OPENAI_API_KEY OPENAI_MODEL
export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$REPO}"
export DG_MCP_REPO="${DG_MCP_REPO:-$REPO}"

cd "$REPO"
exec "${cmd[@]}"
