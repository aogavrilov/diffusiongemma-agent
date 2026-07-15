#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$DG_ROOT/scripts/dg_agent.sh" capabilities --json --timeout 120 >/tmp/dg-capabilities-smoke.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-capabilities-smoke.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
paths = data.get("report_paths", {})
assert paths.get("latest"), data
assert Path(paths["latest"]).exists(), paths
scenarios = {item["name"]: item for item in data["scenarios"]}
assert scenarios["workspace-run-dry"]["status"] == "passed", scenarios
assert scenarios["workspace-launchers-static"]["status"] == "passed", scenarios
assert scenarios["workspace-launchers-static"]["launchers_checked"] >= 26, scenarios["workspace-launchers-static"]
assert not scenarios["workspace-launchers-static"]["failed_launchers"], scenarios["workspace-launchers-static"]
assert ".dg-agent" not in scenarios["workspace-launchers-static"]["git_status"], scenarios["workspace-launchers-static"]
assert scenarios["oss-wrapper-audit-static"]["status"] == "passed", scenarios
assert {"aider", "agentapi", "opencode", "goose", "litellm", "serena"} <= set(scenarios["oss-wrapper-audit-static"]["installed"]), scenarios["oss-wrapper-audit-static"]
assert not scenarios["oss-wrapper-audit-static"]["missing"], scenarios["oss-wrapper-audit-static"]
assert not scenarios["oss-wrapper-audit-static"]["failed_smokes"], scenarios["oss-wrapper-audit-static"]
assert scenarios["external-agent-profiles-static"]["status"] == "passed", scenarios
assert scenarios["external-agent-profiles-static"]["mini_swe_agent_installed"] is True, scenarios["external-agent-profiles-static"]
assert scenarios["external-agent-profiles-static"]["mini_swe_agent_binary"].endswith("/.tools/external-agents/bin/mini"), scenarios["external-agent-profiles-static"]
assert scenarios["proxy-adapter-static"]["status"] == "passed", scenarios
assert scenarios["supervisor-exact-replace"]["status"] == "passed", scenarios
assert scenarios["supervisor-exact-replace"]["strategy"] == "deterministic-first", scenarios["supervisor-exact-replace"]
assert scenarios["workspace-run-dry"]["launchers_ok"] is True, scenarios["workspace-run-dry"]
assert ".dg-agent" not in scenarios["workspace-run-dry"]["git_status"], scenarios["workspace-run-dry"]
PY

"$DG_ROOT/scripts/dg_agent.sh" capabilities --latest --json >/tmp/dg-capabilities-latest.json
"$DG_ROOT/scripts/dg_agent.sh" capabilities --latest --path-only >/tmp/dg-capabilities-latest-path.txt

python3 - <<'PY'
import json
from pathlib import Path

latest = json.loads(Path("/tmp/dg-capabilities-latest.json").read_text(encoding="utf-8"))
assert latest["status"] == "success", latest
path = Path("/tmp/dg-capabilities-latest-path.txt").read_text(encoding="utf-8").strip()
assert path, path
assert Path(path).exists(), path
assert Path(path).name == "latest.json", path
PY

echo "DG capabilities smoke passed."
