#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-haystack.XXXXXX)"
PY_CMD="python3"
if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
  PY_CMD="python"
fi

python_path() {
  if [[ "${OS:-}" == "Windows_NT" ]] && command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

cleanup() {
  echo "DG Haystack smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
TMP_REPO_PY="$(python_path "$TMP_REPO")"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/install_haystack_local.sh"
test -x "$DG_ROOT/scripts/run_haystack_local.sh"
test -x "$DG_ROOT/scripts/dg_haystack_runner.py"
bash -n "$DG_ROOT/scripts/install_haystack_local.sh" "$DG_ROOT/scripts/run_haystack_local.sh"
"$PY_CMD" -m py_compile "$DG_ROOT/scripts/dg_haystack_runner.py"
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/haystack.dg.json" >/dev/null

"$DG_ROOT/scripts/run_haystack_local.sh" --help-local >/tmp/dg-haystack-help.txt
grep -F "Haystack BM25 RAG" /tmp/dg-haystack-help.txt

DRY_JSON=/tmp/dg-haystack-dry.json
"$PY_CMD" "$DG_ROOT/scripts/dg_haystack_runner.py" \
  --repo "$TMP_REPO_PY" \
  --config "$DG_ROOT/configs/client_profiles/haystack.dg.json" \
  --dry-run \
  --json >"$DRY_JSON"

HAYSTACK_DRY_JSON="$(python_path "$DRY_JSON")" "$PY_CMD" - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ["HAYSTACK_DRY_JSON"]).read_text(encoding="utf-8"))
assert data["document_store"].endswith("InMemoryDocumentStore"), data
assert data["retriever"].endswith("InMemoryBM25Retriever"), data
assert data["generator"].endswith("OpenAIChatGenerator"), data
assert data["generator_kwargs"]["api_base_url"] == "http://127.0.0.1:8090/v1", data
assert data["generator_kwargs"]["model"] == "diffusiongemma-local", data
assert data["retrieval"]["top_k"] == 4, data
PY

"$DG_ROOT/scripts/dg_agent.sh" haystack -- --repo "$TMP_REPO_PY" --dry-run --json >/tmp/dg-haystack-dg-dry.json
grep -F "OpenAIChatGenerator" /tmp/dg-haystack-dg-dry.json
grep -F "InMemoryBM25Retriever" /tmp/dg-haystack-dg-dry.json

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO_PY" --json >/tmp/dg-haystack-workspace.json
test -s "$TMP_REPO/.dg-agent/haystack.dg.json"
"$PY_CMD" -m json.tool "$TMP_REPO/.dg-agent/haystack.dg.json" >/dev/null
test -x "$TMP_REPO/.dg-agent/bin/haystack"
bash -n "$TMP_REPO/.dg-agent/bin/haystack"
"$TMP_REPO/.dg-agent/bin/haystack" --dry-run --json >/tmp/dg-haystack-workspace-dry.json
grep -F "OpenAIChatGenerator" /tmp/dg-haystack-workspace-dry.json

echo "DG Haystack local profile smoke passed."
