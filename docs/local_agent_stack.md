# Local Agent Stack

This repo now has fifteen layers around the local DiffusionGemma runtime. The
preferred entrypoint is:

```bash
cd /root/diffusiongemma-agent
scripts/dg_agent.sh status
scripts/dg_agent.sh up
scripts/dg_agent.sh doctor
scripts/dg_agent.sh capabilities --live
```

Docs: `docs/dg_agent_cli.md`.

OSS wrapper matrix: `docs/oss_agent_wrappers.md`.

## Last Verified Runtime State

Checked on 2026-07-14 from the Windows checkout
`C:\Users\alexg\Downloads\diffusiongemma-agent` with the active backend in WSL.
Runtime availability is time-sensitive; recheck with `scripts/dg_agent.sh status`
or `scripts/dg_agent.sh doctor` before relying on these endpoints.

Runtime:

```text
backend  http://127.0.0.1:4100/healthz
proxy    http://127.0.0.1:8090/healthz
litellm  http://127.0.0.1:4100/v1/models
model    diffusiongemma-26b-a4b-it-iq3m-fullgpu
gpu      full offload profile, ngl=999, maxtok=768, about 14.7 GiB VRAM loaded
```

Installed and audited OSS agent surfaces:

```text
Aider        active WSL runtime, 0.86.2
OpenCode     .tools/opencode/node_modules/.bin/opencode plus opencode-linux-x64, 1.17.20; provider/run/MCP/ACP smoke pass
MCP SDK      active WSL runtime, 1.28.1
Serena       WSL bridge, 1.5.3, live Pyright symbols
Qwen Code    .tools/qwen-code/node_modules/.bin/qwen, 0.19.10, WSL runner + MCP
LangGraph    WSL Python 3.14 venv from local cp314 wheelhouse; smoke-import/dry-run pass
Watchdog     repo-local status/up/watchdog stack-control scripts restored and smoke pass
```

Core verification completed on this checkout:

```bash
python scripts/dg_agent.py smoke --suite qwen-code --timeout 180
python scripts/dg_agent.py smoke --suite mcp --suite serena-mcp --timeout 180
python scripts/dg_agent.py smoke --suite opencode-provider --suite opencode-run --suite opencode-mcp --suite opencode-acp --timeout 180
python scripts/dg_agent.py smoke --suite langgraph --timeout 240
python scripts/dg_agent.py smoke --suite watchdog --suite stack-control --timeout 60
python scripts/dg_agent.py smoke --suite wrappers --timeout 180
```

OpenCode is installed from the Windows npm payload for PowerShell usage and the
Linux optional package `opencode-linux-x64` for WSL MCP process spawning. Live
`opencode mcp list` verifies `dg_agent` and `repomix` as connected. Serena has
a separate MCP smoke with live Pyright symbols and is intended for IDE bundles.

The verified Aider end-to-end scenario changed only an allowed Python file
through the GPU gateway, then passed an independent WSL Python assertion. The
temporary Aider histories stayed outside the target repository. Optional
OpenHands, AutoGen, smolagents, CrewAI, Open Interpreter,
LlamaIndex, and SWE-family wrappers remain separate experiments and
must be smoke-tested individually before use.

External clients should prefer the client pack plus MCP resources instead of
large prompts. The exported `local_agent` profile includes artifact commands:
`scripts/dg_agent.sh agent-runs list`,
`scripts/dg_agent.sh agent-runs show --latest`, and
`scripts/dg_agent.sh agent-runs artifact transcript --latest`.

## 1. Fast Backend

```text
http://127.0.0.1:4100/v1
```

Start from Windows:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\root\diffusiongemma-agent\scripts\start_agent_fast_service_windows.ps1
```

## 2. Aider-Compatible Model Proxy

```text
http://127.0.0.1:8090/v1
```

This proxy compresses Aider prompts, repairs malformed output fences, applies
exact single-file return constraints when the model output is malformed, and
limits the model output to a size the current DG profile can handle.

Start:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\root\diffusiongemma-agent\scripts\start_aider_proxy_windows.ps1
```

## 3. Reliable Automated Edits

Use the agent profile for the normal Codex-like local workflow:

```bash
/root/diffusiongemma-agent/scripts/dg_agent.sh agent \
  --repo /path/to/repo \
  --task "Fix the failing test and keep the public API unchanged" \
  --file path/to/file.py
```

This wraps the context packer, task runner, automatic verification, rollback on
failure, deterministic repair fallbacks for exact small edits, and preserved
session artifacts into one command.

Use the lower-level task runner for explicit multi-step plans:

