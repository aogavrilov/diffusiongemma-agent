# DG Agent CLI

`scripts/dg_agent.sh` is the unified entrypoint for the local agent stack. It
does not replace the open-source tools; it routes to the existing Aider,
AgentAPI, and OpenCode wrappers and provides one readiness check.

OSS wrapper map: `docs/oss_agent_wrappers.md`.

## Doctor

```bash
cd /root/diffusiongemma-agent
scripts/dg_agent.sh doctor
scripts/dg_agent.sh doctor --json
scripts/dg_agent.sh status
scripts/dg_agent.sh up
scripts/dg_agent.sh wrappers
scripts/dg_agent.sh wrappers --json
scripts/dg_agent.sh bootstrap
scripts/dg_agent.sh client-pack
scripts/dg_agent.sh client-init --repo /path/to/repo --client cursor
scripts/dg_agent.sh client-report --repo /path/to/repo --client cursor --live
scripts/dg_agent.sh agent-commands --repo /path/to/repo --target all
scripts/dg_agent.sh codex-profile --repo /path/to/repo --target all
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server opencode-acp
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server openhands-acp
scripts/dg_agent.sh openhands-mcp -- --repo /path/to/repo --reset
scripts/dg_agent.sh qwen-code -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh autogen -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh crewai -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh open-interpreter -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh llamaindex -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh haystack -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh workspace-init --repo /path/to/repo
scripts/dg_agent.sh repo-map --repo /path/to/repo --map-tokens 512
scripts/dg_agent.sh ast-grep --repo /path/to/repo --lang python --pattern 'return $X' --json
scripts/dg_agent.sh code-outline --repo /path/to/repo --lang python --json
scripts/dg_agent.sh agent --repo /path/to/repo --task "..." --mode auto
scripts/dg_agent.sh agent --repo /path/to/repo --task "Read file app.py" --mode read
scripts/dg_agent.sh agent --repo /path/to/repo --task "Fix app.py" --mode edit --file app.py
scripts/dg_agent.sh agent-runs list
scripts/dg_agent.sh agent-runs artifact transcript --latest
scripts/dg_agent.sh tool-loop --repo /path/to/repo --task "..." --out runlogs/tool-loop/latest.json
scripts/dg_agent.sh preflight --repo /path/to/repo
scripts/dg_agent.sh run --repo /path/to/repo --task "..." --file path --start
scripts/dg_agent.sh mcp --list-tools
scripts/dg_agent.sh serena-mcp --help-local
scripts/dg_agent.sh goose-mcp -- info -v
scripts/dg_agent.sh goose-acp -- --help
scripts/dg_agent.sh goose-serve -- --host 127.0.0.1 --port 3294
scripts/dg_agent.sh openhands-acp -- --help
scripts/dg_agent.sh openhands-mcp -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh qwen-code -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh autogen -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh crewai -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh open-interpreter -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh llamaindex -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh haystack -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh capabilities
scripts/dg_agent.sh capabilities --live
```

Checks:

- backend on `127.0.0.1:4100`
- safe agent gateway / Aider-compatible proxy on `127.0.0.1:8090`
- Aider install
- AgentAPI install and running state
- OpenCode and local Node install
- Goose install
- LiteLLM gateway install
- Serena semantic MCP install
- wrapper/smoke script presence

Bootstrap checks local OSS-wrapper installs and can reinstall missing wrappers:

```bash
scripts/dg_agent.sh bootstrap
scripts/dg_agent.sh bootstrap --json
scripts/dg_agent.sh bootstrap --install
scripts/dg_agent.sh bootstrap --external
scripts/dg_agent.sh bootstrap --only openhands,mini-swe-agent --install
scripts/dg_agent.sh bootstrap --smoke-static
```

By default, `bootstrap` audits the already recommended core wrappers. Pass
`--external` to include optional OpenHands/SWE-family CLI wrappers. External
installers are isolated under repo-local `.tools/` or `.venv-*` paths and are
not required for the default reliable `agent/session/task` path.

Client pack exports endpoint and launch profiles for external clients:

```bash
scripts/dg_agent.sh client-pack
scripts/dg_agent.sh client-pack --json
scripts/dg_agent.sh client-pack --env
scripts/dg_agent.sh client-pack --write
scripts/dg_agent.sh client-init --repo /path/to/repo --client cursor
scripts/dg_agent.sh client-smoke --repo /path/to/repo --client cursor --live
scripts/dg_agent.sh client-report --repo /path/to/repo --client cursor --live
scripts/dg_agent.sh agent-commands --repo /path/to/repo --target all
scripts/dg_agent.sh codex-profile --repo /path/to/repo --target all
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server opencode-acp
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server openhands-acp
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor --with-serena
scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor --with-oss-stack
scripts/dg_agent.sh agent-rules --repo /path/to/repo --target all
```

The safe gateway exposes OpenAI-compatible discovery endpoints:

