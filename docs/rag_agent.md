# Agent-Side RAG

The fast local model cannot hold a whole repository in prompt. The practical
agent pattern is:

1. Search locally with `rg`.
2. Build a tiny file map.
3. Read only matching snippets.
4. Send the compact context to the OpenAI-compatible local endpoint.
5. Let an outer agent or human apply and test patches.

This repo includes a minimal read-only wrapper:

```text
scripts/rag_code_agent.py
scripts/dg_agent.sh rag
.dg-agent/bin/rag
scripts/dg_agent.sh repo-pack
.dg-agent/bin/repo-pack
scripts/dg_agent.sh repo-map
.dg-agent/bin/repo-map
scripts/dg_agent.sh ast-grep
.dg-agent/bin/ast-grep
scripts/dg_agent.sh code-outline
.dg-agent/bin/code-outline
```

It does not edit files. It retrieves context and asks the currently running
local model for the next action or a patch.

## Start The Fast Backend

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\root\diffusiongemma-agent\scripts\start_agent_fast_service_windows.ps1 -StopExisting
```

The expected endpoint is:

```text
http://127.0.0.1:4100/v1
```

## Ask About A Repo

From WSL:

```bash
cd /root/diffusiongemma-agent
scripts/dg_agent.sh rag --repo /path/to/repo \
  --task "Find where the server starts and explain how to change the port"
```

Preview only the retrieved context:

```bash
scripts/dg_agent.sh rag --repo /path/to/repo \
  --task "where is CUDA env configured?" \
  --print-context
```

After `workspace-init`, use the repo-local launcher:

```bash
.dg-agent/bin/rag --task "where is CUDA env configured?" --print-context
```

## Client Settings

The fast backend has `MAXTOK=768`, so keep retrieval compact:

```text
--max-context-chars 500-900
--max-files 2-3
--max-tokens 128-256
```

For file-level coding tasks, ask for one scoped change at a time:

```bash
scripts/dg_agent.sh rag --repo /path/to/repo \
  --max-context-chars 650 --max-files 2 --max-tokens 128 \
  --task "In server.py, find the health endpoint and propose the smallest patch to add uptime_ms"
```

The same retrieval path is exposed to MCP clients as `dg_rag_context` and
`dg_rag_answer`. Prefer `dg_rag_context` when an external agent should inspect
the retrieved file map/snippets before deciding whether to call the model.

For OSS repository packing, use the Repomix wrapper:

```bash
scripts/dg_agent.sh repo-pack --repo /path/to/repo \
  --include "src/**" \
  --style markdown \
  --compress \
  --token-budget 20000 \
  --stdout
```

The MCP tool name is `dg_repo_pack`. Prefer tight include filters so the packed
artifact stays within the local model's small working context.

For an Aider-style repository sketch, use:

```bash
scripts/dg_agent.sh repo-map --repo /path/to/repo \
  --map-tokens 512 \
  --map-only
```

The MCP tool name is `dg_repo_map`. It uses upstream Aider's repo-map logic but
keeps history files temporary and passes `--no-gitignore`, so it should not
dirty the target repo.

For structural search, use the upstream ast-grep wrapper:

```bash
scripts/dg_agent.sh ast-grep --repo /path/to/repo \
  --lang python \
  --pattern 'return $X' \
  --json
```

The MCP tool name is `dg_ast_grep`. Use it when an agent needs language-aware
matches instead of raw text matches from `rg`.

For symbol maps, use the upstream ast-grep outline wrapper:

```bash
scripts/dg_agent.sh code-outline --repo /path/to/repo \
  --lang python \
  --view expanded \
  --json
```

The MCP tool name is `dg_code_outline`. Use it before file reads when class,
function, import, or member names are enough to choose the next file.

## Why This Works

The model sees only a small, relevant working set instead of the whole repo.
The agent wrapper owns tools such as `rg`, file reading, patch application, git
status, and tests. The model only reasons over the selected snippets.
