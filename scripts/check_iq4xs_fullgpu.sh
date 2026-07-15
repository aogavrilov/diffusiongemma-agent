#!/usr/bin/env bash
set -euo pipefail

cd /root/diffusiongemma-agent

log=/tmp/dg-iq4xs-fullgpu-server.log
pidfile=/tmp/dg-iq4xs-fullgpu-server.pid
rm -f "$log" "$pidfile"

export DG_VISUAL_SERVER_BIN=/root/diffusiongemma-agent/llama.cpp-diffusion/build/bin/llama-diffusion-gemma-visual-server
export DG_MODEL="${DG_CHECK_MODEL:-/root/diffusiongemma-agent/models/diffusiongemma/diffusiongemma-26B-A4B-it-IQ4_XS-from-Q4_K_M.gguf}"
export DG_MODEL_ID="${DG_CHECK_MODEL_ID:-diffusiongemma-26b-a4b-it-iq4xs-fullgpu-local}"
export DG_NGL=999
export DG_ALLOW_FULL_NGL=1
export DG_MAXTOK="${DG_CHECK_MAXTOK:-1024}"
export DG_FA=1
export DG_KVCACHE=1
export DG_FUSED_MMQ_GLU="${DG_CHECK_FUSED_MMQ_GLU:-1}"
export DG_FUSED_MOE_DOWN_REDUCE="${DG_CHECK_FUSED_MOE_DOWN_REDUCE:-1}"
export DG_LAZY_RESERVE="${DG_CHECK_LAZY_RESERVE:-1}"
export DG_SAFE_COOLDOWN_SECONDS=30
export DG_STARTUP_TIMEOUT=900
export DG_REQUEST_TIMEOUT=900
export DG_PORT="${DG_CHECK_PORT:-8080}"

.venv/bin/python server.py > "$log" 2>&1 &
echo $! > "$pidfile"

cleanup() {
  if [[ -f "$pidfile" ]]; then
    kill "$(cat "$pidfile")" 2>/dev/null || true
    wait "$(cat "$pidfile")" 2>/dev/null || true
  fi
}
trap cleanup EXIT

for _ in $(seq 1 900); do
  if curl -fsS "http://127.0.0.1:${DG_PORT}/healthz" >/tmp/dg-iq4xs-health.json 2>/tmp/dg-iq4xs-curl.err; then
    break
  fi
  if ! kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "SERVER_EXITED"
    tail -120 "$log" || true
    exit 1
  fi
  sleep 1
done

echo "=== healthz ==="
cat /tmp/dg-iq4xs-health.json
echo
echo "=== nvidia-smi ==="
nvidia-smi --query-gpu=memory.used,memory.free,power.draw --format=csv,noheader,nounits
echo "=== buffer log ==="
grep -E "offloaded|CUDA0 model buffer|CPU_Mapped model buffer|CUDA0 compute buffer|CUDA_Host compute buffer|model buffer|compute buffer|READY|error|failed|out of memory|Runtime env" "$log" | tail -100 || true

echo "=== smoke ==="
cat >/tmp/dg-iq4xs-request.json <<JSON
{
  "model": "${DG_MODEL_ID}",
  "messages": [
    {"role": "user", "content": "Коротко и по-русски: что такое MoE в языковых моделях?"}
  ],
  "max_tokens": 160,
  "seed": 123,
  "n_blocks": ${DG_CHECK_N_BLOCKS:-2}
}
JSON

start=$(date +%s)
curl -fsS \
  -H "Content-Type: application/json" \
  -d @/tmp/dg-iq4xs-request.json \
  "http://127.0.0.1:${DG_PORT}/v1/chat/completions" >/tmp/dg-iq4xs-response.json
end=$(date +%s)
echo "elapsed_s=$((end-start))"
cat /tmp/dg-iq4xs-response.json
echo
echo "=== nvidia-smi after smoke ==="
nvidia-smi --query-gpu=memory.used,memory.free,power.draw --format=csv,noheader,nounits
