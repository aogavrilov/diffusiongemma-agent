# LlamaIndex Local Profile

LlamaIndex is configured as an optional OSS RAG/agent framework over the local
OpenAI-compatible DiffusionGemma endpoint.

```bash
scripts/install_llamaindex_local.sh
scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run
scripts/dg_agent.sh llamaindex -- --repo /repo --smoke-import
scripts/dg_agent.sh llamaindex -- --repo /repo --task "Summarize this repo"
scripts/dg_agent.sh llamaindex -- --repo /repo --task "Summarize this repo" --direct
```

The profile uses:

```text
api_base: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
llm: llama_index.llms.openai_like.OpenAILike
workflow: llama_index.core.agent.workflow.AgentWorkflow
agent: llama_index.core.agent.workflow.ReActAgent
function_agent: llama_index.core.agent.workflow.FunctionAgent
context_window: 768
max_tokens: 256
is_function_calling_model: false
tools: list_files, read_file, search_repo
```

`AgentWorkflow.from_tools_or_functions` is used because LlamaIndex selects
`ReActAgent` when the configured LLM does not support native function calling.
`FunctionAgent` remains listed for future profiles where
`is_function_calling_model=true`.

Keep real repository edits on `scripts/dg_agent.sh agent/session/task`. Use
LlamaIndex for RAG/query-engine and framework compatibility experiments.
