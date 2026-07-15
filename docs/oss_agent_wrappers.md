# OSS Agent Wrappers

This project intentionally avoids a from-scratch coding agent. The strongest
current stack is a thin local control layer over ready-made OSS tools:

```text
dg_agent.sh agent
  -> rg/file context pack
  -> task-runner plan
  -> Aider-compatible edit path
  -> verification
  -> rollback on failure
  -> preserved session artifacts
```

## Default Path

For an interactive terminal agent on Windows, use upstream OpenCode through
the compact delegate profile:

```powershell
Set-Location C:\path\to\repo
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_agent_windows.ps1
```

It exposes a single OpenCode `bash` tool and has the gateway map that tool to
the verified read/session workflow. This is the default interactive route;
the model does not have to emit a native tool call. The command also has a
non-interactive form:

```powershell
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_agent_windows.ps1 run `
  --format json 'Read src/app.py and explain the request flow. Do not edit files.'
```

For automation and explicit multi-step work, use:

Use:

```bash
cd /root/diffusiongemma-agent
scripts/dg_agent.sh agent \
  --repo /path/to/repo \
  --task "Fix the failing test and keep the public API unchanged" \
  --file path/to/file.py
```

Why this is the default:

- Aider is better for file edits than a raw chat loop.
- The local DiffusionGemma runtime has small practical context, so the wrapper
  must feed only relevant files and snippets.
- The task runner adds deterministic first-pass fixes, verification, rollback,
  and structured reports.
- Every run is artifacted under `runlogs/dg-agent-sessions/`.

Inspect wrapper status:

```bash
scripts/dg_agent.sh wrappers
scripts/dg_agent.sh wrappers --json
```

Audit or restore local wrapper installs:

```bash
scripts/dg_agent.sh bootstrap
scripts/dg_agent.sh bootstrap --json
scripts/dg_agent.sh bootstrap --install
scripts/dg_agent.sh bootstrap --only aider,litellm --install
scripts/dg_agent.sh bootstrap --external
scripts/dg_agent.sh bootstrap --only openhands,mini-swe-agent --install
scripts/dg_agent.sh bootstrap --smoke-static
```

`bootstrap` is audit-only by default. It runs network/package installers only
when `--install` is passed. External OpenHands/SWE-family wrappers are opt-in:
use `--external` for audit or `--only ... --install` for selected installs.

Export client settings for external OSS agents and IDE clients:

```bash
scripts/dg_agent.sh client-pack
scripts/dg_agent.sh client-pack --json
scripts/dg_agent.sh client-pack --env
scripts/dg_agent.sh client-pack --write
```

Prepare a target repo with repo-local profiles:

```bash
scripts/dg_agent.sh workspace-init --repo /path/to/repo
```

This writes `.dg-agent/` inside the target repo with the client pack, env vars,
local copies of Continue/OpenCode/MCP profiles, and repo-local launchers under
`.dg-agent/bin/`.

It also writes `.dg-agent/IDE_CLIENTS.md`, `.dg-agent/ide-client-snippets.json`,
and `.dg-agent/kilo-code.config.json` for existing IDE agents such as Continue,
Cline, Roo Code, and Kilo Code. Use the LiteLLM endpoint for chat/edit and the
safe proxy endpoint for command-like tool delegation.

For Codex CLI, use the generated safe-proxy project profile:

```bash
.dg-agent/bin/codex-profile --target all
source .dg-agent/codex.env
codex
```

## Installed OSS Layers

| Layer | Role | Local command | Status |
| --- | --- | --- | --- |
| Aider | Primary file-edit engine | `scripts/run_aider_local.sh /repo` | primary backend for edits |
| Aider repo-map | OSS repository sketch | `scripts/dg_agent.sh repo-map --repo /repo --map-tokens 512` | context tool |
| AgentAPI | Web/API surface over Aider | `scripts/dg_agent.sh web --repo /repo --port 3284` | useful UI/API layer |
| OpenCode compact delegate | Primary bounded terminal workflow | `scripts/dg_agent.sh opencode-agent -- /repo` | OpenCode UI plus deterministic gateway delegate; live read/edit Git checks pass |
| OpenCode | Generic Codex-like terminal agent | `scripts/dg_agent.sh opencode -- /repo` | installed, 1.17.20; provider/run smoke pass |
| OpenCode + MCP stack | OpenCode with DG, Repomix, and Serena MCP servers mounted | `scripts/dg_agent.sh opencode-mcp -- /repo` | live MCP list passes |
| OpenCode ACP | OpenCode ACP server with the DG MCP profile | `scripts/dg_agent.sh opencode-acp -- --cwd /repo --hostname 127.0.0.1 --port 3295` | ACP smoke passes |
| Goose | MCP-capable agent shell | `scripts/dg_agent.sh goose -- run --no-profile --max-turns 1 --text "..."` | experimental |
| Goose + MCP stack | Goose with DG and Serena tools mounted as stdio MCP extensions | `scripts/dg_agent.sh goose-mcp -- info -v` | experimental |
| Goose ACP | ACP stdio/HTTP server over Goose + DG+Serena MCP | `scripts/dg_agent.sh goose-acp` / `scripts/dg_agent.sh goose-serve -- --port 3294` | experimental |
| LiteLLM | OpenAI-compatible gateway | `scripts/dg_agent.sh litellm` | external client bridge |
| ast-grep | OSS structural code search | `scripts/dg_agent.sh ast-grep --repo /repo --lang python --pattern 'return $X' --json` | context tool |
| ast-grep outline | OSS symbol map | `scripts/dg_agent.sh code-outline --repo /repo --lang python --json` | context tool |
| Continue/Cline/Roo/Kilo | IDE clients | use `http://127.0.0.1:4100/v1` and `diffusiongemma-local` | manual IDE workflows |
| OpenHands | Heavy autonomous dev-agent shell | use `configs/client_profiles/openhands.dg.toml` | optional external experiment |
| OpenHands ACP | OpenHands ACP stdio agent server | `scripts/dg_agent.sh openhands-acp` or `scripts/dg_agent.sh agent-bridge --repo /repo --server openhands-acp` | experimental |
| OpenHands + MCP | OpenHands built-in MCP config with DG, Repomix, and Serena | `scripts/dg_agent.sh openhands-mcp -- --repo /repo --reset` | experimental |
| Qwen Code | Open-source terminal inspection shell with DG, Repomix, and Serena MCP | `scripts/dg_agent.sh qwen-code -- --repo /repo -- --prompt "Read path/to/file.py. Summarize ..."` | experimental, 0.19.10 smoke pass |
| AutoGen AgentChat | Open-source Python multi-agent framework | `scripts/dg_agent.sh autogen -- --repo /repo --dry-run` | experimental |
| Hugging Face smolagents | Open-source CodeAgent framework | `scripts/dg_agent.sh smolagents -- --repo /repo --dry-run` | experimental |
| LangGraph | Open-source graph-agent framework | `scripts/dg_agent.sh langgraph -- --repo /repo --dry-run` | installed through WSL cp314 wheelhouse; smoke pass |
| CrewAI | Open-source multi-agent crew framework | `scripts/dg_agent.sh crewai -- --repo /repo --dry-run` | experimental |
| Open Interpreter | Open-source code-execution shell | `scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run` | experimental |
| LlamaIndex | Open-source RAG/agent workflow framework | `scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run` | experimental |
| Haystack | Open-source BM25 RAG pipeline | `scripts/dg_agent.sh haystack -- --repo /repo --dry-run` | retrieval-first experiment |
| SWE-agent | Benchmark-style coding agent | use `configs/client_profiles/swe-agent.dg.yaml` | optional, maintenance-mode upstream |
| mini-swe-agent | Smaller SWE-agent successor | use `configs/client_profiles/mini-swe-agent.dg.yaml` | optional external experiment |
| MCP stdio | Official Python SDK tool bridge for MCP-capable clients | `scripts/dg_agent.sh mcp` | reliable DG tools |
| MCP HTTP | Official streamable HTTP MCP endpoint for clients that cannot spawn stdio | `scripts/dg_agent.sh mcp-http -- --port 8765` | reliable DG tools |
| Serena MCP | Upstream semantic/LSP MCP server | `scripts/dg_agent.sh serena-mcp` | available through the active WSL runtime, 1.5.3 |

