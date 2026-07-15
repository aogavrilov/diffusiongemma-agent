#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO=""
TASK=""
TASK_FILE=""
DRY_RUN=0
HELP=0
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Runs OpenHands against the local DiffusionGemma LiteLLM proxy profile.

Usage:
  scripts/run_openhands_local.sh [--repo PATH] [--task TEXT | --task-file FILE] [--dry-run] [-- ARGS...]

The wrapper sources:
  configs/client_profiles/openhands.env
  configs/client_profiles/openhands.dg.toml

It expects an OpenHands CLI named `openhands` to be installed separately.
Use --dry-run to print the exact command and environment without executing it.
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
    --task-file|--file)
      TASK_FILE="$2"
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

PROFILE="$DG_ROOT/configs/client_profiles/openhands.dg.toml"
ENV_FILE="$DG_ROOT/configs/client_profiles/openhands.env"
if [[ -f "$REPO/.dg-agent/openhands.dg.toml" ]]; then
  PROFILE="$REPO/.dg-agent/openhands.dg.toml"
fi
if [[ -f "$REPO/.dg-agent/openhands.env" ]]; then
  ENV_FILE="$REPO/.dg-agent/openhands.env"
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
export OPENHANDS_CONFIG="$PROFILE"

OPENHANDS_BIN="${OPENHANDS_BIN:-}"
if [[ -z "$OPENHANDS_BIN" ]]; then
  if [[ -x "$DG_ROOT/.tools/external-agents/bin/openhands" ]]; then
    OPENHANDS_BIN="$DG_ROOT/.tools/external-agents/bin/openhands"
  else
    OPENHANDS_BIN="$(command -v openhands || true)"
  fi
fi

cmd=()
if [[ -n "$OPENHANDS_BIN" ]]; then
  cmd=("$OPENHANDS_BIN")
else
  cmd=("openhands")
fi

if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  cmd+=("${EXTRA_ARGS[@]}")
else
  if [[ -n "$TASK" || -n "$TASK_FILE" ]]; then
    cmd+=("--headless")
    if [[ -n "$TASK" ]]; then
      cmd+=("-t" "$TASK")
    fi
    if [[ -n "$TASK_FILE" ]]; then
      cmd+=("-f" "$TASK_FILE")
    fi
  fi
fi

if [[ "$DRY_RUN" == "1" || -z "$OPENHANDS_BIN" ]]; then
  echo "repo: $REPO"
  echo "profile: $PROFILE"
  echo "env_file: $ENV_FILE"
  echo "model: ${LLM_MODEL:-}"
  echo "base_url: ${LLM_BASE_URL:-}"
  printf 'command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
  if [[ -z "$OPENHANDS_BIN" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "OpenHands CLI not found in PATH; install OpenHands, or set OPENHANDS_BIN."
      exit 0
    fi
    echo "OpenHands CLI not found in PATH; install OpenHands, or set OPENHANDS_BIN." >&2
    exit 127
  fi
  exit 0
fi

cd "$REPO"
exec "${cmd[@]}"
