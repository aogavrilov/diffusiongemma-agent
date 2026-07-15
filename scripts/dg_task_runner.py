#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUPERVISOR = DG_ROOT / "scripts" / "run_supervisor_agent.sh"


def run_cmd(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=exc.stdout if isinstance(exc.stdout, str) else "",
            stderr=f"task step timed out after {timeout}s",
        )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_cmd(["git", *args], repo, timeout=60)


def safe_repo_file(repo: Path, value: str) -> str:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"file must be a repo-relative path: {value}")
    resolved = (repo / raw).resolve()
    if resolved != repo and repo not in resolved.parents:
        raise ValueError(f"file escapes repo: {value}")
    return raw.as_posix()


def load_plan(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read plan: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("steps"), list) or not payload["steps"]:
        raise ValueError("plan must contain a non-empty steps array")
    return payload


def step_config(step: Any, defaults: dict[str, Any], repo: Path) -> dict[str, Any]:
    if not isinstance(step, dict):
        raise ValueError("each plan step must be an object")
    task = str(step.get("task") or "").strip()
    if not task:
        raise ValueError("each plan step requires task")
    raw_files = step.get("files", [])
    if isinstance(raw_files, str):
        raw_files = [raw_files]
    if not isinstance(raw_files, list):
        raise ValueError("step files must be an array")
    files = [safe_repo_file(repo, str(item)) for item in raw_files if str(item).strip()]
    return {
        "name": str(step.get("name") or "task"),
        "task": task,
        "files": files,
        "max_files": int(step.get("max_files", defaults.get("max_files", max(1, len(files) or 1)))),
        "aider_timeout": int(step.get("aider_timeout", defaults.get("aider_timeout", 420))),
        "repair_attempts": int(step.get("repair_attempts", defaults.get("repair_attempts", 1))),
        "test_timeout": int(step.get("test_timeout", defaults.get("test_timeout", 120))),
        "test_cmd": str(step.get("test_cmd") or ""),
        "no_deterministic_first": bool(step.get("no_deterministic_first", False)),
    }


def write_json(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def command_text(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def step_report_name(index: int, name: str) -> str:
    slug = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in name).strip("-_")
    return f"{index:02d}-{slug or 'task'}.json"


def rollback_clean_start(repo: Path, before_diff: str) -> dict[str, Any]:
    if not before_diff:
        patch = git(repo, "diff", "--binary").stdout
        if not patch.strip():
            return {"attempted": False, "status": "not-needed"}
        proc = subprocess.run(
            ["git", "apply", "--reverse", "--whitespace=nowarn"],
            cwd=str(repo),
            input=patch,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return {
            "attempted": True,
            "status": "success" if proc.returncode == 0 else "failed",
            "method": "reverse-working-tree-diff-from-clean-start",
            "stderr": proc.stderr[-2000:],
        }
    return {"attempted": False, "status": "skipped", "reason": "repo was dirty before task"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute an artifacted, bounded DG task plan.")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--supervisor", default="")
    parser.add_argument("--step-report-dir", type=Path, default=None)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback-on-failure", action="store_true")
    parser.add_argument("--continue-on-failure", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    plan_path = args.plan.resolve()
    report_path = args.report.resolve() if args.report else None
    started = time.time()

    if not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    if git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        print(f"repo is not a git repository: {repo}", file=sys.stderr)
        return 2
    try:
        plan = load_plan(plan_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    defaults = plan.get("defaults") if isinstance(plan.get("defaults"), dict) else {}
    try:
        steps = [step_config(step, defaults, repo) for step in plan["steps"]]
    except (TypeError, ValueError) as exc:
        print(f"invalid plan: {exc}", file=sys.stderr)
        return 2

    status_before = git(repo, "status", "--short").stdout
    if status_before.strip() and not args.allow_dirty:
        print("Refusing to start with a dirty repo. Use --allow-dirty if this is intentional.", file=sys.stderr)
        return 3

    supervisor = Path(args.supervisor).resolve() if args.supervisor else DEFAULT_SUPERVISOR
    if not args.dry_run and not supervisor.exists():
        print(f"supervisor runner missing: {supervisor}", file=sys.stderr)
        return 2

    if args.step_report_dir:
        step_dir = args.step_report_dir.resolve()
    elif report_path:
        step_dir = report_path.parent / "steps"
    else:
        step_dir = Path(tempfile.mkdtemp(prefix="dg-task-steps."))
    if not args.dry_run:
        step_dir.mkdir(parents=True, exist_ok=True)

    aggregate: dict[str, Any] = {
        "repo": str(repo),
        "plan": str(plan_path),
        "dry_run": args.dry_run,
        "started_at": started,
        "status_before": status_before,
        "steps": [],
        "rollback": {"attempted": False, "status": "not-needed"},
    }
    failed = False
    for index, step in enumerate(steps, start=1):
        step_report = step_dir / step_report_name(index, step["name"])
        command = [
            str(supervisor),
            "--repo",
            str(repo),
            "--task",
            step["task"],
            "--max-files",
            str(max(1, step["max_files"])),
            "--aider-timeout",
            str(max(1, step["aider_timeout"])),
            "--repair-attempts",
            str(max(0, step["repair_attempts"])),
            "--test-timeout",
            str(max(1, step["test_timeout"])),
            "--report",
            str(step_report),
        ]
        for file_name in step["files"]:
            command.extend(["--file", file_name])
        if step["test_cmd"]:
            command.extend(["--test-cmd", step["test_cmd"]])
        if step["no_deterministic_first"]:
            command.append("--no-deterministic-first")
        if args.allow_dirty:
            command.append("--allow-dirty")

        if args.dry_run:
            step_result = {
                "index": index,
                "name": step["name"],
                "status": "dry-run",
                "command": command,
                "step_report": str(step_report),
            }
            print(f"DRY RUN step {index}: {command_text(command)}")
        else:
            timeout = max(30, step["aider_timeout"] + step["test_timeout"] + 60)
            proc = run_cmd(command, repo, timeout=timeout)
            step_result = {
                "index": index,
                "name": step["name"],
                "status": "success" if proc.returncode == 0 else "failed",
                "returncode": proc.returncode,
                "command": command,
                "step_report": str(step_report),
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-4000:],
                "supervisor_report": read_json(step_report),
            }
            if proc.stdout:
                print(proc.stdout, end="")
            if proc.stderr:
                print(proc.stderr, end="", file=sys.stderr)
        aggregate["steps"].append(step_result)
        if step_result["status"] == "failed":
            failed = True
            if not args.continue_on_failure and bool(plan.get("stop_on_failure", True)):
                break

    if failed and args.rollback_on_failure:
        aggregate["rollback"] = rollback_clean_start(repo, status_before)

    aggregate["finished_at"] = time.time()
    aggregate["elapsed_sec"] = round(aggregate["finished_at"] - started, 3)
    aggregate["status"] = "failed" if failed else "success"
    aggregate["status_after"] = git(repo, "status", "--short").stdout
    write_json(report_path, aggregate)
    print(f"DG task runner finished: {aggregate['status']}")
    if report_path:
        print(f"Task report: {report_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
