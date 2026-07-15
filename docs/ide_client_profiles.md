# IDE Client Profiles

The local model is exposed through LiteLLM as a normal OpenAI-compatible
endpoint:

```text
base_url: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
```

Use these profile files:

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
configs/client_profiles/litellm-local-model-registry.json
```

Generate or inspect the full client pack:

```bash
scripts/dg_agent.sh client-pack
scripts/dg_agent.sh client-pack --json
scripts/dg_agent.sh client-pack --env
scripts/dg_agent.sh client-pack --write
```

The client pack includes settings for OpenAI SDK, Aider, OpenCode, Goose,
Continue, Cline, Roo Code, Kilo Code, MCP-capable IDE clients, and optional
OpenHands/SWE-agent routes through the local LiteLLM endpoint.

## One-Shot Client Init

For Cursor, Claude Code, Claude Desktop, or VS Code, use the high-level
bootstrap:

```bash
scripts/dg_agent.sh client-init --repo /path/to/repo --client cursor
scripts/dg_agent.sh client-smoke --repo /path/to/repo --client cursor --live
scripts/dg_agent.sh client-report --repo /path/to/repo --client cursor --live
scripts/dg_agent.sh agent-commands --repo /path/to/repo --target all
```

By default this writes `.dg-agent/`, adds the DG MCP server and Repomix, then
adds Serena only when `serena-mcp --check-installed` succeeds. It also writes
AGENTS, Claude, Copilot, VS Code, and Cursor instruction files. The current
WSL Serena runtime passes that check, so the active default bundle is
`diffusiongemma-local-agent + repomix + serena`.

Run `client-smoke` after bootstrap when you want a readiness gate before
attaching an external IDE or ACP client. It verifies the repo-local hub, MCP
client config, agent rules, launchers, and with `--live` also checks the
backend, proxy, and LiteLLM endpoints.

Run `client-report` when you want a portable handoff for another agent or IDE
session. It writes `.dg-agent/CLIENT_HANDOFF.md` and
`.dg-agent/client-handoff.json` with ready commands, MCP config, route map,
latest capability snapshot, and optional live endpoint status.

Run `agent-commands` to install the repo command layer. It keeps generic
workflow snippets in `.dg-agent/commands/` and writes the Claude Code project
skill `.claude/skills/dg-local-agent/SKILL.md`.

For ACP-capable clients, use the bridge command instead of wiring the OSS agent
server by hand:

```bash
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server opencode-acp
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server opencode-acp --start
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server openhands-acp
```

The default bridge prepares the repo through `client-init`, then exposes it via
the upstream OpenCode ACP server with DG MCP and Repomix mounted. Add the
separate Serena MCP entry in an IDE when semantic/LSP tools are needed.
`--server goose-serve`, `--server goose-acp`, and `--server openhands-acp` use
Goose or OpenHands ACP modes instead.

After any workspace bootstrap, open `.dg-agent/AGENT_HUB.md` or run
`.dg-agent/bin/hub`. That handoff is the shortest route map for humans and
external agents; `.dg-agent/bin/hub --json` prints the same data as JSON.

## Repo-Local Workspace Init

For a target repository, write a local `.dg-agent/` directory:

```bash
scripts/dg_agent.sh workspace-init --repo /path/to/repo
```

It creates:

```text
.dg-agent/client-pack.json
.dg-agent/AGENT_HUB.md
.dg-agent/agent-hub.json
.dg-agent/COMMANDS.md
.dg-agent/command-kit.json
.dg-agent/commands/dg-report.md
.dg-agent/commands/dg-smoke.md
.dg-agent/commands/dg-context.md
.dg-agent/commands/dg-plan-task.md
.dg-agent/commands/dg-agent.md
.dg-agent/commands/dg-verify.md
.dg-agent/commands/dg-mcp-handoff.md
.dg-agent/commands/dg-codex.md
.dg-agent/claude-skill/SKILL.md
.dg-agent/CODEX.md
.dg-agent/codex.config.toml
.dg-agent/codex.env
.dg-agent/IDE_CLIENTS.md
.dg-agent/ide-client-snippets.json
.dg-agent/openai-compatible.local.json
.dg-agent/openai.env
.dg-agent/kilo-code.config.json
.dg-agent/env.sh
.dg-agent/README.md
.dg-agent/aider.dg-fast.conf.yml
.dg-agent/aider.dg-model-settings.yml
.dg-agent/aider.dg-model-metadata.json
.dg-agent/continue.config.yaml
.dg-agent/opencode.dg.json
.dg-agent/opencode.dg-mcp.json
.dg-agent/openhands.dg.toml
.dg-agent/openhands.env
.dg-agent/swe-agent.dg.yaml
.dg-agent/mini-swe-agent.dg.yaml
.dg-agent/mcp-server.json
.dg-agent/mcp-client-snippets.json
.dg-agent/claude-code.mcp.json
.dg-agent/claude-desktop-mcp.json
.dg-agent/cursor.mcp.json
.dg-agent/vscode.mcp.json
.dg-agent/agent-instructions.md
.dg-agent/AGENTS.dg.md
.dg-agent/CLAUDE.dg.md
.dg-agent/copilot-instructions.dg.md
.dg-agent/diffusiongemma.instructions.md
.dg-agent/cursor-rules.dg.mdc
.dg-agent/goose-mcp.dg.yaml
.dg-agent/litellm-local-model-registry.json
.dg-agent/bin/agent
.dg-agent/bin/client-smoke
.dg-agent/bin/client-report
.dg-agent/bin/context
.dg-agent/bin/verify
.dg-agent/bin/status
.dg-agent/bin/aider
.dg-agent/bin/opencode
.dg-agent/bin/opencode-mcp
.dg-agent/bin/opencode-acp
.dg-agent/bin/goose
.dg-agent/bin/goose-mcp
.dg-agent/bin/mcp
.dg-agent/bin/serena-mcp
.dg-agent/bin/client-init
.dg-agent/bin/agent-bridge
.dg-agent/bin/hub
.dg-agent/bin/agent-commands
```

For git repositories, `workspace-init` writes both `.dg-agent/` and `.serena/`
to the repo-local `.git/info/exclude`. Serena may create `.serena/project.yml`
on first semantic-MCP startup, and this keeps that local metadata out of
normal `git status`.

Load the env from the target repo:

```bash
set -a
. .dg-agent/env.sh
set +a
```

Then use the repo-local launchers:

```bash
.dg-agent/bin/status
.dg-agent/bin/agent --task "..." --file path/to/file
.dg-agent/bin/aider app.py --message "Make the smallest patch"
.dg-agent/bin/context --task "..." --max-files 3
.dg-agent/bin/verify --file path/to/file
.dg-agent/bin/openhands --task "..." --dry-run
.dg-agent/bin/openhands-acp --dry-run
.dg-agent/bin/swe-agent --task "..." --dry-run
.dg-agent/bin/mini-swe-agent --task "..." --dry-run
.dg-agent/bin/mini-swe-run --task "..." --dry-run --json
.dg-agent/bin/mini-swe-runs list
.dg-agent/bin/mcp --list-tools
.dg-agent/bin/mcp-http --host 127.0.0.1 --port 8765
.dg-agent/bin/serena-mcp --help-local
.dg-agent/bin/client-init --client cursor
.dg-agent/bin/client-smoke --client cursor --live
.dg-agent/bin/client-report --client cursor --live
.dg-agent/bin/agent-commands --target all
.dg-agent/bin/agent-bridge --server opencode-acp
.dg-agent/bin/agent-bridge --server openhands-acp
.dg-agent/bin/hub
.dg-agent/bin/goose-mcp --help-local
.dg-agent/bin/agent-rules --target all
```

Check readiness before a live edit:

```bash
scripts/dg_agent.sh preflight --repo /path/to/repo --task "..." --file path
```

Use `--force` only when you intentionally want to overwrite changed
`.dg-agent/` files.

## OpenAI SDK

Bash:

```bash
set -a
. /root/diffusiongemma-agent/configs/client_profiles/openai.env
set +a
```

Python client shape:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:4100/v1",
    api_key="dummy",
)

models = client.models.list()
```

