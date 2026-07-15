#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DG_ROOT
TMP_REPO="$(mktemp -d /tmp/dg-client-init-smoke.XXXXXX)"

cleanup() {
  echo "DG client-init smoke repo: $TMP_REPO"
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

"$DG_ROOT/scripts/dg_agent.sh" client-init --repo "$TMP_REPO" --client cursor --json >/tmp/dg-client-init.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-init.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["client"] == "cursor", data
expected_servers = data["bundle"]["servers"]
assert {"diffusiongemma-local-agent", "repomix"} <= set(expected_servers), data
assert data["bundle"]["servers"] == expected_servers, data
steps = {item["step"]: item for item in data["steps"]}
assert steps["workspace-init"]["status"] == "success", steps
assert steps["mcp-client-config"]["status"] == "written", steps
assert steps["agent-rules"]["status"] == "success", steps
assert steps["agent-commands"]["status"] == "success", steps
assert steps["mcp-client-config"]["report"]["servers"] == expected_servers, steps
assert data["next"]["workspace"].endswith(".dg-agent"), data
PY

test -x .dg-agent/bin/client-init
test -x .dg-agent/bin/client-smoke
test -x .dg-agent/bin/client-report
test -x .dg-agent/bin/agent-commands
test -x .dg-agent/bin/agent-bridge
test -x .dg-agent/bin/hub
test -s .dg-agent/client-pack.json
test -s .dg-agent/AGENT_HUB.md
test -s .dg-agent/agent-hub.json
test -s .dg-agent/COMMANDS.md
test -s .dg-agent/command-kit.json
test -s .dg-agent/README.md
test -s .cursor/mcp.json
test -s .claude/skills/dg-local-agent/SKILL.md
test -s AGENTS.md
test -s CLAUDE.md
test -s .github/copilot-instructions.md
test -s .github/instructions/diffusiongemma.instructions.md
test -s .cursor/rules/diffusiongemma-local-agent.mdc
grep -F ".dg-agent/bin/client-init --client cursor" .dg-agent/README.md
grep -F "DG_CLIENT_INIT_COMMAND=scripts/dg_agent.sh client-init --repo /repo --client cursor" .dg-agent/env.sh
grep -F "DG_CLIENT_SMOKE_COMMAND=scripts/dg_agent.sh client-smoke --repo /repo --client cursor" .dg-agent/env.sh
grep -F "DG_CLIENT_REPORT_COMMAND=scripts/dg_agent.sh client-report --repo /repo --client cursor" .dg-agent/env.sh
grep -F "DG_AGENT_COMMANDS_COMMAND=scripts/dg_agent.sh agent-commands --repo /repo --target all" .dg-agent/env.sh
grep -F "DG_AGENT_BRIDGE_COMMAND=scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp" .dg-agent/env.sh
grep -F "DG_WORKSPACE_AGENT_HUB=.dg-agent/AGENT_HUB.md" .dg-agent/env.sh
grep -F "DG Local Agent Hub" .dg-agent/AGENT_HUB.md
grep -F "DG Agent Command Kit" .dg-agent/COMMANDS.md
grep -F "DG Local Agent Skill" .claude/skills/dg-local-agent/SKILL.md
python3 -m json.tool .dg-agent/agent-hub.json >/dev/null
grep -F ".dg-agent/" .git/info/exclude
grep -F ".serena/" .git/info/exclude

python3 - <<'PY'
import json
from pathlib import Path

cfg = json.loads(Path(".cursor/mcp.json").read_text(encoding="utf-8"))
servers = cfg["mcpServers"]
assert {"diffusiongemma-local-agent", "repomix"} <= set(servers), servers
primary = servers["diffusiongemma-local-agent"]
primary_args = " ".join(primary.get("args", []))
assert (
    primary["command"].endswith("scripts/run_mcp_server.sh")
    or (primary["command"] == "bash" and "scripts/run_mcp_server.sh" in primary_args)
), servers
assert servers["repomix"]["command"].endswith("scripts/run_repomix_mcp.sh"), servers
if "serena" in servers:
    assert servers["serena"]["command"].endswith("scripts/run_serena_mcp.sh"), servers
PY

.dg-agent/bin/client-init --client cursor --json >/tmp/dg-client-init-second.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-init-second.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
steps = {item["step"]: item for item in data["steps"]}
assert steps["workspace-init"]["status"] == "success", steps
assert steps["mcp-client-config"]["status"] == "unchanged", steps
assert steps["agent-rules"]["status"] == "success", steps
assert steps["agent-commands"]["status"] == "success", steps
assert all(item["status"] == "unchanged" for item in steps["agent-rules"]["report"]["files"]), steps["agent-rules"]
assert all(item["status"] == "unchanged" for item in steps["agent-commands"]["report"]["files"]), steps["agent-commands"]
PY

"$DG_ROOT/scripts/dg_agent.sh" client-init --repo "$TMP_REPO" --client vscode --dry-run --no-workspace --no-rules --no-oss-stack --with-serena --json >/tmp/dg-client-init-dry.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-client-init-dry.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["bundle"]["servers"] == ["diffusiongemma-local-agent", "serena"], data
steps = {item["step"]: item for item in data["steps"]}
assert steps["workspace-init"]["status"] == "skipped", steps
assert steps["mcp-client-config"]["status"] == "would_write", steps
assert steps["mcp-client-config"]["report"]["servers"] == ["diffusiongemma-local-agent", "serena"], steps
assert steps["agent-rules"]["status"] == "skipped", steps
assert steps["agent-commands"]["status"] == "skipped", steps
PY

if git status --short --untracked-files=all | grep -q '.dg-agent'; then
  echo ".dg-agent should be written to git info/exclude by client-init/workspace-init" >&2
  exit 1
fi

echo "DG client-init smoke passed."
