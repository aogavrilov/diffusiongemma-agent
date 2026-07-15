# Portable Bundle

Build the self-contained IQ3 package on the working machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\portable\Build-DiffusionGemmaAgentBundle.ps1 -Archive
```

It creates `dist/diffusiongemma-agent-portable` and an optional tar archive.
The package includes the 12.4 GB IQ3 GGUF, known working CUDA runtime binary,
CUDA 13 runtime libraries, server, and agent code. It excludes logs, virtual environments, source build
trees, OpenCode, and optional agent frameworks.

On another Windows machine with NVIDIA driver, WSL2, and Ubuntu already
available, extract and install in one line:

```powershell
tar -xf .\diffusiongemma-agent-portable.tar; powershell -ExecutionPolicy Bypass -File .\diffusiongemma-agent-portable\Install-DiffusionGemmaAgent.ps1
```

The installer copies runtime files to WSL ext4, creates Python runtime with
FastAPI, Aider, and Haystack, then starts backend plus safe proxy. Run a task:

```powershell
& .\diffusiongemma-agent-portable\dg.ps1 -Repo C:\work\repo -Task "Fix src/x.py and run pytest -q" -File src/x.py
```

The target needs about 14 GB free in WSL and about 16 GB VRAM. During transfer
and installation, allow about 38 GB while tar, extracted files, and WSL copy
coexist. The CUDA Toolkit is bundled. NVIDIA driver and WSL2 remain prerequisites.
