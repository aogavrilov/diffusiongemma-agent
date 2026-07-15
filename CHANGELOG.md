# Changelog

## 0.1.2 - 2026-07-15

- Added automatic discovery of compatible runtime bundles and standalone IQ3
  GGUF files in common Windows download and Hugging Face cache locations.
- Reuse complete local bundles without downloading and stage standalone model
  files with an NTFS hardlink when possible.
- Show the detected model source and reuse mode in desktop setup.

## 0.1.1 - 2026-07-15

- Added a standalone Windows desktop app and NSIS installer that do not require
  a system Python installation.
- Added guided compatibility checks, runtime installation, task execution,
  diff review, service control, and logs to the desktop UI.
- Added actionable `doctor`, `update`, `logs`, and guarded `uninstall` flows.
- Added complete help text and examples for every public CLI command.
- Added disk, WSL, network, GPU, and VRAM preflight checks.
- Added explicit runtime size, context, performance, and quality limitations.
- Added troubleshooting, lifecycle, security, source, and reproducibility docs.
- Normalized and validated custom WSL installation paths.
- Added a configurable `--max-steps` task limit.

## 0.1.0 - 2026-07-15

- Initial PyPI installer and Hugging Face IQ3 CUDA 13 runtime release.
