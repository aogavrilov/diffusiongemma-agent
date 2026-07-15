# DiffusionGemma Agent

Run a local DiffusionGemma coding agent on a 16 GB NVIDIA GPU from Windows and
WSL2. The package combines a quantized 26B-A4B model, a custom full-GPU
llama.cpp backend, bounded repository retrieval, Aider-compatible editing,
automatic test execution, and rollback on failed sessions.

> **Alpha software.** This is a hardware-specific experimental runtime, not an
> official Google, NVIDIA, Hugging Face, Aider, or llama.cpp distribution.

## What it does

- searches a repository with bounded `rg`/RAG context instead of sending the
  whole project to the model;
- asks the local model to plan and edit a focused working set;
- runs repository tests when it can identify them;
- records session artifacts and a final diff;
- rolls back the session when validation fails;
- exposes a localhost OpenAI-compatible gateway for supported agent clients.

It is best suited to concrete file-level tasks such as fixing a known bug,
updating a small feature, or adding focused tests. It is not a replacement for
a large-context cloud agent on broad, ambiguous repository-wide work.

## Quick start

Run these commands in PowerShell:

```powershell
python -m pip install --upgrade diffusiongemma-agent
dg-agent doctor
dg-agent install --accept-licenses
dg-agent status
```

The first installation downloads approximately 13.2 GB and creates another
runtime copy inside WSL. Plan for at least 30 GiB of free disk space.

Run a task against a clean Git worktree:

```powershell
dg-agent run --repo C:\work\my-project --task "Fix the null handling bug in src/parser.py and run the parser tests" --file src/parser.py
```

Stop the service and release GPU memory when finished:

```powershell
dg-agent stop
```

## Requirements

| Requirement | Supported configuration |
| --- | --- |
| OS | Windows 10/11 x64 |
| Linux layer | Initialized WSL2 Ubuntu distribution |
| GPU | NVIDIA GPU visible inside WSL2 |
| VRAM | 16 GB minimum; the tested GPU is an RTX 3080 Laptop 16 GB |
| Driver | Current NVIDIA Windows driver with WSL CUDA support |
| Disk | 15 GiB hard minimum for download; 30 GiB recommended for download + WSL copy |
| Python | Python 3.10 or newer on Windows |
| Network | Required for PyPI, Hugging Face, and WSL Python dependencies during install |

CPU-only execution, native Linux installation, macOS, AMD GPUs, and GPUs below
16 GB VRAM are not supported by release `0.1.1`.

## What installation changes

`dg-agent install` performs the following actions:

1. downloads the immutable runtime tag from Hugging Face;
2. verifies the expected model size and shared-library dependencies;
3. copies the model, backend, and agent scripts into
   `~/.local/share/diffusiongemma-agent` inside WSL by default;
4. creates a private Python virtual environment inside that directory;
5. installs FastAPI, Aider, Haystack, and runtime dependencies;
6. starts the model backend on `127.0.0.1:4100` and the safe gateway on
   `127.0.0.1:8090` unless `--no-start` is used.

Run `dg-agent doctor` before installation to check Windows, WSL2, GPU/VRAM,
disk space, and access to the pinned runtime revision.

## Typical workflow

```text
> dg-agent run --repo C:\work\my-project --task "Fix parser.py and run tests" --file src/parser.py

repository context -> bounded retrieval
editing route       -> checkpointed Aider session
validation          -> detected focused tests
result              -> final diff and session artifacts
failure             -> working tree restored to the session checkpoint
```

The exact output depends on the repository. Review the resulting diff and test
output before committing it.

## Commands