```text
http://127.0.0.1:8090/v1/model_card
http://127.0.0.1:8090/v1/capabilities
http://127.0.0.1:8090/v1/agent/routes
http://127.0.0.1:8090/v1/agent/session
http://127.0.0.1:8090/v1/agent/tool
http://127.0.0.1:8090/v1/agent/context
http://127.0.0.1:8090/v1/agent/rag
http://127.0.0.1:8090/v1/agent/sessions
http://127.0.0.1:8090/v1/agent/sessions/latest
http://127.0.0.1:8090/v1/agent/sessions/latest/diff
http://127.0.0.1:8090/v1/agent/sessions/latest/artifacts/{artifact}
http://127.0.0.1:8090/v1/agent/runs
http://127.0.0.1:8090/v1/agent/runs/latest
http://127.0.0.1:8090/v1/agent/runs/latest/artifacts/{artifact}
http://127.0.0.1:8090/v1/agent/tool_manifest
http://127.0.0.1:8090/.well-known/agent.json
```

Use these when an external OSS agent needs to discover the recommended local
route, model limits, tool-call delegation behavior, or MCP resources without
opening `.dg-agent` files directly. The tool manifest includes copy-ready
OpenAI Chat Completions and Responses API tool schemas for safe
`execute_command` delegation through `dg_agent.sh session`.
It also includes DG-specific OpenAI function tools for clients that can call
tools but cannot mount MCP:

```text
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

The repo tools are fixed read-only `git`/`rg`/file-read operations for clients
without MCP. The OSS repo tools delegate to Repomix, Aider repo-map, and
ast-grep/code-outline. `dg_agent` is the high-level HTTP facade over
`scripts/dg_agent.sh agent --mode auto/read/edit`. `dg_context` and
`dg_rag_context` are read-only; `dg_session` defaults to dry-run unless HTTP
execution is explicitly enabled; `dg_session_artifact` reads preserved session
outputs such as `final_diff`, `context_md`, `stdout`, and `stderr`;
`dg_agent_run_artifact` reads preserved high-level `agent` run reports and
tool-loop transcripts from `runlogs/dg-agent-runs/`.
`/v1/agent/tool` executes those DG-specific tool calls and returns a ready
`role=tool` response payload for the next OpenAI-compatible turn. It accepts
either `{name, arguments}` or a full OpenAI `tool_call` object. Arbitrary
`execute_command` shell execution is blocked there; use repo tools for
read-only navigation and `dg_session` for bounded repo changes.
`/v1/agent/session` returns a dry-run session command by default; real HTTP
execution requires `DG_AIDER_PROXY_ENABLE_AGENT_EXEC=1` and `execute=true`.
`/v1/agent/context` and `/v1/agent/rag` are read-only HTTP versions of
`dg_agent.sh context` and `dg_agent.sh rag --print-context`; use them when a
client has no MCP support but still needs bounded repo context before deciding
what to edit. The RAG endpoint is retrieve-only and does not call the model.
`/v1/agent/sessions*` is read-only and exposes preserved session artifacts for
HTTP-only clients that cannot mount the DG MCP resources. Artifact names match
the CLI names below, including `context_md`, `plan`, `task_report`,
`verify_report`, `final_diff`, `stdout`, and `stderr`.
`/v1/agent/runs*` is the matching read-only surface for high-level
`scripts/dg_agent.sh agent` runs. Artifact names include `agent_json`,
`transcript`, `stdout`, and `stderr`.
The same artifacts are available from the CLI through
`scripts/dg_agent.sh agent-runs list`, `agent-runs show --latest`, and
`agent-runs artifact transcript --latest`.
MCP clients get the same surface through `dg_agent_runs`,
`dg_agent_run_artifact`, `dg://agent-runs`, `dg://agent-runs/latest`, and
`dg://agent-runs/latest/transcript`.

Use `client-init` as the highest-level client bootstrap. It runs
`workspace-init`, installs the default DG+Repomix+Serena MCP bundle for the
chosen client, and writes the repo instruction files used by Claude/Cursor/VS
Code/Copilot-compatible agents.

Use `client-smoke` as a target-repo readiness gate before connecting an
external client. It can prepare the repo through `client-init`, then validates
hub files, MCP config, agent rules, key launchers, and optionally live endpoints
with `--live`.

Use `client-report` after `client-smoke` when an IDE, ACP server, or another
agent needs a portable handoff. It writes `.dg-agent/CLIENT_HANDOFF.md` and
`.dg-agent/client-handoff.json` with the ready commands, route map, MCP config,
latest capability snapshot, and live endpoint status when `--live` is set.

Use `agent-commands` to install a project command layer for existing clients.
It keeps generic snippets under `.dg-agent/commands/` and installs the Claude
Code project skill `.claude/skills/dg-local-agent/SKILL.md`.

Use `agent-bridge` when the client speaks ACP and needs a running agent server
instead of only MCP tools. It prepares the repo through `client-init`, then
prints or starts an upstream OpenCode ACP, Goose ACP, or OpenHands ACP server
over the same local model/tool bundle.

Every `workspace-init` also writes `.dg-agent/AGENT_HUB.md` and
`.dg-agent/agent-hub.json`. Open those first when connecting a new external
agent; they summarize the recommended route, endpoint, MCP bundle, ACP bridge,
and fallback order for the current repo.

The client pack includes OpenAI SDK, Aider, OpenCode, Goose, Continue,
Cline/Roo/Kilo, OpenHands, SWE-agent, mini-swe-agent, MCP stdio profiles,
Serena semantic MCP, and copy-ready MCP client configs for Claude Code, Claude
Desktop, Cursor, and VS Code. The OpenHands/SWE/MCP profiles are copied into `.dg-agent/` by
`workspace-init` as experimental heavy-agent entrypoints over the same local
LiteLLM gateway.

