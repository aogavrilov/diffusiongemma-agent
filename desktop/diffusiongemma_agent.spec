# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "desktop" / "diffusiongemma_agent_gui.py")],
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=["hf_xet", "hf_xet.hf_xet"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PIL",
        "boto3",
        "botocore",
        "jax",
        "llvmlite",
        "matplotlib",
        "numba",
        "numpy",
        "onnxruntime",
        "pandas",
        "pyarrow",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

gui = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DiffusionGemmaAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    version=str(ROOT / "desktop" / "version_info.txt"),
)

core = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="dg-agent-core",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    version=str(ROOT / "desktop" / "version_info.txt"),
)

bundle = COLLECT(
    gui,
    core,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DiffusionGemmaAgent",
)