| Command | Purpose |
| --- | --- |
| `dg-agent doctor` | Check WSL2, NVIDIA GPU/VRAM, disk, network, and install state |
| `dg-agent install --accept-licenses` | Download and install the pinned runtime |
| `dg-agent status` | Show package, runtime revision, backend, and gateway state |
| `dg-agent start` | Start the backend and gateway |
| `dg-agent run --repo PATH --task TEXT` | Run one checkpointed coding task |
| `dg-agent logs` | Show recent backend and gateway logs |
| `dg-agent stop` | Stop services and release GPU memory |
| `dg-agent update --accept-licenses` | Update the existing installation to the package default revision |
| `dg-agent uninstall --yes` | Remove the WSL runtime but keep the Windows download cache |
| `dg-agent uninstall --yes --remove-download` | Remove the WSL runtime, cache, and local configuration |

Use `dg-agent COMMAND --help` for all options. The launcher-independent form is
`python -m diffusiongemma_agent`.

## Model and performance limits

- Base model: `google/diffusiongemma-26B-A4B-it`.
- Runtime quantization: IQ3 GGUF.
- Execution profile: full GPU, batch size 1, custom CUDA 13 runtime.
- Effective agent context: 768 input tokens with up to 256 output tokens;
  repository retrieval is used to keep the working set bounded.
- A short warmed probe reached approximately 19.6 words/s on the tested RTX
  3080 Laptop 16 GB. End-to-end agent tasks are slower because retrieval,
  diffusion passes, editing, and tests add latency.
- Quality is below the original higher-precision model because of IQ3
  quantization. Always review generated changes.

These are measurements from one machine, not a general performance guarantee.

## Safety model

The agent modifies files and can execute repository tests and bounded local
commands. Checkpoints and rollback reduce accidental damage, but they are not
a security sandbox. Use a clean Git worktree, inspect diffs, and do not run the
agent on untrusted repositories with sensitive credentials available.

Native model-selected tool calls are disabled in the default route. Tool use is
mediated by the local gateway and deterministic supervisor. Services bind to
localhost by default.

See the [security policy](https://github.com/aogavrilov/diffusiongemma-agent/blob/main/SECURITY.md)
before using the agent on important code.

## Troubleshooting

Start with:

```powershell
dg-agent doctor
dg-agent status
dg-agent logs --lines 120
```

Common fixes:

- WSL missing: run `wsl --install`, reboot, and initialize Ubuntu once.
- GPU missing in WSL: update the NVIDIA Windows driver and confirm
  `/usr/lib/wsl/lib/nvidia-smi` works.
- Backend fails to start: stop other GPU workloads and inspect
  `dg-agent logs`.
- Download interrupted: rerun `dg-agent install --accept-licenses`; Hugging
  Face resumes cached files.
- Windows Application Control blocks Python launchers: use
  `python -m diffusiongemma_agent` or allow the Python installation.
- Display resets or the machine powers off under load: stop the service and
  diagnose power delivery, thermals, and GPU stability before retrying.

Detailed diagnostics are in the
[troubleshooting guide](https://github.com/aogavrilov/diffusiongemma-agent/blob/main/docs/TROUBLESHOOTING.md).

## Source and reproducibility

- Agent, installer, and packaging source:
  [aogavrilov/diffusiongemma-agent](https://github.com/aogavrilov/diffusiongemma-agent)
- Custom llama.cpp/CUDA backend source:
  [aogavrilov/diffusiongemma-llama-cpp-diffusion](https://github.com/aogavrilov/diffusiongemma-llama-cpp-diffusion)
- Versioned model/runtime files:
  [Hugging Face runtime](https://huggingface.co/aogavrilov/diffusiongemma-agent-iq3-cuda13)
- Python package:
  [PyPI](https://pypi.org/project/diffusiongemma-agent/)

The PyPI wheel contains only the installer CLI. The 13.2 GB model and runtime
are versioned separately so PyPI installation remains small and inspectable.

## Licenses

The Python package is Apache-2.0. The runtime includes separately licensed
components: the DiffusionGemma-derived weights, the MIT-licensed llama.cpp
fork, and NVIDIA CUDA redistributable libraries governed by the NVIDIA EULA.
Review the complete notices in the Hugging Face `LICENSES/` directory before
installation or redistribution.
