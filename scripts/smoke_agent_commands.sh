#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-agent-commands.XXXXXX)"

cleanup() {
  echo "DG agent-commands repo: $TMP_REPO"
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

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-agent-commands-workspace.json
"$DG_ROOT/scripts/dg_agent.sh" agent-commands --repo "$TMP_REPO" --target all --json >/tmp/dg-agent-commands.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-commands.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["files"][0]["target"] == "claude-skill", data
assert data["files"][0]["status"] == "written", data
assert data["files"][0]["path"].endswith(".claude/skills/dg-local-agent/SKILL.md"), data
PY

test -s .dg-agent/COMMANDS.md
test -s .dg-agent/command-kit.json
test -s .dg-agent/commands/dg-report.md
test -s .dg-agent/commands/dg-smoke.md
test -s .dg-agent/commands/dg-context.md
test -s .dg-agent/commands/dg-plan-task.md
test -s .dg-agent/commands/dg-agent.md
test -s .dg-agent/commands/dg-verify.md
test -s .dg-agent/commands/dg-mcp-handoff.md
test -s .dg-agent/commands/dg-codex.md
test -s .dg-agent/claude-skill/SKILL.md
test -s .claude/skills/dg-local-agent/SKILL.md
grep -F "DG Agent Command Kit" .dg-agent/COMMANDS.md
grep -F "dg_client_report" .dg-agent/command-kit.json
grep -F "DG Local Agent Skill" .claude/skills/dg-local-agent/SKILL.md
grep -F ".dg-agent/bin/client-report --client cursor --live" .claude/skills/dg-local-agent/SKILL.md

.dg-agent/bin/agent-commands --target all --json >/tmp/dg-agent-commands-second.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-commands-second.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["files"][0]["status"] == "unchanged", data
PY

"$DG_ROOT/scripts/dg_agent.sh" agent-commands --repo "$TMP_REPO" --target claude-skill --dry-run --force --json >/tmp/dg-agent-commands-dry.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-commands-dry.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["dry_run"] is True, data
PY

printf '\nlocal edit\n' >> .claude/skills/dg-local-agent/SKILL.md
if "$DG_ROOT/scripts/dg_agent.sh" agent-commands --repo "$TMP_REPO" --target all --json >/tmp/dg-agent-commands-blocked.json; then
  echo "agent-commands should block changed skill without --force" >&2
  exit 1
fi
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-commands-blocked.json").read_text(encoding="utf-8"))
assert data["status"] == "blocked", data
assert data["files"][0]["status"] == "blocked", data
PY

"$DG_ROOT/scripts/dg_agent.sh" agent-commands --repo "$TMP_REPO" --target all --force --json >/tmp/dg-agent-commands-force.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-agent-commands-force.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["files"][0]["status"] == "updated", data
PY

echo "DG agent-commands passed."