## Compatibility Endpoint

Use this for clients that support an OpenAI-compatible provider:

```text
base_url: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
```

Config files:

```text
configs/client_profiles/openai-compatible.local.json
configs/client_profiles/openai.env
configs/client_profiles/aider.dg-workspace.conf.yml
configs/client_profiles/continue.config.yaml
configs/client_profiles/agent-client-pack.json
configs/client_profiles/openhands.dg.toml
configs/client_profiles/openhands.env
configs/client_profiles/swe-agent.dg.yaml
configs/client_profiles/mini-swe-agent.dg.yaml
configs/client_profiles/mcp-server.json
configs/client_profiles/mcp-client-snippets.json
configs/client_profiles/claude-code.mcp.json
configs/client_profiles/claude-desktop-mcp.json
configs/client_profiles/cursor.mcp.json
configs/client_profiles/vscode.mcp.json
configs/client_profiles/agent-instructions.md
configs/client_profiles/AGENTS.dg.md
configs/client_profiles/CLAUDE.dg.md
configs/client_profiles/copilot-instructions.dg.md
configs/client_profiles/diffusiongemma.instructions.md
configs/client_profiles/cursor-rules.dg.mdc
configs/client_profiles/goose-mcp.dg.yaml
configs/client_profiles/litellm-local-model-registry.json
configs/client_profiles/llamaindex.dg.json
configs/client_profiles/haystack.dg.json
```

