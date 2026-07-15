#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-repo-map-smoke.XXXXXX)"

cleanup() {
  echo "DG repo-map smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > hello.py <<'PY'
def greet(name):
    return f"hello {name}"

class Runner:
    def run(self):
        return greet("Ada")
PY
git add hello.py
git commit -qm "initial"

"$DG_ROOT/scripts/dg_agent.sh" repo-map \
  --repo "$TMP_REPO" \
  --map-tokens 1024 \
  --map-only \
  --max-chars 8000 \
  --timeout 180 \
  > /tmp/dg-repo-map-smoke.txt

grep -F "Here are summaries" /tmp/dg-repo-map-smoke.txt
grep -F "hello.py:" /tmp/dg-repo-map-smoke.txt
grep -F "def greet" /tmp/dg-repo-map-smoke.txt
grep -F "class Runner" /tmp/dg-repo-map-smoke.txt

status="$(git status --short --untracked-files=all)"
test -z "$status"

echo "DG repo-map smoke passed."
