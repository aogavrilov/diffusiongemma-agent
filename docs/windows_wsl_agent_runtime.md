# Windows + WSL Local Agent Runtime

This checkout runs the GPU model in WSL and exposes the agent gateway to
Windows clients. The gateway keeps the inference service on `4100` unchanged
and adds bounded repository tools on `8090`.

## Start

From PowerShell in this repository:

```powershell
.\scripts\start_agent_gateway.ps1
```

It starts the gateway through WSL with the working Python environment at
`/root/diffusiongemma-agent/.venv-wsl/bin/python`. The gateway forwards model
requests to `http://127.0.0.1:4100/v1` and is healthy at:

```text
http://127.0.0.1:8090/healthz
```

## Connect an IDE

Generate the project-local MCP configuration from PowerShell:

```powershell
python scripts\dg_agent.py client-init --repo C:\path\to\project --client cursor --no-oss-stack
```

Replace `cursor` with `claude-code`, `claude-desktop`, or `vscode` as needed.
The generated primary MCP server uses `wsl.exe` and passes both the Windows
repository location and the WSL Python path explicitly. It therefore works
without copying the project into `/root/diffusiongemma-agent`.

Use `--no-oss-stack` when the client needs only the primary MCP bridge. It
provides repository status, files, search, bounded file reads, Git diff,
context, RAG context, plans, sessions, verification, client reports, and
preserved artifacts. Scoped edits can use the separate WSL Aider runtime
described below; the optional Serena semantic MCP server also runs through WSL.

## Agent Commands

Run a safe inspection task through WSL:

```powershell
wsl.exe --exec bash -lc "cd /mnt/c/Users/alexg/Downloads/diffusiongemma-agent && DG_AGENT_PYTHON=/root/diffusiongemma-agent/.venv-wsl/bin/python ./scripts/dg_agent.sh agent --repo /mnt/c/path/to/project --task 'Find the relevant implementation' --mode read --json"
```

The read route first tries the model tool loop. If the current diffusion model
does not emit a usable final answer or tool call, it returns a deterministic
repository context pack and records both the model transcript and fallback
artifacts under `runlogs/dg-agent-runs/`. This prevents an incomplete internal
thought from being presented as an answer.

## Task Plans

`dg_agent.sh task` is available in the WSL runtime again. It executes the
existing plan format one bounded step at a time, stores an aggregate report and
per-step supervisor reports, and rejects paths outside the repository. A
dry-run validates and prints the planned supervisor commands without changing
files:

```powershell
wsl.exe --exec bash -lc "cd /mnt/c/Users/alexg/Downloads/diffusiongemma-agent && DG_AGENT_PYTHON=/root/diffusiongemma-agent/.venv-wsl/bin/python ./scripts/dg_agent.sh task --repo /mnt/c/path/to/project --plan /mnt/c/path/to/plan.json --dry-run"
```

Non-dry runs refuse a dirty Git worktree unless `--allow-dirty` is explicit.
With `--rollback-on-failure`, the runner reverses only the tracked diff made by
the task when it started from a clean tree; it does not reset the repository or
delete untracked files.

For small tasks with an exact Python return or replacement constraint, the
already checked-in deterministic supervisor can make and verify the change
without a model edit. Other scoped code edits use Aider through
`scripts/run_aider_local.sh`; it applies only the selected files, then the
supervisor checks syntax and the requested test command. Aider history is kept
outside the target repository and Python syntax validation runs in memory, so
the runner does not create `.aider*` files or `__pycache__`.

## OpenCode on Windows

The supported ready-made OSS agent shell on this host is upstream OpenCode,
installed locally under `.tools/opencode`. Install it and start the existing
GPU gateway from this checkout:

```powershell
.\scripts\install_opencode_windows.ps1
.\scripts\start_agent_gateway.ps1
```

Then start it from the target repository, not from this agent repository:

```powershell
Set-Location C:\path\to\project
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_windows.ps1
```

The launcher adds the working `dg_agent` MCP server through WSL and uses the
safe gateway on `http://127.0.0.1:8090/v1`. Live model limits are `768` input
tokens and `256` output tokens. It supports bounded inspection and scoped edit
tasks, with preserved run artifacts; see `docs/opencode_local.md` for commands
and current limits.

## Qwen Code on Windows

The optional Qwen Code `0.19.10` CLI is installed locally and runs through a
private Node `22.17.1` runtime because system Node 24 aborts on Qwen shutdown.
The unified launcher prefers the WSL runner with DG, Repomix, and Serena MCP;
native PowerShell remains an explicit read-only fallback on the safe GPU
gateway. See `docs/qwen_code_local.md`; use Aider/session for edits.

## Current Optional Gaps

The official MCP SDK is working in the WSL runtime. Native WSL Node.js is not
required for the Windows OpenCode launcher, which uses the installed Windows
Node runtime and invokes WSL only for `dg_agent`. Aider `0.86.2` is installed
in a separate portable Python `3.12` environment at
`/root/diffusiongemma-agent/.venv-aider`; the gateway remains on Python `3.14`.
`preflight` reports the core MCP/gateway runtime as ready and lists optional
integrations separately. The model service and primary gateway do not depend on
them.

OpenCode intentionally mounts only the DG MCP server to keep its tool schema
bounded for the small-context model. IDE client profiles can additionally mount
the working WSL Serena runtime.
