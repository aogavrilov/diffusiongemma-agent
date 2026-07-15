#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DG_AGENT = DG_ROOT / "scripts" / "dg_agent.sh"
NOTE_ROOT = DG_ROOT / "runlogs" / "dg-agent-notes"
AGENT_RUN_ROOT = DG_ROOT / "runlogs" / "dg-agent-runs"
AGENT_RUN_ARTIFACT_FILENAMES = {
    "agent_json": "agent.json",
    "transcript": "tool-loop.json",
    "stdout": "stdout.log",
    "stderr": "stderr.log",
}
AGENT_RUN_ARTIFACT_ALIASES = {
    "agent": "agent_json",
    "json": "agent_json",
    "report": "agent_json",
    "tool_loop": "transcript",
    "tool-loop": "transcript",
    "tool-loop.json": "transcript",
    "stdout.log": "stdout",
    "stderr.log": "stderr",
}
WINDOWS_DRIVE_PATH = re.compile(r"^([A-Za-z]):[\\\\/](.*)$")


def normalize_host_path(value: str) -> str:
    """Map Windows client paths to WSL mounts when this server runs in Linux."""
    raw = str(value or "").strip()
    if os.name == "nt":
        return raw
    match = WINDOWS_DRIVE_PATH.match(raw)
    if not match:
        return raw
    drive, tail = match.groups()
    return f"/mnt/{drive.lower()}/{tail.replace(chr(92), '/')}"


def log(message: str) -> None:
    print(f"[dg-mcp] {message}", file=sys.stderr, flush=True)


