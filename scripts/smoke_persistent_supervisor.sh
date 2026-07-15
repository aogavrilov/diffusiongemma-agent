#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/dg-persistent-supervisor.XXXXXX)"
REPO="$TMP_DIR/repo"
STATE="$TMP_DIR/state"

cleanup() {
  echo "Persistent supervisor smoke directory: $TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > calc.py <<'PY'
def add(a, b):
    return a - b
PY
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/run_persistent_supervisor.sh"
test -f "$DG_ROOT/scripts/dg_persistent_supervisor.py"
bash -n "$DG_ROOT/scripts/run_persistent_supervisor.sh"
python3 -m py_compile "$DG_ROOT/scripts/dg_persistent_supervisor.py"

"$DG_ROOT/scripts/run_persistent_supervisor.sh" \
  --repo "$REPO" \
  --task "Fix calc.py so add(a, b) returns the sum of its two arguments. Keep the same function name and signature." \
  --file calc.py \
  --test-cmd "python3 -c \"from calc import add; assert add(5, 2) == 7\"" \
  --state-dir "$STATE" \
  --max-steps 2 \
  --aider-timeout 90 \
  --wall-timeout 150 \
  --json >"$TMP_DIR/result.json"

STATE="$STATE" RESULT="$TMP_DIR/result.json" python3 - <<'PY'
import json
import os
from pathlib import Path

result = json.loads(Path(os.environ["RESULT"]).read_text(encoding="utf-8"))
state_dir = Path(os.environ["STATE"])
state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))

assert result["status"] == "success", result
assert state["status"] == "success", state
assert state["steps"], state
assert state["retrieval"]["retrieval"]["cache_hit"] is False, state
assert Path(state["retrieval"]["retrieval"]["index_file"]).exists(), state
assert (state_dir / "SUMMARY.md").exists(), state
PY

python3 - <<'PY'
from calc import add

assert add(5, 2) == 7
PY

"$DG_ROOT/scripts/run_persistent_supervisor.sh" \
  --repo "$REPO" \
  --task "Fix calc.py so add(a, b) returns the sum of its two arguments. Keep the same function name and signature." \
  --state-dir "$STATE" \
  --status --json >"$TMP_DIR/status.json"
grep -F '"status": "success"' "$TMP_DIR/status.json"

echo "Persistent supervisor smoke passed."