## Continue

Use:

```text
configs/client_profiles/continue.config.yaml
```

The profile uses Continue's `openai` provider pointed at the local LiteLLM
gateway.

## Codex CLI

Use the project-local Codex profile when Codex CLI should talk to the local DG
safe agent proxy:

```bash
.dg-agent/bin/codex-profile --target all
source .dg-agent/codex.env
codex
```

This writes `.codex/config.toml` from `.dg-agent/codex.config.toml`. The default
provider is the safe proxy at `http://127.0.0.1:8090/v1`; for plain chat, switch
`model_provider` to `diffusiongemma-local-chat` in the generated config.

## Aider

Preferred reliable launcher:

```bash
.dg-agent/bin/aider app.py --message "Make the smallest patch"
```

Direct upstream Aider config:

```bash
aider --config .dg-agent/aider.dg-fast.conf.yml app.py
```

The config uses the DG Aider proxy at `http://127.0.0.1:8090/v1`, disables repo
map expansion, keeps chat history small, disables auto commits/lint/test, and
uses `.dg-agent/aider.dg-model-settings.yml` plus
`.dg-agent/aider.dg-model-metadata.json` for local zero-cost model metadata.

## Cline / Roo Code / Kilo Code

Open `.dg-agent/IDE_CLIENTS.md` or `.dg-agent/ide-client-snippets.json` after
`workspace-init`. They include two routes: the LiteLLM chat/edit endpoint and
the safe agent proxy endpoint for command-like tool delegation.

