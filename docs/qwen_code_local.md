# Qwen Code Local Wrapper

Qwen Code is an upstream open-source terminal agent connected to the local
DiffusionGemma GPU gateway. It is an inspection-only companion to the primary
Aider edit workflow.

## Verified Runtime

```text
Qwen Code: 0.19.10
Node: .tools/node-v22.17.1-win-x64/node.exe
WSL/Git Bash gateway: http://127.0.0.1:4100/v1
WSL/Git Bash model: diffusiongemma-local
WSL/Git Bash MCP: diffusiongemma-local-agent, repomix, serena
native Windows fallback gateway: http://127.0.0.1:8090/v1
native Windows fallback model: diffusiongemma-26b-a4b-it-iq4xs-aider-local
mode: read-only inspection
```

The local Node 22 runtime is intentional. The system Node 24 causes an upstream
Qwen/libuv shutdown assertion on this host. The wrapper does not modify the
global Node installation.

## Usage

Start the GPU backend and gateway first:

```powershell
.\scripts\start_agent_gateway.ps1
```

Inspect an explicitly named file from PowerShell through the native read-only
fallback:

```powershell
.\scripts\run_qwen_code_windows.ps1 --repo C:\path\to\repo -- --output-format json --prompt "Read src\app.py. Summarize the request flow."
```

The unified entrypoint maps Git Bash/MSYS and WSL calls to the MCP-enabled
runner. Native PowerShell uses the read-only fallback:

```powershell
python scripts\dg_agent.py qwen-code -- --repo C:\path\to\repo -- --prompt "Read src\app.py. State the error handling path."
```

From WSL, use a repository below `/mnt/<drive>/...` so the wrapper can map it
back to the Windows runner:

```bash
scripts/dg_agent.sh qwen-code -- --repo /mnt/c/path/to/repo -- \
  --prompt "Read src/app.py. State the error handling path."
```

Use prompts that name the file to inspect. The safe proxy offers the matching
file through a bounded `read_file` tool call for the native Windows fallback.
The WSL/Git Bash runner mounts `diffusiongemma-local-agent`, `repomix`, and
`serena` from `qwen-code.mcp.json`. Qwen edit requests are still not the
reliable path on this model; run Aider for any modification:

```powershell
wsl.exe --exec bash -lc 'cd /mnt/c/path/to/repo && /mnt/c/Users/alexg/Downloads/diffusiongemma-agent/scripts/run_aider_local.sh --repo "$PWD" --message "..."'
```

## Verification

```powershell
.\scripts\run_qwen_code_windows.ps1 --help-local
wsl.exe --exec bash -lc 'cd /mnt/c/Users/alexg/Downloads/diffusiongemma-agent && ./scripts/dg_agent.sh smoke --suite qwen-code --timeout 60'
```

The live smoke verifies the native runner and the local GPU gateway. A verified
read-only probe against `calc.py` returned `a - b` without changing the target
repository.