def rpc_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def emit(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def text_result(text: str, *, is_error: bool = False, structured: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    return result


def arg_str(args: dict[str, Any], name: str, default: str = "") -> str:
    value = args.get(name, default)
    if value is None:
        return default
    return str(value)


def arg_int(args: dict[str, Any], name: str, default: int, *, minimum: int = 1, maximum: int = 3600) -> int:
    try:
        value = int(args.get(name, default))
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def arg_bool(args: dict[str, Any], name: str, default: bool = False) -> bool:
    value = args.get(name, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def arg_files(args: dict[str, Any]) -> list[str]:
    value = args.get("files", args.get("file", []))
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def arg_list(args: dict[str, Any], name: str) -> list[str]:
    value = args.get(name, [])
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def run_cmd(command: list[str], *, cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd or DG_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "elapsed_sec": round(time.time() - started, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "returncode": 124,
            "stdout": stdout,
            "stderr": stderr + f"\nTimed out after {timeout}s",
            "elapsed_sec": round(time.time() - started, 3),
            "timed_out": True,
        }


def tail(text: str, limit: int = 8000) -> str:
    return text[-limit:] if len(text) > limit else text


def head(text: str, limit: int = 8000) -> str:
    return text[:limit] if len(text) > limit else text


def command_report(command: list[str], result: dict[str, Any]) -> str:
    output = (result.get("stdout", "") + ("\n" + result.get("stderr", "") if result.get("stderr") else "")).strip()
    return (
        f"command: {' '.join(command)}\n"
        f"returncode: {result['returncode']}\n"
        f"elapsed_sec: {result['elapsed_sec']}\n\n"
        f"{tail(output)}"
    ).rstrip()


def repo_path(repo: str) -> Path:
    path = Path(normalize_host_path(repo)).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"repo does not exist: {path}")
    return path


def safe_repo_file(repo: Path, file_name: str) -> Path:
    if not file_name:
        raise ValueError("missing file path")
    raw = Path(file_name).expanduser()
    target = raw.resolve() if raw.is_absolute() else (repo / raw).resolve()
    if target != repo and repo not in target.parents:
        raise ValueError(f"path escapes repo: {file_name}")
    if not target.exists() or not target.is_file():
        raise ValueError(f"file does not exist: {target}")
    return target


def slugify(text: str, default: str = "note") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip().lower()).strip("-._")
    return (slug or default)[:80]


def note_paths() -> list[Path]:
    if not NOTE_ROOT.exists():
        return []
    return sorted((path for path in NOTE_ROOT.glob("*.md") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)


def safe_note_path(note: str = "", latest: bool = False) -> Path | None:
    paths = note_paths()
    if latest:
        return paths[0] if paths else None
    if not note:
        return None
    raw = Path(note)
    candidate = raw.resolve() if raw.is_absolute() else (NOTE_ROOT / raw.name).resolve()
    root = NOTE_ROOT.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"note path escapes note root: {note}")
    if candidate.exists() and candidate.is_file():
        return candidate
    stem = raw.stem or raw.name
    for path in paths:
        if path.name == note or path.stem == stem or path.name.startswith(stem):
            return path
    return None


def note_summary(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    title = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return {
        "id": path.stem,
        "path": str(path),
        "title": title,
        "mtime": path.stat().st_mtime,
        "size": path.stat().st_size,
    }


def tool_task_note(args: dict[str, Any]) -> dict[str, Any]:
    task = arg_str(args, "task", "")
    body = arg_str(args, "body", "")
    if not task:
        return text_result("Missing required argument: task", is_error=True)
    if not body:
        return text_result("Missing required argument: body", is_error=True)
    repo = arg_str(args, "repo", "")
    title = arg_str(args, "title", task)
    tags = arg_list(args, "tags")
    append_to = arg_str(args, "append_to", "")
    NOTE_ROOT.mkdir(parents=True, exist_ok=True)

    existing = safe_note_path(append_to) if append_to else None
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S %z")
    if existing:
        addition = f"\n\n## Update {timestamp}\n\n{body.rstrip()}\n"
        existing.write_text(existing.read_text(encoding="utf-8", errors="replace").rstrip() + addition, encoding="utf-8")
        path = existing
        status = "updated"
    else:
        filename = f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify(title)}.md"
        path = NOTE_ROOT / filename
        metadata = [
            f"# {title}",
            "",
            f"- created: {timestamp}",
            f"- task: {task}",
        ]
        if repo:
            metadata.append(f"- repo: {repo}")
        if tags:
            metadata.append(f"- tags: {', '.join(tags)}")
        path.write_text("\n".join(metadata) + "\n\n" + body.rstrip() + "\n", encoding="utf-8")
        status = "written"

    structured = {"returncode": 0, "stdout": str(path), "stderr": "", "elapsed_sec": 0, "timed_out": False, "status": status, "note": note_summary(path)}
    return text_result(f"{status}: {path}", structured=structured)


def tool_task_notes(args: dict[str, Any]) -> dict[str, Any]:
    limit = arg_int(args, "limit", 20, maximum=200)
    max_chars = arg_int(args, "max_chars", 20000, maximum=200000)
    note = arg_str(args, "note", "")
    latest = arg_bool(args, "latest", False)
    selected = safe_note_path(note, latest=latest)
    if selected:
        text = head(selected.read_text(encoding="utf-8", errors="replace"), max_chars)
        structured = {
            "returncode": 0,
            "stdout": text,
            "stderr": "",
            "elapsed_sec": 0,
            "timed_out": False,
            "note": note_summary(selected),
            "truncated": selected.stat().st_size > max_chars,
        }
        return text_result(text, structured=structured)
    if note or latest:
        return text_result("No matching task note found.", is_error=True, structured={"returncode": 2, "stdout": "", "stderr": "not found", "elapsed_sec": 0, "timed_out": False})

    notes = [note_summary(path) for path in note_paths()[:limit]]
    text = json.dumps({"notes": notes, "root": str(NOTE_ROOT)}, ensure_ascii=False, indent=2)
    structured = {"returncode": 0, "stdout": text, "stderr": "", "elapsed_sec": 0, "timed_out": False, "notes": notes, "root": str(NOTE_ROOT)}
    return text_result(text, structured=structured)


def tool_repo_status(args: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(arg_str(args, "repo", "."))
    timeout = arg_int(args, "timeout", 30, maximum=180)
    command = ["git", "status", "--short"]
    result = run_cmd(command, cwd=repo, timeout=timeout)
    diff_stat = run_cmd(["git", "diff", "--stat"], cwd=repo, timeout=timeout)
    untracked = run_cmd(["git", "ls-files", "--others", "--exclude-standard"], cwd=repo, timeout=timeout)
    structured = {
        **result,
        "repo": str(repo),
        "diff_stat": diff_stat.get("stdout", ""),
        "untracked": [line for line in untracked.get("stdout", "").splitlines() if line],
    }
    text = command_report(command, result)
    if diff_stat.get("stdout"):
        text += "\n\nDiff stat:\n" + diff_stat["stdout"].strip()
    if untracked.get("stdout"):
        text += "\n\nUntracked files:\n" + head(untracked["stdout"], arg_int(args, "max_chars", 8000, maximum=100000)).strip()
    return text_result(text, is_error=result["returncode"] != 0, structured=structured)


def tool_list_files(args: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(arg_str(args, "repo", "."))
    timeout = arg_int(args, "timeout", 30, maximum=180)
    limit = arg_int(args, "limit", 200, maximum=5000)
    pattern = arg_str(args, "pattern", "")
    command = ["rg", "--files"]
    for glob in arg_list(args, "globs"):
        command.extend(["-g", glob])
    result = run_cmd(command, cwd=repo, timeout=timeout)
    if result["returncode"] != 0:
        command = ["git", "ls-files"]
        result = run_cmd(command, cwd=repo, timeout=timeout)
    files = [line for line in result.get("stdout", "").splitlines() if line]
    if pattern:
        files = [file for file in files if pattern.lower() in file.lower()]
    visible = files[:limit]
    structured = {**result, "repo": str(repo), "files": visible, "total_matches": len(files), "truncated": len(files) > limit}
    text = "\n".join(visible)
    if len(files) > limit:
        text += f"\n... truncated {len(files) - limit} more files"
    return text_result(text, is_error=result["returncode"] != 0, structured=structured)


def tool_search(args: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(arg_str(args, "repo", "."))
    query = arg_str(args, "query", "")
    if not query:
        return text_result("Missing required argument: query", is_error=True)
    timeout = arg_int(args, "timeout", 30, maximum=180)
    max_matches = arg_int(args, "max_matches", 80, maximum=1000)
    max_chars = arg_int(args, "max_chars", 12000, maximum=200000)
    command = ["rg", "--line-number", "--column", "--color", "never"]
    context = arg_int(args, "context", 0, minimum=0, maximum=5)
    if context:
        command.extend(["--context", str(context)])
    for glob in arg_list(args, "globs"):
        command.extend(["-g", glob])
    command.extend(["--", query, "."])
    result = run_cmd(command, cwd=repo, timeout=timeout)
    lines = result.get("stdout", "").splitlines()
    visible = lines[:max_matches]
    text = head("\n".join(visible), max_chars)
    if len(lines) > max_matches:
        text += f"\n... truncated {len(lines) - max_matches} more matching lines"
    structured = {
        **result,
        "repo": str(repo),
        "query": query,
        "matches": visible,
        "total_lines": len(lines),
        "truncated": len(lines) > max_matches or len("\n".join(visible)) > max_chars,
    }
    return text_result(text, is_error=result["returncode"] not in {0, 1}, structured=structured)


def tool_read_file(args: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(arg_str(args, "repo", "."))
    target = safe_repo_file(repo, arg_str(args, "path", ""))
    start_line = arg_int(args, "start_line", 1, minimum=1, maximum=10_000_000)
    max_lines = arg_int(args, "max_lines", 160, maximum=5000)
    max_chars = arg_int(args, "max_chars", 20000, maximum=200000)
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    selected = lines[start_line - 1 : start_line - 1 + max_lines]
    numbered = "\n".join(f"{idx}: {line}" for idx, line in enumerate(selected, start=start_line))
    numbered = head(numbered, max_chars)
    rel = target.relative_to(repo)
    structured = {
        "returncode": 0,
        "stdout": numbered,
        "stderr": "",
        "elapsed_sec": 0,
        "timed_out": False,
        "repo": str(repo),
        "path": str(rel),
        "line_count": len(lines),
        "start_line": start_line,
        "returned_lines": len(selected),
        "truncated": len(selected) < len(lines[start_line - 1 :]) or len(numbered) >= max_chars,
    }
    return text_result(numbered, structured=structured)


def tool_git_diff(args: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(arg_str(args, "repo", "."))
    timeout = arg_int(args, "timeout", 30, maximum=180)
    max_chars = arg_int(args, "max_chars", 20000, maximum=200000)
    command = ["git", "diff"]
    if arg_bool(args, "cached", False):
        command.append("--cached")
    if arg_bool(args, "stat", False):
        command.append("--stat")
    for file_name in arg_files(args):
        command.extend(["--", file_name])
        break
    result = run_cmd(command, cwd=repo, timeout=timeout)
    output = head(result.get("stdout", ""), max_chars)
    structured = {
        **result,
        "repo": str(repo),
        "stdout": output,
        "truncated": len(result.get("stdout", "")) > max_chars,
    }
    return text_result(command_report(command, structured), is_error=result["returncode"] != 0, structured=structured)


def tool_status(args: dict[str, Any]) -> dict[str, Any]:
    timeout = arg_int(args, "timeout", 30, maximum=180)
    command = [str(DG_AGENT), "status"]
    result = run_cmd(command, timeout=timeout)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_context(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    task = arg_str(args, "task", "")
    if not task:
        return text_result("Missing required argument: task", is_error=True)
    timeout = arg_int(args, "timeout", 120, maximum=600)
    command = [
        str(DG_AGENT),
        "context",
        "--repo",
        repo,
        "--task",
        task,
        "--max-files",
        str(arg_int(args, "max_files", 3, maximum=20)),
        "--max-snippet-chars",
        str(arg_int(args, "max_snippet_chars", 1200, maximum=20000)),
    ]
    for file_name in arg_files(args):
        command.extend(["--file", file_name])
    result = run_cmd(command, timeout=timeout)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def rag_command(args: dict[str, Any], *, print_context: bool) -> tuple[list[str], int]:
    repo = arg_str(args, "repo", ".")
    task = arg_str(args, "task", "")
    if not task:
        return [], 0
    timeout = arg_int(args, "timeout", 120 if print_context else 300, maximum=1800)
    command = [
        str(DG_AGENT),
        "rag",
        "--repo",
        repo,
        "--task",
        task,
        "--max-context-chars",
        str(arg_int(args, "max_context_chars", 900 if print_context else 650, maximum=20000)),
        "--max-files",
        str(arg_int(args, "max_files", 3, maximum=20)),
        "--max-tokens",
        str(arg_int(args, "max_tokens", 128, maximum=1024)),
        "--timeout",
        str(timeout),
    ]
    base_url = arg_str(args, "base_url", "")
    if base_url:
        command.extend(["--base-url", base_url])
    model = arg_str(args, "model", "")
    if model:
        command.extend(["--model", model])
    if print_context:
        command.append("--print-context")
    if arg_bool(args, "debug", False):
        command.append("--debug")
    return command, timeout


def tool_rag_context(args: dict[str, Any]) -> dict[str, Any]:
    if not arg_str(args, "task", ""):
        return text_result("Missing required argument: task", is_error=True)
    command, timeout = rag_command(args, print_context=True)
    result = run_cmd(command, timeout=timeout)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_rag_answer(args: dict[str, Any]) -> dict[str, Any]:
    if not arg_str(args, "task", ""):
        return text_result("Missing required argument: task", is_error=True)
    command, timeout = rag_command(args, print_context=False)
    result = run_cmd(command, timeout=timeout + 30)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_repo_pack(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    timeout = arg_int(args, "timeout", 180, maximum=1800)
    max_chars = arg_int(args, "max_chars", 20000, minimum=1000, maximum=200000)
    command = [
        str(DG_AGENT),
        "repo-pack",
        "--repo",
        repo,
        "--style",
        arg_str(args, "style", "markdown"),
        "--stdout",
        "--top-files-len",
        str(arg_int(args, "top_files_len", 5, maximum=50)),
    ]
    for pattern in arg_list(args, "include"):
        command.extend(["--include", pattern])
    for pattern in arg_list(args, "ignore"):
        command.extend(["--ignore", pattern])
    if arg_bool(args, "compress", False):
        command.append("--compress")
    if arg_bool(args, "include_diffs", False):
        command.append("--include-diffs")
    if arg_bool(args, "output_show_line_numbers", False):
        command.append("--output-show-line-numbers")
    if arg_bool(args, "remove_comments", False):
        command.append("--remove-comments")
    if arg_bool(args, "remove_empty_lines", False):
        command.append("--remove-empty-lines")
    if arg_bool(args, "no_files", False):
        command.append("--no-files")
    if arg_bool(args, "no_security_check", False):
        command.append("--no-security-check")
    token_budget = arg_int(args, "token_budget", 0, minimum=0, maximum=2_000_000)
    if token_budget:
        command.extend(["--token-budget", str(token_budget)])

    result = run_cmd(command, timeout=timeout)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    truncated = len(stdout) > max_chars
    body = stdout[:max_chars] + ("\n\n[truncated]\n" if truncated else "")
    report = (
        f"command: {' '.join(command)}\n"
        f"returncode: {result['returncode']}\n"
        f"elapsed_sec: {result['elapsed_sec']}\n"
        f"stdout_chars: {len(stdout)}\n"
        f"truncated: {truncated}\n\n"
        f"{body}"
    ).rstrip()
    if stderr.strip():
        report += "\n\nstderr:\n" + tail(stderr, 4000)
    structured = {**result, "stdout_chars": len(stdout), "truncated": truncated, "max_chars": max_chars}
    return text_result(report, is_error=result["returncode"] != 0, structured=structured)


def tool_repo_map(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    timeout = arg_int(args, "timeout", 180, maximum=1800)
    max_chars = arg_int(args, "max_chars", 20000, minimum=1000, maximum=200000)
    command = [
        str(DG_AGENT),
        "repo-map",
        "--repo",
        repo,
        "--map-tokens",
        str(arg_int(args, "map_tokens", 512, minimum=128, maximum=64000)),
        "--max-chars",
        str(max_chars),
        "--timeout",
        str(timeout),
    ]
    if arg_bool(args, "map_only", True):
        command.append("--map-only")
    base_url = arg_str(args, "base_url", "")
    if base_url:
        command.extend(["--base-url", base_url])
    model = arg_str(args, "model", "")
    if model:
        command.extend(["--model", model])
    for path in arg_list(args, "paths"):
        command.append(path)

    result = run_cmd(command, timeout=timeout + 30)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    truncated = len(stdout) > max_chars
    report = (
        f"command: {' '.join(command)}\n"
        f"returncode: {result['returncode']}\n"
        f"elapsed_sec: {result['elapsed_sec']}\n"
        f"stdout_chars: {len(stdout)}\n"
        f"truncated: {truncated}\n\n"
        f"{stdout[:max_chars]}"
    ).rstrip()
    if truncated:
        report += "\n\n[truncated]"
    if stderr.strip():
        report += "\n\nstderr:\n" + tail(stderr, 4000)
    structured = {**result, "stdout_chars": len(stdout), "truncated": truncated, "max_chars": max_chars}
    return text_result(report, is_error=result["returncode"] != 0, structured=structured)


def tool_ast_grep(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    pattern = arg_str(args, "pattern", "")
    kind = arg_str(args, "kind", "")
    selector = arg_str(args, "selector", "")
    if not any([pattern, kind, selector]):
        return text_result("Missing required argument: pattern, kind, or selector", is_error=True)

    timeout = arg_int(args, "timeout", 120, maximum=1800)
    max_chars = arg_int(args, "max_chars", 20000, minimum=1000, maximum=200000)
    command = [
        str(DG_AGENT),
        "ast-grep",
        "--repo",
        repo,
        "--max-matches",
        str(arg_int(args, "max_matches", 80, maximum=1000)),
        "--max-chars",
        str(max_chars),
        "--timeout",
        str(timeout),
    ]
    lang = arg_str(args, "lang", "")
    if lang:
        command.extend(["--lang", lang])
    if pattern:
        command.extend(["--pattern", pattern])
    if kind:
        command.extend(["--kind", kind])
    if selector:
        command.extend(["--selector", selector])
    strictness = arg_str(args, "strictness", "")
    if strictness:
        command.extend(["--strictness", strictness])
    context = arg_int(args, "context", 0, minimum=0, maximum=20)
    if context:
        command.extend(["--context", str(context)])
    for glob in arg_list(args, "globs"):
        command.extend(["--glob", glob])
    if arg_bool(args, "files_with_matches", False):
        command.append("--files-with-matches")
    elif arg_bool(args, "json", True):
        command.append("--json")
    paths = arg_list(args, "paths")
    command.extend(paths)

    result = run_cmd(command, timeout=timeout + 30)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    truncated = len(stdout) > max_chars
    report = (
        f"command: {' '.join(command)}\n"
        f"returncode: {result['returncode']}\n"
        f"elapsed_sec: {result['elapsed_sec']}\n"
        f"stdout_chars: {len(stdout)}\n"
        f"truncated: {truncated}\n\n"
        f"{stdout[:max_chars]}"
    ).rstrip()
    if truncated:
        report += "\n\n[truncated]"
    if stderr.strip():
        report += "\n\nstderr:\n" + tail(stderr, 4000)
    structured = {**result, "stdout_chars": len(stdout), "truncated": truncated, "max_chars": max_chars}
    return text_result(report, is_error=result["returncode"] != 0, structured=structured)


def tool_code_outline(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    timeout = arg_int(args, "timeout", 120, maximum=1800)
    max_chars = arg_int(args, "max_chars", 20000, minimum=1000, maximum=200000)
    command = [
        str(DG_AGENT),
        "code-outline",
        "--repo",
        repo,
        "--items",
        arg_str(args, "items", "auto"),
        "--view",
        arg_str(args, "view", "auto"),
        "--max-items",
        str(arg_int(args, "max_items", 200, maximum=5000)),
        "--max-chars",
        str(max_chars),
        "--timeout",
        str(timeout),
    ]
    lang = arg_str(args, "lang", "")
    if lang:
        command.extend(["--lang", lang])
    symbol_type = arg_str(args, "type", "")
    if symbol_type:
        command.extend(["--type", symbol_type])
    match = arg_str(args, "match", "")
    if match:
        command.extend(["--match", match])
    if arg_bool(args, "pub_members", False):
        command.append("--pub-members")
    for glob in arg_list(args, "globs"):
        command.extend(["--glob", glob])
    if arg_bool(args, "json", True):
        command.append("--json")
    paths = arg_list(args, "paths")
    command.extend(paths)

    result = run_cmd(command, timeout=timeout + 30)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    truncated = len(stdout) > max_chars
    report = (
        f"command: {' '.join(command)}\n"
        f"returncode: {result['returncode']}\n"
        f"elapsed_sec: {result['elapsed_sec']}\n"
        f"stdout_chars: {len(stdout)}\n"
        f"truncated: {truncated}\n\n"
        f"{stdout[:max_chars]}"
    ).rstrip()
    if truncated:
        report += "\n\n[truncated]"
    if stderr.strip():
        report += "\n\nstderr:\n" + tail(stderr, 4000)
    structured = {**result, "stdout_chars": len(stdout), "truncated": truncated, "max_chars": max_chars}
    return text_result(report, is_error=result["returncode"] != 0, structured=structured)


def repo_output_path(repo: str, value: str) -> str:
    if not value:
        return ""
    raw = Path(value).expanduser()
    if raw.is_absolute():
        return str(raw.resolve())
    return str((repo_path(repo) / raw).resolve())


def tool_preflight(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    timeout = arg_int(args, "timeout", 120, maximum=600)
    command = [str(DG_AGENT), "preflight", "--repo", repo, "--json"]
    task = arg_str(args, "task", "")
    if task:
        command.extend(["--task", task])
    for file_name in arg_files(args):
        command.extend(["--file", file_name])
    if arg_bool(args, "allow_dirty", False):
        command.append("--allow-dirty")
    result = run_cmd(command, timeout=timeout)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_plan(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    task = arg_str(args, "task", "")
    if not task:
        return text_result("Missing required argument: task", is_error=True)

    timeout = arg_int(args, "timeout", 120, maximum=1800)
    command = [
        str(DG_AGENT),
        "plan",
        "--repo",
        repo,
        "--task",
        task,
        "--name",
        arg_str(args, "name", "edit"),
        "--max-files",
        str(arg_int(args, "max_files", 1, maximum=20)),
        "--max-snippet-chars",
        str(arg_int(args, "max_snippet_chars", 1200, maximum=20000)),
        "--test-timeout",
        str(arg_int(args, "test_timeout", 120, maximum=3600)),
        "--aider-timeout",
        str(arg_int(args, "aider_timeout", 420, maximum=7200)),
        "--repair-attempts",
        str(arg_int(args, "repair_attempts", 1, maximum=5)),
    ]
    for file_name in arg_files(args):
        command.extend(["--file", file_name])
    out = arg_str(args, "out", "")
    if out:
        command.extend(["--out", repo_output_path(repo, out)])
    test_cmd = arg_str(args, "test_cmd", "")
    if test_cmd:
        command.extend(["--test-cmd", test_cmd])
    if arg_bool(args, "auto_test", False):
        command.append("--auto-test")
    if arg_bool(args, "no_deterministic_first", False):
        command.append("--no-deterministic-first")

    result = run_cmd(command, timeout=timeout)
    structured = dict(result)
    if result["returncode"] == 0 and out:
        structured["plan_path"] = result.get("stdout", "").strip().splitlines()[-1] if result.get("stdout", "").strip() else repo_output_path(repo, out)
    elif result["returncode"] == 0:
        try:
            structured["plan"] = json.loads(result.get("stdout", ""))
        except Exception:
            pass
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=structured)


def tool_task(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    plan = arg_str(args, "plan", "")
    if not plan:
        return text_result("Missing required argument: plan", is_error=True)

    timeout = arg_int(args, "timeout", 900, maximum=7200)
    command = [str(DG_AGENT), "task", "--repo", repo, "--plan", repo_output_path(repo, plan)]
    report = arg_str(args, "report", "")
    if report:
        command.extend(["--report", repo_output_path(repo, report)])
    supervisor = arg_str(args, "supervisor", "")
    if supervisor:
        command.extend(["--supervisor", repo_output_path(repo, supervisor)])
    step_report_dir = arg_str(args, "step_report_dir", "")
    if step_report_dir:
        command.extend(["--step-report-dir", repo_output_path(repo, step_report_dir)])
    if arg_bool(args, "allow_dirty", False):
        command.append("--allow-dirty")
    if arg_bool(args, "dry_run", False):
        command.append("--dry-run")
    if arg_bool(args, "rollback_on_failure", True):
        command.append("--rollback-on-failure")
    if arg_bool(args, "continue_on_failure", False):
        command.append("--continue-on-failure")

    result = run_cmd(command, timeout=timeout + 60)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_verify(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    timeout = arg_int(args, "timeout", 120, maximum=1800)
    command = [str(DG_AGENT), "verify", "--repo", repo, "--timeout", str(timeout), "--json"]
    test_cmd = arg_str(args, "test_cmd", "")
    if test_cmd:
        command.extend(["--test-cmd", test_cmd])
    for file_name in arg_files(args):
        command.extend(["--file", file_name])
    result = run_cmd(command, timeout=timeout + 30)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def session_artifacts(stdout: str) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    patterns = {
        "session_dir": r"(?m)^Session dir:\s*(.+)$",
        "context": r"(?m)^Context:\s*(.+)$",
        "plan": r"(?m)^Plan:\s*(.+)$",
        "session_report": r"(?m)^Session report:\s*(.+)$",
        "aggregate_report": r"(?m)^Aggregate report:\s*(.+)$",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, stdout)
        if match:
            artifacts[key] = match.group(1).strip()
    return artifacts


def tool_session(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    task = arg_str(args, "task", "")
    if not task:
        return text_result("Missing required argument: task", is_error=True)

    wall_timeout = arg_int(args, "wall_timeout", 900, maximum=7200)
    command = [
        str(DG_AGENT),
        "session",
        "--repo",
        repo,
        "--task",
        task,
        "--max-files",
        str(arg_int(args, "max_files", 1, maximum=20)),
        "--max-snippet-chars",
        str(arg_int(args, "max_snippet_chars", 1200, maximum=20000)),
        "--test-timeout",
        str(arg_int(args, "test_timeout", 120, maximum=3600)),
        "--aider-timeout",
        str(arg_int(args, "aider_timeout", 420, maximum=7200)),
        "--repair-attempts",
        str(arg_int(args, "repair_attempts", 1, maximum=5)),
        "--wall-timeout",
        str(wall_timeout),
        "--rollback-on-failure",
    ]
    for file_name in arg_files(args):
        command.extend(["--file", file_name])
    test_cmd = arg_str(args, "test_cmd", "")
    if test_cmd:
        command.extend(["--test-cmd", test_cmd])
    if arg_bool(args, "auto_test", False):
        command.append("--auto-test")
    if arg_bool(args, "allow_dirty", False):
        command.append("--allow-dirty")
    if arg_bool(args, "dry_run", False):
        command.append("--dry-run")
    if arg_bool(args, "no_verify_after", False):
        command.append("--no-verify-after")

    result = run_cmd(command, timeout=wall_timeout + 60)
    artifacts = session_artifacts(result.get("stdout", ""))
    structured = {**result, "artifacts": artifacts}
    report = command_report(command, result)
    if artifacts:
        report += "\n\nartifacts:\n" + "\n".join(f"- {key}: {value}" for key, value in artifacts.items())
    return text_result(report, is_error=result["returncode"] != 0, structured=structured)


def tool_capabilities(args: dict[str, Any]) -> dict[str, Any]:
    timeout = arg_int(args, "timeout", 180, maximum=1800)
    command = [str(DG_AGENT), "capabilities", "--latest", "--json"]
    if arg_bool(args, "run_live", False):
        command = [str(DG_AGENT), "capabilities", "--live", "--json", "--timeout", str(timeout)]
    result = run_cmd(command, timeout=timeout + 60)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_client_smoke(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    client = arg_str(args, "client", "cursor")
    timeout = arg_int(args, "timeout", 180, maximum=1800)
    command = [str(DG_AGENT), "client-smoke", "--repo", repo, "--client", client, "--json"]
    target = arg_str(args, "target", "")
    if target:
        command.extend(["--target", target])
    if arg_bool(args, "force_init", False):
        command.append("--force-init")
    if arg_bool(args, "no_init", False):
        command.append("--no-init")
    if arg_bool(args, "no_rules", False):
        command.append("--no-rules")
    if arg_bool(args, "no_oss_stack", False):
        command.append("--no-oss-stack")
    if arg_bool(args, "live", False):
        command.append("--live")
    result = run_cmd(command, timeout=timeout + 60)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_client_report(args: dict[str, Any]) -> dict[str, Any]:
    repo = arg_str(args, "repo", ".")
    client = arg_str(args, "client", "cursor")
    timeout = arg_int(args, "timeout", 240, maximum=1800)
    command = [str(DG_AGENT), "client-report", "--repo", repo, "--client", client, "--json"]
    target = arg_str(args, "target", "")
    if target:
        command.extend(["--target", target])
    if arg_bool(args, "force_init", False):
        command.append("--force-init")
    if arg_bool(args, "no_init", False):
        command.append("--no-init")
    if arg_bool(args, "no_rules", False):
        command.append("--no-rules")
    if arg_bool(args, "no_oss_stack", False):
        command.append("--no-oss-stack")
    if arg_bool(args, "live", False):
        command.append("--live")
    if arg_bool(args, "no_write", False):
        command.append("--no-write")
    result = run_cmd(command, timeout=timeout + 60)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def agent_run_reports(root: Path = AGENT_RUN_ROOT) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if not root.exists():
        return reports
    for path in root.rglob("agent.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_agent_json"] = str(path)
            data["_mtime"] = path.stat().st_mtime
            reports.append(data)
        except Exception:
            continue
    reports.sort(key=lambda item: float(item.get("_mtime", 0)), reverse=True)
    return reports


def agent_run_summary(report: dict[str, Any]) -> dict[str, Any]:
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    transcript = Path(str(artifacts.get("transcript", "")))
    run_dir = str(report.get("run_dir") or "")
    return {
        "status": report.get("status"),
        "mode": report.get("mode"),
        "route": report.get("route"),
        "task": report.get("task"),
        "repo": report.get("repo"),
        "run_dir": run_dir,
        "run_id": Path(run_dir).name if run_dir else "",
        "agent_json": report.get("_agent_json") or artifacts.get("agent_json"),
        "returncode": report.get("returncode"),
        "elapsed_sec": report.get("elapsed_sec"),
        "steps": report.get("steps"),
        "tool_names": report.get("tool_names"),
        "transcript_bytes": transcript.stat().st_size if transcript.exists() else 0,
    }


def load_agent_run_report(run: str = "", latest: bool = False, root: Path = AGENT_RUN_ROOT) -> dict[str, Any] | None:
    reports = agent_run_reports(root)
    if latest or not run:
        return reports[0] if reports else None
    if run.isdigit():
        index = int(run) - 1
        if 0 <= index < len(reports):
            return reports[index]
    for report in reports:
        summary = agent_run_summary(report)
        if run in {str(summary.get("run_id") or ""), str(summary.get("run_dir") or ""), str(summary.get("agent_json") or "")}:
            return report
    path = Path(normalize_host_path(run))
    if path.is_dir():
        path = path / "agent.json"
    if not path.is_absolute():
        path = root / path
        if path.is_dir():
            path = path / "agent.json"
    if path.exists() and path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_agent_json"] = str(path)
            return data
        except Exception:
            return None
    return None


def agent_run_artifact_path(report: dict[str, Any], artifact: str) -> tuple[str, Path | None]:
    key = AGENT_RUN_ARTIFACT_ALIASES.get(artifact, artifact)
    if key not in AGENT_RUN_ARTIFACT_FILENAMES:
        return key, None
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    raw_path = normalize_host_path(str(artifacts.get(key) or ""))
    if not raw_path and key == "agent_json":
        raw_path = normalize_host_path(str(report.get("_agent_json") or ""))
    if not raw_path:
        run_dir = Path(normalize_host_path(str(report.get("run_dir") or "")))
        if run_dir:
            raw_path = str(run_dir / AGENT_RUN_ARTIFACT_FILENAMES[key])
    if not raw_path:
        return key, None
    path = Path(normalize_host_path(raw_path))
    run_dir_text = normalize_host_path(str(report.get("run_dir") or ""))
    if run_dir_text:
        run_dir = Path(run_dir_text).resolve()
        try:
            resolved = path.resolve()
        except Exception:
            return key, None
        if resolved != run_dir and run_dir not in resolved.parents:
            return key, None
    return key, path


def tool_agent_runs(args: dict[str, Any]) -> dict[str, Any]:
    limit = arg_int(args, "limit", 10, maximum=100)
    root_arg = arg_str(args, "root", "")
    root = Path(normalize_host_path(root_arg)) if root_arg else AGENT_RUN_ROOT
    reports = agent_run_reports(root)
    payload = {"ok": True, "root": str(root), "runs": [agent_run_summary(report) for report in reports[:limit]]}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return text_result(text, structured={"returncode": 0, "stdout": text, "stderr": "", **payload})


def tool_agent_run_artifact(args: dict[str, Any]) -> dict[str, Any]:
    artifact = arg_str(args, "artifact", "agent_json")
    run = arg_str(args, "run", "")
    latest = arg_bool(args, "latest", True)
    path_only = arg_bool(args, "path_only", False)
    limit = arg_int(args, "limit", 200_000, minimum=1_000, maximum=1_000_000)
    root_arg = arg_str(args, "root", "")
    root = Path(normalize_host_path(root_arg)) if root_arg else AGENT_RUN_ROOT
    report = load_agent_run_report(run=run, latest=latest or not run, root=root)
    if report is None:
        payload = {"ok": False, "error": f"agent run not found: {run or 'latest'}", "root": str(root)}
        return text_result(json.dumps(payload, ensure_ascii=False, indent=2), is_error=True, structured=payload)
    key, path = agent_run_artifact_path(report, artifact)
    if path is None:
        payload = {
            "ok": False,
            "error": f"unknown artifact: {artifact}",
            "available_artifacts": sorted(set(AGENT_RUN_ARTIFACT_FILENAMES) | set(AGENT_RUN_ARTIFACT_ALIASES)),
        }
        return text_result(json.dumps(payload, ensure_ascii=False, indent=2), is_error=True, structured=payload)
    if not path.exists():
        payload = {"ok": False, "error": f"artifact missing: {key}", "path": str(path)}
        return text_result(json.dumps(payload, ensure_ascii=False, indent=2), is_error=True, structured=payload)
    if path_only:
        payload = {"ok": True, "artifact": key, "path": str(path), "run": agent_run_summary(report)}
        return text_result(str(path), structured=payload)
    text = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > limit
    content = text[:limit]
    payload = {
        "ok": True,
        "artifact": key,
        "path": str(path),
        "bytes": path.stat().st_size,
        "truncated": truncated,
        "content": content,
        "run": agent_run_summary(report),
    }
    return text_result(content, structured=payload)


def tool_sessions(args: dict[str, Any]) -> dict[str, Any]:
    limit = arg_int(args, "limit", 10, maximum=100)
    timeout = arg_int(args, "timeout", 60, maximum=300)
    command = [str(DG_AGENT), "sessions", "list", "--limit", str(limit), "--json"]
    root = arg_str(args, "root", "")
    if root:
        command.extend(["--root", root])
    result = run_cmd(command, timeout=timeout)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


def tool_session_artifact(args: dict[str, Any]) -> dict[str, Any]:
    artifact = arg_str(args, "artifact", "session_json")
    session = arg_str(args, "session", "")
    timeout = arg_int(args, "timeout", 60, maximum=300)
    command = [str(DG_AGENT), "sessions", "artifact", artifact]
    if session:
        command.append(session)
    if arg_bool(args, "latest", True):
        command.append("--latest")
    if arg_bool(args, "path_only", False):
        command.append("--path-only")
    root = arg_str(args, "root", "")
    if root:
        command.extend(["--root", root])
    result = run_cmd(command, timeout=timeout)
    return text_result(command_report(command, result), is_error=result["returncode"] != 0, structured=result)


TOOLS = {
    "dg_task_note": {
        "description": "Write or append a durable Markdown task note under runlogs for MCP clients.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "body": {"type": "string"},
                "title": {"type": "string"},
                "repo": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "append_to": {"type": "string"},
            },
            "required": ["task", "body"],
        },
        "handler": tool_task_note,
    },
    "dg_task_notes": {
        "description": "List or read durable Markdown task notes saved by MCP clients.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note": {"type": "string"},
                "latest": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 20},
                "max_chars": {"type": "integer", "default": 20000},
            },
        },
        "handler": tool_task_notes,
    },
    "dg_repo_status": {
        "description": "Inspect git status, diff stat, and untracked files for a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "max_chars": {"type": "integer", "default": 8000},
                "timeout": {"type": "integer", "default": 30},
            },
        },
        "handler": tool_repo_status,
    },
    "dg_list_files": {
        "description": "List repository files using ripgrep or git fallback, with optional glob filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "pattern": {"type": "string"},
                "globs": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 200},
                "timeout": {"type": "integer", "default": 30},
            },
        },
        "handler": tool_list_files,
    },
    "dg_search": {
        "description": "Search a repository with ripgrep and return bounded line/column matches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "query": {"type": "string"},
                "globs": {"type": "array", "items": {"type": "string"}},
                "context": {"type": "integer", "default": 0},
                "max_matches": {"type": "integer", "default": 80},
                "max_chars": {"type": "integer", "default": 12000},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["query"],
        },
        "handler": tool_search,
    },
    "dg_read_file": {
        "description": "Read a bounded, line-numbered slice of a file inside a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "path": {"type": "string"},
                "start_line": {"type": "integer", "default": 1},
                "max_lines": {"type": "integer", "default": 160},
                "max_chars": {"type": "integer", "default": 20000},
            },
            "required": ["path"],
        },
        "handler": tool_read_file,
    },
    "dg_git_diff": {
        "description": "Read a bounded git diff or diff stat for a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "files": {"type": "array", "items": {"type": "string"}},
                "cached": {"type": "boolean", "default": False},
                "stat": {"type": "boolean", "default": False},
                "max_chars": {"type": "integer", "default": 20000},
                "timeout": {"type": "integer", "default": 30},
            },
        },
        "handler": tool_git_diff,
    },
    "dg_status": {
        "description": "Check local DiffusionGemma backend/proxy/LiteLLM health.",
        "inputSchema": {
            "type": "object",
            "properties": {"timeout": {"type": "integer", "minimum": 1, "maximum": 180}},
        },
        "handler": tool_status,
    },
    "dg_context": {
        "description": "Build a compact rg-based context pack for a repository task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "task": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "max_files": {"type": "integer", "default": 3},
                "max_snippet_chars": {"type": "integer", "default": 1200},
                "timeout": {"type": "integer", "default": 120},
            },
            "required": ["task"],
        },
        "handler": tool_context,
    },
    "dg_rag_context": {
        "description": "Retrieve a compact read-only RAG context for a repository task without calling the model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "task": {"type": "string"},
                "max_context_chars": {"type": "integer", "default": 900},
                "max_files": {"type": "integer", "default": 3},
                "debug": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 120},
            },
            "required": ["task"],
        },
        "handler": tool_rag_context,
    },
    "dg_rag_answer": {
        "description": "Ask the local model using a compact rg-retrieved repository context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "task": {"type": "string"},
                "base_url": {"type": "string"},
                "model": {"type": "string"},
                "max_context_chars": {"type": "integer", "default": 650},
                "max_files": {"type": "integer", "default": 3},
                "max_tokens": {"type": "integer", "default": 128},
                "debug": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 300},
            },
            "required": ["task"],
        },
        "handler": tool_rag_answer,
    },
    "dg_repo_pack": {
        "description": "Pack repository content with the upstream Repomix OSS tool and return bounded output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "style": {"type": "string", "default": "markdown"},
                "include": {"type": "array", "items": {"type": "string"}},
                "ignore": {"type": "array", "items": {"type": "string"}},
                "compress": {"type": "boolean", "default": False},
                "include_diffs": {"type": "boolean", "default": False},
                "output_show_line_numbers": {"type": "boolean", "default": False},
                "remove_comments": {"type": "boolean", "default": False},
                "remove_empty_lines": {"type": "boolean", "default": False},
                "no_files": {"type": "boolean", "default": False},
                "no_security_check": {"type": "boolean", "default": False},
                "token_budget": {"type": "integer", "default": 0},
                "top_files_len": {"type": "integer", "default": 5},
                "max_chars": {"type": "integer", "default": 20000},
                "timeout": {"type": "integer", "default": 180},
            },
        },
        "handler": tool_repo_pack,
    },
    "dg_repo_map": {
        "description": "Build a bounded upstream Aider repo-map for repository-scale code context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "map_tokens": {"type": "integer", "default": 512},
                "paths": {"type": "array", "items": {"type": "string"}},
                "map_only": {"type": "boolean", "default": True},
                "base_url": {"type": "string"},
                "model": {"type": "string"},
                "max_chars": {"type": "integer", "default": 20000},
                "timeout": {"type": "integer", "default": 180},
            },
        },
        "handler": tool_repo_map,
    },
    "dg_ast_grep": {
        "description": "Search repository code structurally with upstream ast-grep and bounded output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "pattern": {"type": "string", "description": "AST pattern, for example: return $X"},
                "kind": {"type": "string", "description": "Tree-sitter node kind or ESQuery-style kind selector"},
                "selector": {"type": "string"},
                "strictness": {"type": "string"},
                "lang": {"type": "string", "description": "Pattern language, for example python, ts, rust, go"},
                "context": {"type": "integer", "default": 0},
                "globs": {"type": "array", "items": {"type": "string"}},
                "paths": {"type": "array", "items": {"type": "string"}},
                "json": {"type": "boolean", "default": True},
                "files_with_matches": {"type": "boolean", "default": False},
                "max_matches": {"type": "integer", "default": 80},
                "max_chars": {"type": "integer", "default": 20000},
                "timeout": {"type": "integer", "default": 120},
            },
        },
        "handler": tool_ast_grep,
    },
    "dg_code_outline": {
        "description": "Build a bounded symbol outline with upstream ast-grep outline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "lang": {"type": "string", "description": "Input language, for example python, ts, rust, go"},
                "items": {"type": "string", "default": "auto"},
                "view": {"type": "string", "default": "auto"},
                "type": {"type": "string", "description": "Comma-separated symbol types to keep"},
                "match": {"type": "string", "description": "Regex matched against top-level item names/signatures"},
                "pub_members": {"type": "boolean", "default": False},
                "globs": {"type": "array", "items": {"type": "string"}},
                "paths": {"type": "array", "items": {"type": "string"}},
                "json": {"type": "boolean", "default": True},
                "max_items": {"type": "integer", "default": 200},
                "max_chars": {"type": "integer", "default": 20000},
                "timeout": {"type": "integer", "default": 120},
            },
        },
        "handler": tool_code_outline,
    },
    "dg_preflight": {
        "description": "Check whether a target repository and local DG wrapper stack are ready for agent work.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "task": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "allow_dirty": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 120},
            },
        },
        "handler": tool_preflight,
    },
    "dg_plan": {
        "description": "Generate a JSON task-runner plan from a natural-language repository task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "task": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "out": {"type": "string"},
                "name": {"type": "string", "default": "edit"},
                "test_cmd": {"type": "string"},
                "auto_test": {"type": "boolean", "default": False},
                "max_files": {"type": "integer", "default": 1},
                "max_snippet_chars": {"type": "integer", "default": 1200},
                "test_timeout": {"type": "integer", "default": 120},
                "aider_timeout": {"type": "integer", "default": 420},
                "repair_attempts": {"type": "integer", "default": 1},
                "no_deterministic_first": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 120},
            },
            "required": ["task"],
        },
        "handler": tool_plan,
    },
    "dg_task": {
        "description": "Execute an existing DG task-runner plan; use dry_run to inspect the command without editing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "plan": {"type": "string"},
                "report": {"type": "string"},
                "supervisor": {"type": "string"},
                "step_report_dir": {"type": "string"},
                "allow_dirty": {"type": "boolean", "default": False},
                "dry_run": {"type": "boolean", "default": False},
                "rollback_on_failure": {"type": "boolean", "default": True},
                "continue_on_failure": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 900},
            },
            "required": ["plan"],
        },
        "handler": tool_task,
    },
    "dg_session": {
        "description": "Run the artifacted local DG coding-agent session with rollback on failure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "task": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "test_cmd": {"type": "string"},
                "auto_test": {"type": "boolean", "default": False},
                "allow_dirty": {"type": "boolean", "default": False},
                "dry_run": {"type": "boolean", "default": False},
                "max_files": {"type": "integer", "default": 1},
                "max_snippet_chars": {"type": "integer", "default": 1200},
                "test_timeout": {"type": "integer", "default": 120},
                "aider_timeout": {"type": "integer", "default": 420},
                "repair_attempts": {"type": "integer", "default": 1},
                "wall_timeout": {"type": "integer", "default": 900},
            },
            "required": ["task"],
        },
        "handler": tool_session,
    },
    "dg_verify": {
        "description": "Run or infer a repository verification command.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "files": {"type": "array", "items": {"type": "string"}},
                "test_cmd": {"type": "string"},
                "timeout": {"type": "integer", "default": 120},
            },
        },
        "handler": tool_verify,
    },
    "dg_capabilities": {
        "description": "Read the latest DG wrapper capability report, or run a live capability probe.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_live": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 180},
            },
        },
        "handler": tool_capabilities,
    },
    "dg_client_smoke": {
        "description": "Prepare or validate a target repo for external IDE/agent clients.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "client": {"type": "string", "default": "cursor", "enum": ["claude-code", "claude-desktop", "cursor", "vscode"]},
                "target": {"type": "string"},
                "force_init": {"type": "boolean", "default": False},
                "no_init": {"type": "boolean", "default": False},
                "no_rules": {"type": "boolean", "default": False},
                "no_oss_stack": {"type": "boolean", "default": False},
                "live": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 180},
            },
        },
        "handler": tool_client_smoke,
    },
    "dg_client_report": {
        "description": "Generate repo-local Markdown/JSON handoff files for external clients.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": "."},
                "client": {"type": "string", "default": "cursor", "enum": ["claude-code", "claude-desktop", "cursor", "vscode"]},
                "target": {"type": "string"},
                "force_init": {"type": "boolean", "default": False},
                "no_init": {"type": "boolean", "default": False},
                "no_rules": {"type": "boolean", "default": False},
                "no_oss_stack": {"type": "boolean", "default": False},
                "live": {"type": "boolean", "default": False},
                "no_write": {"type": "boolean", "default": False},
                "timeout": {"type": "integer", "default": 240},
            },
        },
        "handler": tool_client_report,
    },
    "dg_sessions": {
        "description": "List recent artifacted DG agent sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
                "root": {"type": "string"},
                "timeout": {"type": "integer", "default": 60},
            },
        },
        "handler": tool_sessions,
    },
    "dg_session_artifact": {
        "description": "Read a preserved artifact from a DG agent session, defaulting to the latest session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "artifact": {"type": "string", "default": "session_json"},
                "session": {"type": "string"},
                "latest": {"type": "boolean", "default": True},
                "path_only": {"type": "boolean", "default": False},
                "root": {"type": "string"},
                "timeout": {"type": "integer", "default": 60},
            },
        },
        "handler": tool_session_artifact,
    },
    "dg_agent_runs": {
        "description": "List recent high-level dg_agent runs and their preserved artifacts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
                "root": {"type": "string"},
            },
        },
        "handler": tool_agent_runs,
    },
    "dg_agent_run_artifact": {
        "description": "Read a preserved artifact from a high-level dg_agent run, defaulting to the latest run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "artifact": {"type": "string", "default": "agent_json"},
                "run": {"type": "string"},
                "latest": {"type": "boolean", "default": True},
                "path_only": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 200000, "minimum": 1000, "maximum": 1000000},
                "root": {"type": "string"},
            },
        },
        "handler": tool_agent_run_artifact,
    },
}


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": meta["description"],
            "inputSchema": meta["inputSchema"],
        }
        for name, meta in TOOLS.items()
    ]


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    if "id" not in message:
        return None

    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    try:
        if method == "initialize":
            protocol = params.get("protocolVersion") or "2025-03-26"
            return rpc_response(
                request_id,
                {
                    "protocolVersion": protocol,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "diffusiongemma-local-agent", "version": "0.1.0"},
                },
            )
        if method == "tools/list":
            return rpc_response(request_id, {"tools": list_tools()})
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            if name not in TOOLS:
                return rpc_error(request_id, -32602, f"Unknown tool: {name}")
            handler = TOOLS[name]["handler"]
            return rpc_response(request_id, handler(arguments))
        if method == "ping":
            return rpc_response(request_id, {})
        return rpc_error(request_id, -32601, f"Method not found: {method}")
    except Exception as exc:
        log(f"request failed: {type(exc).__name__}: {exc}")
        return rpc_error(request_id, -32000, f"{type(exc).__name__}: {exc}")


def serve() -> int:
    log("started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            log(f"invalid JSON line: {exc}")
            continue
        messages = message if isinstance(message, list) else [message]
        responses: list[dict[str, Any]] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            response = handle_request(item)
            if response is not None:
                responses.append(response)
        if isinstance(message, list):
            if responses:
                emit(responses)
        elif responses:
            emit(responses[0])
    log("stopped")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP stdio server exposing local DiffusionGemma agent tools.")
    parser.add_argument("--stdio", action="store_true", help="Run stdio MCP server (default)")
    parser.add_argument("--list-tools", action="store_true", help="Print tool list JSON and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_tools:
        print(json.dumps({"tools": list_tools()}, ensure_ascii=False, indent=2))
        return 0
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
