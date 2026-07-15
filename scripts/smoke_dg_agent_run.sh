#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-run-smoke.XXXXXX)"

cleanup() {
  echo "DG run smoke repo: $TMP_REPO"
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
git add hello.py
git commit -qm "initial"

"$DG_ROOT/scripts/dg_agent.sh" run \
  --repo "$TMP_REPO" \
  --task "Fix hello.py so greet('Ada') returns exactly hello, Ada!" \
  --file hello.py \
  --dry-run \
  --json >/tmp/dg-run-dry.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-run-dry.json").read_text(encoding="utf-8"))
assert data["status"] == "dry-run", data
steps = [item["step"] for item in data["actions"]]
assert "workspace-init" in steps, steps
assert "preflight" in steps, steps
cmd = data["would_run"]
assert "agent" in cmd, cmd
assert "--repo" in cmd, cmd
assert "--task" in cmd, cmd
assert "--file" in cmd and "hello.py" in cmd, cmd
PY

test -x .dg-agent/bin/run
if git status --short --untracked-files=all | grep -q '.dg-agent'; then
  git status --short --untracked-files=all >&2
  echo ".dg-agent should be written to the local git info/exclude by workspace-init" >&2
  exit 1
fi
if [[ -n "$(git status --short)" ]]; then
  git status --short >&2
  echo "run dry-run should leave an otherwise clean repo clean" >&2
  exit 1
fi
.dg-agent/bin/run --task "Fix hello.py" --file hello.py --dry-run --json >/tmp/dg-run-local-dry.json
python3 -m json.tool /tmp/dg-run-local-dry.json >/dev/null

if ! curl -fsS --max-time 2 http://127.0.0.1:4100/healthz >/dev/null 2>&1; then
  if "$DG_ROOT/scripts/dg_agent.sh" run \
    --repo "$TMP_REPO" \
    --task "Fix hello.py" \
    --file hello.py \
    --no-init \
    --json >/tmp/dg-run-no-start.json; then
    echo "run without --dry-run or --start should not execute when backend is unavailable" >&2
    exit 1
  fi
  python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-run-no-start.json").read_text(encoding="utf-8"))
assert data["status"] in {"needs-start", "blocked"}, data
PY
fi

echo "DG agent run smoke passed."
