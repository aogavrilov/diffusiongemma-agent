#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-code-outline-smoke.XXXXXX)"
PYTHON="$DG_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
    PYTHON="python"
  else
    PYTHON="python3"
  fi
fi

cleanup() {
  echo "DG code-outline smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cat > "$TMP_REPO/hello.py" <<'PY'
import os

class Greeter:
    def __init__(self, prefix):
        self.prefix = prefix

    def greet(self, name):
        return f"{self.prefix} {name}"

def double(value):
    return value * 2
PY

"$DG_ROOT/scripts/dg_agent.sh" code-outline \
  --repo "$TMP_REPO" \
  --lang python \
  --json \
  --max-items 10 \
  --max-chars 8000 \
  > /tmp/dg-code-outline-smoke.json

"$PYTHON" -c '
import json
import sys

data = json.load(sys.stdin)
assert isinstance(data, list), data
assert len(data) == 1, data
entry = data[0]
assert entry["path"].endswith("hello.py"), data
names = {item.get("name") for item in entry.get("items", [])}
assert {"Greeter", "double"} <= names, data
types = {item.get("symbolType") for item in entry.get("items", [])}
assert "class" in types and "function" in types, data
' < /tmp/dg-code-outline-smoke.json

"$DG_ROOT/scripts/dg_agent.sh" code-outline \
  --repo "$TMP_REPO" \
  --lang python \
  --view expanded \
  > /tmp/dg-code-outline-smoke.txt

grep -F "class Greeter" /tmp/dg-code-outline-smoke.txt
grep -F "def greet" /tmp/dg-code-outline-smoke.txt
grep -F "def double" /tmp/dg-code-outline-smoke.txt

echo "DG code-outline smoke passed."
