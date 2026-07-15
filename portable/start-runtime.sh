#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$ROOT/runtime/bin:${LD_LIBRARY_PATH:-}"
export DG_RUNTIME_PRESET=iq3_fullgpu_fast
export DG_PORT="${DG_PORT:-4100}"
export DG_MODEL_ID=diffusiongemma-26b-a4b-it-iq3m-fullgpu
export DG_VISUAL_SERVER_BIN="$ROOT/runtime/bin/llama-diffusion-gemma-visual-server"
export DG_MODEL="$ROOT/models/diffusiongemma/diffusiongemma-26B-A4B-it-IQ3_M-from-Q4_K_M.gguf"
export DG_AGENT_PYTHON="$ROOT/.venv-runtime/bin/python"
exec "$DG_AGENT_PYTHON" "$ROOT/server.py"
