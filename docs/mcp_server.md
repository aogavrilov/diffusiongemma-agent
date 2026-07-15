# DG MCP Server

The MCP layer is a local stdio bridge around the existing DiffusionGemma agent
commands. It is meant for MCP-capable IDEs and OSS agents that can launch a
server process and call tools.

The default server uses the official `modelcontextprotocol/python-sdk`
`FastMCP` implementation. A dependency-free legacy JSON-RPC fallback is kept for
debugging.

Run it directly:

```bash
cd /root/diffusiongemma-agent
scripts/dg_agent.sh mcp --list-tools
scripts/dg_agent.sh mcp
scripts/dg_agent.sh mcp --legacy
```

Repo-local launchers are created by:

```bash
scripts/dg_agent.sh workspace-init --repo /path/to/repo
```

Then use:

```bash
/path/to/repo/.dg-agent/bin/mcp --list-tools
/path/to/repo/.dg-agent/bin/mcp
/path/to/repo/.dg-agent/bin/mcp-http --host 127.0.0.1 --port 8765
/path/to/repo/.dg-agent/bin/serena-mcp --help-local
/path/to/repo/.dg-agent/bin/opencode-mcp --help
/path/to/repo/.dg-agent/bin/opencode-acp --help
/path/to/repo/.dg-agent/bin/goose-mcp --help-local
/path/to/repo/.dg-agent/bin/goose-acp --help
/path/to/repo/.dg-agent/bin/goose-serve --help
```

The checked-in OpenCode MCP profile mounts `dg_agent` and `repomix`. Serena is
available as a separate IDE MCP entry because its Pyright startup exceeds
OpenCode's fixed connection timeout on this host.
The checked-in Goose MCP profile mounts `dg_agent` and `serena`.

Client config:

```text
configs/client_profiles/mcp-server.json
configs/client_profiles/mcp-client-snippets.json
configs/client_profiles/claude-code.mcp.json
configs/client_profiles/claude-desktop-mcp.json
configs/client_profiles/cursor.mcp.json
configs/client_profiles/vscode.mcp.json
```

Workspace copy:

```text
.dg-agent/mcp-server.json
.dg-agent/mcp-client-snippets.json
.dg-agent/claude-code.mcp.json
.dg-agent/claude-desktop-mcp.json
.dg-agent/cursor.mcp.json
.dg-agent/vscode.mcp.json
.dg-agent/goose-mcp.dg.yaml
```

Client targets:

```text
Claude Code project: .mcp.json <- .dg-agent/claude-code.mcp.json
Claude Desktop: claude_desktop_config.json <- .dg-agent/claude-desktop-mcp.json
Cursor project: .cursor/mcp.json <- .dg-agent/cursor.mcp.json
VS Code workspace: .vscode/mcp.json <- .dg-agent/vscode.mcp.json
```

`mcp-client-snippets.json` preserves all of those shapes in one manifest. The
Cursor/Claude-family configs use top-level `mcpServers`; VS Code uses top-level
`servers` with a `stdio` server type. The snippets also include optional native
Repomix MCP server entries through `scripts/run_repomix_mcp.sh` for clients
and Serena MCP server entries through `scripts/run_serena_mcp.sh` for clients
that should use upstream repository-packing and semantic/LSP tools directly
alongside the DG tools.

For clients that cannot launch a local stdio process, run the same DG MCP server
over the official SDK streamable HTTP transport:

```bash
scripts/dg_agent.sh mcp-http -- --host 127.0.0.1 --port 8765
```

Endpoint:

```text
http://127.0.0.1:8765/mcp
```

You can also merge the local server entry into a repo client config without
overwriting unrelated servers:

```bash
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client claude-code
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor --with-repomix
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor --with-serena
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor --with-repomix --with-serena
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor --with-oss-stack
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client vscode
scripts/dg_agent.sh mcp-client-config --client claude-desktop --target /path/to/claude_desktop_config.json
```

After `workspace-init`, the same command is available as:

```bash
.dg-agent/bin/mcp-client-config --client cursor
.dg-agent/bin/mcp-client-config --client cursor --with-repomix
.dg-agent/bin/mcp-client-config --client cursor --with-serena
.dg-agent/bin/mcp-client-config --client cursor --with-oss-stack
```

Serena is an upstream semantic/LSP MCP server. Install and smoke-test it with:

```bash
scripts/install_serena_local.sh
scripts/dg_agent.sh smoke --suite serena-mcp --timeout 300
```

On Windows, use `scripts/run_serena_mcp.sh` rather than a direct Serena binary.
The runner prefers a WSL bridge with local Linux Node/Pyright so semantic tools
avoid blocked Windows `.exe` shims and native `.pyd` wheels. The smoke includes
a live `get_symbols_overview` call, so it validates the Pyright-backed symbol
path as well as MCP startup.

Run it over stdio from a target repo:

```bash
.dg-agent/bin/serena-mcp
```

Or expose Serena over streamable HTTP when a client cannot spawn stdio:

```bash
.dg-agent/bin/serena-mcp --transport streamable-http --port 9121
```

For clients that read project instruction files, install matching DG/MCP usage
rules:

```bash
.dg-agent/bin/agent-rules --target all
```

Exposed tools:

