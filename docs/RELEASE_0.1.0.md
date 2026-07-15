# DiffusionGemma Agent 0.1.0

Published Hugging Face repository:

https://huggingface.co/aogavrilov/diffusiongemma-agent-iq3-cuda13

Published PyPI project:

https://pypi.org/project/diffusiongemma-agent/0.1.0/

## Immutable revisions

- Runtime tag `v0.1.0-cu13-iq3` ->
  `0817a672a6f83f2e720f2102d65535750929d90f`
- Python package tag `v0.1.0` ->
  `bc388650ec34c194af8bf8fc877da83737afaea5`

The public remote inventory was verified after publication. The IQ3 GGUF is
stored through Xet/LFS and reports `12,401,034,720` bytes. The model manifest,
runtime index, model card, Apache 2.0 license, llama.cpp MIT license, and CUDA
13.1 EULA are present.

## Installation

```powershell
python -m pip install "https://huggingface.co/aogavrilov/diffusiongemma-agent-iq3-cuda13/resolve/v0.1.0/python/diffusiongemma_agent-0.1.0-py3-none-any.whl"; dg-agent install --accept-licenses
```

Run a repository task:

```powershell
dg-agent run --repo C:\work\repo --task "Fix the requested issue and run tests"
```

The direct wheel installation was tested without a Hugging Face token in a
clean Windows virtual environment. The PyPI wheel and sdist passed
`twine check`; installation of `diffusiongemma-agent==0.1.0` by package name
from the public PyPI index was also verified in a clean virtual environment.

PyPI SHA-256 values:

- wheel: `d8c17cd4245e5031752458b6a4ed1d672ff4001ee4053fa320851dc03de454b9`
- sdist: `6023ab5bdbb97cfdfd21195bf728e7e7064966c3073ce2b2823889f508a1bccb`