Use `agent-rules` to install client instruction files (`AGENTS.md`,
`CLAUDE.md`, GitHub Copilot, VS Code instructions, and Cursor rules) that tell
external clients to use DG MCP repo tools and bounded sessions instead of
pasting large repository context.

The Aider profile is exported as `.dg-agent/aider.dg-fast.conf.yml` with local
model settings/metadata copies, so upstream Aider can also be launched directly:

```bash
aider --config .dg-agent/aider.dg-fast.conf.yml path/to/file
```

External OSS-agent launchers:

```bash
scripts/dg_agent.sh openhands -- --repo /path/to/repo --task "..." --dry-run
scripts/dg_agent.sh openhands-acp -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh openhands-mcp -- --repo /path/to/repo --reset
scripts/dg_agent.sh qwen-code -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh autogen -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh crewai -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh open-interpreter -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh llamaindex -- --repo /path/to/repo --dry-run
scripts/dg_agent.sh swe-agent -- --repo /path/to/repo --task "..." --dry-run
scripts/dg_agent.sh mini-swe-agent -- --repo /path/to/repo --task "..." --dry-run
scripts/dg_agent.sh mini-swe-run --repo /path/to/repo --task "..." --dry-run --json
scripts/dg_agent.sh mini-swe-runs list
scripts/dg_agent.sh mini-swe-runs show --latest
scripts/dg_agent.sh mini-swe-runs artifact report --latest --path-only
scripts/dg_agent.sh goose-mcp -- info -v
scripts/dg_agent.sh goose-acp -- --help
scripts/dg_agent.sh goose-serve -- --help
```

These wrappers use installed upstream CLIs when present. Without the CLI they
print the exact local profile, model, endpoint, and command to run after
installation.

The MCP-enabled OpenCode profile mounts `dg_agent` and `repomix`. Serena is
available through the separate IDE MCP bundle because its cold start exceeds
OpenCode's MCP connection budget on this host.
The MCP-enabled Goose profile mounts `dg_agent` and `serena`.

`mini-swe-run` uses the upstream mini-SWE CLI but, in the default safe gateway
mode, the proxy adapts mini-SWE text actions into a delegated
`dg_agent.sh session` command. This avoids enabling unsafe generic generation
while preserving mini-SWE trajectory, stdout/stderr, command and JSON report
artifacts.

Workspace init writes repo-local `.dg-agent/` profiles:

```bash
scripts/dg_agent.sh workspace-init --repo /path/to/repo
scripts/dg_agent.sh workspace-init --repo /path/to/repo --force
```

For git repositories, `.dg-agent/` is added to the repo-local
`.git/info/exclude`. This keeps the launchers available in the workspace
without changing the project's tracked `.gitignore` or making normal agent
runs start from a dirty tree.

It also writes repo-local launchers:

```bash
.dg-agent/bin/run --task "..." --file path --start
.dg-agent/bin/agent --task "..." --file path
.dg-agent/bin/preflight --task "..." --file path
.dg-agent/bin/capabilities --latest
.dg-agent/bin/doctor
.dg-agent/bin/up
.dg-agent/bin/down
.dg-agent/bin/plan --task "..." --file path --auto-test
.dg-agent/bin/edit --task "..." --file path --auto-test
.dg-agent/bin/task --plan plan.json --rollback-on-failure
.dg-agent/bin/supervisor --task "..." --file path
.dg-agent/bin/web --port 3284
.dg-agent/bin/context --task "..."
.dg-agent/bin/repo-map --map-tokens 512
.dg-agent/bin/ast-grep --lang python --pattern 'return $X' --json
.dg-agent/bin/code-outline --lang python --json
.dg-agent/bin/client-init --client cursor
.dg-agent/bin/client-smoke --client cursor --live
.dg-agent/bin/client-report --client cursor --live
.dg-agent/bin/agent-commands --target all
.dg-agent/bin/codex-profile --target all
.dg-agent/bin/agent-bridge --server opencode-acp
.dg-agent/bin/agent-bridge --server openhands-acp
.dg-agent/bin/hub
.dg-agent/bin/verify --file path
.dg-agent/bin/sessions list
.dg-agent/bin/aider --help-local
.dg-agent/bin/openhands --help-local
.dg-agent/bin/openhands-acp --help-local
.dg-agent/bin/swe-agent --help-local
.dg-agent/bin/mini-swe-agent --help-local
.dg-agent/bin/mini-swe-run --task "..." --dry-run --json
.dg-agent/bin/mini-swe-runs list
.dg-agent/bin/mcp --list-tools
.dg-agent/bin/mcp-http --help-local
.dg-agent/bin/serena-mcp --help-local
.dg-agent/bin/goose-mcp --help-local
.dg-agent/bin/goose-acp --help
.dg-agent/bin/goose-serve --help
```

Preflight checks a target repo before a live agent run:

```bash
scripts/dg_agent.sh preflight --repo /path/to/repo
scripts/dg_agent.sh preflight --repo /path/to/repo --task "..." --file path --json
```

