# Release 0.1.2

This package and desktop update adds validated reuse of an existing
DiffusionGemma Agent runtime or compatible IQ3 GGUF.

## Published artifacts

- Desktop release: `desktop-v0.1.1`
- Desktop application: `0.1.1`
- Python package and bundled core: `0.1.2`
- Compatible runtime tag: `v0.1.1-cu13-iq3` (unchanged)

## Checksums

```text
b0d4dda153b0fbf605a885156382905510a6e0d535601ffe30f5bd75c68a2f22  DiffusionGemmaAgentSetup-0.1.1.exe
04a2afa10c70496ad5a25060a3d561a13ae9a567c5ef019aa4eb6eb5b5479299  diffusiongemma_agent-0.1.2-py3-none-any.whl
9cc7ae718850b19aac6f20aba52762c606d5ce007fc22509af72b1c4de6d4789  diffusiongemma_agent-0.1.2.tar.gz
```

## Validation

- 16 Windows unit tests passed.
- Wheel and source distribution passed `twine check`.
- A fresh wheel installation found the existing complete runtime.
- The frozen desktop core found the existing complete runtime without a
  system Python installation.
- The existing 13.2 GB bundle passed its WSL/CUDA `-VerifyOnly` check.
- The desktop installer upgraded the local installation successfully and the
  installed core selected the existing runtime directory.

The Windows installer remains unsigned and may trigger an unknown-publisher or
SmartScreen warning.