## Serena Semantic MCP

Serena is an optional upstream tool, not part of the model runtime. Client
bootstrap checks its active WSL route before adding it to a MCP bundle:

```bash
scripts/install_serena_local.sh
scripts/dg_agent.sh serena-mcp --help-local
scripts/dg_agent.sh smoke --suite serena-mcp --timeout 300
```

When it becomes available, use it for semantic code navigation instead of more
raw context in the prompt: symbol overview, references, diagnostics, renames,
and safe symbol-body edits. Until then, use the supported DG MCP server plus
`repo-map`, `code-outline`, and bounded RAG context.

The checked command is:

```bash
scripts/dg_agent.sh serena-mcp --check-installed
```

The current WSL runtime returns success. A future nonzero result is deliberately surfaced by
`doctor` and `bootstrap` as an unavailable optional integration rather than a
core-agent failure.

The compact OpenCode delegate deliberately does not launch Serena on every
task: its cold MCP startup exceeds OpenCode's connection window. Use Serena
from an IDE bundle for symbol navigation and references, or use the already
available `repo-map`, `code-outline`, and Repomix tools before larger tasks.

## Optional Candidates

For Aider, `workspace-init` copies a direct upstream config:

```bash
.dg-agent/bin/aider app.py --message "Make the smallest patch"
aider --config .dg-agent/aider.dg-fast.conf.yml app.py
```

The launcher remains preferred because it checks local proxy health and uses the
repo-local history paths consistently.

OpenHands, SWE-agent, and mini-swe-agent now have repo-local profiles that
route through the existing LiteLLM gateway:

```bash
scripts/dg_agent.sh client-pack --write
scripts/dg_agent.sh workspace-init --repo /path/to/repo
```

OpenHands uses the LiteLLM Proxy provider:

```text
config: configs/client_profiles/openhands.dg.toml
model: litellm_proxy/diffusiongemma-local
base_url: http://127.0.0.1:4100
```

Launcher:

```bash
scripts/dg_agent.sh openhands -- --repo /path/to/repo --task "..." --dry-run
scripts/dg_agent.sh openhands-acp -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server openhands-acp
scripts/dg_agent.sh openhands-mcp -- --repo /path/to/repo --reset
```

The ACP route intentionally uses `openhands acp --override-with-envs`. Do not
use the standalone `openhands-acp` executable directly; in the current package
that entrypoint can fail while the upstream subcommand works.

The MCP setup route uses OpenHands' own `openhands mcp add` command and writes a
repo-local config at `.dg-agent/openhands-persistence/mcp.json`. It mounts:

