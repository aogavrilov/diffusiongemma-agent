#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = DG_ROOT / "runlogs" / "mini-swe-agent"
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "mini-swe-agent.dg.yaml"
DEFAULT_REGISTRY = DG_ROOT / "configs" / "client_profiles" / "litellm-local-model-registry.json"
LOCAL_MINI = DG_ROOT / ".tools" / "external-agents" / "bin" / "mini"
MINI_GLOBAL_CONFIG_DIR = DG_ROOT / ".tools" / "external-agents" / "mini-swe-config"


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


def tail(text: str, limit: int = 6000) -> str:
    return text[-limit:] if len(text) > limit else text


def resolve_repo(path: str) -> Path:
    repo = Path(path or ".").resolve()
    if not repo.exists() or not repo.is_dir():
        raise SystemExit(f"repo does not exist: {repo}")
    return repo


def resolve_binary() -> str:
    if LOCAL_MINI.exists():
        return str(LOCAL_MINI)
    for name in ("mini", "mini-swe-agent"):
        resolved = shutil_which(name)
        if resolved:
            return resolved
    return ""


def shutil_which(name: str) -> str:
    for part in os.environ.get("PATH", "").split(os.pathsep):
        path = Path(part) / name
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_mini_global_config() -> Path:
    env_path = MINI_GLOBAL_CONFIG_DIR / ".env"
    if not env_path.exists():
        write_text(
            env_path,
            "\n".join(
                [
                    "MSWEA_CONFIGURED=true",
                    "MSWEA_MODEL_NAME=openai/diffusiongemma-local",
                    "OPENAI_API_KEY=dummy",
                    "OPENAI_BASE_URL=http://127.0.0.1:4100/v1",
                ]
            )
            + "\n",
        )
    return env_path


def analyze_trajectory(path: Path, stdout: str) -> dict[str, Any]:
    analysis: dict[str, Any] = {"failed": False, "reasons": [], "exit_status": ""}
    if "RepeatedFormatError" in stdout:
        analysis["failed"] = True
        analysis["reasons"].append("RepeatedFormatError in stdout")
    if "Session status: failed" in stdout or "DG task runner finished: failed" in stdout:
        analysis["failed"] = True
        analysis["reasons"].append("delegated DG session failed")

    if not path.exists():
        return analysis

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        analysis["failed"] = True
        analysis["reasons"].append(f"trajectory is not valid JSON: {exc}")
        return analysis

    messages = data.get("messages", []) if isinstance(data, dict) else data
    if not isinstance(messages, list):
        return analysis

    for message in messages:
        if not isinstance(message, dict):
            continue
        content = str(message.get("content", ""))
        extra = message.get("extra", {}) if isinstance(message.get("extra"), dict) else {}
        if message.get("role") == "exit":
            exit_status = str(extra.get("exit_status") or content).strip()
            analysis["exit_status"] = exit_status
            if exit_status in {"RepeatedFormatError"}:
                analysis["failed"] = True
                analysis["reasons"].append(f"mini-swe exit status: {exit_status}")
        if "Session status: failed" in content or "DG task runner finished: failed" in content:
            analysis["failed"] = True
            analysis["reasons"].append("delegated DG session failed in trajectory")

    analysis["reasons"] = sorted(set(analysis["reasons"]))
    return analysis


def build_command(args: argparse.Namespace, repo: Path, out_dir: Path) -> tuple[list[str], Path, Path, Path]:
    binary = args.binary or resolve_binary()
    if not binary:
        binary = "mini"

    config = Path(args.config).resolve() if args.config else DEFAULT_CONFIG
    registry = Path(args.model_registry).resolve() if args.model_registry else DEFAULT_REGISTRY
    trajectory = Path(args.output).resolve() if args.output else out_dir / "trajectory.json"

    cmd = [binary, "-c", str(config), "-t", args.task, "-o", str(trajectory)]
    if args.yolo:
        cmd.append("--yolo")
    if args.exit_immediately:
        cmd.append("--exit-immediately")
    if args.cost_limit is not None:
        cmd.extend(["--cost-limit", str(args.cost_limit)])
    for item in args.extra_config:
        cmd.extend(["-c", item])
    if args.extra_args:
        cmd.extend(args.extra_args)

    return cmd, config, registry, trajectory


