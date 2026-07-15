# Haystack Local RAG Profile

Haystack is configured as an optional OSS RAG pipeline over the local
OpenAI-compatible DiffusionGemma endpoint. It indexes bounded repository files
into a bounded BM25 store before calling the model, which is useful with the
current small context profile. Source documents are cached persistently outside
the target repository under `runlogs/dg-retrieval-index/`.

```bash
scripts/install_haystack_local.sh
scripts/dg_agent.sh haystack -- --repo /repo --dry-run
scripts/dg_agent.sh haystack -- --repo /repo --smoke-import
scripts/dg_agent.sh haystack -- --repo /repo --task "Where is add(a, b) implemented?"
```

The profile uses:

```text
document_store: haystack.document_stores.in_memory.InMemoryDocumentStore
retriever: haystack.components.retrievers.in_memory.InMemoryBM25Retriever
generator: haystack.components.generators.chat.OpenAIChatGenerator
api_base_url: http://127.0.0.1:8090/v1
api_key: dummy
model: diffusiongemma-local
top_k: 4
max_files: 120
max_file_chars: 4000
max_tokens: 256
```

Use `--retrieve-only` for external supervision without a model call. Keep real
repository edits on `scripts/dg_agent.sh autonomous` or the existing bounded
`agent/session/task` routes.