It reports whether the repo is `needs-setup`, `static-ready`, or `live-ready`.
`static-ready` means the wrapper/repo setup is valid but the backend model is
not loaded yet.

One-command run combines workspace init, preflight, optional service startup,
and the reliable agent path:

```bash
scripts/dg_agent.sh run --repo /path/to/repo --task "..." --file path
scripts/dg_agent.sh run --repo /path/to/repo --task "..." --file path --start
scripts/dg_agent.sh run --repo /path/to/repo --task "..." --file path --dry-run --json
```

`run` does not load the model unless `--start` is passed.

`agent` is the highest-level local facade:

```bash
scripts/dg_agent.sh agent --repo /path/to/repo --task "Find where add(a, b) is implemented" --mode auto
scripts/dg_agent.sh agent --repo /path/to/repo --task "Fix add(a, b)" --mode edit --file calc.py
```

`--mode auto` routes inspection tasks to the read-only OpenAI tool-loop and
edit tasks to the artifacted `session` runner. `--mode read` always uses
bounded repo tools and writes `runlogs/dg-agent-runs/*/agent.json` plus the
tool-loop transcript. `--mode edit` keeps the older session behavior:
context, plan, task runner, verification, rollback, and `session.json`.

`tool-loop` is the reference OpenAI-compatible tool-calling client. It fetches
DG tool schemas from `/v1/agent/tool_manifest`, calls Chat Completions through
LiteLLM, executes returned tool calls through `/v1/agent/tool`, appends
`role=tool` messages, and can save the full transcript:

```bash
scripts/dg_agent.sh tool-loop \
  --repo /path/to/repo \
  --task "Find the implementation of add(a, b)" \
  --out runlogs/tool-loop/latest.json
```

Use `--stop-after-tool` when the caller wants only the raw tool transcript.
Without it, the proxy turns the final `role=tool` payload into a deterministic
summary response. Use `--tool dg_read_file` or `--read-only` to constrain the
loop to repo inspection tools when connecting a cautious external agent.

The reliable edit path is intentionally layered. It tries the Aider-compatible
OSS wrapper first, then verifies syntax/tests, then applies small deterministic
repairs when the model call produced no usable diff but the task states an exact
code constraint. It also adds transient `.aider.dg-local/` metadata to the
target repo's local `.git/info/exclude`, so repeated runs do not start from a
dirty tree. Session reports mark repaired model attempts as
`aider-with-deterministic-repair`.

Capability probes run a small end-to-end audit of the wrapper stack:

```bash
scripts/dg_agent.sh capabilities
scripts/dg_agent.sh capabilities --json
scripts/dg_agent.sh capabilities --live --json
scripts/dg_agent.sh capabilities --latest
scripts/dg_agent.sh capabilities --latest --path-only
```

Without `--live`, this checks repo-local workspace bootstrapping, every
repo-local `.dg-agent/bin/*` launcher, the installed OSS wrapper matrix,
OpenHands/SWE-family profile launchers, the proxy adapter, and exact replace
repair without loading the model. With `--live`, it also runs a real GPU-backed
Aider edit where malformed model output is repaired by the proxy and then
applied as an Aider diff.

Capability reports are saved under:

```text
runlogs/dg-agent-capabilities/latest.json
runlogs/dg-agent-capabilities/YYYYMMDD-HHMMSS-{static,live}.json
```

Use `--no-save` to skip writing these files for a one-off probe.

Short stack commands:

- `status`: check backend, proxy and LiteLLM
- `up`: ensure backend, proxy and LiteLLM are running
- `down`: stop backend, proxy and LiteLLM

## Smoke

```bash
scripts/dg_agent.sh smoke
scripts/dg_agent.sh smoke --suite context
scripts/dg_agent.sh smoke --suite auto-test
scripts/dg_agent.sh smoke --suite verify
scripts/dg_agent.sh smoke --suite session
scripts/dg_agent.sh smoke --suite sessions
scripts/dg_agent.sh smoke --suite session-artifacts
scripts/dg_agent.sh smoke --suite agent
scripts/dg_agent.sh smoke --suite capabilities
scripts/dg_agent.sh smoke --suite proxy-adapter
scripts/dg_agent.sh smoke --suite supervisor
scripts/dg_agent.sh smoke --suite wrappers
scripts/dg_agent.sh smoke --suite bootstrap
scripts/dg_agent.sh smoke --suite client-pack
scripts/dg_agent.sh smoke --suite workspace-init
scripts/dg_agent.sh smoke --suite client-init
scripts/dg_agent.sh smoke --suite client-smoke
scripts/dg_agent.sh smoke --suite client-report
scripts/dg_agent.sh smoke --suite agent-commands
scripts/dg_agent.sh smoke --suite codex-profile
scripts/dg_agent.sh smoke --suite ide-clients
scripts/dg_agent.sh smoke --suite agent-bridge
scripts/dg_agent.sh smoke --suite external-agents
scripts/dg_agent.sh smoke --suite mini-swe-runner
scripts/dg_agent.sh smoke --suite preflight
scripts/dg_agent.sh smoke --suite run
scripts/dg_agent.sh smoke --suite task
scripts/dg_agent.sh smoke --suite goose
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
scripts/dg_agent.sh smoke --suite litellm
scripts/dg_agent.sh smoke --suite gateway-clients
scripts/dg_agent.sh smoke --suite openai-sdk
scripts/dg_agent.sh smoke --suite mcp
scripts/dg_agent.sh smoke --suite mcp-http
scripts/dg_agent.sh smoke --suite serena-mcp
scripts/dg_agent.sh smoke --suite watchdog
scripts/dg_agent.sh smoke --suite stack-control
scripts/dg_agent.sh smoke --suite agentapi --suite opencode-provider
```

