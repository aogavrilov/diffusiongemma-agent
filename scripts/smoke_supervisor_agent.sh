#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-supervisor-smoke.XXXXXX)"

cleanup() {
  echo "Supervisor smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > hello.py <<'PY'
def greet(name):
    return f"hello {name}"
PY
cat > test_hello.py <<'PY'
from hello import greet

def test_greet():
    assert greet("Ada") == "hello, Ada!"
PY
git add hello.py test_hello.py
git commit -qm "initial"

"$DG_ROOT/scripts/run_supervisor_agent.sh" \
  --repo "$TMP_REPO" \
  --task "Fix hello.py so greet('Ada') returns exactly hello, Ada! Keep the function name and signature unchanged." \
  --file hello.py \
  --test-cmd "python3 -c \"from hello import greet; assert greet('Ada') == 'hello, Ada!'\"" \
  --aider-timeout 120 \
  --repair-attempts 1 \
  --report "$TMP_REPO/supervisor-report.json"

python3 - <<'PY'
from hello import greet
assert greet("Ada") == "hello, Ada!"
PY
rm -rf __pycache__
rm -f supervisor-report.json
git add hello.py
git commit -qm "apply greeting fix"

cat > score.py <<'PY'
def label_score(score):
    return "TODO"
PY
git add score.py
git commit -qm "add score"

"$DG_ROOT/scripts/run_supervisor_agent.sh" \
  --repo "$TMP_REPO" \
  --task "Edit score.py. Implement label_score(score): return 'high' when score is greater than or equal to 90, otherwise return 'normal'. Keep the same function name." \
  --file score.py \
  --test-cmd "python3 -c \"from score import label_score; assert label_score(90) == 'high'; assert label_score(89) == 'normal'\"" \
  --no-deterministic-first \
  --aider-timeout 90 \
  --repair-attempts 0 \
  --report "$TMP_REPO/supervisor-threshold-report.json"

python3 - <<'PY'
import json
from pathlib import Path
from score import label_score

assert label_score(90) == "high"
assert label_score(89) == "normal"
report = json.loads(Path("supervisor-threshold-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["strategy"] in {"aider", "aider-with-deterministic-repair"}, report
PY
rm -rf __pycache__
rm -f supervisor-threshold-report.json
git add score.py
git commit -qm "apply score fix"

cat > calc.py <<'PY'
def add(a, b):
    return a + b
PY
git add calc.py
git commit -qm "add calc"

"$DG_ROOT/scripts/run_supervisor_agent.sh" \
  --repo "$TMP_REPO" \
  --task "Edit calc.py so add(a, b) returns a - b. Derived exact code constraint: return a - b" \
  --file calc.py \
  --test-cmd "python3 -c \"from calc import add; assert add(5, 2) == 3\"" \
  --aider-timeout 90 \
  --repair-attempts 0 \
  --report "$TMP_REPO/supervisor-explicit-return-report.json"

python3 - <<'PY'
import json
from pathlib import Path
from calc import add

assert add(5, 2) == 3
report = json.loads(Path("supervisor-explicit-return-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["strategy"] == "deterministic-first", report
assert "return a - b" in report["diff"], report
PY
rm -rf __pycache__
rm -f supervisor-explicit-return-report.json
git add calc.py
git commit -qm "apply calc fix"

"$DG_ROOT/scripts/run_supervisor_agent.sh" \
  --repo "$TMP_REPO" \
  --task "Fix calc.py so add(a, b) returns the sum of its two arguments. Keep the same function name and signature." \
  --file calc.py \
  --test-cmd "python3 -c \"from calc import add; assert add(5, 2) == 7\"" \
  --aider-timeout 90 \
  --repair-attempts 0 \
  --report "$TMP_REPO/supervisor-binary-operation-report.json"

python3 - <<'PY'
import json
from pathlib import Path
from calc import add

assert add(5, 2) == 7
report = json.loads(Path("supervisor-binary-operation-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["strategy"] == "deterministic-first", report
assert "return a + b" in report["diff"], report
PY
rm -rf __pycache__
rm -f supervisor-binary-operation-report.json
git add calc.py
git commit -qm "restore calc addition"

cat > message.py <<'PY'
WELCOME = "hello beta"

def welcome():
    return WELCOME
PY
git add message.py
git commit -qm "add message"

"$DG_ROOT/scripts/run_supervisor_agent.sh" \
  --repo "$TMP_REPO" \
  --task "In message.py, replace 'hello beta' with 'hello stable'. Keep everything else unchanged." \
  --file message.py \
  --test-cmd "python3 -c \"from message import welcome; assert welcome() == 'hello stable'\"" \
  --aider-timeout 90 \
  --repair-attempts 0 \
  --report "$TMP_REPO/supervisor-replace-report.json"

python3 - <<'PY'
import json
from pathlib import Path
from message import welcome

assert welcome() == "hello stable"
report = json.loads(Path("supervisor-replace-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["strategy"] == "deterministic-first", report
assert "hello stable" in report["diff"], report
PY

rm -rf __pycache__
rm -f supervisor-replace-report.json
git add message.py
git commit -qm "apply message fix"

cat > protected.py <<'PY'
def add(a, b):
    return a + b
PY
cat > README-protected.md <<'MD'
# Must remain unchanged
MD
git add protected.py README-protected.md
git commit -qm "add protected fixture"

"$DG_ROOT/scripts/run_supervisor_agent.sh" \
  --repo "$TMP_REPO" \
  --task "Change protected.py only so add returns a - b. Do not modify README-protected.md or create files." \
  --max-files 1 \
  --test-cmd "python3 -c \"from protected import add; assert add(5, 2) == 3\"" \
  --aider-timeout 90 \
  --repair-attempts 0 \
  --report "$TMP_REPO/supervisor-protected-report.json"

python3 - <<'PY'
import json
from pathlib import Path
from protected import add

assert add(5, 2) == 3
assert Path("README-protected.md").read_text(encoding="utf-8") == "# Must remain unchanged\n"
report = json.loads(Path("supervisor-protected-report.json").read_text(encoding="utf-8"))
assert report["status"] == "success", report
assert report["strategy"] == "deterministic-first", report
assert report["selected_files"] == ["protected.py"], report
assert "README-protected.md" not in report["diff"], report
PY

echo "Supervisor smoke passed."
git diff -- hello.py score.py calc.py message.py protected.py README-protected.md
