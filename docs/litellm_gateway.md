# LiteLLM Gateway

LiteLLM is an optional OpenAI-compatible gateway in front of the local
DiffusionGemma safe agent gateway on `127.0.0.1:8090`.

It gives external tools one stable endpoint and model alias:

```text
base_url: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
```

Start:

```bash
cd /root/diffusiongemma-agent
scripts/dg_agent.sh litellm
```

Equivalent direct launcher:

```bash
scripts/run_litellm_gateway.sh
```

Start from Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\root\diffusiongemma-agent\scripts\start_litellm_gateway_windows.ps1
```

The gateway config lives at:

```text
configs/litellm.dg.yaml
```

It routes:

```text
diffusiongemma-local -> http://127.0.0.1:8090/v1
diffusiongemma-26b-a4b-it-iq4xs-aider-local -> http://127.0.0.1:8090/v1
```

The second alias exists for Aider and delegated OSS-agent flows that use the
Aider model id directly.

The lower-level safe gateway also exposes discovery endpoints for clients and
diagnostics:

```text
GET http://127.0.0.1:8090/v1/model_card
GET http://127.0.0.1:8090/v1/capabilities
GET http://127.0.0.1:8090/v1/agent/routes
POST http://127.0.0.1:8090/v1/agent/session
POST http://127.0.0.1:8090/v1/agent/tool
POST http://127.0.0.1:8090/v1/agent/context
POST http://127.0.0.1:8090/v1/agent/rag
GET http://127.0.0.1:8090/v1/agent/sessions
GET http://127.0.0.1:8090/v1/agent/sessions/latest
GET http://127.0.0.1:8090/v1/agent/sessions/latest/diff
GET http://127.0.0.1:8090/v1/agent/sessions/latest/artifacts/{artifact}
GET http://127.0.0.1:8090/v1/agent/runs
GET http://127.0.0.1:8090/v1/agent/runs/latest
GET http://127.0.0.1:8090/v1/agent/runs/latest/artifacts/{artifact}
GET http://127.0.0.1:8090/v1/agent/tool_manifest
GET http://127.0.0.1:8090/v1/agent/actions
GET http://127.0.0.1:8090/.well-known/agent.json
GET http://127.0.0.1:8090/openapi.json
```

Those endpoints describe the model limits, safe-mode behavior, OpenAI
Chat/Responses compatibility, tool-call delegation, MCP route, and LiteLLM
route without requiring a client to read repo files first. `tool_manifest`
contains copy-ready OpenAI Chat Completions and Responses API `execute_command`
tool schemas that delegate repository work to `dg_agent.sh session`.

The same manifest also exposes DG-specific OpenAI tool schemas:

```text
execute_command
dg_repo_status
dg_git_diff
dg_list_files
dg_read_file
dg_search
dg_repo_pack
dg_repo_map
dg_ast_grep
dg_code_outline
dg_agent
dg_session
dg_context
dg_rag_context
dg_session_artifact
dg_agent_run_artifact
```

Use these when a client supports function calling but not MCP. The repo tools
are fixed read-only `git`/`rg`/file-read operations for Codex-style navigation.
The OSS repo tools delegate to Repomix, Aider repo-map, and ast-grep/code
outline. `dg_agent` is the high-level facade: read-only tasks run through
tool-loop and edit tasks default to a dry-run session unless HTTP execution is
explicitly enabled. `dg_context` and `dg_rag_context` are read-only context
tools, `dg_session` delegates bounded edits to the artifacted session runner,
`dg_session_artifact` reads the latest or indexed preserved session output, and
`dg_agent_run_artifact` reads high-level `dg_agent` run reports/transcripts.

`POST /v1/agent/tool` is the matching HTTP tool runtime for those schemas. It
accepts either:

```json
{"name": "dg_context", "arguments": {"repo": "/path/to/repo", "task": "Find add(a, b)"}}
```

Read-only repo examples:

```json
{"name": "dg_search", "arguments": {"repo": "/path/to/repo", "query": "def add", "globs": ["*.py"]}}
```

```json
{"name": "dg_read_file", "arguments": {"repo": "/path/to/repo", "path": "calc.py", "start_line": 1, "max_lines": 80}}
```

OSS-backed repo examples:

```json
{"name": "dg_code_outline", "arguments": {"repo": "/path/to/repo", "lang": "python", "paths": ["calc.py"]}}
```

```json
{"name": "dg_repo_pack", "arguments": {"repo": "/path/to/repo", "compress": true, "max_chars": 20000}}
```

High-level facade example:

```json
{"name": "dg_agent", "arguments": {"repo": "/path/to/repo", "task": "Read file calc.py", "mode": "read", "tools": ["dg_read_file"]}}
```

or an OpenAI `tool_call` object:

```json
{
  "tool_call": {
    "id": "call_...",
    "type": "function",
    "function": {
      "name": "dg_context",
      "arguments": "{\"repo\":\"/path/to/repo\",\"task\":\"Find add(a, b)\"}"
    }
  }
}
```

The response includes `tool_response`, a ready `role=tool` payload for the next
OpenAI-compatible turn. Arbitrary `execute_command` shell execution is blocked
in this runtime; use the repo inspection tools for read-only navigation and
`dg_session` for bounded repository changes.

The repo includes a reference tool-loop client that wires these pieces together:

```bash
scripts/dg_agent.sh agent \
  --repo /path/to/repo \
  --task "Find the implementation of add(a, b)" \
  --mode auto