Suites:

- `context`: context pack and generated task-runner plan
- `auto-test`: automatic verification command inference
- `verify`: standalone verification command runner
- `session`: full context->plan->task->verify artifacted run
- `sessions`: session history listing and inspection
- `session-artifacts`: direct retrieval of preserved session artifacts
- `agent`: recommended local coding-agent mode
- `capabilities`: compact capability harness for workspace launchers, installed OSS wrappers, external-agent profiles, proxy, and live-ready paths
- `proxy-adapter`: file-listing normalization and exact repair fallback in the Aider proxy
- `supervisor`: rg + Aider/model + verification + deterministic repair fallback
- `wrappers`: installed OSS-wrapper matrix and recommended routing
- `bootstrap`: audit/install wrapper control path without loading the model
- `client-pack`: OpenAI-compatible client/IDE/agent profile export
- `workspace-init`: repo-local `.dg-agent/` client pack and quickstart files
- `client-init`: one-shot workspace + MCP bundle + client rules bootstrap
- `client-smoke`: target-repo readiness gate for external IDE/agent clients
- `client-report`: portable Markdown/JSON handoff for external clients
- `agent-commands`: repo-local command kit and Claude Code project skill
- `codex-profile`: project-local Codex CLI config for the DG safe proxy
- `ide-clients`: Continue/Cline/Roo/Kilo/OpenAI-compatible repo-local profile snippets
- `agent-bridge`: one-shot ACP bridge over OpenCode/Goose/OpenHands OSS agent servers
- `external-agents`: OpenHands/SWE/mini-SWE local profile wrappers and launchers
- `mini-swe-runner`: artifacted mini-SWE runner dry-run contract
- `preflight`: target-repo readiness check before agent execution
- `run`: one-command workspace-init -> preflight -> optional start -> agent
- `edit`: natural-language `dg_agent.sh edit`
- `task`: multi-step task runner
- `agentapi`: AgentAPI over Aider
- `goose`: Goose over the local OpenAI-compatible proxy
- `litellm`: LiteLLM gateway over the local OpenAI-compatible proxy
- `gateway-clients`: checked-in IDE/OpenAI-compatible client profiles
- `openai-sdk`: real Python OpenAI SDK chat completion through LiteLLM
- `mcp`: MCP stdio server initialize, tools/list, and `dg_context` tool call
- `watchdog`: backend/proxy/LiteLLM watchdog status and ensure
- `stack-control`: one-command `status`, `up` and `ensure` aliases
- `opencode-provider`: OpenCode provider discovery
- `opencode-run`: minimal OpenCode run fallback

## Agent Mode

Use `run` as the default local coding-agent entrypoint:

```bash
scripts/dg_agent.sh run \
  --repo /path/to/repo \
  --task "Fix hello.py so greet('Ada') returns exactly hello, Ada!" \
  --file hello.py \
  --start
```

Use `agent` directly when workspace/preflight/service startup are already
handled:

```bash
scripts/dg_agent.sh agent \
  --repo /path/to/repo \
  --task "Fix hello.py so greet('Ada') returns exactly hello, Ada!" \
  --file hello.py
```

`agent` is a conservative profile over the artifacted `session` path. It
builds a compact repo context pack, generates a task-runner plan, enables
auto-test inference, verifies after the edit, rolls back failed task-runner
edits, uses deterministic repair fallbacks for exact small Python edits, and
preserves all artifacts under `runlogs/dg-agent-sessions/`.

Useful options:

- `--file path`: repeatable file hints for small-context work
- `--test-cmd "..."`: explicit verification from the target repo
- `--max-files N`: default `3`, for bounded repo-RAG context
- `--no-auto-test`: disable inferred verification
- `--no-rollback`: keep failed edits for inspection
- `--out-dir /path`: write session artifacts outside the default runlog

Smoke:

```bash
scripts/dg_agent.sh smoke --suite agent
```

## Reliable Edits

Run the full artifacted agent session:

```bash
scripts/dg_agent.sh session \
  --repo /path/to/repo \
  --task "Fix hello.py so greet('Ada') returns exactly hello, Ada!" \
  --file hello.py \
  --auto-test \
  --rollback-on-failure
```

The session writes a directory under `runlogs/dg-agent-sessions/` by default:

- `context.md`
- `context.json`
- `plan.json`
- `task-report.json`
- `verify.json`
- `before.status.txt`
- `after.status.txt`
- `before.diff`
- `final.diff`
- `session.json`

List and inspect prior sessions:

```bash
scripts/dg_agent.sh sessions list
scripts/dg_agent.sh sessions show --latest
scripts/dg_agent.sh sessions show /path/to/session-or-session.json
scripts/dg_agent.sh sessions list --json
```

