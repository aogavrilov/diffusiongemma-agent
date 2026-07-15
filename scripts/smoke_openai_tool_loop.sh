#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$DG_ROOT/scripts/dg_agent.sh" up --wait-timeout 180 >/tmp/dg-openai-tool-loop-up.log

out="/tmp/dg-openai-tool-loop-report.json"
"$DG_ROOT/scripts/dg_agent.sh" tool-loop \
  --repo "$DG_ROOT" \
  --task "Find scripts/aider_dg_proxy.py and explain tool_delegate." \
  --stop-after-tool \
  --max-steps 1 \
  --timeout 120 \
  --json \
  --out "$out" >/tmp/dg-openai-tool-loop-response.json

python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("/tmp/dg-openai-tool-loop-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["steps"] == 1, report
runtime_events = [item for item in report["events"] if item["kind"] == "tool_runtime"]
assert runtime_events, report
runtime = runtime_events[0]["runtime"]
assert runtime["ok"] is True, runtime
assert runtime["tool"] in {"dg_context", "dg_rag_context"}, runtime
assert runtime["tool_response"]["role"] == "tool", runtime
content = runtime["result"].get("content") or runtime["result"].get("text") or ""
assert "scripts/aider_dg_proxy.py" in content, runtime
PY

out_final="/tmp/dg-openai-tool-loop-final-report.json"
"$DG_ROOT/scripts/dg_agent.sh" tool-loop \
  --repo "$DG_ROOT" \
  --task "Read file scripts/dg_openai_tool_loop.py." \
  --tool dg_read_file \
  --max-steps 2 \
  --timeout 120 \
  --json \
  --out "$out_final" >/tmp/dg-openai-tool-loop-final-response.json

python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("/tmp/dg-openai-tool-loop-final-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["steps"] == 2, report
assert report["tool_names"] == ["dg_read_file"], report
assert "Tool result summary" in report["final_content"], report
assert "DEFAULT_BASE_URL" in report["final_content"], report
PY

echo "OpenAI tool-loop smoke passed."
