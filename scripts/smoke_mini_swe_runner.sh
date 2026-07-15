#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-mini-swe-runner.XXXXXX)"
OUT_DIR="$(mktemp -d /tmp/dg-mini-swe-runner-out.XXXXXX)"

cleanup() {
  echo "DG mini-SWE runner smoke repo: $TMP_REPO"
  echo "DG mini-SWE runner smoke out: $OUT_DIR"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

"$DG_ROOT/scripts/dg_agent.sh" mini-swe-run \
  --repo "$TMP_REPO" \
  --task "Inspect calc.py without changing files." \
  --out-dir "$OUT_DIR" \
  --dry-run \
  --json >/tmp/dg-mini-swe-runner.json

python3 - <<'PY'
import json
import importlib.util
from pathlib import Path

import yaml

data = json.loads(Path("/tmp/dg-mini-swe-runner.json").read_text(encoding="utf-8"))
assert data["status"] == "dry-run", data
assert data["repo"].startswith("/tmp/dg-mini-swe-runner."), data
assert "mini-swe-agent.dg.yaml" in data["config"], data
assert data["model_registry"].endswith("litellm-local-model-registry.json"), data
assert data["trajectory"].endswith("trajectory.json"), data
assert data["command"][0].endswith("/mini") or data["command"][0] == "mini", data
assert "-c" in data["command"], data
assert "-t" in data["command"], data
assert Path(data["run_dir"]).exists(), data
assert Path(data["run_dir"], "command.sh").exists(), data
assert Path(data["stdout"]).exists(), data
assert Path(data["stderr"]).exists(), data
assert Path(data["run_dir"], "report.json").exists(), data
profile = yaml.safe_load(Path(data["config"]).read_text(encoding="utf-8"))
assert "model" in profile and "environment" in profile and "agent" in profile, profile
assert "model" not in profile["agent"], profile
assert "environment" not in profile["agent"], profile
assert profile["model"]["model_name"] == "openai/diffusiongemma-local", profile
assert profile["model"]["model_class"] == "litellm_textbased", profile
assert "format_error_template" in profile["model"], profile
assert profile["environment"]["timeout"] == 480, profile

spec = importlib.util.spec_from_file_location("dg_mini_swe_runner", Path(data["config"]).parents[2] / "scripts" / "dg_mini_swe_runner.py")
if spec is None or spec.loader is None:
    raise AssertionError("could not load dg_mini_swe_runner")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
bad_traj = Path("/tmp/dg-mini-swe-repeated-format.traj.json")
bad_traj.write_text(json.dumps({"messages": [{"role": "exit", "content": "RepeatedFormatError", "extra": {"exit_status": "RepeatedFormatError"}}]}), encoding="utf-8")
analysis = module.analyze_trajectory(bad_traj, "")
assert analysis["failed"], analysis
PY

test -f "$DG_ROOT/.tools/external-agents/mini-swe-config/.env"
grep -F "MSWEA_CONFIGURED=true" "$DG_ROOT/.tools/external-agents/mini-swe-config/.env"
grep -F "MSWEA_MODEL_NAME=openai/diffusiongemma-local" "$DG_ROOT/.tools/external-agents/mini-swe-config/.env"

"$DG_ROOT/scripts/dg_agent.sh" mini-swe-runs list --root "$OUT_DIR" --json >/tmp/dg-mini-swe-runs-list.json
"$DG_ROOT/scripts/dg_agent.sh" mini-swe-runs show --root "$OUT_DIR" --latest --json >/tmp/dg-mini-swe-runs-show.json
"$DG_ROOT/scripts/dg_agent.sh" mini-swe-runs artifact report --root "$OUT_DIR" --latest --path-only >/tmp/dg-mini-swe-runs-report-path.txt
"$DG_ROOT/scripts/dg_agent.sh" mini-swe-runs artifact command --root "$OUT_DIR" --latest --path-only >/tmp/dg-mini-swe-runs-command-path.txt

python3 - <<'PY'
import json
from pathlib import Path

listed = json.loads(Path("/tmp/dg-mini-swe-runs-list.json").read_text(encoding="utf-8"))
assert len(listed["runs"]) == 1, listed
assert listed["runs"][0]["status"] == "dry-run", listed
shown = json.loads(Path("/tmp/dg-mini-swe-runs-show.json").read_text(encoding="utf-8"))
assert shown["status"] == "dry-run", shown
report_path = Path("/tmp/dg-mini-swe-runs-report-path.txt").read_text(encoding="utf-8").strip()
command_path = Path("/tmp/dg-mini-swe-runs-command-path.txt").read_text(encoding="utf-8").strip()
assert report_path.endswith("report.json"), report_path
assert command_path.endswith("command.sh"), command_path
assert Path(report_path).exists(), report_path
assert Path(command_path).exists(), command_path
PY

echo "DG mini-SWE runner smoke passed."