Print the latest session diff or a specific preserved artifact:

```bash
scripts/dg_agent.sh sessions diff --latest
scripts/dg_agent.sh sessions diff 1
scripts/dg_agent.sh sessions artifact context_md --latest
scripts/dg_agent.sh sessions artifact plan --latest --path-only
scripts/dg_agent.sh sessions artifact stdout --latest --path-only
```

The same preserved artifacts are available through the safe gateway:

```text
GET http://127.0.0.1:8090/v1/agent/sessions
GET http://127.0.0.1:8090/v1/agent/sessions/latest
GET http://127.0.0.1:8090/v1/agent/sessions/latest/diff
GET http://127.0.0.1:8090/v1/agent/sessions/latest/artifacts/context_md
GET http://127.0.0.1:8090/v1/agent/sessions/{session_id}/artifacts/final_diff
```

Useful artifact names:

- `context_md`
- `context_json`
- `plan`
- `task_report`
- `verify_report`
- `before_diff`
- `final_diff`
- `task_stdout`
- `task_stderr`

Build a compact repo context pack without calling the model:

```bash
scripts/dg_agent.sh context \
  --repo /path/to/repo \
  --task "Find where health response is built" \
  --max-files 3 \
  --out /tmp/dg-context.md
```

Generate a task-runner plan from a normal task:

```bash
scripts/dg_agent.sh plan \
  --repo /path/to/repo \
  --task "Add uptime_ms to the health response" \
  --file server.py \
  --auto-test \
  --out /tmp/dg-plan.json
```

Natural-language one-step edit without writing a JSON plan:

```bash
scripts/dg_agent.sh edit \
  --repo /path/to/repo \
  --task "Fix hello.py so greet('Ada') returns exactly hello, Ada!" \
  --file hello.py \
  --auto-test \
  --rollback-on-failure
```

This creates a temporary task-runner plan and delegates to
`scripts/run_task_runner.sh`.

`--auto-test` currently infers conservative commands such as:

- `python3 -m py_compile file.py`
- `bash -n file.sh`
- `python3 -m json.tool file.json >/dev/null`
- `go test ./...`
- `cargo test`
- `npm test -- --runInBand`
- `python3 -m pytest -q`

Run the same verification layer directly:

```bash
scripts/dg_agent.sh verify \
  --repo /path/to/repo \
  --file server.py \
  --report /tmp/dg-verify.json
```

or with an explicit command:

```bash
scripts/dg_agent.sh verify \
  --repo /path/to/repo \
  --test-cmd "python3 -m pytest -q" \
  --json
```

Explicit multi-step plan:

```bash
scripts/dg_agent.sh task \
  --repo /path/to/repo \
  --plan /path/to/plan.json \
  --report /tmp/dg-task-report.json \
  --rollback-on-failure
```

This delegates to `scripts/run_task_runner.sh`.

## Web/API Agent

```bash
scripts/dg_agent.sh web --repo /path/to/repo --port 3284
```

Open:

```text
http://127.0.0.1:3284/chat
```

This delegates to AgentAPI over Aider.

## OpenCode

```bash
scripts/dg_agent.sh opencode-agent -- /path/to/repo
scripts/dg_agent.sh opencode -- /path/to/repo
scripts/dg_agent.sh opencode-mcp -- /path/to/repo
scripts/dg_agent.sh opencode-acp -- --cwd /path/to/repo --hostname 127.0.0.1 --port 3295
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server opencode-acp --start
```

For the primary bounded terminal workflow on Windows, use
`scripts/dg_agent.sh opencode-agent -- /path/to/repo` or
`scripts/run_opencode_agent_windows.ps1` from the target repository. It keeps
only OpenCode's Bash tool and routes it through the verified DG read/session
delegate. Generic OpenCode/MCP/ACP remain separate OSS integration paths.

OpenCode is available as an experimental TUI, MCP-enabled TUI, and ACP server.
The current local package includes the Windows OpenCode payload for PowerShell
usage and `opencode-linux-x64` for WSL MCP process spawning. Provider/run, ACP,
and live MCP smokes pass; `opencode mcp list` verifies `dg_agent`, `repomix`,
and `serena` as connected.
For reliable edits, prefer `dg_agent.sh task`.

## Goose Experiment

```bash
scripts/dg_agent.sh goose -- run \
  --no-profile \
  --max-turns 1 \
  --text "Reply exactly OK."
```

Goose is available as an experimental ready-made OSS agent shell over the same
local OpenAI-compatible proxy. It brings sessions, MCP/extensions, review, and
TUI commands, but the current local DG profile is not reliable enough at native
tool-calling to replace the Aider/task-runner path. Keep `--max-turns` and an
external `timeout` around non-interactive `goose run` experiments.

`scripts/dg_agent.sh goose-mcp -- ...` runs Goose with an isolated Goose HOME
and mounts both the local DG MCP SDK server and upstream Serena semantic/LSP
MCP as stdio extensions.
`scripts/dg_agent.sh goose-acp` exposes that same profile as a stdio ACP agent
server; `scripts/dg_agent.sh goose-serve -- --port 3294` exposes Goose's
HTTP/WebSocket ACP server.

OpenHands is also available as an ACP stdio server:

```bash
scripts/dg_agent.sh openhands-acp -- --help
scripts/dg_agent.sh agent-bridge --repo /path/to/repo --server openhands-acp --start
```

This route uses `openhands acp --override-with-envs` under the hood because the
standalone `openhands-acp` entrypoint is not reliable in the current package.

OpenHands can also consume the repo-local MCP stack directly through its own
MCP config:

```bash
scripts/dg_agent.sh openhands-mcp -- --repo /path/to/repo --reset
.dg-agent/bin/openhands-mcp --reset
```

This writes `.dg-agent/openhands-persistence/mcp.json` with
`diffusiongemma-local-agent`, `repomix`, and `serena`.

Qwen Code is available on this Windows host as a bounded terminal inspection
experiment. The unified entrypoint prefers the WSL runner with DG, Repomix, and
Serena MCP mounted; the native Windows launcher remains a read-only fallback on
the safe GPU gateway. Edit requests stay on the Aider/session path:

```bash
scripts/dg_agent.sh qwen-code -- --repo /path/to/repo --dry-run
.dg-agent/bin/qwen-code --dry-run
python scripts/dg_agent.py qwen-code -- --repo . --dry-run -- --help
```

Use an explicit file path in the prompt, for example
`--prompt "Read src/app.py. Summarize the request flow."`. See
`docs/qwen_code_local.md` for the current runner and verified behavior.

AutoGen AgentChat is available as a Python framework route:

```bash
scripts/dg_agent.sh autogen -- --repo /path/to/repo --dry-run
.dg-agent/bin/autogen --dry-run
```

It uses `autogen-agentchat`, `autogen-ext[openai]`, and
`configs/client_profiles/autogen.dg.json`.

Hugging Face smolagents is available as another Python framework route:

```bash
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --dry-run
.dg-agent/bin/smolagents --dry-run
```

It uses `smolagents[toolkit]`, `openai`, and
`configs/client_profiles/smolagents.dg.json`.

LangGraph/LangChain is available as another Python graph-agent framework route:

```bash
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --dry-run
.dg-agent/bin/langgraph --dry-run
```

It uses `langgraph`, `langchain`, `langchain-openai`, and
`configs/client_profiles/langgraph.dg.json`. The working local route uses WSL
Python 3.14 plus Linux cp314 wheels in `.wheelhouse/langgraph-wsl-cp314`; the
Windows venv is not used for imports because Windows App Control blocks
`pydantic_core`.

CrewAI is available as another Python multi-agent framework route:

```bash
scripts/dg_agent.sh crewai -- --repo /path/to/repo --dry-run
.dg-agent/bin/crewai --dry-run
```

It uses `crewai.Agent`, `Task`, `Crew`, `LLM`, and
`configs/client_profiles/crewai.dg.json`.

Open Interpreter is available as an OSS code-execution shell route:

```bash
scripts/dg_agent.sh open-interpreter -- --repo /path/to/repo --dry-run
.dg-agent/bin/open-interpreter --dry-run
```

It uses `open-interpreter` with `auto_run=false`, `safe_mode=ask`, and
`configs/client_profiles/open-interpreter.dg.json`.

LlamaIndex is available as a RAG/agent workflow framework route:

```bash
scripts/dg_agent.sh llamaindex -- --repo /path/to/repo --dry-run
.dg-agent/bin/llamaindex --dry-run
```

It uses `OpenAILike` plus `AgentWorkflow.from_tools_or_functions`, which
selects `ReActAgent` for the current non-function-calling model profile.

Haystack is available as a BM25 RAG pipeline over repository files:

```bash
scripts/dg_agent.sh haystack -- --repo /path/to/repo --dry-run
.dg-agent/bin/haystack --dry-run
```

It uses `haystack-ai` with `InMemoryDocumentStore`,
`InMemoryBM25Retriever`, and `OpenAIChatGenerator`.

Docs: `docs/goose_local.md`, `docs/qwen_code_local.md`, `docs/autogen_local.md`, `docs/smolagents_local.md`, `docs/langgraph_local.md`, `docs/crewai_local.md`, `docs/open_interpreter_local.md`, `docs/llamaindex_local.md`, `docs/haystack_local.md`.

## LiteLLM Gateway

```bash
scripts/dg_agent.sh litellm
```

Then point OpenAI-compatible clients at:

```text
base_url: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
```

This is the preferred compatibility endpoint for external IDE clients and
agent shells. It routes to the local Aider-compatible proxy and keeps a stable
model alias in `configs/litellm.dg.yaml`.

In safe mode, generic chat still avoids raw backend generation. If a client
sends a command-like OpenAI `tools` schema, the proxy returns a `tool_calls`
response that delegates to `dg_agent.sh session --rollback-on-failure`.
The same delegate is available through non-streaming `POST /v1/responses` as a
Responses API `function_call` output item.

Docs: `docs/litellm_gateway.md`.

Client profiles for Continue, Cline/Roo/Kilo style OpenAI-compatible clients,
and OpenAI SDK scripts are in `configs/client_profiles/`.

## RAG Context

```bash
scripts/dg_agent.sh rag --repo /repo --task "..." --print-context
scripts/dg_agent.sh rag --repo /repo --task "..." --max-context-chars 650 --max-files 3 --max-tokens 128
scripts/dg_agent.sh repo-pack --repo /repo --include "src/**" --style markdown --stdout
```

