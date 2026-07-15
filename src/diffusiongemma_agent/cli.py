from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from huggingface_hub import snapshot_download

from . import __version__


DEFAULT_RUNTIME_REPO = os.environ.get("DG_RUNTIME_REPO", "aogavrilov/diffusiongemma-agent-iq3-cuda13")
DEFAULT_REVISION = os.environ.get("DG_RUNTIME_REVISION", "v0.1.1-cu13-iq3")
BACKEND_HEALTH_URL = "http://127.0.0.1:4100/healthz"
GATEWAY_HEALTH_URL = "http://127.0.0.1:8090/healthz"
GIB = 1024**3
MIN_DOWNLOAD_FREE_GIB = 15
RECOMMENDED_FREE_GIB = 30
MIN_VRAM_MIB = 15_500
LICENSE_URLS = (
    "https://huggingface.co/google/diffusiongemma-26B-A4B-it",
    "https://docs.nvidia.com/cuda/eula/",
)


def state_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "diffusiongemma-agent"


def config_path() -> Path:
    return state_dir() / "config.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if not executable:
        raise RuntimeError("PowerShell is required on Windows")
    return executable


def wsl_executable() -> str | None:
    return shutil.which("wsl.exe") or shutil.which("wsl")


def invoke(command: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, check=check)


def configured_runtime() -> tuple[dict[str, Any], Path | None]:
    config = read_json(config_path())
    raw_path = str(config.get("runtime_dir") or "")
    path = Path(raw_path) if raw_path else None
    return config, path


def runtime_dir_from_config() -> Path:
    _, path = configured_runtime()
    if path is None or not path.is_dir():
        raise RuntimeError("Runtime is not installed. Run: dg-agent install --accept-licenses")
    return path


def disk_anchor(path: Path) -> Path:
    current = path.expanduser().resolve()
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def free_disk_gib(path: Path) -> float:
    return shutil.disk_usage(disk_anchor(path)).free / GIB