scripts/dg_agent.sh tool-loop \
  --repo /path/to/repo \
  --task "Find the implementation of add(a, b)" \
  --out runlogs/tool-loop/latest.json
```

Use `agent --mode auto` as the high-level local facade. It routes read-only
inspection tasks through the tool-loop and edit tasks through artifacted
sessions. Use `tool-loop` directly when building or debugging a client that
already controls the OpenAI function-call loop.

Use `--stop-after-tool` for raw tool output only. By default the second turn
converts the `role=tool` JSON into a readable deterministic summary. Use
`--tool dg_read_file`, `--tool dg_search`, or `--read-only` to restrict the
tool set for cautious clients.

`POST /v1/agent/session` builds an artifacted `dg_agent.sh session` command and
returns it in dry-run mode by default. Real HTTP-triggered execution is disabled
unless the proxy is started with `DG_AIDER_PROXY_ENABLE_AGENT_EXEC=1` and the
request sets `execute=true`.

`POST /v1/agent/context` and `POST /v1/agent/rag` are read-only context
endpoints for HTTP-only clients. They delegate to the existing
`dg_agent.sh context` and `dg_agent.sh rag --print-context` commands, so clients
can retrieve compact repo context before asking the model or launching a
session. The RAG endpoint is retrieve-only and does not call the model.

Example:

```json
{
  "repo": "/path/to/repo",
  "task": "Find the implementation of add(a, b)",
  "files": ["calc.py"],
  "max_files": 3,
  "max_snippet_chars": 1200
}
```

`GET /v1/agent/sessions*` is read-only access to preserved
`runlogs/dg-agent-sessions/` artifacts for clients that cannot use MCP. The
available artifact names include `context_md`, `plan`, `task_report`,
`verify_report`, `final_diff`, `stdout`, and `stderr`.

`GET /v1/agent/runs*` is read-only access to high-level
`runlogs/dg-agent-runs/` artifacts from `scripts/dg_agent.sh agent`. Available
artifact names include `agent_json`, `transcript`, `stdout`, and `stderr`.

## Smoke

```bash
scripts/dg_agent.sh smoke --suite litellm --timeout 180
scripts/dg_agent.sh smoke --suite openai-sdk --timeout 180
```

The smoke installs LiteLLM if needed, starts it on a temporary port, and checks
the model registry. It deliberately avoids generation and readiness probes
because short generic probes can stress the current DiffusionGemma backend.

The `openai-sdk` smoke separately performs one bounded Python OpenAI SDK chat
completion through the live gateway and then checks that the stack stayed
healthy.

Generic free-form chat requests are served in safe compatibility mode by the
Aider-compatible proxy. They prove client/API compatibility without sending
arbitrary prompts into the DiffusionGemma runner, because those prompts can
crash the current backend. Set `DG_AIDER_PROXY_ENABLE_GENERIC_GENERATION=1`
only for unsafe experiments.

OpenAI-compatible clients that send a command-like `tools` schema, for example
`execute_command(command=...)`, get a real `tool_calls` response in safe mode.
The tool call delegates repository work to:

```bash
scripts/dg_agent.sh session --repo "$(pwd)" ... --rollback-on-failure
```

This gives tool-calling OSS agents a safe execution path without forwarding
their arbitrary planning prompt into the unstable generic backend route.

The same safe delegate is exposed through a minimal Responses API shim:

```text
POST http://127.0.0.1:4100/v1/responses
```

For non-streaming `responses.create(...)` calls with a command-like function
tool, the proxy returns a `function_call` output item whose arguments contain
the delegated `dg_agent.sh session` command. Responses streaming is explicitly
not supported by this local shim.

## Recommended Use

Use LiteLLM for clients that expect a normal OpenAI-compatible endpoint:

- Continue
- Cline/Roo Code
- custom OpenAI SDK scripts
- other agent shells with only `base_url`, `api_key`, and `model` settings

Client profiles:

```text
configs/client_profiles/openai-compatible.local.json
configs/client_profiles/openai.env
configs/client_profiles/continue.config.yaml
```

Docs: `docs/ide_client_profiles.md`.

For reliable code edits, keep using the artifacted Aider/task-runner path:

```bash
scripts/dg_agent.sh session --repo /repo --task "..." --file path --auto-test --rollback-on-failure
```
