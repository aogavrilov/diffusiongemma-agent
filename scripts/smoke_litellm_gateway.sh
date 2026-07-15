#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${DG_LITELLM_SMOKE_PORT:-14100}"
LOG_OUT="/tmp/dg-litellm-gateway-smoke.out"
LOG_ERR="/tmp/dg-litellm-gateway-smoke.err"

"$DG_ROOT/scripts/install_litellm_local.sh" >/tmp/dg-litellm-install.log

if ! curl -fsS --max-time 3 http://127.0.0.1:8090/healthz >/dev/null; then
  echo "Aider-compatible proxy is not healthy at http://127.0.0.1:8090/healthz" >&2
  exit 1
fi

LITELLM_PORT="$PORT" "$DG_ROOT/scripts/run_litellm_gateway.sh" >"$LOG_OUT" 2>"$LOG_ERR" &
pid=$!
cleanup() {
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}
trap cleanup EXIT

ready=0
for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/v1/models" >/tmp/dg-litellm-models.json 2>/dev/null; then
    ready=1
    break
  fi
  sleep 1
done

if [[ "$ready" != "1" ]]; then
  echo "LiteLLM gateway did not become ready on port $PORT" >&2
  tail -n 120 "$LOG_ERR" >&2 || true
  tail -n 120 "$LOG_OUT" >&2 || true
  exit 1
fi

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-litellm-models.json").read_text(encoding="utf-8"))
ids = [item.get("id") for item in data.get("data", []) if isinstance(item, dict)]
assert "diffusiongemma-local" in ids, data
assert "diffusiongemma-26b-a4b-it-iq4xs-aider-local" in ids, data
PY

echo "LiteLLM gateway smoke passed."