This wraps `scripts/rag_code_agent.py`, the read-only `rg` retrieval layer for
small-context use. Use `--print-context` when an outer agent should inspect the
selected file map and snippets before planning edits.

`repo-pack` wraps upstream Repomix through local `npx --yes repomix`. Use tight
`--include` filters, `--compress`, and `--token-budget` when the client needs a
packed artifact rather than ranked snippets.

For MCP-capable clients, `configs/client_profiles/mcp-client-snippets.json`
also includes optional native Repomix MCP server snippets using
`scripts/run_repomix_mcp.sh`. The wrapper pins the local Node path before
launching upstream `repomix --mcp`, which is more reliable from IDE-launched MCP
processes than calling `npx` directly.

Docs: `docs/rag_agent.md`.

## MCP Server

```bash
scripts/dg_agent.sh mcp --list-tools
scripts/dg_agent.sh mcp
scripts/dg_agent.sh mcp-http -- --host 127.0.0.1 --port 8765
scripts/dg_agent.sh serena-mcp --help-local
```

The MCP server is a local stdio bridge for clients that can launch MCP tools.
The default implementation uses the official `modelcontextprotocol/python-sdk`
`FastMCP` server; `--legacy` keeps the dependency-free JSON-RPC fallback for
debugging. It exposes reliable DG wrapper commands as tools instead of asking
the model to invent tool calls:

`mcp-http` exposes the same tools over the official streamable HTTP transport at
`http://127.0.0.1:8765/mcp` for clients that cannot spawn stdio servers.

`serena-mcp` is an optional upstream semantic/LSP MCP server. Its active WSL
runtime is currently available; `client-init` includes it only after the live
`serena-mcp --check-installed` probe succeeds. The core DG MCP server remains
available independently.

- `dg_repo_status`
- `dg_list_files`
- `dg_search`
- `dg_read_file`
- `dg_git_diff`
- `dg_task_note`
- `dg_task_notes`
- `dg_status`
- `dg_context`
- `dg_rag_context`
- `dg_rag_answer`
- `dg_repo_pack`
- `dg_preflight`
- `dg_plan`
- `dg_task`
- `dg_session`
- `dg_verify`
- `dg_capabilities`
- `dg_client_smoke`
- `dg_client_report`
- `dg_sessions`
- `dg_session_artifact`

It also exposes resources `dg://client-pack`, `dg://status`, `dg://usage`,
`dg://sessions`, `dg://sessions/latest`, `dg://sessions/latest/diff`,
`dg://capabilities/latest`, `dg://client-handoff`, and
`dg://client-handoff/markdown`; repo-local handoff resources
`dg://agent-hub`, `dg://agent-hub/markdown`, `dg://command-kit`,
`dg://command-kit/markdown`, `dg://ide-clients`,
`dg://ide-clients/markdown`, `dg://codex-profile`, and
`dg://codex-profile/config`; and prompts `dg_agent_session`, `dg_agent_context`,
`dg_agent_continue_latest` for MCP clients that support prompt/resource
discovery.

Use `dg_client_report` first when an MCP client needs a portable repo handoff,
then read `dg://client-handoff` or `dg://client-handoff/markdown`.
For a broader bootstrap, read `dg://agent-hub/markdown`, then use the command,
IDE, or Codex resources matching the external client.
Use `dg_rag_context` for compact repository-scale retrieval without model
generation, or `dg_repo_pack` for bounded Repomix packed context. Use `dg_session` for one-shot bounded edits. Use `dg_preflight`,
`dg_context`, `dg_plan`, and `dg_task` when an MCP client should inspect or
persist a task plan before execution.

Use `configs/client_profiles/mcp-server.json` or the workspace-local
`.dg-agent/mcp-server.json` profile in MCP-capable clients. Copy-ready client
templates are exported as `.dg-agent/claude-code.mcp.json`,
`.dg-agent/claude-desktop-mcp.json`, `.dg-agent/cursor.mcp.json`,
`.dg-agent/vscode.mcp.json`, and `.dg-agent/mcp-client-snippets.json`.

Use `scripts/dg_agent.sh mcp-client-config --repo /path/to/repo --client cursor`
or `.dg-agent/bin/mcp-client-config --client cursor` to merge the local server
entry into project client configs without removing unrelated MCP servers. Add
`--with-repomix` to install the optional native Repomix MCP server in the same
config. Add `--with-serena` to install the optional native Serena MCP server;
the flags can be combined. Use `--with-oss-stack` for the recommended full
bundle: DG workflow tools, Repomix repository packing, and Serena semantic/LSP
tools.

Docs: `docs/mcp_server.md`.

Docs: `docs/ide_client_profiles.md`.

## Watchdog

```bash
scripts/dg_agent.sh status
scripts/dg_agent.sh up
scripts/dg_agent.sh watchdog -- status
scripts/dg_agent.sh watchdog -- ensure
scripts/dg_agent.sh watchdog -- watch --interval 30 --restart
```

Docs: `docs/stack_watchdog.md`.

## Windows

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\root\diffusiongemma-agent\scripts\dg_agent_windows.ps1 doctor
```
