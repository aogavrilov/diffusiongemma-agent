#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-codex-profile.XXXXXX)"

cleanup() {
  echo "DG codex-profile smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > main.py <<'PY'
def main():
    return "ok"
PY
git add main.py
git commit -qm "initial"

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-codex-workspace.json
"$DG_ROOT/scripts/dg_agent.sh" codex-profile --repo "$TMP_REPO" --target all --json >/tmp/dg-codex-profile.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-codex-profile.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["files"][0]["target"] == "config", data
assert data["files"][0]["status"] == "written", data
assert data["files"][0]["path"].endswith(".codex/config.toml"), data
assert data["env"] == ".dg-agent/codex.env", data
PY

test -s .dg-agent/CODEX.md
test -s .dg-agent/codex.config.toml
test -s .dg-agent/codex.env
test -s .dg-agent/commands/dg-codex.md
test -s .dg-agent/bin/codex-profile
test -s .codex/config.toml
grep -F "DG Codex CLI Profile" .dg-agent/CODEX.md
grep -F "DiffusionGemma Local Safe Agent Proxy" .dg-agent/codex.config.toml
grep -F "base_url = \"http://127.0.0.1:8090/v1\"" .codex/config.toml
grep -F "model = \"diffusiongemma-26b-a4b-it-iq4xs-aider-local\"" .codex/config.toml
grep -F "wire_api = \"chat\"" .codex/config.toml
grep -F "OPENAI_API_KEY=dummy" .dg-agent/codex.env

.dg-agent/bin/codex-profile --target all --json >/tmp/dg-codex-profile-second.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-codex-profile-second.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["files"][0]["status"] == "unchanged", data
PY

"$DG_ROOT/scripts/dg_agent.sh" codex-profile --repo "$TMP_REPO" --target config --dry-run --force --json >/tmp/dg-codex-profile-dry.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-codex-profile-dry.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["dry_run"] is True, data
PY

printf '\n# local edit\n' >> .codex/config.toml
if "$DG_ROOT/scripts/dg_agent.sh" codex-profile --repo "$TMP_REPO" --target all --json >/tmp/dg-codex-profile-blocked.json; then
  echo "codex-profile should block changed config without --force" >&2
  exit 1
fi
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-codex-profile-blocked.json").read_text(encoding="utf-8"))
assert data["status"] == "blocked", data
assert data["files"][0]["status"] == "blocked", data
PY

"$DG_ROOT/scripts/dg_agent.sh" codex-profile --repo "$TMP_REPO" --target all --force --json >/tmp/dg-codex-profile-force.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-codex-profile-force.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert data["files"][0]["status"] == "updated", data
PY

echo "DG codex-profile passed."
