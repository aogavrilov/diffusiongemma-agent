# Windows desktop installer

The desktop application is the recommended path for users who do not want to
manage Python, PowerShell commands, or model runtime files manually.

[Download the current Windows installer](https://github.com/aogavrilov/diffusiongemma-agent/releases/download/desktop-v0.1.0/DiffusionGemmaAgentSetup-0.1.0.exe)
and open it normally. Python and the CUDA Toolkit do not need to be installed.

## User flow

1. Download and open `DiffusionGemmaAgentSetup-0.1.0.exe`.
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
and includes its own Python runtime. The model runtime remains a separate
13.2 GB first-run
download because bundling it into the Windows installer would make updates and
resume behavior substantially worse.

## What is automated

- Windows, WSL2, NVIDIA GPU, VRAM, disk, and runtime availability checks;
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
