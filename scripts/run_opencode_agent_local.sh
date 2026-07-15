#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export OPENCODE_CONFIG="$DG_ROOT/configs/opencode.dg-agent.json"
# Keep the upstream Bash tool alive through the bounded DG edit session.
export OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS="${OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS:-450000}"

exec "$DG_ROOT/scripts/run_opencode_local.sh" "$@"
