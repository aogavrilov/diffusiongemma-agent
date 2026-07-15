#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DG_ROOT
TMP_REPO="$(mktemp -d /tmp/dg-client-smoke.XXXXXX)"

cleanup() {
  echo "DG client-smoke repo: $TMP_REPO"
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

"$DG_ROOT/scripts/dg_agent.sh" client-smoke --repo "$TMP_REPO" --client cursor --json >/tmp/dg-client-smoke.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-smoke.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["client"] == "cursor", data
assert data["target"].endswith(".cursor/mcp.json"), data
checks = {item["name"]: item for item in data["checks"]}
for name in ["workspace", "agent_hub_markdown", "agent_hub_json", "mcp_client_config", "agent_rules", "agent_commands", "launchers"]:
    assert checks[name]["status"] == "passed", checks[name]
assert {"diffusiongemma-local-agent", "repomix"} <= set(checks["mcp_client_config"]["servers"]), checks["mcp_client_config"]
assert "safe_code_edit" in checks["agent_hub_json"]["routes"], checks["agent_hub_json"]
assert any(item["step"] == "client-init" and item["status"] == "success" for item in data["actions"]), data["actions"]
PY

test -x .dg-agent/bin/client-smoke
test -x .dg-agent/bin/agent-commands
test -s .claude/skills/dg-local-agent/SKILL.md
.dg-agent/bin/client-smoke --client cursor --no-init --json >/tmp/dg-client-smoke-second.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-smoke-second.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["actions"][0]["status"] == "skipped", data["actions"]
PY

"$DG_ROOT/scripts/dg_agent.sh" client-smoke --repo "$TMP_REPO" --client cursor --no-init --live --json >/tmp/dg-client-smoke-live.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-smoke-live.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
checks = {item["name"]: item for item in data["checks"]}
assert checks["live_endpoints"]["status"] == "passed", checks["live_endpoints"]
assert {item["name"] for item in checks["live_endpoints"]["endpoints"]} == {"backend", "proxy", "litellm"}, checks["live_endpoints"]
PY

if git status --short --untracked-files=all | grep -q '.dg-agent'; then
  echo ".dg-agent should be written to git info/exclude by client-smoke/client-init" >&2
  exit 1
fi

echo "DG client-smoke passed."
