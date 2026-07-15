#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-ast-grep-smoke.XXXXXX)"

cleanup() {
  echo "DG ast-grep smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cat > "$TMP_REPO/hello.py" <<'PY'
def greet(name):
    return f"hello {name}"

def double(value):
    return value * 2
PY

"$DG_ROOT/scripts/run_ast_grep.sh" --version | grep -F "ast-grep"
"$DG_ROOT/scripts/run_ast_grep.sh" --help-local | grep -F "upstream ast-grep"

"$DG_ROOT/scripts/dg_agent.sh" ast-grep \
  --repo "$TMP_REPO" \
  --lang python \
  --pattern 'return $X' \
  --json \
  --max-matches 5 \
  --max-chars 8000 \
  > /tmp/dg-ast-grep-smoke.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/dg-ast-grep-smoke.json").read_text(encoding="utf-8"))
assert isinstance(data, list), data
assert len(data) == 2, data
texts = {item.get("text") for item in data}
assert 'return f"hello {name}"' in texts, data
assert "return value * 2" in texts, data
assert all(item.get("file", "").endswith("hello.py") for item in data), data
PY

"$DG_ROOT/scripts/dg_agent.sh" ast-grep \
  --repo "$TMP_REPO" \
  --lang python \
  --pattern 'return $X' \
  --files-with-matches \
  > /tmp/dg-ast-grep-files.txt
grep -F "hello.py" /tmp/dg-ast-grep-files.txt

echo "DG ast-grep smoke passed."