Configure the provider as OpenAI-compatible for the safe agent route:

```text
Provider: OpenAI Compatible
Base URL: http://127.0.0.1:8090/v1
API key: dummy
Model: diffusiongemma-26b-a4b-it-iq4xs-aider-local
```

For simple chat/edit flows that do not need command delegation, use:

```text
Base URL: http://127.0.0.1:4100/v1
Model: diffusiongemma-local
```

For Kilo Code, use `.dg-agent/kilo-code.config.json` as the local
OpenAI-compatible custom provider template. Keep requests small. The current
runtime is tuned for file-level tasks and short context packs, not
repository-wide chat history.

## MCP-capable clients

Use the local MCP SDK server when a client can mount stdio MCP tools. This is
the strongest wrapper path for existing clients because the model does not need
to invent tool JSON; clients call stable tools that delegate to the repository
agent pipeline.

When a client supports MCP over HTTP but cannot spawn local stdio processes,
run the streamable HTTP launcher instead:

```bash
.dg-agent/bin/mcp-http --host 127.0.0.1 --port 8765
```

Endpoint:

```text
http://127.0.0.1:8765/mcp
```

Server command:

```text
/root/diffusiongemma-agent/scripts/run_mcp_server.sh
```

Copy-ready templates:

```text
Claude Code project .mcp.json: .dg-agent/claude-code.mcp.json
Claude Desktop claude_desktop_config.json: .dg-agent/claude-desktop-mcp.json
Cursor project .cursor/mcp.json: .dg-agent/cursor.mcp.json
VS Code workspace .vscode/mcp.json: .dg-agent/vscode.mcp.json
All snippets: .dg-agent/mcp-client-snippets.json
```

Install or merge the server entry from a target repo:

```bash
.dg-agent/bin/mcp-client-config --client claude-code
.dg-agent/bin/mcp-client-config --client cursor
.dg-agent/bin/mcp-client-config --client cursor --with-repomix
.dg-agent/bin/mcp-client-config --client cursor --with-serena
.dg-agent/bin/mcp-client-config --client cursor --with-repomix --with-serena
.dg-agent/bin/mcp-client-config --client cursor --with-oss-stack
.dg-agent/bin/mcp-client-config --client vscode
```

The merge keeps existing unrelated MCP servers. If the
`diffusiongemma-local-agent` entry already exists with different settings, use
`--force` only when you intentionally want to replace it.

