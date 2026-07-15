# Release 0.1.1

Released on 2026-07-15.

## Published artifacts

- Agent source implementation commit:
  `32ff30c7eae6d2491655ff8c40b5e1324e5c85e0`
- Backend source commit:
  `f19c6775974607bc09d238bedd8855ad887f25d9`
- Hugging Face runtime commit:
  `93331cb4b7eb76cb5319faa11ac4517c8835ae86`
- Runtime tag: `v0.1.1-cu13-iq3`
- Package/runtime tag: `v0.1.1`
- PyPI release: https://pypi.org/project/diffusiongemma-agent/0.1.1/

Python artifact SHA-256 values:

```text
5cdcc3211d6e10cc6f0fd7d06efef6c3341d5930ccb75deaa0f34479488cff7e  diffusiongemma_agent-0.1.1-py3-none-any.whl
c0c65f3e3688aaa6f4eb2699e02a5315283126f3eb1ff3294da1e2019caf8aad  diffusiongemma_agent-0.1.1.tar.gz
```

The same wheel is available from PyPI and the versioned Hugging Face runtime.

## Validation

- 8 package lifecycle and path-safety tests passed locally.
- Wheel and sdist passed `twine check`.
- Wheel installed in an empty Windows Python 3.12 virtual environment.
- Standard `dg-agent` console entry point and module entry point both worked.
- Public PyPI installation of exactly 0.1.1 succeeded without a local cache.
- Public Hugging Face wheel download matched the PyPI SHA-256 value.
- `dg-agent doctor --json` passed Windows, WSL2, NVIDIA, VRAM, disk, and
  runtime-revision checks on the release workstation.
- Portable runtime `VerifyOnly` passed model-size and native-library checks.
- Runtime staging validated 3915 manifest files and 13,239,579,913 bytes.
- GitHub Actions passed on Windows with Python 3.10 and 3.12.

## Runtime policy

The release uses the validated `iq3_fullgpu_fast` profile with batch size 1.
Experimental merged gate/up and MoE down-reduce fusion kernels remain in the
backend source but are disabled by default because fused probes previously
showed output-quality regressions. The release does not claim their benchmark
speed for normal agent tasks.

Known limits remain 768 effective input tokens, up to 256 output tokens, IQ3
quality loss, Windows + WSL2 only, and a 16 GB NVIDIA GPU requirement.
