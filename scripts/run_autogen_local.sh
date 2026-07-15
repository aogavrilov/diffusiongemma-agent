#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$DG_ROOT/.venv-autogen/bin/python"
REPO=""
CONFIG=""
HELP_LOCAL=0

usage() {
  cat <<'EOF'
Runs Microsoft AutoGen AgentChat against the local DiffusionGemma profile.

Usage:
  scripts/run_autogen_local.sh [--repo PATH] [--config PATH] [--dry-run|--smoke-import|--task TEXT]

Default config:
  configs/client_profiles/autogen.dg.json

Examples:
  scripts/run_autogen_local.sh --repo /repo --dry-run
  scripts/run_autogen_local.sh --repo /repo --smoke-import
  scripts/run_autogen_local.sh --repo /repo --task "Summarize this repo"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --config)
      CONFIG="$2"
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

if [[ ! -x "$PYTHON" ]]; then
  "$DG_ROOT/scripts/install_autogen_local.sh" >/tmp/dg-autogen-install.log
fi

if [[ -z "$CONFIG" ]]; then
  if [[ -s "$REPO/.dg-agent/autogen.dg.json" ]]; then
    CONFIG="$REPO/.dg-agent/autogen.dg.json"
  else
    CONFIG="$DG_ROOT/configs/client_profiles/autogen.dg.json"
  fi
fi

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:4100/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
export AUTOGEN_MODEL="${AUTOGEN_MODEL:-diffusiongemma-local}"
export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$REPO}"

exec "$PYTHON" "$DG_ROOT/scripts/dg_autogen_runner.py" --repo "$REPO" --config "$CONFIG" "$@"