def require_install_prerequisites(destination: Path) -> None:
    if platform.system() != "Windows":
        raise RuntimeError("This runtime currently supports Windows 10/11 with WSL2 only")
    wsl = wsl_executable()
    if not wsl:
        raise RuntimeError("WSL2 is missing. Run 'wsl --install', reboot if requested, and retry")
    probe = subprocess.run([wsl, "--exec", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode != 0:
        raise RuntimeError("Initialize a default WSL2 Ubuntu distribution once, then retry")
    free_gib = free_disk_gib(destination)
    if free_gib < MIN_DOWNLOAD_FREE_GIB:
        raise RuntimeError(
            f"Only {free_gib:.1f} GiB is free at {disk_anchor(destination)}; "
            f"at least {MIN_DOWNLOAD_FREE_GIB} GiB is required for the download"
        )
    if free_gib < RECOMMENDED_FREE_GIB:
        print(
            f"Warning: {free_gib:.1f} GiB is free. About {RECOMMENDED_FREE_GIB} GiB is recommended "
            "for the 13.2 GB download plus its WSL installation.",
            file=sys.stderr,
        )


def install_runtime(args: argparse.Namespace) -> int:
    if not args.accept_licenses:
        joined = "\n".join(f"- {item}" for item in LICENSE_URLS)
        raise RuntimeError("Pass --accept-licenses after reviewing:\n" + joined)

    destination = Path(args.local_dir).expanduser().resolve() if args.local_dir else state_dir() / "runtime"
    require_install_prerequisites(destination)
    destination.mkdir(parents=True, exist_ok=True)
    token = args.token or os.environ.get("HF_TOKEN") or None
    print("This download is approximately 13.2 GB and may take a while.", flush=True)
    print(f"Downloading {args.runtime_repo}@{args.revision} to {destination}", flush=True)
    snapshot_download(
        repo_id=args.runtime_repo,
        revision=args.revision,
        local_dir=destination,
        token=token,
        allow_patterns=[
            "README.md",
            "manifest.json",
            "runtime-index.json",
            "LICENSES/*",
            "Install-DiffusionGemmaAgent.ps1",
            "dg.ps1",
            "start-runtime.sh",
            "payload/**",
        ],
        force_download=args.force_download,
    )
    installer = destination / "Install-DiffusionGemmaAgent.ps1"
    if not installer.is_file():
        raise RuntimeError(f"Runtime snapshot is incomplete: {installer} is missing")
    command = [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(installer)]
    if args.wsl_root:
        command.extend(["-WslRoot", args.wsl_root])
    if args.no_start:
        command.append("-NoStart")
    result = invoke(command)
    if result.returncode != 0:
        return result.returncode
    installed = read_json(destination / "installed.json")
    write_json(
        config_path(),
        {
            "version": 2,
            "package_version": __version__,
            "runtime_repo": args.runtime_repo,
            "revision": args.revision,
            "runtime_dir": str(destination),
            "wsl_root": installed.get("wsl_root", args.wsl_root),
            "licenses_accepted_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"Installed runtime: {destination}")
    print("Next: dg-agent status")
    print('Run:  dg-agent run --repo C:\\work\\repo --task "Describe the change and tests"')
    print("Stop: dg-agent stop")
    return 0


def update_runtime(args: argparse.Namespace) -> int:
    config, runtime = configured_runtime()
    if runtime is None or not runtime.is_dir():
        raise RuntimeError("Runtime is not installed; use 'dg-agent install --accept-licenses' first")
    install_args = argparse.Namespace(
        runtime_repo=args.runtime_repo or str(config.get("runtime_repo") or DEFAULT_RUNTIME_REPO),
        revision=args.revision or DEFAULT_REVISION,
        local_dir=str(runtime),
        wsl_root=str(config.get("wsl_root") or ""),
        token=args.token,
        accept_licenses=args.accept_licenses,
        force_download=args.force_download,
        no_start=args.no_start,
    )
    return install_runtime(install_args)


def invoke_runtime(extra: list[str]) -> int:
    runtime = runtime_dir_from_config()
    launcher = runtime / "dg.ps1"
    if not launcher.is_file():
        raise RuntimeError(f"Runtime launcher is missing: {launcher}")
    return invoke([powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), *extra]).returncode


def endpoint_health(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            value = json.loads(response.read().decode("utf-8"))
        return {"ok": bool(value.get("ok")), "url": url, "detail": value}
    except (OSError, ValueError) as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def status(as_json: bool) -> int:
    config, runtime = configured_runtime()
    installed = bool(runtime and runtime.is_dir())
    result = {
        "installed": installed,
        "package_version": __version__,
        "runtime_revision": config.get("revision"),
        "runtime_dir": str(runtime) if runtime else None,
        "wsl_root": config.get("wsl_root"),
        "backend": endpoint_health(BACKEND_HEALTH_URL),
        "gateway": endpoint_health(GATEWAY_HEALTH_URL),
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"installed: {'yes' if installed else 'no'}")
        print(f"package: {__version__}")
        print(f"runtime: {config.get('revision') or 'not configured'}")
        print(f"backend: {'ready' if result['backend']['ok'] else 'stopped'}")
        print(f"gateway: {'ready' if result['gateway']['ok'] else 'stopped'}")
        if installed:
            print(f"runtime directory: {runtime}")
    return 0 if installed and result["backend"]["ok"] and result["gateway"]["ok"] else 1


def wsl_nvidia_check(wsl: str) -> dict[str, Any]:
    probe = subprocess.run(
        [
            wsl,
            "--exec",
            "bash",
            "-lc",
            "NVIDIA_SMI=$(command -v nvidia-smi || true); "
            "if [ -z \"$NVIDIA_SMI\" ] && [ -x /usr/lib/wsl/lib/nvidia-smi ]; then NVIDIA_SMI=/usr/lib/wsl/lib/nvidia-smi; fi; "
            "if [ -z \"$NVIDIA_SMI\" ]; then exit 127; fi; "
            "\"$NVIDIA_SMI\" --query-gpu=name,memory.total --format=csv,noheader,nounits",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    detail = (probe.stdout or probe.stderr).strip()
    match = re.search(r",\s*(\d+)\s*$", probe.stdout.strip())
    vram_mib = int(match.group(1)) if match else 0
    return {
        "ok": probe.returncode == 0 and vram_mib >= MIN_VRAM_MIB,
        "detail": detail or "NVIDIA GPU was not detected inside WSL",
        "vram_mib": vram_mib,
        "minimum_vram_mib": MIN_VRAM_MIB,
    }


def hub_check() -> dict[str, Any]:
    url = f"https://huggingface.co/api/models/{DEFAULT_RUNTIME_REPO}/revision/{DEFAULT_REVISION}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return {"ok": response.status == 200, "detail": f"{DEFAULT_RUNTIME_REPO}@{DEFAULT_REVISION}"}
    except OSError as exc:
        return {"ok": False, "detail": str(exc)}


def doctor(as_json: bool) -> int:
    wsl = wsl_executable()
    destination = state_dir() / "runtime"
    free_gib = free_disk_gib(destination)
    config, runtime = configured_runtime()
    checks: dict[str, dict[str, Any]] = {
        "windows": {"ok": platform.system() == "Windows", "detail": platform.platform()},
        "wsl": {"ok": bool(wsl), "detail": wsl or "WSL2 is not installed"},
        "disk": {
            "ok": free_gib >= MIN_DOWNLOAD_FREE_GIB,
            "detail": f"{free_gib:.1f} GiB free; {RECOMMENDED_FREE_GIB} GiB recommended for a new install",
        },
        "runtime_download": hub_check(),
        "installed": {
            "ok": bool(runtime and runtime.is_dir()),
            "detail": str(runtime) if runtime else "not installed",
            "required": False,
        },
        "backend": {**endpoint_health(BACKEND_HEALTH_URL), "required": False},
        "gateway": {**endpoint_health(GATEWAY_HEALTH_URL), "required": False},
    }
    checks["nvidia"] = wsl_nvidia_check(wsl) if wsl else {
        "ok": False,
        "detail": "WSL2 is unavailable",
        "vram_mib": 0,
        "minimum_vram_mib": MIN_VRAM_MIB,
    }
    result = {
        "package_version": __version__,
        "runtime_revision": config.get("revision"),
        "checks": checks,
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for name, value in checks.items():
            if value.get("ok"):
                label = "OK"
            elif value.get("required", True):
                label = "FAIL"
            else:
                label = "INFO"
            detail = value.get("detail") or value.get("error") or ""
            print(f"[{label:4}] {name:16} {detail}")
    required = [value for value in checks.values() if value.get("required", True)]
    return 0 if all(value.get("ok") for value in required) else 1


def validate_wsl_removal_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or not path.is_absolute() or ".." in path.parts or len(path.parts) < 4:
        raise RuntimeError(f"Refusing to remove unsafe WSL path: {value!r}")
    if str(path) in {"/", "/root", "/home", "/usr", "/var"}:
        raise RuntimeError(f"Refusing to remove unsafe WSL path: {value!r}")
    return path


def uninstall_runtime(args: argparse.Namespace) -> int:
    if not args.yes:
        raise RuntimeError("Uninstall is destructive. Re-run with --yes after reviewing 'dg-agent status'.")
    config, runtime = configured_runtime()
    if not config:
        print("DiffusionGemma Agent runtime is not configured.")
        return 0

    if runtime and (runtime / "dg.ps1").is_file():
        invoke_runtime(["-Stop"])
    wsl_root = str(config.get("wsl_root") or "")
    if wsl_root:
        path = validate_wsl_removal_path(wsl_root)
        wsl = wsl_executable()
        if not wsl:
            raise RuntimeError("WSL is unavailable; cannot remove the installed Linux runtime")
        marker = f"{path}/start-runtime.sh"
        marker_probe = subprocess.run([wsl, "--exec", "test", "-f", marker])
        if marker_probe.returncode != 0:
            raise RuntimeError(f"Refusing to remove WSL path without the runtime marker: {path}")
        result = invoke([wsl, "--exec", "rm", "-rf", "--", str(path)])
        if result.returncode != 0:
            return result.returncode
        print(f"Removed WSL runtime: {path}")

    if args.remove_download and runtime and runtime.is_dir():
        required_markers = (runtime / "manifest.json", runtime / "dg.ps1")
        if not all(marker.is_file() for marker in required_markers):
            raise RuntimeError(f"Refusing to remove unrecognized download directory: {runtime}")
        shutil.rmtree(runtime)
        print(f"Removed downloaded runtime: {runtime}")
    config_path().unlink(missing_ok=True)
    print("Removed local configuration.")
    if not args.remove_download and runtime:
        print(f"Kept the 13.2 GB download cache at: {runtime}")
    return 0


def show_logs(lines: int) -> int:
    config, _ = configured_runtime()
    wsl_root = str(config.get("wsl_root") or "")
    if not wsl_root:
        raise RuntimeError("Runtime is not configured")
    wsl = wsl_executable()
    if not wsl:
        raise RuntimeError("WSL is unavailable")
    found = False
    for name in ("backend.out.log", "backend.err.log", "gateway.out.log", "gateway.err.log"):
        path = f"{wsl_root}/runtime/{name}"
        probe = subprocess.run([wsl, "--exec", "test", "-f", path])
        if probe.returncode != 0:
            continue
        found = True
        print(f"\n== {name} ==", flush=True)
        invoke([wsl, "--exec", "tail", "-n", str(lines), path])
    if not found:
        print("No runtime logs exist yet. Start the service with: dg-agent start")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="dg-agent",
        description="Install and operate the local DiffusionGemma coding agent on Windows + WSL2.",
        epilog=(
            "First install:\n"
            "  dg-agent doctor\n"
            "  dg-agent install --accept-licenses\n\n"
            "Run a task:\n"
            '  dg-agent run --repo C:\\work\\repo --task "Fix the bug and run tests"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    result.add_argument("--version", action="version", version=__version__)
    sub = result.add_subparsers(dest="command", required=True, title="commands")

    install = sub.add_parser("install", help="Download 13.2 GB and install the runtime into WSL2")
    install.add_argument("--runtime-repo", default=DEFAULT_RUNTIME_REPO, help="Hugging Face model repo")
    install.add_argument("--revision", default=DEFAULT_REVISION, help="Immutable runtime tag or commit")
    install.add_argument("--local-dir", default="", help="Windows download directory (default: LocalAppData)")
    install.add_argument("--wsl-root", default="", help="Linux install directory (default: ~/.local/share/diffusiongemma-agent)")
    install.add_argument("--token", default="", help=argparse.SUPPRESS)
    install.add_argument("--accept-licenses", action="store_true", help="Confirm review of model and CUDA licenses")
    install.add_argument("--force-download", action="store_true", help="Re-download files even when cached")
    install.add_argument("--no-start", action="store_true", help="Install without starting backend and gateway")

    update = sub.add_parser("update", help="Update an existing runtime installation")
    update.add_argument("--runtime-repo", default="", help="Override the configured Hugging Face repo")
    update.add_argument("--revision", default=DEFAULT_REVISION, help="Runtime revision to install")
    update.add_argument("--token", default="", help=argparse.SUPPRESS)
    update.add_argument("--accept-licenses", action="store_true", help="Confirm review of model and CUDA licenses")
    update.add_argument("--force-download", action="store_true", help="Re-download files even when cached")
    update.add_argument("--no-start", action="store_true", help="Update without starting services")

    sub.add_parser("start", help="Start the model backend and safe agent gateway")
    sub.add_parser("stop", help="Stop services and release GPU memory")

    run = sub.add_parser("run", help="Run one checkpointed repository task")
    run.add_argument("--repo", default=str(Path.cwd()), help="Windows path to the Git repository")
    run.add_argument("--task", required=True, help="Concrete change and validation requested from the agent")
    run.add_argument("--file", default="", help="Optional repository-relative file to prioritize")
    run.add_argument("--max-steps", type=int, choices=range(1, 6), default=3, metavar="1-5", help="Maximum agent iterations (default: 3)")

    status_parser = sub.add_parser("status", help="Show installation and service health")
    status_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    doctor_parser = sub.add_parser("doctor", help="Check WSL2, GPU/VRAM, disk, network, and runtime state")
    doctor_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    logs_parser = sub.add_parser("logs", help="Show recent backend and gateway logs")
    logs_parser.add_argument("--lines", type=int, default=80, help="Lines per log file (default: 80)")
    uninstall = sub.add_parser("uninstall", help="Remove the installed WSL runtime and configuration")
    uninstall.add_argument("--yes", action="store_true", help="Confirm removal of the configured WSL runtime")
    uninstall.add_argument("--remove-download", action="store_true", help="Also delete the 13.2 GB Windows download cache")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "install":
            return install_runtime(args)
        if args.command == "update":
            return update_runtime(args)
        if args.command == "start":
            return invoke_runtime(["-StartOnly"])
        if args.command == "stop":
            return invoke_runtime(["-Stop"])
        if args.command == "run":
            repo = Path(args.repo).expanduser().resolve()
            if not repo.is_dir():
                raise RuntimeError(f"Repository directory does not exist: {repo}")
            command = ["-Repo", str(repo), "-Task", args.task, "-MaxSteps", str(args.max_steps)]
            if args.file:
                command.extend(["-File", args.file])
            return invoke_runtime(command)
        if args.command == "status":
            return status(args.json)
        if args.command == "doctor":
            return doctor(args.json)
        if args.command == "logs":
            return show_logs(max(1, args.lines))
        if args.command == "uninstall":
            return uninstall_runtime(args)
    except (OSError, RuntimeError) as exc:
        print(f"dg-agent: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
