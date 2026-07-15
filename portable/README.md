# DiffusionGemma Agent Portable

Extract, install, and start on another Windows machine in one line:

```powershell
tar -xf .\diffusiongemma-agent-portable.tar; powershell -ExecutionPolicy Bypass -File .\diffusiongemma-agent-portable\Install-DiffusionGemmaAgent.ps1
```

Run a repository task:

```powershell
& .\dg.ps1 -Repo C:\work\repo -Task "Fix src/x.py and run pytest -q" -File src/x.py
```

Stop the local backend and proxy:

```powershell
& .\dg.ps1 -Stop
```

Required outside the bundle: Windows 10/11, initialized WSL2 Ubuntu, current
NVIDIA Windows driver with WSL CUDA support, about 14 GB free WSL storage, and
about 16 GB VRAM. The CUDA Toolkit itself is bundled and is not required. Keep
about 38 GB free while archive, extracted folder, and installed WSL copy coexist.