- `diffusiongemma-local-agent`: the local DG MCP server
- `repomix`: upstream repo packer MCP
- `serena`: upstream semantic/LSP MCP with `--project /repo`

Qwen Code is a separate terminal inspection path. On this Windows host the
unified entrypoint prefers the WSL runner with DG, Repomix, and Serena MCP
mounted. The native Windows launcher remains a read-only fallback on the safe
gateway, so use Aider/session/task for modifications:

```bash
scripts/dg_agent.sh qwen-code -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh qwen-code -- --repo /path/to/repo -- \
  --prompt "Read src/app.py. Summarize the request flow."
.\scripts\run_qwen_code_windows.ps1 --repo C:\path\to\repo -- --prompt "Read src\app.py. Summarize the request flow."
```

Docs: `docs/qwen_code_local.md`.

AutoGen AgentChat uses the same local OpenAI-compatible endpoint through
`autogen-ext[openai]`:

```bash
scripts/dg_agent.sh autogen -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh autogen -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/autogen.dg.json`.
Docs: `docs/autogen_local.md`.

Hugging Face smolagents uses the same local OpenAI-compatible endpoint through
`OpenAIModel`:

```bash
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/smolagents.dg.json`.
Docs: `docs/smolagents_local.md`.

LangGraph/LangChain uses the same local OpenAI-compatible endpoint through
`ChatOpenAI`:

```bash
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/langgraph.dg.json`.
Docs: `docs/langgraph_local.md`.

CrewAI uses the same local OpenAI-compatible endpoint through `crewai.LLM`:

```bash
scripts/dg_agent.sh crewai -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh crewai -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/crewai.dg.json`.
Docs: `docs/crewai_local.md`.

Open Interpreter uses the same local OpenAI-compatible endpoint through its
upstream `interpreter` shell object:

```bash
scripts/dg_agent.sh open-interpreter -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh open-interpreter -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/open-interpreter.dg.json`.
Docs: `docs/open_interpreter_local.md`.

LlamaIndex uses the same local OpenAI-compatible endpoint through
`OpenAILike` and `AgentWorkflow.from_tools_or_functions`. Because the current
model profile is not a native function-calling model, LlamaIndex selects
`ReActAgent` and exposes bounded repo tools:

```bash
scripts/dg_agent.sh llamaindex -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh llamaindex -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/llamaindex.dg.json`.
Docs: `docs/llamaindex_local.md`.

Haystack is available as a retrieval-first RAG pipeline over repository files.
It uses `InMemoryDocumentStore`, `InMemoryBM25Retriever`, and
`OpenAIChatGenerator` against the same local OpenAI-compatible endpoint:

```bash
scripts/dg_agent.sh haystack -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh haystack -- --repo /path/to/repo --smoke-import
```

Config: `configs/client_profiles/haystack.dg.json`.
Docs: `docs/haystack_local.md`.

SWE-agent and mini-swe-agent use the OpenAI-compatible LiteLLM endpoint:

```text
config: configs/client_profiles/swe-agent.dg.yaml
config: configs/client_profiles/mini-swe-agent.dg.yaml
model: openai/diffusiongemma-local
base_url: http://127.0.0.1:4100/v1
```

Launchers:

```bash
scripts/dg_agent.sh swe-agent -- --repo /path/to/repo --task "..." --dry-run
scripts/dg_agent.sh mini-swe-agent -- --repo /path/to/repo --task "..." --dry-run
scripts/dg_agent.sh mini-swe-run --repo /path/to/repo --task "..." --dry-run --json
scripts/dg_agent.sh mini-swe-runs list
scripts/dg_agent.sh mini-swe-runs show --latest
```

`mini-swe-run` is the preferred local integration point for mini-SWE because it
preserves stdout, stderr, the trajectory path, a runnable command file, and a
JSON report under `runlogs/mini-swe-agent/`.

In safe mode, mini-SWE traffic is adapted by the Aider-compatible proxy instead
of being forwarded as arbitrary generic chat. The proxy returns a valid
`mswea_bash_command` action that delegates the actual repository work to
`scripts/dg_agent.sh session --repo "$(pwd)" ... --rollback-on-failure`, then
mini-SWE submits after the delegated session succeeds. This keeps mini-SWE as
the upstream loop while avoiding raw prompts that can crash the current backend.

