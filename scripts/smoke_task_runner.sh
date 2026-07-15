#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-task-smoke.XXXXXX)"
TMP_ARTIFACTS="$(mktemp -d /tmp/dg-task-artifacts.XXXXXX)"

cleanup() {
  rm -rf "$TMP_REPO"
  rm -rf "$TMP_ARTIFACTS"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > calc.py <<'PY'
def add(a, b):
    return a + b
PY
git add calc.py
git commit -qm "initial"

cat > "$TMP_ARTIFACTS/plan.json" <<'JSON'
{
  "stop_on_failure": true,
  "defaults": {"test_timeout": 30, "aider_timeout": 30, "repair_attempts": 0},
  "steps": [
    {
      "name": "subtract",
      "task": "Edit calc.py so add(a, b) returns a - b. Derived exact code constraint: return a - b",
      "files": ["calc.py"],
      "test_cmd": "python3 -c \"from calc import add; assert add(5, 2) == 3\""
    }
  ]
}
JSON

DG_AGENT_PYTHON="${DG_AGENT_PYTHON:-python3}" "$DG_ROOT/scripts/run_task_runner.sh" \
  --repo "$TMP_REPO" \
  --plan "$TMP_ARTIFACTS/plan.json" \
  --report "$TMP_ARTIFACTS/task-report.json" >/tmp/dg-task-smoke.out

grep -F "DG task runner finished: success" /tmp/dg-task-smoke.out || {
  cat /tmp/dg-task-smoke.out >&2
  exit 1
}
REPORT="$TMP_ARTIFACTS/task-report.json" python3 - <<'PY'
import json
import os
from calc import add
from pathlib import Path

assert add(5, 2) == 3
report = json.loads(Path(os.environ["REPORT"]).read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["steps"][0]["supervisor_report"]["strategy"] == "deterministic-first", report
assert Path(report["steps"][0]["step_report"]).exists(), report
PY

rm -rf __pycache__
git add calc.py
git commit -qm "apply subtraction"

PLAN="$TMP_ARTIFACTS/plan.json" FAILING_PLAN="$TMP_ARTIFACTS/failing-plan.json" python3 - <<'PY'
import json
import os
from pathlib import Path

plan = json.loads(Path(os.environ["PLAN"]).read_text(encoding="utf-8"))
plan["steps"][0]["task"] = "Edit calc.py so add(a, b) returns a * b. Derived exact code constraint: return a * b"
plan["steps"][0]["test_cmd"] = "python3 -c \"import sys; sys.exit(1)\""
Path(os.environ["FAILING_PLAN"]).write_text(json.dumps(plan), encoding="utf-8")
PY

if DG_AGENT_PYTHON="${DG_AGENT_PYTHON:-python3}" "$DG_ROOT/scripts/run_task_runner.sh" \
  --repo "$TMP_REPO" \
  --plan "$TMP_ARTIFACTS/failing-plan.json" \
  --report "$TMP_ARTIFACTS/failing-task-report.json" \
  --rollback-on-failure >/tmp/dg-task-failing.out 2>&1; then
  echo "failing task unexpectedly succeeded" >&2
  exit 1
fi

grep -F "DG task runner finished: failed" /tmp/dg-task-failing.out || {
  cat /tmp/dg-task-failing.out >&2
  exit 1
}
rm -rf __pycache__
REPORT="$TMP_ARTIFACTS/failing-task-report.json" python3 - <<'PY'
import json
import os
from calc import add
from pathlib import Path

report = json.loads(Path(os.environ["REPORT"]).read_text(encoding="utf-8"))
assert add(5, 2) == 3, (Path("calc.py").read_text(encoding="utf-8"), report)
assert report["status"] == "failed", report
assert report["rollback"]["status"] == "success", report
PY

rm -rf __pycache__
DG_AGENT_PYTHON="${DG_AGENT_PYTHON:-python3}" "$DG_ROOT/scripts/run_task_runner.sh" \
  --repo "$TMP_REPO" \
  --plan "$TMP_ARTIFACTS/plan.json" \
  --dry-run \
  --report "$TMP_ARTIFACTS/dry-run-report.json" >/tmp/dg-task-dry.out

grep -F "DG task runner finished: success" /tmp/dg-task-dry.out || {
  cat /tmp/dg-task-dry.out >&2
  exit 1
}
grep -F "DRY RUN step 1:" /tmp/dg-task-dry.out || {
  cat /tmp/dg-task-dry.out >&2
  exit 1
}

echo "DG task runner smoke passed."
