#!/usr/bin/env python3
"""Checkpointed controller for bounded DG coding sessions.

The controller never asks DiffusionGemma to choose or execute shell commands.
It delegates retrieval to Haystack BM25 and code changes to the existing
session/Aider path, while preserving all state and test feedback between
bounded retries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_ROOT = DG_ROOT / "runlogs" / "dg-autonomous-supervisor"
STATE_VERSION = 1


def now() -> float:
    return time.time()


def slug(value: str, limit: int = 48) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    return text[:limit] or "task"


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp = Path(handle.name)
    temp.replace(path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def git(repo: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_status(repo: Path) -> str:
    return git(repo, "status", "--short").stdout


def git_snapshot(repo: Path) -> dict[str, str]:
    return {
        "status": git_status(repo),
        "diff": git(repo, "diff", "--binary", "--", ".").stdout,
        "cached_diff": git(repo, "diff", "--cached", "--binary", "--", ".").stdout,
        "head": git(repo, "rev-parse", "HEAD").stdout.strip(),
    }


def wsl_path(path: Path) -> str:
    raw = str(path.resolve())
    if os.name != "nt":
        return raw
    match = re.match(r"^([A-Za-z]):\\(.*)$", raw)
    if not match:
        return raw
    drive, tail = match.groups()
    return f"/mnt/{drive.lower()}/{tail.replace(chr(92), '/') }"


def haystack_command(repo: Path, task: str, index_dir: Path, rebuild: bool) -> list[str]:
    runner = DG_ROOT / "scripts" / "dg_haystack_runner.py"
    if os.name == "nt":
        linux_python = wsl_path(DG_ROOT / ".venv-haystack" / "bin" / "python")
        command = [
            "wsl.exe",
            "--exec",
            linux_python,
            wsl_path(runner),
            "--repo",
            wsl_path(repo),
            "--task",
            task,
            "--retrieve-only",
            "--json",
            "--index-dir",
            wsl_path(index_dir),
        ]
    else:
        python = Path(os.environ.get("DG_HAYSTACK_PYTHON", DG_ROOT / ".venv-haystack" / "bin" / "python"))
        command = [
            str(python),
            str(runner),
            "--repo",
            str(repo),
            "--task",
            task,
            "--retrieve-only",
            "--json",
            "--index-dir",
            str(index_dir),
        ]
    if rebuild:
        command.append("--rebuild-index")
    return command


def run_retrieval(repo: Path, task: str, index_dir: Path, rebuild: bool, timeout: int) -> tuple[dict[str, Any], int]:
    command = haystack_command(repo, task, index_dir, rebuild)
    try:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "error": str(exc), "command": command}, 1
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        payload = {"status": "failed", "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    if not isinstance(payload, dict):
        payload = {"status": "failed", "error": "Haystack did not return a JSON object"}
    payload["command"] = command
    payload["returncode"] = proc.returncode
    if proc.stderr:
        payload["stderr_tail"] = proc.stderr[-4000:]
    return payload, proc.returncode


def planner_guidance(args: argparse.Namespace, retrieval: dict[str, Any]) -> dict[str, Any]:
    """Optional planner is advisory: it cannot execute commands or modify files."""
    if not args.planner_url or not args.planner_model:
        return {"status": "disabled"}
    paths = retrieval.get("retrieval", {}).get("paths", []) if isinstance(retrieval.get("retrieval"), dict) else []
    prompt = "Give concise file-level coding guidance. Do not emit shell commands or patches. Existing paths: " + ", ".join(map(str, paths)) + "\nTask: " + args.task
    request = urllib.request.Request(
        args.planner_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": args.planner_model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {args.planner_api_key or 'dummy'}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.planner_timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"status": "success", "model": args.planner_model, "guidance": str(payload["choices"][0]["message"]["content"]).strip()[:2400]}
    except (KeyError, TypeError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        return {"status": "failed", "model": args.planner_model, "error": str(exc)}


def state_dir_for(args: argparse.Namespace, repo: Path) -> Path:
    if args.state_dir:
        return Path(args.state_dir).resolve()
    digest = hashlib.sha256(f"{repo}\0{args.task}".encode("utf-8")).hexdigest()[:12]
    return DEFAULT_STATE_ROOT / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug(args.task)}-{digest}"


def initial_state(args: argparse.Namespace, repo: Path, state_dir: Path) -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "repo": str(repo),
        "task": args.task,
        "state_dir": str(state_dir),
        "created_at": now(),
        "updated_at": now(),
        "status": "created",
        "max_steps": args.max_steps,
        "initial_git": git_snapshot(repo),
        "retrieval": {},
        "planner": {"status": "not-run"},
        "steps": [],
        "rollback": {"attempted": False, "status": "not-needed"},
        "warnings": [],
    }


def write_state(state_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    atomic_write_json(state_dir / "state.json", state)
    retrieval = state.get("retrieval") if isinstance(state.get("retrieval"), dict) else {}
    lines = [
        "# DG Persistent Supervisor",
        "",
        f"- Status: `{state.get('status')}`",
        f"- Repository: `{state.get('repo')}`",
        f"- Task: {state.get('task')}",
        f"- Steps: `{len(state.get('steps', []))}/{state.get('max_steps')}`",
    ]
    paths = retrieval.get("retrieval", {}).get("paths", []) if isinstance(retrieval.get("retrieval"), dict) else []
    if paths:
        lines.extend(["", "## Retrieved Files", *[f"- `{item}`" for item in paths]])
    if state.get("steps"):
        lines.extend(["", "## Attempts"])
        for item in state["steps"]:
            lines.append(f"- Step {item.get('index')}: `{item.get('status')}` ({item.get('session_dir', '')})")
    if state.get("warnings"):
        lines.extend(["", "## Warnings", *[f"- {item}" for item in state["warnings"]]])
    (state_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def feedback_from_session(session: dict[str, Any], limit: int = 1800) -> str:
    artifacts = session.get("artifacts") if isinstance(session.get("artifacts"), dict) else {}
    parts: list[str] = []
    for key in ("verify_report", "task_stderr", "task_stdout"):
        path = Path(str(artifacts.get(key) or ""))
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            parts.append(text[-limit:])
    return "\n\n".join(parts)[-limit:]


def session_command(args: argparse.Namespace, repo: Path, state_dir: Path, step: int, retrieval: dict[str, Any], feedback: str, planner: dict[str, Any]) -> list[str]:
    task = args.task
    stats = retrieval.get("retrieval") if isinstance(retrieval.get("retrieval"), dict) else {}
    paths = stats.get("paths") if isinstance(stats.get("paths"), list) else []
    if paths:
        task += "\n\nSupervisor retrieval candidates: " + ", ".join(str(item) for item in paths[: args.max_files])
    if feedback:
        task += "\n\nPrevious verified attempt failed. Keep the task scope unchanged and use this test feedback:\n" + feedback[-1800:]
    if planner.get("status") == "success":
        task += "\n\nExternal planner guidance (advisory only; verify against repository):\n" + str(planner.get("guidance") or "")
    command = [
        sys.executable,
        str(DG_ROOT / "scripts" / "dg_agent.py"),
        "session",
        "--repo",
        str(repo),
        "--task",
        task,
        "--out-dir",
        str(state_dir / "sessions"),
        "--max-files",
        str(args.max_files),
        "--max-snippet-chars",
        str(args.max_snippet_chars),
        "--test-timeout",
        str(args.test_timeout),
        "--aider-timeout",
        str(args.aider_timeout),
        "--repair-attempts",
        str(args.repair_attempts),
        "--wall-timeout",
        str(args.wall_timeout),
        "--rollback-on-failure",
    ]
    for file_name in args.file:
        command.extend(["--file", file_name])
    if args.test_cmd:
        command.extend(["--test-cmd", args.test_cmd])
    if args.auto_test:
        command.append("--auto-test")
    if args.no_deterministic_first:
        command.append("--no-deterministic-first")
    if args.dry_run:
        command.append("--dry-run")
    return command


def latest_session(sessions_dir: Path) -> dict[str, Any] | None:
    candidates = sorted(sessions_dir.glob("*/session.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return read_json(candidates[0]) if candidates else None


def rollback_clean_start(repo: Path, state_dir: Path, initial: dict[str, Any]) -> dict[str, Any]:
    if str(initial.get("status") or "").strip():
        return {"attempted": False, "status": "skipped", "reason": "repository was dirty before the run"}
    status = git_status(repo)
    if not status.strip():
        return {"attempted": False, "status": "not-needed"}
    if any(line.startswith("??") for line in status.splitlines()):
        return {"attempted": False, "status": "blocked", "reason": "unexpected untracked files; refusing to remove them", "status_after": status}
    patch = git(repo, "diff", "--binary", "--", ".").stdout
    if not patch:
        return {"attempted": False, "status": "blocked", "reason": "staged or non-diff changes remain", "status_after": status}
    snapshot = state_dir / "unexpected-failure.diff"
    snapshot.write_text(patch, encoding="utf-8")
    proc = git(repo, "apply", "--reverse", "--whitespace=nowarn", input_text=patch)
    return {
        "attempted": True,
        "status": "success" if proc.returncode == 0 and not git_status(repo).strip() else "failed",
        "patch": str(snapshot),
        "stderr": proc.stderr[-2000:],
        "status_after": git_status(repo),
    }


def run(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    if git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        print(f"repo is not a git repository: {repo}", file=sys.stderr)
        return 2
    if not 1 <= args.max_steps <= 5:
        print("--max-steps must be between 1 and 5", file=sys.stderr)
        return 2

    state_dir = state_dir_for(args, repo)
    state_path = state_dir / "state.json"
    state = read_json(state_path) if args.resume or args.status else None
    if args.status:
        if state is None:
            print(f"state is missing: {state_path}", file=sys.stderr)
            return 2
        print(json.dumps(state, ensure_ascii=False, indent=2) if args.json else f"{state.get('status')} {state_path}")
        return 0
    if state is None:
        if state_path.exists():
            print(f"state already exists: {state_dir}; pass --resume to continue it", file=sys.stderr)
            return 2
        state_dir.mkdir(parents=True, exist_ok=False)
        state = initial_state(args, repo, state_dir)
        if str(state["initial_git"].get("status") or "").strip() and not args.allow_dirty:
            state["status"] = "blocked"
            state["warnings"].append("repository is dirty; use --allow-dirty to run without controller rollback")
            write_state(state_dir, state)
            print(f"Supervisor state: {state_path}")
            return 3
        if args.allow_dirty:
            state["warnings"].append("started from a dirty repository; controller rollback is disabled")
    elif state.get("status") == "success":
        print(json.dumps(state, ensure_ascii=False, indent=2) if args.json else f"Supervisor already succeeded: {state_path}")
        return 0

    index_dir = Path(args.index_dir).resolve() if args.index_dir else (DG_ROOT / "runlogs" / "dg-retrieval-index" / hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:16])
    retrieval, retrieval_rc = run_retrieval(repo, args.task, index_dir, args.rebuild_index, args.retrieval_timeout)
    state["retrieval"] = retrieval
    (state_dir / "retrieval.json").write_text(json.dumps(retrieval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if retrieval_rc != 0 or retrieval.get("status") != "success":
        state["status"] = "blocked"
        state["warnings"].append("Haystack retrieval failed; no edit was attempted")
        write_state(state_dir, state)
        print(f"Supervisor state: {state_path}")
        return 1

    planner = planner_guidance(args, retrieval)
    state["planner"] = planner
    if planner.get("status") == "failed":
        state["warnings"].append("external planner failed; continuing without planner guidance")
    write_state(state_dir, state)

    start_index = len(state.get("steps", [])) + 1
    feedback = ""
    if state.get("steps"):
        previous = state["steps"][-1]
        feedback = str(previous.get("feedback") or "")
    for index in range(start_index, args.max_steps + 1):
        before = git_snapshot(repo)
        checkpoint = state_dir / "checkpoints" / f"{index:02d}-before.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps(before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        command = session_command(args, repo, state_dir, index, retrieval, feedback, planner)
        if args.dry_run:
            attempt = {"index": index, "status": "dry-run", "command": command, "checkpoint": str(checkpoint)}
            state["steps"].append(attempt)
            state["status"] = "dry-run"
            write_state(state_dir, state)
            break
        try:
            proc = subprocess.run(command, cwd=DG_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=args.wall_timeout + 30)
        except subprocess.TimeoutExpired as exc:
            proc = subprocess.CompletedProcess(command, 124, stdout="", stderr=f"controller timed out after {exc.timeout}s")
        session = latest_session(state_dir / "sessions") or {}
        feedback = feedback_from_session(session)
        attempt = {
            "index": index,
            "status": "success" if proc.returncode == 0 and session.get("status") == "success" else "failed",
            "returncode": proc.returncode,
            "command": command,
            "checkpoint": str(checkpoint),
            "session_dir": str(session.get("session_dir") or ""),
            "session_report": session,
            "feedback": feedback,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
        state["steps"].append(attempt)
        if attempt["status"] == "success":
            state["status"] = "success"
            state["rollback"] = {"attempted": False, "status": "not-needed"}
            write_state(state_dir, state)
            break
        if not args.allow_dirty:
            rollback = rollback_clean_start(repo, state_dir, state["initial_git"])
            state["rollback"] = rollback
            if rollback.get("status") == "blocked":
                state["status"] = "blocked"
                state["warnings"].append("unexpected repository state after failed session")
                write_state(state_dir, state)
                break
        state["status"] = "retrying" if index < args.max_steps else "failed"
        write_state(state_dir, state)

    write_state(state_dir, state)
    result = {"status": state.get("status"), "state_dir": str(state_dir), "state": str(state_path), "steps": len(state.get("steps", []))}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Supervisor status: {result['status']}\nSupervisor state: {state_path}")
    return 0 if state.get("status") == "success" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a checkpointed persistent controller over Haystack retrieval and DG sessions.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--state-dir", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--index-dir", default="")
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--max-files", type=int, default=3)
    parser.add_argument("--max-snippet-chars", type=int, default=1200)
    parser.add_argument("--test-cmd", default="")
    parser.add_argument("--auto-test", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--test-timeout", type=int, default=120)
    parser.add_argument("--aider-timeout", type=int, default=300)
    parser.add_argument("--repair-attempts", type=int, default=1)
    parser.add_argument("--wall-timeout", type=int, default=420)
    parser.add_argument("--retrieval-timeout", type=int, default=180)
    parser.add_argument("--planner-url", default=os.environ.get("DG_PLANNER_URL", ""), help="Optional stronger OpenAI-compatible planner URL")
    parser.add_argument("--planner-model", default=os.environ.get("DG_PLANNER_MODEL", ""))
    parser.add_argument("--planner-api-key", default=os.environ.get("DG_PLANNER_API_KEY", ""))
    parser.add_argument("--planner-timeout", type=int, default=60)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--no-deterministic-first", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
