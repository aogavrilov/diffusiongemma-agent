#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

audit_json="$("$DG_ROOT/scripts/dg_agent.sh" bootstrap --json)"
JSON_OUT="$audit_json" python3 - <<'PY'
import json
import os

data = json.loads(os.environ["JSON_OUT"])
assert set(data["selected"]) == {"aider", "agentapi", "opencode", "goose", "litellm", "mcp", "serena"}, data["selected"]
assert data["install_requested"] is False, data
after = {row["id"]: row for row in data["after"]}
for key in data["selected"]:
    assert key in after, key
    assert after[key]["install_script_exists"], after[key]
PY

"$DG_ROOT/scripts/dg_agent.sh" bootstrap --only aider,litellm --json >/tmp/dg-bootstrap-subset.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-bootstrap-subset.json").read_text(encoding="utf-8"))
assert data["selected"] == ["aider", "litellm"], data["selected"]
PY

"$DG_ROOT/scripts/dg_agent.sh" bootstrap --external --json >/tmp/dg-bootstrap-external.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-bootstrap-external.json").read_text(encoding="utf-8"))
selected = set(data["selected"])
assert {"aider", "agentapi", "opencode", "goose", "litellm", "mcp", "serena"} <= selected, selected
assert {"openhands", "mini-swe-agent", "swe-agent"} <= selected, selected
after = {row["id"]: row for row in data["after"]}
for key in ["openhands", "mini-swe-agent", "swe-agent"]:
    assert after[key]["external"] is True, after[key]
    assert after[key]["install_script_exists"], after[key]
PY

"$DG_ROOT/scripts/dg_agent.sh" bootstrap --only openhands,mini-swe-agent,swe-agent --json >/tmp/dg-bootstrap-external-subset.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-bootstrap-external-subset.json").read_text(encoding="utf-8"))
assert data["selected"] == ["openhands", "mini-swe-agent", "swe-agent"], data["selected"]
assert all(row["external"] for row in data["after"]), data["after"]
PY

"$DG_ROOT/scripts/dg_agent.sh" bootstrap --smoke-static --json >/tmp/dg-bootstrap-static.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-bootstrap-static.json").read_text(encoding="utf-8"))
smokes = data["smoke_results"]
assert len(smokes) == 1, smokes
assert smokes[0]["suite"] == "wrappers", smokes
assert smokes[0]["status"] == "success", smokes
PY

echo "DG wrapper bootstrap smoke passed."
