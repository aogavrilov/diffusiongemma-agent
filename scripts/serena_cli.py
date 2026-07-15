#!/usr/bin/env python
"""Small Python entrypoint for Serena when generated .exe shims are blocked."""

from __future__ import annotations

import contextlib
import dataclasses
import os
import sys
import types


overlay = os.environ.get("DG_SERENA_OVERLAY")
if overlay:
    sys.path.append(overlay)


def patch_optional_native_deps() -> None:
    if not os.environ.get("DG_SERENA_STUB_OPTIONAL_NATIVE"):
        return
    if "psutil" in sys.modules:
        return

    module = types.ModuleType("psutil")

    class Error(Exception):
        pass

    class NoSuchProcess(Error):
        pass

    class AccessDenied(Error):
        pass

    class Process:
        def __init__(self, _pid: int):
            raise NoSuchProcess()

    module.Error = Error
    module.NoSuchProcess = NoSuchProcess
    module.AccessDenied = AccessDenied
    module.Process = Process
    sys.modules["psutil"] = module

    if "PIL" not in sys.modules:
        pil = types.ModuleType("PIL")
        image = types.ModuleType("PIL.Image")

        def open_image(*_args, **_kwargs):
            raise RuntimeError("Pillow is unavailable in the headless Serena MCP shim")

        image.open = open_image
        pil.Image = image
        sys.modules["PIL"] = pil
        sys.modules["PIL.Image"] = image


patch_optional_native_deps()


def patch_windows_mcp_client_stdio_import() -> None:
    """Avoid pywin32-only MCP client imports when starting the server on Windows."""

    if sys.platform != "win32" or "start-mcp-server" not in sys.argv:
        return
    if "mcp.client.stdio" in sys.modules:
        return

    module = types.ModuleType("mcp.client.stdio")

    @dataclasses.dataclass
    class StdioServerParameters:
        command: str
        args: list[str] = dataclasses.field(default_factory=list)
        env: dict[str, str] | None = None
        cwd: str | None = None
        encoding: str = "utf-8"
        encoding_error_handler: str = "strict"

    @contextlib.asynccontextmanager
    async def stdio_client(*_args, **_kwargs):
        raise RuntimeError("mcp.client.stdio is unavailable in this Serena server-only Windows shim")

    module.StdioServerParameters = StdioServerParameters
    module.stdio_client = stdio_client
    sys.modules["mcp.client.stdio"] = module


patch_windows_mcp_client_stdio_import()

from serena.cli import top_level


if __name__ == "__main__":
    top_level()