The exported MCP tools are `dg_repo_status`, `dg_list_files`, `dg_search`,
`dg_read_file`, `dg_git_diff`, `dg_task_note`, `dg_task_notes`, `dg_status`,
`dg_context`, `dg_rag_context`, `dg_rag_answer`, `dg_repo_pack`,
`dg_repo_map`, `dg_ast_grep`, `dg_code_outline`,
`dg_preflight`, `dg_plan`, `dg_task`, `dg_session`, `dg_verify`,
`dg_capabilities`, `dg_client_smoke`, `dg_client_report`, `dg_sessions`, and
`dg_session_artifact`. Use the repo tools for navigation and inspection, use
`dg_rag_context` for compact repo-scale retrieval, use `dg_repo_pack` for
filtered Repomix packed context, save handoff notes with
`dg_task_note`, generate client handoff with `dg_client_report`, then run either the one-shot `dg_session` path or the stepwise
`dg_plan` -> `dg_task` path.

`mcp-client-snippets.json` also carries optional native Repomix MCP server
and Serena MCP server entries. Copy Repomix when the IDE should talk to
upstream repository packing directly. Copy Serena when the IDE should use
semantic/LSP tools such as symbol overview, references, diagnostics, renames,
and safe symbol edits in addition to the DG MCP tool bridge.

## Agent Rules

Install repo-local instruction files for clients that read project rules:

```bash
.dg-agent/bin/agent-rules --target all
```

Targets:

```text
AGENTS.md
CLAUDE.md
.github/copilot-instructions.md
.github/instructions/diffusiongemma.instructions.md
.cursor/rules/diffusiongemma-local-agent.mdc
```

Existing `AGENTS.md`, `CLAUDE.md`, and Copilot instructions are preserved with
a marked DG block. Dedicated Cursor and VS Code generated files are not replaced
unless `--force` is used.

## OpenHands

Use the LiteLLM Proxy profile:

```text
Config: configs/client_profiles/openhands.dg.toml
Model: litellm_proxy/diffusiongemma-local
Base URL: http://127.0.0.1:4100
API key: dummy
```

For a target repo initialized with `workspace-init`, use the copied files:

```text
.dg-agent/openhands.dg.toml
.dg-agent/openhands.env
```

Launcher:

```bash
.dg-agent/bin/openhands --task "..." --dry-run
.dg-agent/bin/openhands-acp --dry-run
.dg-agent/bin/openhands-mcp --reset
.dg-agent/bin/qwen-code --dry-run
.dg-agent/bin/autogen --dry-run
.dg-agent/bin/smolagents --dry-run
.dg-agent/bin/langgraph --dry-run
.dg-agent/bin/crewai --dry-run
.dg-agent/bin/open-interpreter --dry-run
.dg-agent/bin/llamaindex --dry-run
.dg-agent/bin/haystack --dry-run
```

For ACP clients, use `.dg-agent/bin/openhands-acp` or
`.dg-agent/bin/agent-bridge --server openhands-acp`. This route uses
`openhands acp --override-with-envs`; avoid the standalone `openhands-acp`
entrypoint from the package.

For OpenHands' built-in MCP management, run `.dg-agent/bin/openhands-mcp --reset`.
It writes `.dg-agent/openhands-persistence/mcp.json` with the DG MCP server,
Repomix, and Serena bound to the current repo.

For Qwen Code, run `.dg-agent/bin/qwen-code --dry-run` first. On this Windows
host the launcher prefers the WSL MCP route with DG, Repomix, and Serena;
native PowerShell falls back to explicit read-only mode on the safe GPU gateway.
Name a file in the prompt and use Aider/session for edits.

For AutoGen AgentChat, run `.dg-agent/bin/autogen --dry-run` or
`.dg-agent/bin/autogen --smoke-import`. The launcher uses
`.dg-agent/autogen.dg.json` with `OpenAIChatCompletionClient`.

For Hugging Face smolagents, run `.dg-agent/bin/smolagents --dry-run` or
`.dg-agent/bin/smolagents --smoke-import`. The launcher uses
`.dg-agent/smolagents.dg.json` with `CodeAgent` and `OpenAIModel`.

For LangGraph/LangChain, run `.dg-agent/bin/langgraph --dry-run` or
`.dg-agent/bin/langgraph --smoke-import`. The launcher uses
`.dg-agent/langgraph.dg.json` with `ChatOpenAI` and a LangGraph/LangChain agent
factory.

