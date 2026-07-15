#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-ide-clients.XXXXXX)"

cleanup() {
  echo "DG IDE clients smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > app.py <<'PY'
def add(a, b):
    return a + b
PY
git add app.py
git commit -qm "initial"

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-ide-clients-workspace.json

test -s .dg-agent/IDE_CLIENTS.md
test -s .dg-agent/ide-client-snippets.json
test -s .dg-agent/openai-compatible.local.json
test -s .dg-agent/openai.env
test -s .dg-agent/continue.config.yaml
test -s .dg-agent/kilo-code.config.json

python3 -m json.tool .dg-agent/ide-client-snippets.json >/dev/null
python3 -m json.tool .dg-agent/openai-compatible.local.json >/dev/null
python3 -m json.tool .dg-agent/kilo-code.config.json >/dev/null

grep -F "DG IDE Client Profiles" .dg-agent/IDE_CLIENTS.md
grep -F "Continue" .dg-agent/IDE_CLIENTS.md
grep -F "Cline" .dg-agent/IDE_CLIENTS.md
grep -F "Roo Code" .dg-agent/IDE_CLIENTS.md
grep -F "Kilo Code" .dg-agent/IDE_CLIENTS.md
grep -F "http://127.0.0.1:4100/v1" .dg-agent/IDE_CLIENTS.md
grep -F "http://127.0.0.1:8090/v1" .dg-agent/IDE_CLIENTS.md
grep -F "provider: openai" .dg-agent/continue.config.yaml
grep -F "diffusiongemma-local" .dg-agent/openai-compatible.local.json
grep -F "OPENAI_BASE_URL=http://127.0.0.1:4100/v1" .dg-agent/openai.env

python3 - <<'PY'
import json
from pathlib import Path

snippets = json.loads(Path(".dg-agent/ide-client-snippets.json").read_text(encoding="utf-8"))
assert snippets["endpoints"]["chat"]["base_url"] == "http://127.0.0.1:4100/v1", snippets
assert snippets["endpoints"]["chat"]["model"] == "diffusiongemma-local", snippets
assert snippets["endpoints"]["safe_agent_proxy"]["base_url"] == "http://127.0.0.1:8090/v1", snippets
assert snippets["endpoints"]["safe_agent_proxy"]["model"] == "diffusiongemma-26b-a4b-it-iq4xs-aider-local", snippets
assert snippets["clients"]["continue"]["config_file"] == ".dg-agent/continue.config.yaml", snippets
assert snippets["clients"]["cline"]["api_provider"] == "OpenAI Compatible", snippets
assert snippets["clients"]["roo_code"]["api_provider"] == "OpenAI Compatible", snippets
assert snippets["clients"]["kilo_code"]["template_file"] == ".dg-agent/kilo-code.config.json", snippets

kilo = json.loads(Path(".dg-agent/kilo-code.config.json").read_text(encoding="utf-8"))
safe = kilo["providers"]["diffusiongemma-local-safe-agent"]
chat = kilo["providers"]["diffusiongemma-local-chat"]
assert safe["type"] == "openai-compatible", kilo
assert safe["baseUrl"] == "http://127.0.0.1:8090/v1", kilo
assert safe["limit"]["context"] == 768, kilo
assert chat["baseUrl"] == "http://127.0.0.1:4100/v1", kilo

workspace = json.loads(Path("/tmp/dg-ide-clients-workspace.json").read_text(encoding="utf-8"))
names = {Path(item["path"]).name for item in workspace["files"]}
assert "IDE_CLIENTS.md" in names, workspace
assert "ide-client-snippets.json" in names, workspace
assert "kilo-code.config.json" in names, workspace
PY

echo "DG IDE client profiles smoke passed."
