---
license: apache-2.0
library_name: diffusiongemma-agent
base_model: google/diffusiongemma-26B-A4B-it
base_model_relation: quantized
pipeline_tag: text-generation
tags:
  - gguf
  - diffusiongemma
  - coding-agent
  - cuda
  - wsl
---

# Run DiffusionGemma as a local coding agent on a 16 GB GPU

This is a ready-to-run DiffusionGemma stack for Windows + WSL2. It turns the
26B-A4B model into a repository-aware coding agent on a single 16 GB NVIDIA
GPU, without requiring you to compile llama.cpp, convert weights, assemble
CUDA libraries, or build an agent wrapper yourself.

This release contains more than a quantized GGUF:

- an IQ3 model profile that fits entirely in 16 GB VRAM;
- a matched custom llama.cpp/CUDA backend for DiffusionGemma;
- pinned CUDA 13 runtime libraries and launch settings;
- repository retrieval instead of sending the whole codebase to the model;
- focused file editing through Aider, automatic tests, session artifacts, and
  rollback when validation fails;
- a localhost OpenAI-compatible endpoint for supported coding clients.

## Why use this instead of a standalone quantization?

| Standalone GGUF | This runtime |
| --- | --- |
| Supplies model weights | Supplies a tested model, backend, CUDA runtime, and agent workflow |
| Requires finding a compatible DiffusionGemma runner | Includes the exact custom backend used by the release |
| Requires manual offload, memory, and launch tuning | Ships a full-GPU preset tested on a 16 GB RTX 3080 Laptop GPU |
| Primarily provides raw generation/chat | Searches a repository, edits focused files, runs tests, and records results |
| Leaves integration and reproducibility to the user | Installs and operates through one versioned CLI |

Use another GGUF if you only need weights or want to assemble your own
inference stack. Use this release when you want a reproducible local coding
agent that is already wired together for 16 GB NVIDIA hardware.

## Easiest Windows setup

You do not need Python, a CUDA Toolkit, a compiler, or ML setup experience.

1. [Download the standalone Windows installer](https://github.com/aogavrilov/diffusiongemma-agent/releases/download/desktop-v0.1.1/DiffusionGemmaAgentSetup-0.1.1.exe).
2. Open **DiffusionGemma Agent** after installation.
3. Let the app check Windows, WSL2, the GPU, VRAM, disk, and download access.
4. Review the model and CUDA licenses and click **Download and install**.
5. Choose a Git repository, enter one concrete task, and review the generated
   diff and test output in the app.

The desktop app includes its own Python runtime. It automatically reuses a
compatible runtime or IQ3 GGUF already present in common download and Hugging
Face cache folders. The separate 13.2 GB download, when needed, is resumable.
The current alpha installer is not code-signed, so
Windows may show an unknown-publisher warning; GitHub publishes its SHA-256
checksum beside the download.

## Command-line alternative

Run in Windows PowerShell:

```powershell
python -m pip install --upgrade diffusiongemma-agent
dg-agent doctor
dg-agent install --accept-licenses
dg-agent status
```

Run a focused repository task:

```powershell
dg-agent run --repo C:\work\repo --task "Fix src/x.py and run its tests" --file src/x.py
```

Stop the service and release GPU memory with `dg-agent stop`.

## What a task looks like

```text
your request
  -> bounded repository search
  -> focused edit session
  -> detected tests and verification
  -> final diff and saved session artifacts
  -> rollback if validation fails
```

This works best for concrete file-level changes, focused bug fixes, and tests.
It is not intended to replace a large-context cloud agent for broad,
underspecified repository-wide work.

## Hardware and storage

- Windows 10/11 with an initialized WSL2 Ubuntu distribution;
- NVIDIA GPU with at least 16 GB VRAM;
- current NVIDIA Windows driver with WSL CUDA support;
- at least 15 GiB free for download, with 30 GiB recommended for the download
  plus the installed WSL copy;
- network access during first installation.

The tested system is an RTX 3080 Laptop GPU with 16 GB VRAM. CPU-only, native
Linux, macOS, AMD, and sub-16-GB GPU installations are not supported by this
release.

## Contents

- IQ3 GGUF derived from `google/diffusiongemma-26B-A4B-it`;
- Linux x86-64 custom llama.cpp DiffusionGemma backend;
- private CUDA 13 runtime libraries required by that backend;
- checkpointed repository supervisor, bounded retrieval, Haystack, and Aider
  adapters;
- service launchers for localhost ports `4100` and `8090`;
- `manifest.json` with file sizes and SHA-256 values;
- complete third-party notices under `LICENSES/`.

## Limits

The default fast agent profile uses a 768-token effective input context and up
to 256 output tokens. It compensates with bounded repository retrieval; it does
not load an entire large repository into the model context. IQ3 quantization
reduces quality relative to the original model. Native model-selected tool
calls are disabled in the default route.

A short warmed probe measured approximately 19.6 words/s on the tested RTX
3080 Laptop 16 GB. Full agent tasks are slower because retrieval, diffusion
passes, edits, and tests add latency. This is not a performance guarantee.

## Status and scope

This is alpha, hardware-specific software. It is not an official Google,
NVIDIA, Hugging Face, Aider, or upstream llama.cpp distribution.

## Safety

The agent can modify files and run repository tests. Checkpointing and rollback
are not a security sandbox. Use a clean Git worktree, inspect generated diffs,
and do not expose secrets to untrusted repositories. Services bind to localhost
by default.

Source code:

- [agent and installer](https://github.com/aogavrilov/diffusiongemma-agent)
- [custom llama.cpp/CUDA backend](https://github.com/aogavrilov/diffusiongemma-llama-cpp-diffusion)

See the public source README for lifecycle commands, troubleshooting, update,
uninstall, and architecture details.

## Licenses

Review `LICENSES/NOTICE.md` before installation or redistribution. The runtime
contains Apache-2.0 model-derived material, MIT-licensed llama.cpp code, and
NVIDIA redistributable libraries governed by the included CUDA EULA.
