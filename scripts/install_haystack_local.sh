#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV="$DG_ROOT/.tools/uv/bin/uv"
VENV="$DG_ROOT/.venv-haystack"
if [[ -x "$VENV/bin/python" ]]; then
  "$VENV/bin/python" - <<'PY'
from haystack import Document
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

print("haystack ready")
print(Document.__name__)
print(InMemoryDocumentStore.__name__)
print(InMemoryBM25Retriever.__name__)
print(OpenAIChatGenerator.__name__)
PY
  exit 0
fi

if [[ ! -x "$UV" ]]; then
  "$DG_ROOT/scripts/install_uv_local.sh"
fi

"$UV" venv "$VENV"
"$UV" pip install --python "$VENV/bin/python" haystack-ai

"$VENV/bin/python" - <<'PY'
from haystack import Document
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

print("haystack ready")
print(Document.__name__)
print(InMemoryDocumentStore.__name__)
print(InMemoryBM25Retriever.__name__)
print(OpenAIChatGenerator.__name__)
PY
