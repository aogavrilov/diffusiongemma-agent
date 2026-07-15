#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-open-interpreter.XXXXXX)"
trap 'rm -rf "$TMP_REPO"' EXIT

echo "hello" >"$TMP_REPO/README.md"

test -s "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json"
python3 -m json.tool "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json" >/dev/null
python3 -m py_compile "$DG_ROOT/scripts/dg_open_interpreter_runner.py"

"$DG_ROOT/scripts/dg_open_interpreter_runner.py" \
  --repo "$TMP_REPO" \
  --config "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json" \
  --dry-run \
  --json >/tmp/dg-open-interpreter-dry.json

python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/dg-open-interpreter-dry.json").read_text(encoding="utf-8"))
assert data["settings"]["api_base"] == "http://127.0.0.1:4100/v1", data
assert data["settings"]["model"] == "openai/diffusiongemma-local", data
assert data["settings"]["auto_run"] is False, data
assert data["module"] == "interpreter", data
PY

"$DG_ROOT/scripts/run_open_interpreter_local.sh" --help-local >/tmp/dg-open-interpreter-help.txt
grep -F "Open Interpreter" /tmp/dg-open-interpreter-help.txt

echo "Open Interpreter local profile smoke passed."
