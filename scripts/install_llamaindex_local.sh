#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV="$DG_ROOT/.tools/uv/bin/uv"
VENV="$DG_ROOT/.venv-llamaindex"

if [[ ! -x "$UV" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh"
fi

"$UV" venv "$VENV"
"$UV" pip install --python "$VENV/bin/python" \
  llama-index-core \
  llama-index-llms-openai-like

"$VENV/bin/python" - <<'PY'
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent, ReActAgent

print("llamaindex ready")
print(OpenAILike.__name__)
print(AgentWorkflow.__name__)
print(FunctionAgent.__name__)
print(ReActAgent.__name__)
PY
