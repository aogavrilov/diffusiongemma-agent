#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
mkdir -p "$ROOT/runtime"

case "$MODE" in
  backend)
    COMMAND=("$ROOT/start-runtime.sh")
    ;;
  gateway)
    COMMAND=(env \
      DG_AGENT_PYTHON="$ROOT/.venv-runtime/bin/python" \
      DG_AIDER_PYTHON="$ROOT/.venv-runtime/bin/python" \
      "$ROOT/scripts/run_agent_gateway_wsl.sh")
    ;;
  *)
    echo "usage: $0 {backend|gateway}" >&2
    exit 2
    ;;
esac

exec "${COMMAND[@]}" \
  >>"$ROOT/runtime/$MODE.out.log" \
  2>>"$ROOT/runtime/$MODE.err.log" \
  </dev/null
