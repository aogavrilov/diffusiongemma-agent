#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINI_GLOBAL_CONFIG_DIR="$DG_ROOT/.tools/external-agents/mini-swe-config"
REPO=""
TASK=""
DRY_RUN=0
HELP=0
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Runs mini-swe-agent against the local DiffusionGemma LiteLLM profile.

Usage:
  scripts/run_mini_swe_agent_local.sh [--repo PATH] [--task TEXT] [--dry-run] [-- ARGS...]

The wrapper uses:
  configs/client_profiles/mini-swe-agent.dg.yaml
  configs/client_profiles/litellm-local-model-registry.json

It expects a mini-swe-agent CLI named `mini` or `mini-swe-agent` to be installed
separately. Use --dry-run to print the exact command without executing it.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --task)
      TASK="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|--help-local)
      HELP=1
      shift
      ;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "$HELP" == "1" ]]; then
  usage
  exit 0
fi

if [[ -z "$REPO" ]]; then
  REPO="$PWD"
fi
REPO="$(cd "$REPO" && pwd)"

CONFIG="$DG_ROOT/configs/client_profiles/mini-swe-agent.dg.yaml"
REGISTRY="$DG_ROOT/configs/client_profiles/litellm-local-model-registry.json"
if [[ -f "$REPO/.dg-agent/mini-swe-agent.dg.yaml" ]]; then
  CONFIG="$REPO/.dg-agent/mini-swe-agent.dg.yaml"
fi
if [[ -f "$REPO/.dg-agent/litellm-local-model-registry.json" ]]; then
  REGISTRY="$REPO/.dg-agent/litellm-local-model-registry.json"
fi
export LITELLM_MODEL_REGISTRY_PATH="$REGISTRY"
mkdir -p "$MINI_GLOBAL_CONFIG_DIR"
if [[ ! -f "$MINI_GLOBAL_CONFIG_DIR/.env" ]]; then
  cat >"$MINI_GLOBAL_CONFIG_DIR/.env" <<'EOF'
MSWEA_CONFIGURED=true
MSWEA_MODEL_NAME=openai/diffusiongemma-local
OPENAI_API_KEY=dummy
OPENAI_BASE_URL=http://127.0.0.1:4100/v1
EOF
fi
export MSWEA_GLOBAL_CONFIG_DIR="$MINI_GLOBAL_CONFIG_DIR"
export MSWEA_CONFIGURED=true
export MSWEA_MODEL_NAME=openai/diffusiongemma-local
export MSWEA_SILENT_STARTUP=1
export OPENAI_API_KEY=dummy
export OPENAI_BASE_URL=http://127.0.0.1:4100/v1

MINI_SWE_AGENT_BIN="${MINI_SWE_AGENT_BIN:-}"
if [[ -z "$MINI_SWE_AGENT_BIN" ]]; then
  if [[ -x "$DG_ROOT/.tools/external-agents/bin/mini" ]]; then
    MINI_SWE_AGENT_BIN="$DG_ROOT/.tools/external-agents/bin/mini"
  else
    MINI_SWE_AGENT_BIN="$(command -v mini || command -v mini-swe-agent || true)"
  fi
fi

cmd=()
if [[ -n "$MINI_SWE_AGENT_BIN" ]]; then
  cmd=("$MINI_SWE_AGENT_BIN")
else
  cmd=("mini")
fi

if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  cmd+=("${EXTRA_ARGS[@]}")
else
  cmd+=("-c" "$CONFIG")
  if [[ -n "$TASK" ]]; then
    cmd+=("-t" "$TASK")
  fi
fi

if [[ "$DRY_RUN" == "1" || -z "$MINI_SWE_AGENT_BIN" ]]; then
  echo "repo: $REPO"
  echo "config: $CONFIG"
  echo "model_registry: $REGISTRY"
  printf 'command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
  if [[ -z "$MINI_SWE_AGENT_BIN" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "mini-swe-agent CLI not found in PATH; install mini-swe-agent, or set MINI_SWE_AGENT_BIN."
      exit 0
    fi
    echo "mini-swe-agent CLI not found in PATH; install mini-swe-agent, or set MINI_SWE_AGENT_BIN." >&2
    exit 127
  fi
  exit 0
fi

cd "$REPO"
exec "${cmd[@]}"
