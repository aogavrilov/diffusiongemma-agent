#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_CMD="python3"
if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
  PY_CMD="python"
fi

json_out="$("$DG_ROOT/scripts/dg_agent.sh" wrappers --json)"
text_out="$("$DG_ROOT/scripts/dg_agent.sh" wrappers)"

JSON_OUT="$json_out" "$PY_CMD" - <<'PY'
import json
import os
import sys

data = json.loads(os.environ["JSON_OUT"])
assert data["default"]["name"] == "DG agent mode", data
names = {item["name"] for item in data["ready_made_oss"]}
for required in {"Aider", "AgentAPI", "OpenCode", "ACP agent bridge", "Goose", "LiteLLM", "MCP Python SDK server", "Serena", "AutoGen AgentChat", "Hugging Face smolagents", "LangGraph", "CrewAI", "Open Interpreter", "LlamaIndex", "Haystack", "Continue/Cline/Roo/Kilo profiles"}:
    assert required in names, names
assert data["runtime"]["base_url"] == "http://127.0.0.1:4100/v1", data["runtime"]
PY

grep -F "DG OSS wrapper stack" <<<"$text_out"
grep -F "scripts/dg_agent.sh agent --repo /repo --task" <<<"$text_out"
grep -F "OpenCode" <<<"$text_out"
grep -F "agent-bridge" <<<"$text_out"
grep -F "LiteLLM" <<<"$text_out"
grep -F "MCP Python SDK server" <<<"$text_out"
grep -F "Serena" <<<"$text_out"
grep -F "AutoGen AgentChat" <<<"$text_out"
grep -F "Hugging Face smolagents" <<<"$text_out"
grep -F "LangGraph" <<<"$text_out"
grep -F "CrewAI" <<<"$text_out"
grep -F "Open Interpreter" <<<"$text_out"
grep -F "LlamaIndex" <<<"$text_out"
grep -F "Haystack" <<<"$text_out"

echo "DG agent wrappers smoke passed."