```bash
/root/diffusiongemma-agent/scripts/run_task_runner.sh \
  --repo /path/to/repo \
  --plan /path/to/plan.json \
  --report /tmp/dg-task-report.json \
  --rollback-on-failure
```

This is the most reliable current mode because it splits work into bounded
steps, verifies each step, can repair common exact Python return edits when the
model/Aider output is malformed, can handle explicit single-occurrence text
replacement tasks, and can rollback a failed step patch.

Docs: `docs/task_runner.md`.

## 4. Interactive Web/API Agent

Use AgentAPI when you want a ready-made web/API surface over Aider:

```bash
/root/diffusiongemma-agent/scripts/run_agentapi_aider.sh \
  --repo /path/to/repo \
  --port 3284
```

Open:

```text
http://127.0.0.1:3284/chat
```

Docs: `docs/agentapi_aider.md`.

## OpenCode Compact Delegate

The primary interactive terminal route is the compact OpenCode delegate:

```powershell
Set-Location C:\path\to\repo
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_agent_windows.ps1
```

or through the unified CLI:

```bash
scripts/dg_agent.sh opencode-agent -- /path/to/repo
```

It uses the upstream OpenCode interface but exposes one `bash` tool. The safe
gateway immediately delegates that tool to the existing read/persistent-supervisor runner,
so a task gets ranked retrieval, narrow deterministic repairs when applicable,
Aider for broader file edits, verification, and rollback. This avoids relying
on native tool-calling from the diffusion model. The compact profile uses a
450-second OpenCode bash deadline to cover the 420-second bounded session.

The model remains on the GPU; OpenCode, retrieval, Git checks, and MCP process
management run on CPU and do not add model VRAM residency.

For semantic navigation before wide work, use the default IDE MCP bundle with
Serena, or `repo-map`/`code-outline`. Serena is not auto-mounted here because
its cold start exceeds OpenCode's MCP connect timeout.

## Experimental: Generic OpenCode

`configs/opencode.dg.json` points generic OpenCode at the same local proxy. Node.js and
OpenCode are installed locally under `.tools/`, and provider discovery is
validated with `scripts/smoke_opencode_local.sh`. A minimal `opencode run`
fallback is validated with `scripts/smoke_opencode_run_fallback.sh`; it confirms
that the CLI does not hang or expose proxy 500s, not that OpenCode edits are
reliable with this model.

`configs/opencode.dg-mcp.json` mounts the DG MCP server and upstream Repomix
MCP. `scripts/dg_agent.sh opencode-mcp -- /repo` launches that profile as a
TUI, and `scripts/dg_agent.sh opencode-acp -- --cwd /repo --hostname 127.0.0.1 --port 3295` exposes
OpenCode's ACP server over the same profile.

Docs: `docs/opencode_local.md`.

## Experimental: Goose

Goose is installed locally under `.tools/goose` and launched through the same
OpenAI-compatible proxy:

```bash
/root/diffusiongemma-agent/scripts/run_goose_local.sh run \
  --no-profile \
  --max-turns 1 \
  --text "Reply exactly OK."
```

It is useful as a ready-made OSS agent shell with sessions, MCP/extensions,
review, and TUI commands. Treat it as experimental with the current DG model:
native tool-calling is still the weak point, so reliable edits should stay on
the Aider/task-runner path.

Docs: `docs/goose_local.md`.

## OpenAI Gateway: LiteLLM

LiteLLM is available as a stable external compatibility layer:

```bash
/root/diffusiongemma-agent/scripts/run_litellm_gateway.sh
```

External clients can use:

```text
base_url: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
```

Docs: `docs/litellm_gateway.md`.

Checked-in client profiles:

```text
configs/client_profiles/openai-compatible.local.json
configs/client_profiles/openai.env
configs/client_profiles/continue.config.yaml
```

Docs: `docs/ide_client_profiles.md`.

## Watchdog

Use the watchdog to check and recover the local runtime stack:

```bash
/root/diffusiongemma-agent/scripts/dg_agent.sh status
/root/diffusiongemma-agent/scripts/dg_agent.sh up --restart
/root/diffusiongemma-agent/scripts/dg_agent.sh watchdog -- status
/root/diffusiongemma-agent/scripts/dg_agent.sh watchdog -- ensure --restart
```

It covers backend `4100`, Aider proxy `8090`, and LiteLLM-compatible `4100/v1`.

Docs: `docs/stack_watchdog.md`.

## Recommended Use

