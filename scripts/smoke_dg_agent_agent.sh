#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$DG_ROOT/scripts/dg_agent.sh" up --wait-timeout 180 >/tmp/dg-agent-agent-up.log

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
repo="$tmp/repo"
mkdir -p "$repo"
cat >"$repo/calc.py" <<'PY'
def add(a, b):
    return a + b
PY

out_dir="$tmp/agent-runs"
report="$tmp/agent-report.json"
"$DG_ROOT/scripts/dg_agent.sh" agent \
  --repo "$repo" \
  --task "Read file calc.py." \
  --mode read \
  --tool dg_read_file \
  --out-dir "$out_dir" \
  --report "$report" \
  --json >/tmp/dg-agent-agent-response.json

REPORT="$report" python3 - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ["REPORT"]).read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["mode"] == "read", report
assert report["route"] == "openai_tool_loop_read_only", report
assert report["returncode"] == 0, report
assert report["tool_names"] == ["dg_read_file"], report
assert "Tool result summary" in report["final_content"], report
assert "def add" in report["final_content"], report
for artifact in ["transcript", "stdout", "stderr", "agent_json"]:
    assert Path(report["artifacts"][artifact]).exists(), (artifact, report)
PY

"$DG_ROOT/scripts/dg_agent.sh" agent-runs list --root "$out_dir" --json >/tmp/dg-agent-runs-list.json
"$DG_ROOT/scripts/dg_agent.sh" agent-runs show --root "$out_dir" --latest --json >/tmp/dg-agent-runs-show.json
"$DG_ROOT/scripts/dg_agent.sh" agent-runs artifact transcript --root "$out_dir" --latest >/tmp/dg-agent-runs-transcript.json
"$DG_ROOT/scripts/dg_agent.sh" agent-runs artifact transcript --root "$out_dir" --latest --path-only >/tmp/dg-agent-runs-transcript.path

python3 - <<'PY'
import json
from pathlib import Path

listed = json.loads(Path("/tmp/dg-agent-runs-list.json").read_text(encoding="utf-8"))
shown = json.loads(Path("/tmp/dg-agent-runs-show.json").read_text(encoding="utf-8"))
transcript = Path("/tmp/dg-agent-runs-transcript.json").read_text(encoding="utf-8")
transcript_path = Path("/tmp/dg-agent-runs-transcript.path").read_text(encoding="utf-8").strip()

assert listed["runs"], listed
assert listed["runs"][0]["status"] == "success", listed
assert shown["status"] == "success", shown
assert shown["artifacts"]["transcript"] == transcript_path, shown
assert "dg_read_file" in transcript and "def add" in transcript, transcript[:1000]
assert Path(transcript_path).exists(), transcript_path
PY

echo "DG agent high-level smoke passed."