- `dg_repo_status`: inspect `git status --short`, diff stat, and untracked files.
- `dg_list_files`: list repository files through `rg --files` with git fallback.
- `dg_code_outline`: bounded symbol outline with upstream ast-grep outline.
- `dg_search`: bounded ripgrep search with line and column locations.
- `dg_ast_grep`: bounded structural code search with upstream ast-grep.
- `dg_read_file`: bounded line-numbered file reads inside the repo.
- `dg_git_diff`: bounded git diff or diff stat reads.
- `dg_task_note`: save durable Markdown task notes under `runlogs/`.
- `dg_task_notes`: list or read saved task notes.
- `dg_status`: check backend, Aider proxy, and LiteLLM health.
- `dg_context`: build the bounded repo context pack for a task.
- `dg_rag_context`: retrieve compact read-only RAG context without calling the model.
- `dg_rag_answer`: ask the local model over compact retrieved repo context.
- `dg_repo_pack`: pack filtered repo content with upstream Repomix.
- `dg_repo_map`: build a bounded upstream Aider repo-map for codebase context.
- `dg_preflight`: check repo workspace, wrappers, services, and GPU readiness.
- `dg_plan`: generate a task-runner JSON plan from a natural-language task.
- `dg_task`: execute an existing task-runner plan; use `dry_run` for inspection.
- `dg_session`: run context -> plan -> task -> verify with rollback on failure.
- `dg_verify`: run or infer a repo verification command.
- `dg_capabilities`: read or run wrapper capability probes.
- `dg_client_smoke`: prepare or validate a target repo for external IDE/agent clients.
- `dg_client_report`: generate `.dg-agent/CLIENT_HANDOFF.md` and `.dg-agent/client-handoff.json`.
- `dg_sessions`: list recent artifacted DG agent sessions.
- `dg_session_artifact`: read a preserved session artifact, defaulting to latest.

Exposed resources:

- `dg://client-pack`: current endpoints, profiles, launchers, and limits.
- `dg://status`: live backend/proxy/LiteLLM health snapshot.
- `dg://usage`: short Markdown usage guide for local agent workflows.
- `dg://notes`: recent task notes saved by MCP clients.
- `dg://notes/latest`: latest task note.
- `dg://sessions`: recent session list.
- `dg://sessions/latest`: latest `session.json`.
- `dg://sessions/latest/diff`: latest `final.diff`.
- `dg://capabilities/latest`: latest saved capability report.
- `dg://client-handoff`: repo-local handoff JSON generated by `dg_client_report`.
- `dg://client-handoff/markdown`: repo-local handoff Markdown generated by `dg_client_report`.
- `dg://agent-hub`: repo-local agent hub JSON generated by `workspace-init`.
- `dg://agent-hub/markdown`: repo-local first-read agent hub Markdown.
- `dg://command-kit`: repo-local command kit JSON for reusable workflows.
- `dg://command-kit/markdown`: repo-local command kit Markdown.
- `dg://ide-clients`: repo-local IDE client snippet JSON.
- `dg://ide-clients/markdown`: repo-local IDE client profile guide.
- `dg://codex-profile`: repo-local Codex CLI profile guide.
- `dg://codex-profile/config`: repo-local Codex CLI config template.

Exposed prompts:

- `dg_agent_session`: guide an MCP client through context -> session -> verify.
- `dg_agent_context`: guide an MCP client to gather bounded repo context before editing.
- `dg_agent_continue_latest`: guide an MCP client to inspect latest artifacts before continuing.

The server runs over MCP stdio through the official Python SDK. It deliberately
maps tools to existing reliable wrapper commands instead of relying on raw
model-generated tool syntax. The smoke test uses the SDK client
`ClientSession` over `stdio_client`, so it checks real MCP compatibility rather
than only hand-written JSON.

For full IDE-agent use, start with the repo tools (`dg_repo_status`,
`dg_list_files`, `dg_repo_map`, `dg_code_outline`, `dg_search`, `dg_ast_grep`, `dg_read_file`, `dg_git_diff`), save handoff state
with `dg_task_note` when useful, then run `dg_preflight` and `dg_context`.
For external clients, call `dg_client_smoke` or `dg_client_report` first; the
latter writes and exposes the repo-local handoff through `dg://client-handoff`.
For first-time bootstrap, read `dg://agent-hub/markdown` and then the matching
command kit, IDE, or Codex resource instead of manually opening repo files.
For larger repository questions, use `dg_rag_context` before asking the model or
planning edits. Use `dg_repo_map` for an Aider-style repository sketch, then `dg_code_outline` when a symbol map is enough to choose files or functions before reading source. Use `dg_ast_grep` for language-aware code patterns such as
returns, decorators, call sites, and declarations. Use `dg_repo_pack` with tight include filters when a Repomix
packed artifact is better than ranked snippets. Use `dg_session` for one-shot bounded edits. Use `dg_plan` followed by
`dg_task` when the client should review or store the plan before executing it.

Verification:

```bash
scripts/dg_agent.sh smoke --suite mcp --timeout 120
scripts/dg_agent.sh smoke --suite goose-mcp --timeout 180
scripts/dg_agent.sh smoke --suite goose-acp --timeout 180
```