- Default coding-agent mode: `scripts/dg_agent.sh agent --repo /repo --task "..." --file path`
- One-command coding-agent mode: `scripts/dg_agent.sh run --repo /repo --task "..." --file path --start`
- OSS wrapper status: `scripts/dg_agent.sh wrappers`
- OSS wrapper audit/install: `scripts/dg_agent.sh bootstrap` and `scripts/dg_agent.sh bootstrap --install`
- Client/IDE profile export: `scripts/dg_agent.sh client-pack --write`
- Target repo setup: `scripts/dg_agent.sh workspace-init --repo /repo`
- Repo-local launchers: `.dg-agent/bin/run --task "..." --file path --start`
- Repo-local health: `.dg-agent/bin/capabilities --latest`, `.dg-agent/bin/doctor`, `.dg-agent/bin/status`
- Repo-local work: `.dg-agent/bin/plan`, `.dg-agent/bin/edit`, `.dg-agent/bin/task`, `.dg-agent/bin/supervisor`, `.dg-agent/bin/web`
- Target repo preflight: `scripts/dg_agent.sh preflight --repo /repo --task "..." --file path`
- Capability audit: `scripts/dg_agent.sh capabilities` or `scripts/dg_agent.sh capabilities --live`
- Last capability report: `scripts/dg_agent.sh capabilities --latest`
- Small direct code edit: `scripts/run_supervisor_agent.sh`.
- Repo context pack: `scripts/dg_agent.sh context --repo /repo --task "..."`
- Repo-scale compact RAG retrieval: `scripts/dg_agent.sh rag --repo /repo --task "..." --print-context`
- OSS repo packer: `scripts/dg_agent.sh repo-pack --repo /repo --include "src/**" --style markdown --stdout`
- Generated plan: `scripts/dg_agent.sh plan --repo /repo --task "..."`
- Full session with artifacts: `scripts/dg_agent.sh session --repo /repo --task "..." --auto-test`
- Session history: `scripts/dg_agent.sh sessions list` and `scripts/dg_agent.sh sessions show --latest`
- Session diff/artifacts: `scripts/dg_agent.sh sessions diff --latest` and `scripts/dg_agent.sh sessions artifact context_md --latest`
- Natural-language edit: `scripts/dg_agent.sh edit --repo /repo --task "..." --auto-test`
- Standalone verification: `scripts/dg_agent.sh verify --repo /repo --file path`
- Multi-file or multi-step task: `scripts/dg_agent.sh task` with an explicit plan.
- Browser/API interaction: `scripts/dg_agent.sh web`.
- Primary OpenCode terminal route: `scripts/dg_agent.sh opencode-agent`.
- Generic Codex-like TUI experiment: `scripts/dg_agent.sh opencode`.
- Goose/MCP agent experiment: `scripts/dg_agent.sh goose -- run --no-profile --max-turns 1 --text "..."`
- OpenHands MCP setup: `scripts/dg_agent.sh openhands-mcp -- --repo /repo --reset`
- Qwen Code read-only inspection: `scripts/dg_agent.sh qwen-code -- --repo /repo -- --prompt "Read path/to/file.py. Summarize ..."`
- AutoGen AgentChat framework experiment: `scripts/dg_agent.sh autogen -- --repo /repo --dry-run`
- smolagents CodeAgent framework experiment: `scripts/dg_agent.sh smolagents -- --repo /repo --dry-run`
- LangGraph graph-agent framework experiment: `scripts/dg_agent.sh langgraph -- --repo /repo --dry-run`
- CrewAI multi-agent framework experiment: `scripts/dg_agent.sh crewai -- --repo /repo --dry-run`
- Open Interpreter shell experiment: `scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run`
- LlamaIndex RAG/agent framework experiment: `scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run`
- Haystack BM25 RAG: `scripts/dg_agent.sh haystack -- --repo /repo --retrieve-only --task "..."`
- Persistent local coding controller: `scripts/dg_agent.sh autonomous -- --repo /repo --task "..."`
- MCP HTTP endpoint: `scripts/dg_agent.sh mcp-http -- --host 127.0.0.1 --port 8765`
- Serena semantic MCP: `scripts/dg_agent.sh serena-mcp`
- External OpenAI-compatible clients: `scripts/dg_agent.sh litellm`.
- Validate IDE/OpenAI-compatible profiles: `scripts/dg_agent.sh smoke --suite gateway-clients`.
- Recover local services: `scripts/dg_agent.sh watchdog -- ensure --restart`.
- One-command stack control: `scripts/dg_agent.sh status`, `scripts/dg_agent.sh up`, `scripts/dg_agent.sh down`.
