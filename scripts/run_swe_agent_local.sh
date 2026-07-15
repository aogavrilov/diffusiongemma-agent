#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO=""
TASK=""
DRY_RUN=0
HELP=0
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Runs classic SWE-agent against the local DiffusionGemma LiteLLM profile.

Usage:
  scripts/run_swe_agent_local.sh [--repo PATH] [--task TEXT] [--dry-run] [-- ARGS...]

The wrapper uses:
  configs/client_profiles/swe-agent.dg.yaml
  configs/client_profiles/litellm-local-model-registry.json

It expects a SWE-agent CLI named `sweagent` or `swe-agent` to be installed
separately. SWE-agent is maintenance-mode upstream; prefer mini-swe-agent for
new local experiments.
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

CONFIG="$DG_ROOT/configs/client_profiles/swe-agent.dg.yaml"
REGISTRY="$DG_ROOT/configs/client_profiles/litellm-local-model-registry.json"
if [[ -f "$REPO/.dg-agent/swe-agent.dg.yaml" ]]; then
  CONFIG="$REPO/.dg-agent/swe-agent.dg.yaml"
fi
if [[ -f "$REPO/.dg-agent/litellm-local-model-registry.json" ]]; then
  REGISTRY="$REPO/.dg-agent/litellm-local-model-registry.json"
fi
export LITELLM_MODEL_REGISTRY_PATH="$REGISTRY"

SWE_AGENT_BIN="${SWE_AGENT_BIN:-}"
if [[ -z "$SWE_AGENT_BIN" ]]; then
  if [[ -x "$DG_ROOT/.venv-swe-agent/bin/sweagent" ]]; then
    SWE_AGENT_BIN="$DG_ROOT/.venv-swe-agent/bin/sweagent"
  else
    SWE_AGENT_BIN="$(command -v sweagent || command -v swe-agent || true)"
  fi
fi

cmd=()
if [[ -n "$SWE_AGENT_BIN" ]]; then
  cmd=("$SWE_AGENT_BIN")
else
  cmd=("sweagent")
fi

if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  cmd+=("${EXTRA_ARGS[@]}")
else
  cmd+=("run" "--config" "$CONFIG" "--problem_statement.repo_path" "$REPO")
  if [[ -n "$TASK" ]]; then
    cmd+=("--problem_statement.text" "$TASK")
  fi
fi

if [[ "$DRY_RUN" == "1" || -z "$SWE_AGENT_BIN" ]]; then
  echo "repo: $REPO"
  echo "config: $CONFIG"
  echo "model_registry: $REGISTRY"
  printf 'command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
  if [[ -z "$SWE_AGENT_BIN" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "SWE-agent CLI not found in PATH; install SWE-agent, or set SWE_AGENT_BIN."
      exit 0
    fi
    echo "SWE-agent CLI not found in PATH; install SWE-agent, or set SWE_AGENT_BIN." >&2
    exit 127
  fi
  exit 0
fi

cd "$REPO"
exec "${cmd[@]}"