def command_string(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def run(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    run_dir = Path(args.out_dir).resolve() if args.out_dir else DEFAULT_RUN_ROOT / f"{timestamp()}-{repo.name}"
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    report_path = Path(args.report).resolve() if args.report else run_dir / "report.json"
    command_path = run_dir / "command.sh"
    cmd, config, registry, trajectory = build_command(args, repo, run_dir)

    report: dict[str, Any] = {
        "status": "dry-run" if args.dry_run else "running",
        "repo": str(repo),
        "task": args.task,
        "run_dir": str(run_dir),
        "command": cmd,
        "command_text": command_string(cmd),
        "config": str(config),
        "model_registry": str(registry),
        "trajectory": str(trajectory),
        "command_file": str(command_path),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "timeout": args.timeout,
        "started_at": time.time(),
    }

    run_dir.mkdir(parents=True, exist_ok=True)
    write_text(command_path, "#!/usr/bin/env bash\nset -euo pipefail\ncd " + shlex.quote(str(repo)) + "\n" + command_string(cmd) + "\n")
    command_path.chmod(command_path.stat().st_mode | 0o755)

    env = os.environ.copy()
    ensure_mini_global_config()
    env["MSWEA_GLOBAL_CONFIG_DIR"] = str(MINI_GLOBAL_CONFIG_DIR)
    env["MSWEA_CONFIGURED"] = "true"
    env["MSWEA_MODEL_NAME"] = "openai/diffusiongemma-local"
    env["MSWEA_SILENT_STARTUP"] = "1"
    env["OPENAI_API_KEY"] = "dummy"
    env["OPENAI_BASE_URL"] = "http://127.0.0.1:4100/v1"
    env["LITELLM_MODEL_REGISTRY_PATH"] = str(registry)
    if str(LOCAL_MINI.parent) not in env.get("PATH", "").split(os.pathsep):
        env["PATH"] = str(LOCAL_MINI.parent) + os.pathsep + env.get("PATH", "")

    if args.dry_run:
        report["status"] = "dry-run"
        report["returncode"] = None
        write_text(stdout_path, "")
        write_text(stderr_path, "")
        write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else str(report_path))
        return 0

    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
        )
        elapsed = time.time() - started
        write_text(stdout_path, proc.stdout)
        write_text(stderr_path, proc.stderr)
        mini_swe_analysis = analyze_trajectory(trajectory, proc.stdout)
        report.update(
            {
                "status": "failed" if mini_swe_analysis["failed"] else ("success" if proc.returncode == 0 else "failed"),
                "returncode": proc.returncode,
                "elapsed_sec": round(elapsed, 3),
                "trajectory_exists": trajectory.exists(),
                "trajectory_bytes": trajectory.stat().st_size if trajectory.exists() else 0,
                "mini_swe_analysis": mini_swe_analysis,
                "stdout_tail": tail(proc.stdout),
                "stderr_tail": tail(proc.stderr),
            }
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        write_text(stdout_path, stdout)
        write_text(stderr_path, stderr)
        report.update(
            {
                "status": "timeout",
                "returncode": None,
                "elapsed_sec": round(time.time() - started, 3),
                "trajectory_exists": trajectory.exists(),
                "trajectory_bytes": trajectory.stat().st_size if trajectory.exists() else 0,
                "stdout_tail": tail(stdout),
                "stderr_tail": tail(stderr),
            }
        )

    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report_path)
    return 0 if report["status"] == "success" else (124 if report["status"] == "timeout" else 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Artifacted runner for mini-swe-agent over the local DG LiteLLM profile.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--output", default="", help="Trajectory JSON path")
    parser.add_argument("--config", default="")
    parser.add_argument("--model-registry", default="")
    parser.add_argument("--binary", default="")
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--cost-limit", type=float, default=0.01)
    parser.add_argument("--yolo", action="store_true")
    parser.add_argument("--exit-immediately", action="store_true")
    parser.add_argument("--extra-config", action="append", default=[])
    parser.add_argument("--extra-args", nargs=argparse.REMAINDER, default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