For CrewAI, run `.dg-agent/bin/crewai --dry-run` or
`.dg-agent/bin/crewai --smoke-import`. The launcher uses `.dg-agent/crewai.dg.json`
with CrewAI `Agent`, `Task`, `Crew`, and `LLM`.

For Open Interpreter, run `.dg-agent/bin/open-interpreter --dry-run` or
`.dg-agent/bin/open-interpreter --smoke-import`. The launcher uses
`.dg-agent/open-interpreter.dg.json` with `auto_run=false` and `safe_mode=ask`.

For LlamaIndex, run `.dg-agent/bin/llamaindex --dry-run` or
`.dg-agent/bin/llamaindex --smoke-import`. The launcher uses
`.dg-agent/llamaindex.dg.json` with `OpenAILike`,
`AgentWorkflow.from_tools_or_functions`, `ReActAgent`, and bounded repo tools.

For Haystack, run `.dg-agent/bin/haystack --dry-run` or
`.dg-agent/bin/haystack --smoke-import`. The launcher uses
`.dg-agent/haystack.dg.json` with `InMemoryDocumentStore`,
`InMemoryBM25Retriever`, and `OpenAIChatGenerator`.

Install the upstream CLI only when you want to run the real external loop:

```bash
scripts/dg_agent.sh bootstrap --only openhands --install
```

## SWE-agent / mini-swe-agent

Use the OpenAI-compatible LiteLLM endpoint:

```text
Config: configs/client_profiles/swe-agent.dg.yaml
Config: configs/client_profiles/mini-swe-agent.dg.yaml
Model: openai/diffusiongemma-local
Base URL: http://127.0.0.1:4100/v1
API key: dummy
```

The mini-swe-agent profile keeps the loop short and sets cost tracking to
`ignore_errors`, which is more practical for a local zero-billing model. These
profiles are experimental; the default reliable path remains
`scripts/dg_agent.sh agent/session/task`.

Launchers:

```bash
.dg-agent/bin/swe-agent --task "..." --dry-run
.dg-agent/bin/mini-swe-agent --task "..." --dry-run
.dg-agent/bin/mini-swe-run --task "..." --dry-run --json
.dg-agent/bin/mini-swe-runs show --latest
```

Prefer `mini-swe-run` when you want preserved artifacts. It writes a report,
logs, command file, and trajectory path under `runlogs/mini-swe-agent/`.
Use `mini-swe-runs` to list, show, or print those artifacts.

Install selected upstream CLIs:

```bash
scripts/dg_agent.sh bootstrap --only mini-swe-agent --install
scripts/dg_agent.sh bootstrap --only swe-agent --install
```

## Smoke

```bash
scripts/dg_agent.sh smoke --suite gateway-clients
scripts/dg_agent.sh smoke --suite openai-sdk
scripts/dg_agent.sh smoke --suite client-pack
scripts/dg_agent.sh smoke --suite workspace-init
scripts/dg_agent.sh smoke --suite client-init
scripts/dg_agent.sh smoke --suite client-smoke
scripts/dg_agent.sh smoke --suite client-report
scripts/dg_agent.sh smoke --suite agent-commands
scripts/dg_agent.sh smoke --suite codex-profile
scripts/dg_agent.sh smoke --suite ide-clients
scripts/dg_agent.sh smoke --suite agent-bridge
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
scripts/dg_agent.sh smoke --suite preflight
scripts/dg_agent.sh smoke --suite external-agents
```

The smoke checks the live LiteLLM model registry and verifies that the checked
in client profiles match the actual endpoint.

The `openai-sdk` smoke uses the installed Python OpenAI SDK against
`http://127.0.0.1:4100/v1`, sends one bounded chat completion, and verifies that
backend, proxy, and LiteLLM remain healthy afterwards.

The gateway intentionally runs generic chat in safe compatibility mode by
default. For real code edits, prefer `scripts/dg_agent.sh session` or
`scripts/dg_agent.sh task`; raw IDE agent loops are still experimental with the
current model profile.
