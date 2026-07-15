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

# DiffusionGemma Agent IQ3 CUDA 13 Runtime

Versioned model and runtime files for
[`diffusiongemma-agent`](https://pypi.org/project/diffusiongemma-agent/). This
repository is consumed by the small Windows CLI; it is not a Transformers
pipeline and is not an official Google or NVIDIA distribution.

## Install

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
