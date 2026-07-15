# Distribution workflow

The release deliberately separates the small Python control plane from the
13.2 GB runtime. PyPI receives only the installer and CLI. Hugging Face stores
the model, custom backend, bundled CUDA runtime, and agent adapters.

## 1. Confirm the runtime repository

The value must be identical in these locations before the public release:

- `DEFAULT_RUNTIME_REPO` in `src/diffusiongemma_agent/cli.py`;
- `Documentation` and `Runtime` URLs in `pyproject.toml`;
- the `--repo-id` passed to `scripts/publish_hf_runtime.py`.

The release repository is
`aogavrilov/diffusiongemma-agent-iq3-cuda13`.

## 2. Build the Python package

Build first because the versioned wheel is also included in the Hugging Face
release as a PyPI-independent installation path.

```powershell
.\scripts\publish_pypi.ps1 -BuildOnly
```

## 3. Stage and publish the runtime

```powershell
.\scripts\prepare_hf_runtime_repo.ps1
python .\scripts\publish_hf_runtime.py --repo-id aogavrilov/diffusiongemma-agent-iq3-cuda13 --check-only
$env:HF_TOKEN = "hf_..."
python .\scripts\publish_hf_runtime.py --repo-id aogavrilov/diffusiongemma-agent-iq3-cuda13
```

The publisher creates a public model repository by default, uploads the
staged folder, and creates tags `v0.1.1-cu13-iq3` and `v0.1.1`. Pass
`--private` only when all users will provide `HF_TOKEN` during installation.

## 4. Publish the Python package to PyPI

Publish the runtime first so that a newly installed CLI never points at a
missing revision.

```powershell
$env:TWINE_PASSWORD = "pypi-..."
.\scripts\publish_pypi.ps1
```

The build produces a wheel, an sdist, and `SHA256SUMS.txt` under
`dist/python`. On this workstation, package validation automatically falls
back to Linux `twine` in WSL because Windows Application Control blocks the
downloaded `nh3` module.

## 5. End-user commands

```powershell
python -m pip install diffusiongemma-agent
dg-agent install --accept-licenses
dg-agent run --repo C:\work\repo --task "Fix src/x.py and run tests" --file src/x.py
```

Before the PyPI upload, install the same wheel directly from Hugging Face:

```powershell
python -m pip install "https://huggingface.co/aogavrilov/diffusiongemma-agent-iq3-cuda13/resolve/v0.1.1/python/diffusiongemma_agent-0.1.1-py3-none-any.whl"
```

`python -m diffusiongemma_agent` is an equivalent fallback when command-file
launchers are restricted by local policy.
