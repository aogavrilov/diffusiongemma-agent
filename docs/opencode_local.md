# OpenCode Local Profile

OpenCode is the primary ready-made open-source terminal-agent shell wired into
this Windows checkout. It runs locally from `.tools/opencode`; it does not
install a global npm package.

```text
OpenCode on Windows -> safe agent gateway :8090 -> WSL GPU model service :4100
```

The gateway restricts this model to a `768`-token input and `256`-token output
budget. It performs tool delegation and repository operations outside the
model, which is necessary for the current small-context DiffusionGemma setup.

## Install and Start

From PowerShell in this repository:

```powershell
.\scripts\install_opencode_windows.ps1
.\scripts\start_agent_gateway.ps1
Invoke-RestMethod http://127.0.0.1:8090/healthz
```

`install_opencode_windows.ps1` installs the upstream `opencode-ai` package
locally and explicitly runs its post-install binary setup. The gateway forwards
to the existing GPU model at `http://127.0.0.1:4100/v1`; it does not restart or
move the model.

## Use in a Repository

Start OpenCode from the target Git repository so its file tools and MCP server
are scoped to that repository:

```powershell
Set-Location C:\path\to\target-repo
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_windows.ps1
```

For a bounded non-interactive request:

```powershell
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_windows.ps1 run `
  --format json `
  --model diffusiongemma-local/diffusiongemma-26b-a4b-it-iq4xs-aider-local `
  'Read src/app.py and explain the request flow. Do not edit files.'
```

## Primary Compact Delegate

For the practical Codex-like local workflow on this machine, use the compact
OpenCode profile instead of the generic one:

```powershell
Set-Location C:\path\to\target-repo
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_agent_windows.ps1
```

For one non-interactive task:

```powershell
C:\Users\alexg\Downloads\diffusiongemma-agent\scripts\run_opencode_agent_windows.ps1 run `
  --format json `
  'Fix src\math_utils.py so add(a, b) returns the sum of its two arguments. Verify the change.'
```

This profile exposes only OpenCode's built-in `bash` tool. The safe gateway
immediately redirects that call to the local DG workflow: read-only requests
use compact repository retrieval; edit requests use the persistent supervisor,
checkpointed session runner, verification, and rollback-on-failure. DiffusionGemma does not need to perform
native tool selection, which is unreliable for this runtime.

The launcher sets `OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS=450000` for
this profile so OpenCode does not interrupt the bounded 420-second edit
session. It restores the previous environment value on exit. Narrow, verified
deterministic repairs such as explicit Python return expressions and an
explicit two-argument sum/difference/product/quotient complete without a
model generation round-trip; broader edits still use Aider and may reach their
own timeout.

The same launcher is used by native Windows `dg_agent.py opencode`,
`opencode-mcp`, and `opencode-acp` commands. Provider discovery can run without
MCP:

```powershell
.\scripts\run_opencode_windows.ps1 -NoMcp models diffusiongemma-local
```

## MCP and Safety

By default, the Windows launcher creates a temporary OpenCode config that
mounts exactly one MCP server: `dg_agent`. It starts that server through WSL,
passes the current Windows repository path as `DG_MCP_REPO`, and removes the
temporary config on exit.

```powershell
.\scripts\run_opencode_windows.ps1 mcp list
```

Serena is intentionally not mounted by this launcher. Its installed Windows
environment is separate from the working WSL Serena runtime. Keeping only
`dg_agent` in OpenCode's temporary profile bounds the tool schema for the
768-token model; IDE client profiles can mount Serena alongside DG MCP.

Read-only tasks delegate to the bounded read agent. Edit requests delegate to
the artifacted persistent supervisor, which selects files, verifies syntax and
optional tests, and can reverse only its own tracked diff when it starts from a
clean worktree. The runner uses the dedicated WSL Aider runtime for scoped
file edits and keeps Aider history in a temporary directory rather than the
target repository. Narrow deterministic repairs remain available as a fallback
for exact replacements and checked Python return-expression changes.

For non-interactive `opencode run`, the Windows runner propagates a nonzero
exit code when the delegated DG session reports failure. Automation should use
that exit code and the session report, not a textual model summary. File names
appearing after a `do not modify` constraint are excluded from bounded edit
selection.

## Validation

This host has verified all of the following against the live GPU gateway:

- OpenCode provider discovery and `dg_agent` MCP connection.
- A read-only file request through the OpenCode `bash` tool, PowerShell bridge,
  and WSL read agent with no file mutation.
- A scoped Python edit through the same route, with a verified Git diff and
  preserved session/task artifacts.
- Aider `0.86.2` through the WSL Python `3.12` runtime, including a verified
  file-level edit with no `.aider*` or `__pycache__` artifacts in the target
  repository.

The gateway itself continues to use WSL Python `3.14`; Aider runs separately
from `/root/diffusiongemma-agent/.venv-aider/bin/python` on Python `3.12`.
Use explicit file hints and small tasks, not broad repository-wide requests,
because the model budget is still `768` input tokens and `256` output tokens.
For semantic navigation before a wider task, use Serena from an IDE MCP bundle
or run `repo-map`/`code-outline`; Serena is intentionally excluded from the
compact OpenCode path because its startup time exceeds OpenCode's MCP connect
budget.
