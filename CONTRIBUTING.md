# Contributing

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,publish]"
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -v
```

Build and validate the Python package:

```powershell
.\scripts\publish_pypi.ps1 -BuildOnly
```

## Scope

- Keep the PyPI package small; model weights and native runtime binaries belong
  in the versioned Hugging Face runtime.
- Do not commit local virtual environments, logs, benchmark outputs, GGUF
  files, CUDA libraries, or generated runtime bundles.
- Add focused tests for CLI lifecycle and path-safety changes.
- Document hardware-specific behavior and distinguish measured results from
  general guarantees.

Changes to the custom CUDA/llama.cpp backend belong in
`aogavrilov/diffusiongemma-llama-cpp-diffusion` and should identify the exact
backend commit used by a runtime release.
