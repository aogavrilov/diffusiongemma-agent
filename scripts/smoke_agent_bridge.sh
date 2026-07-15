#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-agent-bridge-smoke.XXXXXX)"

cleanup() {
  echo "DG agent-bridge smoke repo: $TMP_REPO"
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

"$DG_ROOT/scripts/dg_agent.sh" agent-bridge --repo "$TMP_REPO" --server opencode-acp --json >/tmp/dg-agent-bridge-opencode.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-bridge-opencode.json").read_text(encoding="utf-8"))
assert data["status"] == "ready", data
assert data["server"] == "opencode-acp", data
assert data["connect"]["transport"] == "http", data
assert data["connect"]["url"] == "http://127.0.0.1:3295", data
assert "--cwd" in data["command"], data
assert any(item["step"] == "client-init" and item["status"] == "success" for item in data["actions"]), data
PY

test -x .dg-agent/bin/agent-bridge
test -x .dg-agent/bin/hub
test -s .cursor/mcp.json
test -s .dg-agent/AGENT_HUB.md
test -s .dg-agent/agent-hub.json
grep -F "DG_AGENT_BRIDGE_COMMAND=scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp" .dg-agent/env.sh
grep -F ".dg-agent/bin/agent-bridge --server opencode-acp" .dg-agent/README.md
grep -F "ACP-capable client" .dg-agent/AGENT_HUB.md

.dg-agent/bin/agent-bridge --server goose-serve --no-init --json >/tmp/dg-agent-bridge-goose-serve.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-bridge-goose-serve.json").read_text(encoding="utf-8"))
assert data["status"] == "ready", data
assert data["server"] == "goose-serve", data
assert data["connect"]["transport"] == "http-websocket", data
assert data["connect"]["url"] == "http://127.0.0.1:3294", data
assert data["actions"][0]["status"] == "skipped", data
PY

"$DG_ROOT/scripts/dg_agent.sh" agent-bridge --repo "$TMP_REPO" --server goose-acp --no-init --json >/tmp/dg-agent-bridge-goose-acp.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-bridge-goose-acp.json").read_text(encoding="utf-8"))
assert data["status"] == "ready", data
assert data["server"] == "goose-acp", data
assert data["connect"]["transport"] == "stdio", data
assert data["connect"]["url"] == "", data
assert data["command"][-1] == "goose-acp", data
PY

if git status --short --untracked-files=all | grep -q '.dg-agent'; then
  echo ".dg-agent should be written to git info/exclude by client-init" >&2
  exit 1
fi

echo "DG agent-bridge smoke passed."
