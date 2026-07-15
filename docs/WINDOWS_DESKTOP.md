# Windows desktop installer

The desktop application is the recommended path for users who do not want to
manage Python, PowerShell commands, or model runtime files manually.

[Download the current Windows installer](https://github.com/aogavrilov/diffusiongemma-agent/releases/download/desktop-v0.1.1/DiffusionGemmaAgentSetup-0.1.1.exe)
and open it normally. Python and the CUDA Toolkit do not need to be installed.

## User flow

1. Download and open `DiffusionGemmaAgentSetup-0.1.1.exe`.
2. The installer launches DiffusionGemma Agent when it finishes. It is also
   available from the Start menu afterward.
3. The app checks the computer automatically; **Check this computer** reruns
   the check when needed.
4. Review and accept the model and CUDA licenses, then click **Download and
   install**.
5. On **Agent**, choose a Git repository, describe one concrete task, and click
   **Run task**.
6. Review the activity, generated diff, and test result. Stop the service when
   finished to release GPU memory.

The setup program installs under the current user's local application folder
and includes its own Python runtime. It searches common download folders and
Hugging Face caches for the exact compatible IQ3 GGUF. A complete local bundle
is used directly; a standalone model is hardlinked into the runtime when the
filesystem permits it. Missing runtime files are downloaded with resume
support. The full download is approximately 13.2 GB only when no compatible
local model exists.

Discovery checks the configured/default runtime path, `DG_RUNTIME_DIR`, common
layouts below the Windows Downloads folder, and DiffusionGemma snapshots below
`HF_HOME`, `HF_HUB_CACHE`, and the standard Hugging Face caches. Selection is
validated against the release model filename and exact byte size; unrelated
GGUF files are ignored. The detected source and chosen runtime directory are
shown on **Setup** before installation.

## What is automated

- Windows, WSL2, NVIDIA GPU, VRAM, disk, and runtime availability checks;
- validated discovery and reuse of an existing compatible runtime or IQ3 GGUF;
- elevated WSL2 installation launch when WSL is missing;
- resumable Hugging Face runtime download;
- WSL runtime and Python dependency installation;
- model and agent service start/stop;
- repository task execution, activity output, logs, and diff display.

If WSL2 installation requires a reboot, open the app again afterward and rerun
the computer check. The installed app remains available from the Start menu.

## Security and signing

The locally built preview installer is not Authenticode-signed. Windows may
show an unknown-publisher or SmartScreen warning. A publicly promoted
nontechnical-user release should be signed with an organization-validated code
signing certificate and publish its SHA-256 value alongside the download.

## Build

Requirements for maintainers only: Python 3.10+, NSIS 3, and network access for
the PyInstaller build dependency.

```powershell
.\desktop\Build-DesktopInstaller.ps1
```

The command creates the standalone application, runs GUI and CLI smoke tests,
builds the NSIS installer, and writes checksums under `dist\desktop`.
