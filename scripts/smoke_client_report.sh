#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DG_ROOT
TMP_REPO="$(mktemp -d /tmp/dg-client-report.XXXXXX)"

cleanup() {
  echo "DG client-report repo: $TMP_REPO"
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

"$DG_ROOT/scripts/dg_agent.sh" client-report --repo "$TMP_REPO" --client cursor --json >/tmp/dg-client-report.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-report.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["client"] == "cursor", data
assert data["workspace"]["complete"] is True, data["workspace"]
assert data["client_smoke"]["status"] == "success", data["client_smoke"]
assert data["client_config"]["status"] == "loaded", data["client_config"]
assert {"diffusiongemma-local-agent", "repomix"} <= set(data["client_config"]["servers"]), data["client_config"]
assert data["outputs"]["json"]["path"].endswith(".dg-agent/client-handoff.json"), data["outputs"]
assert data["outputs"]["markdown"]["path"].endswith(".dg-agent/CLIENT_HANDOFF.md"), data["outputs"]
assert "agent_bridge" in data["commands"], data["commands"]
assert "status" in data["capabilities_latest"], data["capabilities_latest"]
PY

test -s .dg-agent/client-handoff.json
test -s .dg-agent/CLIENT_HANDOFF.md
python3 -m json.tool .dg-agent/client-handoff.json >/dev/null
grep -F "DG Client Handoff" .dg-agent/CLIENT_HANDOFF.md
grep -F ".dg-agent/bin/agent-bridge --server opencode-acp" .dg-agent/CLIENT_HANDOFF.md
test -x .dg-agent/bin/client-report

.dg-agent/bin/client-report --client cursor --no-init --no-write --json >/tmp/dg-client-report-nowrite.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-report-nowrite.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["outputs"]["json"]["status"] == "skipped", data["outputs"]
assert data["outputs"]["markdown"]["status"] == "skipped", data["outputs"]
assert data["client_smoke"]["report"]["actions"][0]["status"] == "skipped", data["client_smoke"]
PY

"$DG_ROOT/scripts/dg_agent.sh" client-report --repo "$TMP_REPO" --client cursor --no-init --live --json >/tmp/dg-client-report-live.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-report-live.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
checks = {item["name"]: item for item in data["client_smoke"]["report"]["checks"]}
assert checks["live_endpoints"]["status"] == "passed", checks["live_endpoints"]
PY

if git status --short --untracked-files=all | grep -q '.dg-agent'; then
  echo ".dg-agent should be written to git info/exclude by client-report/client-smoke" >&2
  exit 1
fi

echo "DG client-report passed."