The same safe gateway also supports OpenAI `tools` clients when they expose a
command-like function such as `execute_command(command=...)`. The proxy returns
an OpenAI `tool_calls` response whose command delegates to `dg_agent.sh
session`, so tool-calling OSS shells can use their own executor around the
reliable local DG session path.

For clients built on the newer OpenAI Responses API, the gateway also exposes a
minimal non-streaming `POST /v1/responses` shim. Command-like function tools are
returned as `function_call` output items with the same delegated session
command.

MCP-capable clients can avoid OpenAI-style tool-call prompting entirely and
launch the local stdio server instead. The default path uses the official
`modelcontextprotocol/python-sdk`; `--legacy` keeps the dependency-free fallback
available for debugging:

```bash
scripts/dg_agent.sh mcp --list-tools
scripts/dg_agent.sh mcp
scripts/dg_agent.sh mcp-http -- --host 127.0.0.1 --port 8765
scripts/dg_agent.sh mcp --legacy
scripts/dg_agent.sh opencode-mcp -- mcp list
scripts/dg_agent.sh opencode-acp -- --help
scripts/dg_agent.sh goose-mcp -- info -v
scripts/dg_agent.sh goose-acp -- --help
scripts/dg_agent.sh goose-serve -- --help
scripts/dg_agent.sh openhands-acp -- --help
```

The MCP server exposes repo inspection tools (`dg_repo_status`, `dg_list_files`,
`dg_repo_map`, `dg_code_outline`, `dg_search`, `dg_ast_grep`, `dg_read_file`, `dg_git_diff`), durable handoff-note tools
(`dg_task_note`, `dg_task_notes`), plus agent orchestration tools (`dg_context`,
`dg_rag_context`, `dg_rag_answer`, `dg_repo_pack`, `dg_preflight`, `dg_plan`, `dg_task`, `dg_session`, `dg_verify`,
`dg_capabilities`, `dg_client_smoke`, `dg_client_report`, `dg_sessions`, `dg_session_artifact`). Its base config is
`configs/client_profiles/mcp-server.json`. Goose can mount it through
`configs/client_profiles/goose-mcp.dg.yaml`. Claude Code, Claude Desktop,
Cursor, and VS Code can use the copy-ready templates in
`configs/client_profiles/*mcp*.json`. These profiles are copied into each repo
by `workspace-init`.

For project-local MCP clients, install by merging instead of manual copy:

```bash
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client claude-code
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client vscode
```

Install project instructions for clients that read repo rules:

```bash
scripts/dg_agent.sh agent-rules --repo /path/to/repo --target all
```

This adds or updates the DG block in `AGENTS.md`, `CLAUDE.md`, and
`.github/copilot-instructions.md`, and writes dedicated generated rule files for
VS Code and Cursor.

For clients that support project-local command layers, also install the command
kit:

```bash
scripts/dg_agent.sh agent-commands --repo /path/to/repo --target all
```

This keeps generic workflow snippets under `.dg-agent/commands/` and installs
`.claude/skills/dg-local-agent/SKILL.md` for Claude Code.

Install selected external CLIs into repo-local tool locations:

```bash
scripts/dg_agent.sh bootstrap --only openhands --install
scripts/dg_agent.sh bootstrap --only mini-swe-agent --install
scripts/dg_agent.sh bootstrap --only swe-agent --install
```

OpenHands and mini-swe-agent use a local `uv` install under `.tools/`. Classic
SWE-agent is installed from its GitHub source into `.venv-swe-agent`.

Current local state from the 2026-07-14 audit:

