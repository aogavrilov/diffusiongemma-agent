#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO=""
DRY_RUN=0
HELP=0
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Runs OpenHands as an ACP stdio agent server with the local DiffusionGemma
LiteLLM Proxy profile.

Usage:
  scripts/run_openhands_acp_local.sh [--repo PATH] [--dry-run] [-- ARGS...]

This intentionally uses `openhands acp`, not the separate `openhands-acp`
entrypoint, because the standalone entrypoint can be broken in some OpenHands
packages while the upstream subcommand works.
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
    --help-local)
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
export OPENHANDS_SUPPRESS_BANNER="${OPENHANDS_SUPPRESS_BANNER:-1}"
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore}"

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
cmd+=("acp" "--override-with-envs")
cmd+=("${EXTRA_ARGS[@]}")

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
