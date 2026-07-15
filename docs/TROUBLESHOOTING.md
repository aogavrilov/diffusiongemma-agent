# Troubleshooting

## Start with the preflight

```powershell
dg-agent doctor
dg-agent status
dg-agent logs --lines 120
```

`doctor` returns a non-zero exit code when a required installation prerequisite
fails. Backend and gateway state are informational before installation.

## WSL2 is missing or uninitialized

Install WSL2 from an elevated PowerShell prompt:

```powershell
wsl --install
```

Reboot if Windows requests it, open Ubuntu once, finish its first-run setup,
and run `dg-agent doctor` again.

## NVIDIA GPU is not visible inside WSL

Update the NVIDIA Windows driver, then check:

```powershell
wsl --exec /usr/lib/wsl/lib/nvidia-smi
```

The runtime requires approximately 16 GB VRAM. Stop other GPU applications
before starting the model.

## Insufficient disk space

The Windows download is approximately 13.2 GB. Installation creates another
copy inside the WSL virtual disk and installs Python dependencies. Keep at
least 30 GiB free on the drive backing both locations.

The default Windows cache is:

```text
%LOCALAPPDATA%\diffusiongemma-agent\runtime
```

The default WSL install is:

```text
~/.local/share/diffusiongemma-agent
```

## Download was interrupted

Run the same command again:

```powershell
dg-agent install --accept-licenses
```

Hugging Face reuses completed files. Use `--force-download` only when cached
files are known to be invalid.

## Backend or gateway does not start

```powershell
dg-agent stop
dg-agent start
dg-agent logs --lines 200
```

The backend uses `127.0.0.1:4100`; the gateway uses `127.0.0.1:8090`. Stop
conflicting processes and other large GPU workloads.

## Windows Application Control blocks a launcher

Use the launcher-independent form:

```powershell
python -m diffusiongemma_agent doctor
python -m diffusiongemma_agent start
```

Review the local policy before allowing Python or downloaded native modules.
Do not globally disable security controls solely for this package.

## Display reset, black screen, or machine restart

Stop the service and do not retry sustained GPU work until power delivery,
thermals, the NVIDIA driver, and hardware stability have been checked. A local
model workload can expose an existing hardware or power fault; software
checkpointing cannot protect against a hard power loss.

## Update

```powershell
python -m pip install --upgrade diffusiongemma-agent
dg-agent update --accept-licenses
```

## Uninstall

Remove the WSL runtime while retaining the resumable Windows cache:

```powershell
dg-agent uninstall --yes
```

Remove both copies:

```powershell
dg-agent uninstall --yes --remove-download
```
