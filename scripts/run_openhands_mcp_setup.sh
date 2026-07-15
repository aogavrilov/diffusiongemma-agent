#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO=""
PERSISTENCE_DIR=""
RESET=0
DRY_RUN=0
HELP=0
INCLUDE_REPOMIX=1
INCLUDE_SERENA=1

usage() {
  cat <<'EOF'
Configure OpenHands MCP servers for a target repo.

Usage:
  scripts/run_openhands_mcp_setup.sh [--repo PATH] [--persistence-dir PATH] [--reset] [--dry-run]

This writes an isolated OpenHands MCP config under:
  <repo>/.dg-agent/openhands-persistence/mcp.json

Configured stdio servers:
  diffusiongemma-local-agent -> scripts/run_mcp_server.sh
  repomix                    -> scripts/run_repomix_mcp.sh
  serena                     -> scripts/run_serena_mcp.sh --project <repo>
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --persistence-dir)
      PERSISTENCE_DIR="$2"
      shift 2
      ;;
    --reset)
      RESET=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-repomix)
      INCLUDE_REPOMIX=0
      shift
      ;;
    --no-serena)
      INCLUDE_SERENA=0
      shift
      ;;
    --help|--help-local)
      HELP=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
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

if [[ -z "$PERSISTENCE_DIR" ]]; then
  PERSISTENCE_DIR="$REPO/.dg-agent/openhands-persistence"
fi

OPENHANDS_BIN="${OPENHANDS_BIN:-}"
if [[ -z "$OPENHANDS_BIN" ]]; then
  if [[ -x "$DG_ROOT/.tools/external-agents/bin/openhands" ]]; then
    OPENHANDS_BIN="$DG_ROOT/.tools/external-agents/bin/openhands"
  else
    OPENHANDS_BIN="$(command -v openhands || true)"
  fi
fi

if [[ -z "$OPENHANDS_BIN" ]]; then
  echo "OpenHands CLI not found; run scripts/install_openhands_local.sh first." >&2
  exit 127
fi

export OPENHANDS_SUPPRESS_BANNER="${OPENHANDS_SUPPRESS_BANNER:-1}"
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore}"
export OPENHANDS_PERSISTENCE_DIR="$PERSISTENCE_DIR"
export OPENHANDS_WORK_DIR="$REPO"

config_path="$PERSISTENCE_DIR/mcp.json"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "repo: $REPO"
  echo "persistence_dir: $PERSISTENCE_DIR"
  echo "config: $config_path"
  echo "openhands: $OPENHANDS_BIN"
  echo "server: diffusiongemma-local-agent -> $DG_ROOT/scripts/run_mcp_server.sh"
  if [[ "$INCLUDE_REPOMIX" == "1" ]]; then
    echo "server: repomix -> $DG_ROOT/scripts/run_repomix_mcp.sh"
  fi
  if [[ "$INCLUDE_SERENA" == "1" ]]; then
    echo "server: serena -> $DG_ROOT/scripts/run_serena_mcp.sh --project $REPO"
  fi
  exit 0
fi

mkdir -p "$PERSISTENCE_DIR"
if [[ "$RESET" == "1" ]]; then
  rm -f "$config_path"
fi

remove_if_present() {
  local name="$1"
  "$OPENHANDS_BIN" mcp remove "$name" >/dev/null 2>&1 || true
}

remove_if_present diffusiongemma-local-agent
"$OPENHANDS_BIN" mcp add \
  diffusiongemma-local-agent \
  --transport stdio \
  --env "DG_MCP_REPO=$REPO" \
  --env "DG_AGENT_CALLER_CWD=$REPO" \
  "$DG_ROOT/scripts/run_mcp_server.sh"

if [[ "$INCLUDE_REPOMIX" == "1" ]]; then
  remove_if_present repomix
  "$OPENHANDS_BIN" mcp add \
    repomix \
    --transport stdio \
    "$DG_ROOT/scripts/run_repomix_mcp.sh"
fi

if [[ "$INCLUDE_SERENA" == "1" ]]; then
  remove_if_present serena
  "$OPENHANDS_BIN" mcp add \
    serena \
    --transport stdio \
    "$DG_ROOT/scripts/run_serena_mcp.sh" \
    --project "$REPO"
fi

echo "OpenHands MCP config: $config_path"
"$OPENHANDS_BIN" mcp list
