#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${DG_HAYSTACK_PYTHON:-$DG_ROOT/.venv-haystack/bin/python}"
REPO=""
CONFIG=""
HELP_LOCAL=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Runs Haystack BM25 RAG against the local DiffusionGemma OpenAI-compatible profile.

Usage:
  scripts/run_haystack_local.sh [--repo PATH] [--config PATH] [--dry-run|--smoke-import|--task TEXT]

Default config:
  configs/client_profiles/haystack.dg.json

Examples:
  scripts/run_haystack_local.sh --repo /repo --dry-run
  scripts/run_haystack_local.sh --repo /repo --smoke-import
  scripts/run_haystack_local.sh --repo /repo --task "Where is add(a, b) implemented?"
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

for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    DRY_RUN=1
    break
  fi
done

if [[ "$HELP_LOCAL" == "1" ]]; then
  usage
  exit 0
fi

if [[ -z "$REPO" ]]; then
  REPO="$PWD"
fi
REPO="$(cd "$REPO" && pwd)"

python_path() {
  if [[ "$PYTHON" == *.exe ]] && command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$1"
    return
  fi
  if [[ "${OS:-}" == "Windows_NT" ]] && command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

if [[ ! -x "$PYTHON" && "$DRY_RUN" != "1" ]]; then
  "$DG_ROOT/scripts/install_haystack_local.sh" >/tmp/dg-haystack-install.log
fi

if [[ -z "$CONFIG" ]]; then
  if [[ -s "$REPO/.dg-agent/haystack.dg.json" ]]; then
    CONFIG="$REPO/.dg-agent/haystack.dg.json"
  else
    CONFIG="$DG_ROOT/configs/client_profiles/haystack.dg.json"
  fi
fi

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8090/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
export HAYSTACK_MODEL="${HAYSTACK_MODEL:-diffusiongemma-local}"
export DG_AGENT_CALLER_CWD="${DG_AGENT_CALLER_CWD:-$REPO}"

REPO_FOR_PY="$(python_path "$REPO")"
CONFIG_FOR_PY="$(python_path "$CONFIG")"
RUNNER_FOR_PY="$(python_path "$DG_ROOT/scripts/dg_haystack_runner.py")"

if [[ -x "$PYTHON" ]]; then
  exec "$PYTHON" "$RUNNER_FOR_PY" --repo "$REPO_FOR_PY" --config "$CONFIG_FOR_PY" "$@"
fi

exec python3 "$RUNNER_FOR_PY" --repo "$REPO_FOR_PY" --config "$CONFIG_FOR_PY" "$@"