```text
Aider           installed through active WSL runtime, 0.86.2
OpenCode        installed at .tools/opencode/node_modules/.bin/opencode plus opencode-linux-x64, 1.17.20; provider/run/MCP/ACP smoke pass
MCP SDK         installed through active WSL runtime, 1.28.1
Serena          installed through WSL bridge, 1.5.3 with live Pyright symbols
Qwen Code       installed at .tools/qwen-code/node_modules/.bin/qwen, 0.19.10
AgentAPI        missing
Goose           missing
LiteLLM CLI     missing, but the local OpenAI-compatible backend is running
AutoGen         runner present, venv missing
smolagents      runner present, venv missing
LangGraph       installed in .venv-langgraph-wsl from .wheelhouse/langgraph-wsl-cp314; smoke pass
CrewAI          runner present, venv missing
OpenInterpreter runner present, venv missing
LlamaIndex      runner present, venv missing
Haystack        runner present, venv missing
OpenHands       install script present, binary missing
mini-swe-agent  install script present, binary missing
SWE-agent       install script present, venv missing
```

They are not the default here because the current local model profile is weaker
at long-context planning and native tool-calling than at bounded file edits
through Aider/task-runner. Use them as controlled experiments with short step
limits and explicit issue scopes.

OpenCode note: the Windows npm payload remains installed for PowerShell usage,
and `opencode-linux-x64` is installed for WSL MCP process spawning. The live
`opencode mcp list` smoke verifies `dg_agent` and `repomix` as connected.
Serena has a separate MCP smoke with live Pyright symbols and is available in
IDE client bundles.

smolagents note: the runner and config are present, but installing upstream
`smolagents[toolkit]` is currently blocked by PyPI/network timeouts on this
host. The WSL runtime has Python 3.14, while the local wheelhouse is Python 3.12.

LangGraph note: Windows installation succeeds, but Windows App Control blocks
native `pydantic_core` DLL loading. The working route is WSL Python 3.14 with
Linux cp314 wheels downloaded into `.wheelhouse/langgraph-wsl-cp314`.

The `external-agents` smoke validates more than profile syntax. It checks
OpenHands, classic SWE-agent, and mini-swe-agent dry-run launchers, then verifies
that the installed mini-swe path can write an artifacted dry-run report under a
repo-local `.dg-agent/mini-swe-runs/` directory and read it back through
`mini-swe-runs list/show/artifact`.

## Verification

Static wrapper checks that do not require loading the model:

```bash
scripts/dg_agent.sh bootstrap
scripts/dg_agent.sh bootstrap --smoke-static
scripts/dg_agent.sh smoke --suite wrappers
scripts/dg_agent.sh smoke --suite bootstrap
scripts/dg_agent.sh smoke --suite client-pack
scripts/dg_agent.sh smoke --suite workspace-init
scripts/dg_agent.sh smoke --suite codex-profile
scripts/dg_agent.sh smoke --suite ide-clients
scripts/dg_agent.sh smoke --suite external-agents
scripts/dg_agent.sh smoke --suite mini-swe-runner
scripts/dg_agent.sh smoke --suite repo-map
scripts/dg_agent.sh smoke --suite mcp
scripts/dg_agent.sh smoke --suite mcp-http
scripts/dg_agent.sh smoke --suite ast-grep
scripts/dg_agent.sh smoke --suite code-outline
scripts/dg_agent.sh smoke --suite opencode-mcp
scripts/dg_agent.sh smoke --suite opencode-acp
scripts/dg_agent.sh smoke --suite goose-mcp
scripts/dg_agent.sh smoke --suite goose-acp
scripts/dg_agent.sh smoke --suite openhands-acp
scripts/dg_agent.sh smoke --suite openhands-mcp
scripts/dg_agent.sh smoke --suite qwen-code
scripts/dg_agent.sh smoke --suite autogen
scripts/dg_agent.sh smoke --suite smolagents
scripts/dg_agent.sh smoke --suite langgraph
scripts/dg_agent.sh smoke --suite crewai
scripts/dg_agent.sh smoke --suite open-interpreter
scripts/dg_agent.sh smoke --suite llamaindex
scripts/dg_agent.sh smoke --suite haystack
python3 -m py_compile scripts/dg_agent.py
bash -n scripts/smoke_dg_agent_wrappers.sh
```

Full live checks require the backend model to be loaded:

```bash
scripts/dg_agent.sh up
scripts/dg_agent.sh smoke --suite agent --suite session --suite stack-control
```
