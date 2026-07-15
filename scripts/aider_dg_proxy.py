#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import shlex
import subprocess
import textwrap
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
    FASTAPI_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - used only by static smoke fallback
    FASTAPI_IMPORT_ERROR = exc

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any):
            super().__init__(str(detail))
            self.status_code = status_code
            self.detail = detail

    def Header(default: Any = None) -> Any:
        return default

    class JSONResponse(dict):
        pass

    class StreamingResponse:
        def __init__(self, *args: Any, **kwargs: Any):
            self.args = args
            self.kwargs = kwargs

    class FastAPI:
        def __init__(self, *args: Any, **kwargs: Any):
            self.args = args
            self.kwargs = kwargs

        def get(self, *args: Any, **kwargs: Any):
            def decorator(func: Any) -> Any:
                return func

            return decorator

        def post(self, *args: Any, **kwargs: Any):
            def decorator(func: Any) -> Any:
                return func

            return decorator

    uvicorn = None


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION_ROOT = DG_ROOT / "runlogs" / "dg-agent-sessions"
DEFAULT_AGENT_RUN_ROOT = DG_ROOT / "runlogs" / "dg-agent-runs"
HOST = os.getenv("DG_AIDER_PROXY_HOST", "127.0.0.1")
PORT = int(os.getenv("DG_AIDER_PROXY_PORT", "8090"))
BACKEND_BASE = os.getenv("DG_AIDER_BACKEND_BASE", "http://127.0.0.1:4100/v1").rstrip("/")
BACKEND_MODEL = os.getenv("DG_AIDER_BACKEND_MODEL", "diffusiongemma-26b-a4b-it-iq3m-fullgpu")
PROXY_MODEL = os.getenv("DG_AIDER_PROXY_MODEL", "diffusiongemma-26b-a4b-it-iq4xs-aider-local")
MAX_OUTPUT_TOKENS = int(os.getenv("DG_AIDER_PROXY_MAX_OUTPUT_TOKENS", "256"))
MAX_FILE_CHARS = int(os.getenv("DG_AIDER_PROXY_MAX_FILE_CHARS", "2200"))
REQUEST_TIMEOUT = int(os.getenv("DG_AIDER_PROXY_REQUEST_TIMEOUT", "300"))
TRACE_PATH = os.getenv("DG_AIDER_PROXY_TRACE_PATH", "runlogs/aider_proxy.trace.jsonl")
BACKEND_RETRIES = int(os.getenv("DG_AIDER_PROXY_BACKEND_RETRIES", "3"))
ENABLE_GENERIC_GENERATION = int(os.getenv("DG_AIDER_PROXY_ENABLE_GENERIC_GENERATION", "0"))
ENABLE_AGENT_EXEC = int(os.getenv("DG_AIDER_PROXY_ENABLE_AGENT_EXEC", "0"))
AGENT_EXEC_TIMEOUT = int(os.getenv("DG_AIDER_PROXY_AGENT_EXEC_TIMEOUT", "900"))
AGENT_CONTEXT_TIMEOUT = int(os.getenv("DG_AIDER_PROXY_AGENT_CONTEXT_TIMEOUT", "120"))
AGENT_CONTEXT_OUTPUT_LIMIT = int(os.getenv("DG_AIDER_PROXY_AGENT_CONTEXT_OUTPUT_LIMIT", "200000"))

app = FastAPI(title="DiffusionGemma Aider Compatibility Proxy")

SESSION_ARTIFACT_FILENAMES = {
    "context_md": "context.md",
    "context_json": "context.json",
    "plan": "plan.json",
    "task_report": "task-report.json",
    "verify_report": "verify.json",
    "final_diff": "final.diff",
    "before_status": "before.status.txt",
    "after_status": "after.status.txt",
    "before_diff": "before.diff",
    "task_stdout": "task.stdout.log",
    "task_stderr": "task.stderr.log",
    "session_json": "session.json",
}
SESSION_ARTIFACT_ALIASES = {
    "diff": "final_diff",
    "final": "final_diff",
    "stdout": "task_stdout",
    "stderr": "task_stderr",
    "context": "context_md",
    "report": "session_json",
}
AGENT_RUN_ARTIFACT_FILENAMES = {
    "agent_json": "agent.json",
    "transcript": "tool-loop.json",
    "stdout": "stdout.log",
    "stderr": "stderr.log",
}
AGENT_RUN_ARTIFACT_ALIASES = {
    "agent": "agent_json",
    "report": "agent_json",
    "json": "agent_json",
    "tool_loop": "transcript",
    "tool-loop": "transcript",
    "tool-loop.json": "transcript",
    "stdout.log": "stdout",
    "stderr.log": "stderr",
}
REPO_TOOL_NAMES = [
    "dg_repo_status",
    "dg_git_diff",
    "dg_list_files",
    "dg_read_file",
    "dg_search",
]
OSS_REPO_TOOL_NAMES = [
    "dg_repo_pack",
    "dg_repo_map",
    "dg_ast_grep",
    "dg_code_outline",
]
HTTP_TOOL_NAMES = [
    "execute_command",
    *REPO_TOOL_NAMES,
    *OSS_REPO_TOOL_NAMES,
    "dg_agent",
    "dg_agent_run_artifact",
    "dg_session",
    "dg_context",
    "dg_rag_context",
    "dg_session_artifact",
]


def windows_bash() -> str | None:
    if os.name != "nt":
        return None
    candidates = [
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("bash")
    if found and "WindowsApps" not in found:
        return found
    return None


def adapt_subprocess_cmd(cmd: list[str]) -> list[str]:
    if os.name != "nt" or not cmd:
        return cmd
    first = cmd[0].lower()
    if first.endswith(".sh"):
        bash = windows_bash()
        if bash:
            return [bash, *cmd]
    return cmd

WINDOWS_DRIVE_PATH = re.compile(r"^([A-Za-z]):[\\\\/](.*)$")


def normalize_host_path(value: str) -> str:
    """Map a Windows path from an IDE client to its WSL mount when needed."""
    raw = str(value or "").strip()
    if os.name == "nt":
        return raw
    match = WINDOWS_DRIVE_PATH.match(raw)
    if not match:
        return raw
    drive, tail = match.groups()
    return f"/mnt/{drive.lower()}/{tail.replace(chr(92), '/')}"


def message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content or "")


def parse_added_files(messages: list[dict[str, Any]]) -> dict[str, str]:
    files: dict[str, str] = {}
    listing = re.compile(r"(?m)^([^\n`][^\n]*?)\n```[^\n]*\n(.*?)\n```", re.S)
    for message in messages:
        if message.get("role") != "user":
            continue
        text = message_text(message)
        if "Trust this message as the true contents" not in text and "added these files" not in text:
            continue
        for match in listing.finditer(text):
            path = match.group(1).strip()
            if not path or path.startswith("*") or path.lower().startswith("user "):
                continue
            if any(ch in path for ch in "\r\n`"):
                continue
            files[path] = match.group(2)
    return files


def latest_task(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        text = message_text(message).strip()
        if not text:
            continue
        if "Trust this message as the true contents" in text or "added these files" in text:
            continue
        if "switched to a new code base" in text:
            continue
        for marker in (
            "\nTo suggest changes to a file you MUST",
            "\nYou MUST use this *file listing* format:",
            "\nEvery *file listing* MUST use this format:",
        ):
            if marker in text:
                text = text.split(marker, 1)[0].strip()
        return text
    return ""


def qwen_user_task(messages: list[dict[str, Any]]) -> str:
    """Ignore Qwen Code's synthetic managed-memory prompts."""
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        text = message_text(message).strip()
        if text.startswith("Managed memory has TWO directories."):
            continue
        while text.startswith("<system-reminder>"):
            end = text.find("</system-reminder>")
            if end < 0:
                text = ""
                break
            text = text[end + len("</system-reminder>") :].strip()
        if not text:
            continue
        return text
    return ""


def trace_event(event: dict[str, Any]) -> None:
    if not TRACE_PATH:
        return
    try:
        path = Path(TRACE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {"ts": time.time(), **event}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def language_for(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".ps1": "powershell",
        ".sh": "bash",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".md": "markdown",
        ".rs": "rust",
        ".go": "go",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
    }.get(suffix, "")


def compact_aider_prompt(messages: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, str]]:
    files = parse_added_files(messages)
    task = latest_task(messages)
    if not files or not task:
        return [], files

    too_large = {path: len(content) for path, content in files.items() if len(content) > MAX_FILE_CHARS}
    if too_large:
        detail = ", ".join(f"{path}={chars} chars" for path, chars in too_large.items())
        raise HTTPException(
            status_code=413,
            detail=(
                "Aider file context is too large for the fast DiffusionGemma profile. "
                f"Limit is {MAX_FILE_CHARS} chars per file; got {detail}. "
                "Pass a smaller file or split the task."
            ),
        )

    if len(files) == 1:
        path, content = next(iter(files.items()))
        lang = language_for(path)
        system = (
            "Produce one code block with the complete updated file content. "
            "Do not add helper examples or extra files."
        )
        user = (
            f"Original {path}:\n"
            f"```{lang}\n{content}\n```\n"
            f"Task: {task}\n"
            "Return the complete updated file content in one code block."
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}], files

    file_sections: list[str] = []
    for path, content in files.items():
        lang = language_for(path)
        file_sections.append(f"{path}\n```{lang}\n{content}\n```")

    system = (
        "You are a code editing engine. Modify the supplied files to satisfy the task. "
        "Return only complete updated file listings for changed files. "
        "Do not write thought, analysis, plan, bullets, explanations, or markdown outside file listings. "
        "A file listing is exactly: filename line, opening code fence, complete file content, closing code fence."
    )
    user = (
        "Task:\n"
        f"{task}\n\n"
        "Files:\n"
        + "\n\n".join(file_sections)
        + "\n\nReturn only changed file listings."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}], files


def call_backend(messages: list[dict[str, str]], body: dict[str, Any]) -> str:
    payload = {
        "model": BACKEND_MODEL,
        "messages": messages,
        "max_tokens": int(body.get("max_tokens") or MAX_OUTPUT_TOKENS),
        "n_blocks": int(body.get("n_blocks") or 1),
        "dg_raw_output": True,
    }
    req = urllib.request.Request(
        f"{BACKEND_BASE}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-DG-Raw-Output": "1"},
    )
    last_error = ""
    for attempt in range(1, max(1, BACKEND_RETRIES) + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                return sanitize_backend_text(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"backend HTTP {exc.code}: {detail}"
            trace_event({"kind": "backend_error", "attempt": attempt, "error": last_error})
            if attempt >= BACKEND_RETRIES:
                raise HTTPException(status_code=502, detail=last_error) from exc
            time.sleep(0.25 * attempt)
        except Exception as exc:
            last_error = f"backend request failed: {exc}"
            trace_event({"kind": "backend_error", "attempt": attempt, "error": last_error})
            if attempt >= BACKEND_RETRIES:
                raise HTTPException(status_code=502, detail=last_error) from exc
            time.sleep(0.25 * attempt)
    raise HTTPException(status_code=502, detail=last_error or "backend request failed")


def sanitize_backend_text(raw: str) -> str:
    """Strip DiffusionGemma chat-channel leakage before exposing OpenAI output."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return text

    text = re.sub(r"(?im)^\s*<\|channel\>\s*(thought|analysis)\s*\n?", "", text)
    text = re.sub(r"(?im)^\s*<\|channel\>\s*(final|answer)\s*\n?", "", text)
    text = re.sub(r"<\|/?(?:channel|message|turn|start|end)[^>]*\>", "", text)

    final_match = re.search(r"(?ims)(?:^|\n)\s*(?:final|answer)\s*:\s*(.+)$", text)
    if final_match:
        text = final_match.group(1).strip()

    return text.strip()


def compact_generic_prompt(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    selected = ""
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        text = message_text(message).strip()
        if text:
            selected = text
            break
    if not selected:
        for message in reversed(messages):
            text = message_text(message).strip()
            if text:
                selected = text
                break

    selected = re.sub(r"\n{3,}", "\n\n", selected or "Reply with OK.")
    if len(selected) > 420:
        selected = selected[:420] + "\n...[truncated]"

    system = (
        "Answer directly and concisely. Tools are unavailable in this compatibility mode."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": selected}]


def safe_generic_response(messages: list[dict[str, Any]], had_tools: bool, stream: bool) -> str:
    task = latest_task(messages)
    if not task:
        for message in reversed(messages):
            if message.get("role") == "user":
                task = message_text(message).strip()
                if task:
                    break
    hint = " The request included tool schemas; native tool-calling is disabled in this safe compatibility mode." if had_tools else ""
    return (
        "Local DiffusionGemma gateway is reachable through the OpenAI-compatible API. "
        "Generic free-form chat is disabled in safe mode because this backend can crash on arbitrary non-Aider prompts. "
        "Use scripts/dg_agent.sh session/task for reliable repository edits, or set "
        "DG_AIDER_PROXY_ENABLE_GENERIC_GENERATION=1 to experiment with unsafe generic generation."
        f"{hint}"
    )


def is_mini_swe_request(messages: list[dict[str, Any]]) -> bool:
    joined = "\n".join(message_text(message) for message in messages[-8:])
    return "mswea_bash_command" in joined or "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in joined


def mini_swe_task(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        text = message_text(message).strip()
        match = re.search(r"(?is)Please solve this issue:\s*(.*?)(?:\n\nUse short bash commands\.|\Z)", text)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return latest_task(messages)


def mini_swe_action_block(command: str) -> str:
    return "```mswea_bash_command\n" + command.strip() + "\n```"


def safe_mini_swe_response(messages: list[dict[str, Any]]) -> str | None:
    if not is_mini_swe_request(messages):
        return None

    assistant_text = "\n".join(message_text(message) for message in messages if message.get("role") == "assistant")
    if ("dg_agent.sh" in assistant_text and "session" in assistant_text) or "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in assistant_text:
        return mini_swe_action_block("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")

    task = mini_swe_task(messages)
    if not task:
        return mini_swe_action_block("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")

    return mini_swe_action_block(build_session_command(task))


def build_session_command(task: str) -> str:
    if len(task) > 1200:
        task = task[:1200] + " ...[truncated]"
    return " ".join(
        [
            shlex.quote(str(DG_ROOT / "scripts" / "dg_agent.sh")),
            "session",
            "--repo",
            '"$(pwd)"',
            "--task",
            shlex.quote(task),
            "--allow-dirty",
            "--wall-timeout",
            "420",
            "--aider-timeout",
            "300",
            "--repair-attempts",
            "1",
            "--rollback-on-failure",
        ]
    )


def task_requests_edit(task: str) -> bool:
    task_lower = task.lower()
    # Tool-routing prompts often include a guard such as "do not edit". Remove
    # those negated verbs before classifying the task so a read-only request
    # cannot be sent to the mutation path merely because it names "edit".
    task_lower = re.sub(
        r"\b(?:do\s+not|don't|dont|without|never)\s+(?:\w+\s+){0,2}"
        r"(?:edit|fix|change|update|implement|modify|patch|repair)\b",
        "",
        task_lower,
    )
    return any(
        word in task_lower
        for word in ("edit", "fix", "change", "update", "implement", "modify", "patch", "repair")
    )


def wsl_path_to_windows(value: Path) -> str:
    text = str(value)
    match = re.match(r"^/mnt/([A-Za-z])/(.*)$", text)
    if not match:
        return text
    drive, tail = match.groups()
    windows_tail = tail.replace("/", "\\")
    return f"{drive.upper()}:\\{windows_tail}"


def build_windows_opencode_command(task: str) -> str:
    mode = "edit" if task_requests_edit(task) else "read"
    encoded_task = base64.b64encode(task.encode("utf-8")).decode("ascii")
    bridge = wsl_path_to_windows(DG_ROOT / "scripts" / "run_dg_delegate_windows.ps1")
    quoted_bridge = f'"{bridge}"'
    return " ".join(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            quoted_bridge,
            "-Mode",
            mode,
            "-TaskBase64",
            encoded_task,
        ]
    )


def is_windows_opencode_client(authorization: str | None) -> bool:
    return "dg-opencode-windows" in str(authorization or "").lower()


def is_windows_qwen_client(authorization: str | None) -> bool:
    return "dg-qwen-windows" in str(authorization or "").lower()


def qwen_repo_from_authorization(authorization: str | None) -> str:
    match = re.search(r"dg-qwen-windows\.([A-Za-z0-9_-]+)", str(authorization or ""), flags=re.I)
    if not match:
        return ""
    token = match.group(1).replace("-", "+").replace("_", "/")
    try:
        return base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
    except Exception:
        return ""


def command_tool_parameters() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to run in the current repository.",
            }
        },
        "required": ["command"],
        "additionalProperties": False,
    }


def command_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Run a bounded local command. The DG gateway delegates repo work to dg_agent.sh session with rollback-on-failure.",
            "parameters": command_tool_parameters(),
        },
    }


def responses_command_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "execute_command",
        "description": "Run a bounded local command. The DG gateway delegates repo work to dg_agent.sh session with rollback-on-failure.",
        "parameters": command_tool_parameters(),
    }


def chat_function_tool_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def responses_function_tool_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": parameters,
    }


def agent_session_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "task": {"type": "string", "description": "Natural-language repository task."},
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional file hints passed as repeated --file arguments.",
            },
            "test_cmd": {"type": "string", "description": "Optional deterministic verification command."},
            "auto_test": {"type": "boolean", "default": False},
            "allow_dirty": {"type": "boolean", "default": True},
            "rollback_on_failure": {"type": "boolean", "default": True},
            "dry_run": {"type": "boolean", "default": True},
            "execute": {
                "type": "boolean",
                "default": False,
                "description": "Actually run the session. Requires DG_AIDER_PROXY_ENABLE_AGENT_EXEC=1.",
            },
            "wall_timeout": {"type": "integer", "default": 420, "minimum": 30, "maximum": 3600},
            "aider_timeout": {"type": "integer", "default": 300, "minimum": 30, "maximum": 1800},
            "repair_attempts": {"type": "integer", "default": 1, "minimum": 0, "maximum": 5},
            "max_files": {"type": "integer", "default": 1, "minimum": 1, "maximum": 8},
            "max_snippet_chars": {"type": "integer", "default": 1200, "minimum": 200, "maximum": 8000},
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def session_artifact_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "session": {
                "type": "string",
                "default": "latest",
                "description": "Session id, 1-based list index, session path, or latest.",
            },
            "artifact": {
                "type": "string",
                "enum": sorted(set(SESSION_ARTIFACT_FILENAMES) | set(SESSION_ARTIFACT_ALIASES)),
                "default": "final_diff",
            },
            "limit": {"type": "integer", "default": 200000, "minimum": 1000, "maximum": 1000000},
        },
        "required": ["artifact"],
        "additionalProperties": False,
    }


def agent_run_artifact_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "run": {
                "type": "string",
                "default": "latest",
                "description": "Run id, 1-based list index, run path, or latest.",
            },
            "artifact": {
                "type": "string",
                "enum": sorted(set(AGENT_RUN_ARTIFACT_FILENAMES) | set(AGENT_RUN_ARTIFACT_ALIASES)),
                "default": "agent_json",
            },
            "limit": {"type": "integer", "default": 200000, "minimum": 1000, "maximum": 1000000},
        },
        "required": ["artifact"],
        "additionalProperties": False,
    }


def repo_status_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "max_chars": {"type": "integer", "default": 8000, "minimum": 1000, "maximum": 100000},
            "timeout": {"type": "integer", "default": 30, "minimum": 1, "maximum": 180},
        },
        "additionalProperties": False,
    }


def git_diff_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "files": {"type": "array", "items": {"type": "string"}, "description": "Optional paths inside the repo."},
            "cached": {"type": "boolean", "default": False},
            "stat": {"type": "boolean", "default": False},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1000, "maximum": 200000},
            "timeout": {"type": "integer", "default": 30, "minimum": 1, "maximum": 180},
        },
        "additionalProperties": False,
    }


def list_files_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "pattern": {"type": "string", "description": "Optional case-insensitive substring filter."},
            "globs": {"type": "array", "items": {"type": "string"}, "description": "Optional ripgrep -g glob filters."},
            "limit": {"type": "integer", "default": 200, "minimum": 1, "maximum": 5000},
            "timeout": {"type": "integer", "default": 30, "minimum": 1, "maximum": 180},
        },
        "additionalProperties": False,
    }


def read_file_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "path": {"type": "string", "description": "Path inside the repository."},
            "start_line": {"type": "integer", "default": 1, "minimum": 1},
            "max_lines": {"type": "integer", "default": 160, "minimum": 1, "maximum": 5000},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1000, "maximum": 200000},
        },
        "required": ["path"],
        "additionalProperties": False,
    }


def search_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "query": {"type": "string", "description": "Ripgrep search pattern."},
            "globs": {"type": "array", "items": {"type": "string"}, "description": "Optional ripgrep -g glob filters."},
            "context": {"type": "integer", "default": 0, "minimum": 0, "maximum": 5},
            "max_matches": {"type": "integer", "default": 80, "minimum": 1, "maximum": 1000},
            "max_chars": {"type": "integer", "default": 12000, "minimum": 1000, "maximum": 200000},
            "timeout": {"type": "integer", "default": 30, "minimum": 1, "maximum": 180},
        },
        "required": ["query"],
        "additionalProperties": False,
    }


def repo_pack_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "style": {"type": "string", "enum": ["xml", "markdown", "json", "plain"], "default": "markdown"},
            "include": {"type": "array", "items": {"type": "string"}, "description": "Repomix include globs."},
            "ignore": {"type": "array", "items": {"type": "string"}, "description": "Repomix ignore globs."},
            "compress": {"type": "boolean", "default": False},
            "include_diffs": {"type": "boolean", "default": False},
            "output_show_line_numbers": {"type": "boolean", "default": False},
            "remove_comments": {"type": "boolean", "default": False},
            "remove_empty_lines": {"type": "boolean", "default": False},
            "no_files": {"type": "boolean", "default": False},
            "no_security_check": {"type": "boolean", "default": False},
            "token_budget": {"type": "integer", "default": 0, "minimum": 0, "maximum": 2000000},
            "top_files_len": {"type": "integer", "default": 5, "minimum": 0, "maximum": 50},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1000, "maximum": 200000},
            "timeout": {"type": "integer", "default": 180, "minimum": 1, "maximum": 1800},
        },
        "additionalProperties": False,
    }


def repo_map_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "paths": {"type": "array", "items": {"type": "string"}, "description": "Optional repo-relative paths."},
            "map_tokens": {"type": "integer", "default": 2048, "minimum": 128, "maximum": 64000},
            "map_only": {"type": "boolean", "default": True},
            "base_url": {"type": "string"},
            "model": {"type": "string"},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1000, "maximum": 200000},
            "timeout": {"type": "integer", "default": 180, "minimum": 1, "maximum": 1800},
        },
        "additionalProperties": False,
    }


def ast_grep_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "pattern": {"type": "string", "description": "AST pattern, for example: return $X"},
            "kind": {"type": "string", "description": "Tree-sitter node kind or ESQuery-style selector."},
            "selector": {"type": "string", "description": "Sub-syntax node kind to extract from the pattern."},
            "lang": {"type": "string", "description": "Pattern language, for example python, ts, rust, go."},
            "strictness": {"type": "string", "enum": ["", "cst", "smart", "ast", "relaxed", "signature", "template"], "default": ""},
            "context": {"type": "integer", "default": 0, "minimum": 0, "maximum": 20},
            "globs": {"type": "array", "items": {"type": "string"}},
            "paths": {"type": "array", "items": {"type": "string"}},
            "json": {"type": "boolean", "default": True},
            "files_with_matches": {"type": "boolean", "default": False},
            "max_matches": {"type": "integer", "default": 80, "minimum": 1, "maximum": 1000},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1000, "maximum": 200000},
            "timeout": {"type": "integer", "default": 120, "minimum": 1, "maximum": 1800},
        },
        "additionalProperties": False,
    }


def code_outline_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "lang": {"type": "string", "description": "Input language, for example python, ts, rust, go."},
            "items": {"type": "string", "enum": ["auto", "structure", "exports", "imports", "all"], "default": "auto"},
            "view": {"type": "string", "enum": ["auto", "names", "signatures", "digest", "expanded"], "default": "auto"},
            "type": {"type": "string", "description": "Comma-separated symbol types, e.g. class,function."},
            "match": {"type": "string", "description": "Regex matched against top-level item names/signatures."},
            "pub_members": {"type": "boolean", "default": False},
            "globs": {"type": "array", "items": {"type": "string"}},
            "paths": {"type": "array", "items": {"type": "string"}},
            "json": {"type": "boolean", "default": True},
            "max_items": {"type": "integer", "default": 200, "minimum": 1, "maximum": 5000},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1000, "maximum": 200000},
            "timeout": {"type": "integer", "default": 120, "minimum": 1, "maximum": 1800},
        },
        "additionalProperties": False,
    }


def agent_facade_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "task": {"type": "string", "description": "Natural-language repository task or question."},
            "mode": {"type": "string", "enum": ["auto", "read", "edit"], "default": "auto"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "Editable/read file hints."},
            "execute": {
                "type": "boolean",
                "default": False,
                "description": "Actually run edit mode. Read mode always runs because it is read-only.",
            },
            "dry_run": {"type": "boolean", "default": True},
            "allow_dirty": {"type": "boolean", "default": True},
            "rollback_on_failure": {"type": "boolean", "default": True},
            "auto_test": {"type": "boolean", "default": False},
            "test_cmd": {"type": "string"},
            "max_files": {"type": "integer", "default": 3, "minimum": 1, "maximum": 20},
            "max_snippet_chars": {"type": "integer", "default": 1200, "minimum": 200, "maximum": 20000},
            "test_timeout": {"type": "integer", "default": 120, "minimum": 10, "maximum": 3600},
            "aider_timeout": {"type": "integer", "default": 420, "minimum": 30, "maximum": 7200},
            "repair_attempts": {"type": "integer", "default": 1, "minimum": 0, "maximum": 5},
            "wall_timeout": {"type": "integer", "default": 900, "minimum": 30, "maximum": 7200},
            "base_url": {"type": "string", "default": "http://127.0.0.1:4100/v1"},
            "model": {"type": "string", "default": "diffusiongemma-local"},
            "tool_manifest_url": {"type": "string", "default": "http://127.0.0.1:8090/v1/agent/tool_manifest"},
            "tool_runtime_url": {"type": "string", "default": "http://127.0.0.1:8090/v1/agent/tool"},
            "max_steps": {"type": "integer", "default": 2, "minimum": 1, "maximum": 8},
            "max_tokens": {"type": "integer", "default": 256, "minimum": 16, "maximum": 1024},
            "temperature": {"type": "number", "default": 0.0, "minimum": 0.0, "maximum": 2.0},
            "timeout": {"type": "integer", "default": 120, "minimum": 5, "maximum": 1800},
            "tools": {"type": "array", "items": {"type": "string"}, "description": "Optional tool-loop --tool filters for read mode."},
            "exclude_tools": {"type": "array", "items": {"type": "string"}, "description": "Optional tool-loop --exclude-tool filters for read mode."},
            "stop_after_tool": {"type": "boolean", "default": False},
            "max_chars": {"type": "integer", "default": 200000, "minimum": 1000, "maximum": 1000000},
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def agent_tool_runtime_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "enum": HTTP_TOOL_NAMES,
            },
            "arguments": {
                "type": ["object", "string"],
                "description": "Tool arguments as a JSON object or JSON string.",
            },
            "tool_call": {
                "type": "object",
                "description": "Optional OpenAI tool_call object with id and function{name,arguments}.",
            },
            "tool_call_id": {
                "type": "string",
                "description": "Optional tool call id used to build a tool response payload.",
            },
        },
        "additionalProperties": False,
    }


def agent_context_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "task": {"type": "string", "description": "Natural-language repository task or question."},
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional file hints passed as repeated --file arguments.",
            },
            "format": {"type": "string", "enum": ["json", "markdown"], "default": "json"},
            "max_files": {"type": "integer", "default": 3, "minimum": 1, "maximum": 20},
            "max_snippet_chars": {"type": "integer", "default": 1200, "minimum": 200, "maximum": 20000},
            "timeout": {"type": "integer", "default": 120, "minimum": 5, "maximum": 600},
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def agent_rag_context_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Target repository path.", "default": "."},
            "task": {"type": "string", "description": "Natural-language repository task or question."},
            "max_context_chars": {"type": "integer", "default": 900, "minimum": 200, "maximum": 20000},
            "max_files": {"type": "integer", "default": 3, "minimum": 1, "maximum": 20},
            "max_tokens": {
                "type": "integer",
                "default": 128,
                "minimum": 16,
                "maximum": 512,
                "description": "Forwarded for CLI compatibility; retrieve-only mode does not call the model.",
            },
            "debug": {"type": "boolean", "default": False},
            "timeout": {"type": "integer", "default": 120, "minimum": 5, "maximum": 600},
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def chat_dg_tool_schemas() -> list[dict[str, Any]]:
    return [
        command_tool_schema(),
        chat_function_tool_schema(
            "dg_repo_status",
            "Inspect git status, diff stat, and untracked files for a repository.",
            repo_status_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_git_diff",
            "Read a bounded git diff or diff stat for a repository.",
            git_diff_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_list_files",
            "List repository files using ripgrep or git fallback, with optional glob filters.",
            list_files_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_read_file",
            "Read a bounded, line-numbered slice of a file inside a repository.",
            read_file_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_search",
            "Search a repository with ripgrep and return bounded line/column matches.",
            search_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_repo_pack",
            "Pack repository context with upstream Repomix and return bounded output.",
            repo_pack_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_repo_map",
            "Build an upstream Aider repo-map with bounded output.",
            repo_map_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_ast_grep",
            "Run upstream ast-grep structural search over a repository.",
            ast_grep_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_code_outline",
            "Run upstream ast-grep code outline to summarize repository symbols.",
            code_outline_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_agent",
            "High-level local agent facade. Auto-routes read-only inspection to tool-loop and edits to artifacted sessions.",
            agent_facade_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_agent_run_artifact",
            "Read latest or indexed high-level dg_agent run artifacts such as agent_json, transcript, stdout, or stderr.",
            agent_run_artifact_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_session",
            "Build or run an artifacted dg_agent.sh coding session with rollback-on-failure. Default mode is dry-run.",
            agent_session_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_context",
            "Build a compact rg-based repository context pack without MCP.",
            agent_context_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_rag_context",
            "Retrieve compact read-only RAG context for a repository task without calling the model.",
            agent_rag_context_input_schema(),
        ),
        chat_function_tool_schema(
            "dg_session_artifact",
            "Read latest or indexed dg_agent.sh session artifacts such as final_diff, context_md, stdout, or stderr.",
            session_artifact_input_schema(),
        ),
    ]


def responses_dg_tool_schemas() -> list[dict[str, Any]]:
    return [
        responses_command_tool_schema(),
        responses_function_tool_schema(
            "dg_repo_status",
            "Inspect git status, diff stat, and untracked files for a repository.",
            repo_status_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_git_diff",
            "Read a bounded git diff or diff stat for a repository.",
            git_diff_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_list_files",
            "List repository files using ripgrep or git fallback, with optional glob filters.",
            list_files_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_read_file",
            "Read a bounded, line-numbered slice of a file inside a repository.",
            read_file_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_search",
            "Search a repository with ripgrep and return bounded line/column matches.",
            search_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_repo_pack",
            "Pack repository context with upstream Repomix and return bounded output.",
            repo_pack_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_repo_map",
            "Build an upstream Aider repo-map with bounded output.",
            repo_map_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_ast_grep",
            "Run upstream ast-grep structural search over a repository.",
            ast_grep_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_code_outline",
            "Run upstream ast-grep code outline to summarize repository symbols.",
            code_outline_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_agent",
            "High-level local agent facade. Auto-routes read-only inspection to tool-loop and edits to artifacted sessions.",
            agent_facade_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_agent_run_artifact",
            "Read latest or indexed high-level dg_agent run artifacts such as agent_json, transcript, stdout, or stderr.",
            agent_run_artifact_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_session",
            "Build or run an artifacted dg_agent.sh coding session with rollback-on-failure. Default mode is dry-run.",
            agent_session_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_context",
            "Build a compact rg-based repository context pack without MCP.",
            agent_context_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_rag_context",
            "Retrieve compact read-only RAG context for a repository task without calling the model.",
            agent_rag_context_input_schema(),
        ),
        responses_function_tool_schema(
            "dg_session_artifact",
            "Read latest or indexed dg_agent.sh session artifacts such as final_diff, context_md, stdout, or stderr.",
            session_artifact_input_schema(),
        ),
    ]


def body_bool(body: dict[str, Any], name: str, default: bool) -> bool:
    value = body.get(name, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def body_int(body: dict[str, Any], name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(body.get(name, default))
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def body_string_list(body: dict[str, Any], name: str) -> list[str]:
    value = body.get(name) or body.get("file") or []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out[:16]


def body_list(body: dict[str, Any], name: str, limit: int = 16) -> list[str]:
    value = body.get(name, [])
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out[:limit]


def build_agent_session_argv(body: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    repo = normalize_host_path(str(body.get("repo") or ".").strip() or ".")
    task = str(body.get("task") or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="task is required")
    if len(task) > 4000:
        raise HTTPException(status_code=413, detail="task is too long for the local session endpoint")

    files = body_string_list(body, "files")
    wall_timeout = body_int(body, "wall_timeout", 420, 30, 3600)
    aider_timeout = body_int(body, "aider_timeout", 300, 30, 1800)
    repair_attempts = body_int(body, "repair_attempts", 1, 0, 5)
    max_files = body_int(body, "max_files", 1, 1, 8)
    max_snippet_chars = body_int(body, "max_snippet_chars", 1200, 200, 8000)
    dry_run = body_bool(body, "dry_run", True)
    execute = body_bool(body, "execute", False)
    if not execute:
        dry_run = True

    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "session",
        "--repo",
        repo,
        "--task",
        task,
        "--wall-timeout",
        str(wall_timeout),
        "--aider-timeout",
        str(aider_timeout),
        "--repair-attempts",
        str(repair_attempts),
        "--max-files",
        str(max_files),
        "--max-snippet-chars",
        str(max_snippet_chars),
    ]
    for path in files:
        cmd.extend(["--file", path])
    test_cmd = str(body.get("test_cmd") or "").strip()
    if test_cmd:
        cmd.extend(["--test-cmd", test_cmd])
    if body_bool(body, "auto_test", False):
        cmd.append("--auto-test")
    if body_bool(body, "allow_dirty", True):
        cmd.append("--allow-dirty")
    if body_bool(body, "rollback_on_failure", True):
        cmd.append("--rollback-on-failure")
    if dry_run:
        cmd.append("--dry-run")

    meta = {
        "repo": repo,
        "task": task,
        "files": files,
        "execute": execute,
        "dry_run": dry_run,
        "execution_enabled": bool(ENABLE_AGENT_EXEC),
        "timeout": wall_timeout,
    }
    return cmd, meta


def readonly_command_payload(action: str, cmd: list[str], timeout: int, parse_json: bool = False) -> dict[str, Any]:
    started = time.time()
    run_cmd = adapt_subprocess_cmd(cmd)
    try:
        proc = subprocess.run(
            run_cmd,
            cwd=str(DG_ROOT),
            text=True,
            capture_output=True,
            timeout=max(5, timeout),
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return {
            "ok": False,
            "status": "timeout",
            "action": action,
            "command": cmd,
            "command_text": shlex.join(run_cmd),
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout,
            "text": stdout[:AGENT_CONTEXT_OUTPUT_LIMIT],
            "content": stdout[:AGENT_CONTEXT_OUTPUT_LIMIT],
            "stderr": stderr[-12000:],
            "truncated": len(stdout) > AGENT_CONTEXT_OUTPUT_LIMIT,
        }

    elapsed = time.time() - started
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    content = stdout[:AGENT_CONTEXT_OUTPUT_LIMIT]
    payload: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "status": "success" if proc.returncode == 0 else "failed",
        "action": action,
        "command": cmd,
        "command_text": shlex.join(run_cmd),
        "returncode": proc.returncode,
        "elapsed_seconds": elapsed,
        "text": content,
        "content": content,
        "stderr": stderr[-12000:],
        "truncated": len(stdout) > AGENT_CONTEXT_OUTPUT_LIMIT,
    }
    if parse_json and proc.returncode == 0:
        try:
            payload["context"] = json.loads(stdout)
        except Exception as exc:
            payload["ok"] = False
            payload["status"] = "failed"
            payload["parse_error"] = str(exc)
    return payload


def bounded_command_payload(action: str, cmd: list[str], timeout: int, max_chars: int) -> dict[str, Any]:
    started = time.time()
    run_cmd = adapt_subprocess_cmd(cmd)
    try:
        proc = subprocess.run(
            run_cmd,
            cwd=str(DG_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(1, timeout),
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        content = stdout[:max_chars]
        return {
            "ok": proc.returncode == 0,
            "status": "success" if proc.returncode == 0 else "failed",
            "action": action,
            "command": cmd,
            "command_text": shlex.join(run_cmd),
            "returncode": proc.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "stdout": content,
            "text": content,
            "content": content,
            "stdout_chars": len(stdout),
            "stderr": stderr[-12000:],
            "truncated": len(stdout) > max_chars,
            "max_chars": max_chars,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        content = stdout[:max_chars]
        return {
            "ok": False,
            "status": "timeout",
            "action": action,
            "command": cmd,
            "command_text": shlex.join(run_cmd),
            "returncode": 124,
            "elapsed_seconds": round(time.time() - started, 3),
            "timeout_seconds": timeout,
            "stdout": content,
            "text": content,
            "content": content,
            "stdout_chars": len(stdout),
            "stderr": stderr[-12000:] + f"\nTimed out after {timeout}s",
            "truncated": len(stdout) > max_chars,
            "max_chars": max_chars,
        }


def resolve_repo(body: dict[str, Any]) -> Path:
    raw = normalize_host_path(str(body.get("repo") or ".").strip() or ".")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (DG_ROOT / path).resolve()
    else:
        path = path.resolve()
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail=f"repo does not exist: {path}")
    return path


def safe_repo_file(repo: Path, file_name: str) -> Path:
    if not file_name:
        raise HTTPException(status_code=400, detail="path is required")
    raw = Path(normalize_host_path(file_name)).expanduser()
    target = raw.resolve() if raw.is_absolute() else (repo / raw).resolve()
    if target != repo and repo not in target.parents:
        raise HTTPException(status_code=400, detail=f"path escapes repo: {file_name}")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"file does not exist: {file_name}")
    return target


def run_repo_command(
    action: str,
    cmd: list[str],
    repo: Path,
    timeout: int,
    *,
    max_chars: int = 20000,
    ok_returncodes: set[int] | None = None,
) -> dict[str, Any]:
    ok_returncodes = ok_returncodes or {0}
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(1, timeout),
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        content = stdout[:max_chars]
        return {
            "ok": proc.returncode in ok_returncodes,
            "status": "success" if proc.returncode in ok_returncodes else "failed",
            "action": action,
            "repo": str(repo),
            "command": cmd,
            "command_text": shlex.join(cmd),
            "returncode": proc.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "stdout": content,
            "text": content,
            "content": content,
            "stderr": stderr[-12000:],
            "truncated": len(stdout) > max_chars,
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "status": "missing_command",
            "action": action,
            "repo": str(repo),
            "command": cmd,
            "command_text": shlex.join(cmd),
            "returncode": 127,
            "elapsed_seconds": round(time.time() - started, 3),
            "stdout": "",
            "text": "",
            "content": "",
            "stderr": str(exc),
            "truncated": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        content = stdout[:max_chars]
        return {
            "ok": False,
            "status": "timeout",
            "action": action,
            "repo": str(repo),
            "command": cmd,
            "command_text": shlex.join(cmd),
            "returncode": 124,
            "elapsed_seconds": round(time.time() - started, 3),
            "timeout_seconds": timeout,
            "stdout": content,
            "text": content,
            "content": content,
            "stderr": stderr[-12000:] + f"\nTimed out after {timeout}s",
            "truncated": len(stdout) > max_chars,
        }


def agent_repo_status_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    timeout = body_int(body, "timeout", 30, 1, 180)
    max_chars = body_int(body, "max_chars", 8000, 1000, 100000)
    status = run_repo_command("dg_repo_status", ["git", "status", "--short"], repo, timeout, max_chars=max_chars)
    diff_stat = run_repo_command("dg_repo_status_diff_stat", ["git", "diff", "--stat"], repo, timeout, max_chars=max_chars)
    untracked = run_repo_command("dg_repo_status_untracked", ["git", "ls-files", "--others", "--exclude-standard"], repo, timeout, max_chars=max_chars)
    chunks = []
    if status["stdout"].strip():
        chunks.append("Status:\n" + status["stdout"].strip())
    else:
        chunks.append("Status: clean")
    if diff_stat["stdout"].strip():
        chunks.append("Diff stat:\n" + diff_stat["stdout"].strip())
    if untracked["stdout"].strip():
        chunks.append("Untracked files:\n" + untracked["stdout"].strip())
    content = "\n\n".join(chunks)[:max_chars]
    return {
        **status,
        "ok": status["ok"],
        "status": "success" if status["ok"] else status["status"],
        "diff_stat": diff_stat["stdout"],
        "untracked": [line for line in untracked["stdout"].splitlines() if line],
        "stdout": content,
        "text": content,
        "content": content,
        "truncated": status["truncated"] or diff_stat["truncated"] or untracked["truncated"] or len("\n\n".join(chunks)) > max_chars,
    }


def agent_git_diff_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    timeout = body_int(body, "timeout", 30, 1, 180)
    max_chars = body_int(body, "max_chars", 20000, 1000, 200000)
    cmd = ["git", "diff"]
    if body_bool(body, "cached", False):
        cmd.append("--cached")
    if body_bool(body, "stat", False):
        cmd.append("--stat")
    files = body_list(body, "files", limit=16)
    if files:
        cmd.append("--")
        cmd.extend(files)
    return run_repo_command("dg_git_diff", cmd, repo, timeout, max_chars=max_chars)


def agent_list_files_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    timeout = body_int(body, "timeout", 30, 1, 180)
    limit = body_int(body, "limit", 200, 1, 5000)
    pattern = str(body.get("pattern") or "").strip().lower()
    cmd = ["rg", "--files"]
    for glob in body_list(body, "globs", limit=32):
        cmd.extend(["-g", glob])
    result = run_repo_command("dg_list_files", cmd, repo, timeout, max_chars=1_000_000)
    if not result["ok"]:
        result = run_repo_command("dg_list_files", ["git", "ls-files"], repo, timeout, max_chars=1_000_000)
    files = [line for line in result.get("stdout", "").splitlines() if line]
    if pattern:
        files = [file for file in files if pattern in file.lower()]
    visible = files[:limit]
    content = "\n".join(visible)
    if len(files) > limit:
        content += f"\n... truncated {len(files) - limit} more files"
    return {
        **result,
        "ok": result["ok"],
        "status": "success" if result["ok"] else result["status"],
        "files": visible,
        "total_matches": len(files),
        "stdout": content,
        "text": content,
        "content": content,
        "truncated": len(files) > limit,
    }


def agent_read_file_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    target = safe_repo_file(repo, str(body.get("path") or ""))
    start_line = body_int(body, "start_line", 1, 1, 10_000_000)
    max_lines = body_int(body, "max_lines", 160, 1, 5000)
    max_chars = body_int(body, "max_chars", 20000, 1000, 200000)
    text = target.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    selected = lines[start_line - 1 : start_line - 1 + max_lines]
    numbered = "\n".join(f"{idx}: {line}" for idx, line in enumerate(selected, start=start_line))
    content = numbered[:max_chars]
    rel = target.relative_to(repo)
    return {
        "ok": True,
        "status": "success",
        "action": "dg_read_file",
        "repo": str(repo),
        "path": str(rel),
        "line_count": len(lines),
        "start_line": start_line,
        "returned_lines": len(selected),
        "stdout": content,
        "text": content,
        "content": content,
        "stderr": "",
        "elapsed_seconds": 0,
        "truncated": len(selected) < len(lines[start_line - 1 :]) or len(numbered) > max_chars,
    }


def agent_search_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    query = str(body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    timeout = body_int(body, "timeout", 30, 1, 180)
    max_matches = body_int(body, "max_matches", 80, 1, 1000)
    max_chars = body_int(body, "max_chars", 12000, 1000, 200000)
    cmd = ["rg", "--line-number", "--column", "--color", "never"]
    context = body_int(body, "context", 0, 0, 5)
    if context:
        cmd.extend(["--context", str(context)])
    for glob in body_list(body, "globs", limit=32):
        cmd.extend(["-g", glob])
    cmd.extend(["--", query, "."])
    result = run_repo_command("dg_search", cmd, repo, timeout, max_chars=1_000_000, ok_returncodes={0, 1})
    lines = result.get("stdout", "").splitlines()
    visible = lines[:max_matches]
    content = "\n".join(visible)[:max_chars]
    if len(lines) > max_matches:
        content += f"\n... truncated {len(lines) - max_matches} more matching lines"
    return {
        **result,
        "query": query,
        "matches": visible,
        "total_lines": len(lines),
        "stdout": content,
        "text": content,
        "content": content,
        "truncated": len(lines) > max_matches or len("\n".join(visible)) > max_chars,
    }


def agent_repo_pack_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    timeout = body_int(body, "timeout", 180, 1, 1800)
    max_chars = body_int(body, "max_chars", 20000, 1000, 200000)
    style = str(body.get("style") or "markdown")
    if style not in {"xml", "markdown", "json", "plain"}:
        raise HTTPException(status_code=400, detail="style must be xml, markdown, json, or plain")
    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "repo-pack",
        "--repo",
        str(repo),
        "--style",
        style,
        "--stdout",
        "--top-files-len",
        str(body_int(body, "top_files_len", 5, 0, 50)),
    ]
    for pattern in body_list(body, "include", limit=64):
        cmd.extend(["--include", pattern])
    for pattern in body_list(body, "ignore", limit=64):
        cmd.extend(["--ignore", pattern])
    for key, flag in [
        ("compress", "--compress"),
        ("include_diffs", "--include-diffs"),
        ("output_show_line_numbers", "--output-show-line-numbers"),
        ("remove_comments", "--remove-comments"),
        ("remove_empty_lines", "--remove-empty-lines"),
        ("no_files", "--no-files"),
        ("no_security_check", "--no-security-check"),
    ]:
        if body_bool(body, key, False):
            cmd.append(flag)
    token_budget = body_int(body, "token_budget", 0, 0, 2_000_000)
    if token_budget:
        cmd.extend(["--token-budget", str(token_budget)])
    result = bounded_command_payload("dg_repo_pack", cmd, timeout, max_chars)
    return {**result, "repo": str(repo)}


def agent_repo_map_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    timeout = body_int(body, "timeout", 180, 1, 1800)
    max_chars = body_int(body, "max_chars", 20000, 1000, 200000)
    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "repo-map",
        "--repo",
        str(repo),
        "--map-tokens",
        str(body_int(body, "map_tokens", 2048, 128, 64000)),
        "--max-chars",
        str(max_chars),
        "--timeout",
        str(timeout),
    ]
    if body_bool(body, "map_only", True):
        cmd.append("--map-only")
    base_url = str(body.get("base_url") or "").strip()
    if base_url:
        cmd.extend(["--base-url", base_url])
    model = str(body.get("model") or "").strip()
    if model:
        cmd.extend(["--model", model])
    cmd.extend(body_list(body, "paths", limit=64))
    result = bounded_command_payload("dg_repo_map", cmd, timeout + 30, max_chars)
    return {**result, "repo": str(repo)}


def agent_ast_grep_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    pattern = str(body.get("pattern") or "").strip()
    kind = str(body.get("kind") or "").strip()
    selector = str(body.get("selector") or "").strip()
    if not any([pattern, kind, selector]):
        raise HTTPException(status_code=400, detail="one of pattern, kind, or selector is required")
    timeout = body_int(body, "timeout", 120, 1, 1800)
    max_chars = body_int(body, "max_chars", 20000, 1000, 200000)
    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "ast-grep",
        "--repo",
        str(repo),
        "--max-matches",
        str(body_int(body, "max_matches", 80, 1, 1000)),
        "--max-chars",
        str(max_chars),
        "--timeout",
        str(timeout),
    ]
    lang = str(body.get("lang") or "").strip()
    if lang:
        cmd.extend(["--lang", lang])
    if pattern:
        cmd.extend(["--pattern", pattern])
    if kind:
        cmd.extend(["--kind", kind])
    if selector:
        cmd.extend(["--selector", selector])
    strictness = str(body.get("strictness") or "").strip()
    if strictness:
        cmd.extend(["--strictness", strictness])
    context = body_int(body, "context", 0, 0, 20)
    if context:
        cmd.extend(["--context", str(context)])
    for glob in body_list(body, "globs", limit=64):
        cmd.extend(["--glob", glob])
    if body_bool(body, "files_with_matches", False):
        cmd.append("--files-with-matches")
    elif body_bool(body, "json", True):
        cmd.append("--json")
    cmd.extend(body_list(body, "paths", limit=64))
    result = bounded_command_payload("dg_ast_grep", cmd, timeout + 30, max_chars)
    return {**result, "repo": str(repo)}


def agent_code_outline_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    timeout = body_int(body, "timeout", 120, 1, 1800)
    max_chars = body_int(body, "max_chars", 20000, 1000, 200000)
    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "code-outline",
        "--repo",
        str(repo),
        "--items",
        str(body.get("items") or "auto"),
        "--view",
        str(body.get("view") or "auto"),
        "--max-items",
        str(body_int(body, "max_items", 200, 1, 5000)),
        "--max-chars",
        str(max_chars),
        "--timeout",
        str(timeout),
    ]
    lang = str(body.get("lang") or "").strip()
    if lang:
        cmd.extend(["--lang", lang])
    symbol_type = str(body.get("type") or "").strip()
    if symbol_type:
        cmd.extend(["--type", symbol_type])
    match = str(body.get("match") or "").strip()
    if match:
        cmd.extend(["--match", match])
    if body_bool(body, "pub_members", False):
        cmd.append("--pub-members")
    for glob in body_list(body, "globs", limit=64):
        cmd.extend(["--glob", glob])
    if body_bool(body, "json", True):
        cmd.append("--json")
    cmd.extend(body_list(body, "paths", limit=64))
    result = bounded_command_payload("dg_code_outline", cmd, timeout + 30, max_chars)
    return {**result, "repo": str(repo)}


def infer_agent_mode(task: str) -> str:
    lowered = task.lower()
    edit_markers = {
        "add",
        "change",
        "create",
        "delete",
        "edit",
        "fix",
        "implement",
        "modify",
        "patch",
        "refactor",
        "remove",
        "repair",
        "replace",
        "update",
        "write",
        "добавь",
        "измени",
        "исправь",
        "обнови",
        "переделай",
        "почини",
        "реализуй",
        "сделай",
        "создай",
        "удали",
    }
    read_markers = {
        "analyze",
        "explain",
        "find",
        "grep",
        "inspect",
        "list",
        "read",
        "search",
        "show",
        "summarize",
        "where",
        "где",
        "найди",
        "объясни",
        "покажи",
        "посмотри",
        "прочитай",
        "проанализируй",
        "список",
        "что",
    }
    if any(marker in lowered for marker in edit_markers):
        return "edit"
    if any(marker in lowered for marker in read_markers):
        return "read"
    return "read"


def agent_facade_action(body: dict[str, Any]) -> dict[str, Any]:
    repo = resolve_repo(body)
    task = str(body.get("task") or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="task is required")
    if len(task) > 4000:
        raise HTTPException(status_code=413, detail="task is too long for the local agent endpoint")
    requested_mode = str(body.get("mode") or "auto").strip().lower()
    if requested_mode not in {"auto", "read", "edit"}:
        raise HTTPException(status_code=400, detail="mode must be auto, read, or edit")
    selected_mode = infer_agent_mode(task) if requested_mode == "auto" else requested_mode
    execute = body_bool(body, "execute", False)
    dry_run = body_bool(body, "dry_run", True)
    max_chars = body_int(body, "max_chars", 200000, 1000, 1_000_000)
    wall_timeout = body_int(body, "wall_timeout", 900, 30, 7200)
    timeout = body_int(body, "timeout", 120, 5, 1800)
    command_timeout = timeout + 30 if selected_mode == "read" else wall_timeout + 30

    if selected_mode == "read" and body_bool(body, "deterministic_first", True):
        direct = deterministic_read_agent_action(repo, task, body)
        if direct is not None:
            return {
                **direct,
                "repo": str(repo),
                "task": task,
                "mode": selected_mode,
                "requested_mode": requested_mode,
            }

    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "agent",
        "--repo",
        str(repo),
        "--task",
        task,
        "--mode",
        selected_mode,
    ]
    for path in body_string_list(body, "files"):
        cmd.extend(["--file", path])
    for path in body_string_list(body, "file"):
        if path not in cmd:
            cmd.extend(["--file", path])
    if selected_mode == "read":
        cmd.extend([
            "--base-url",
            str(body.get("base_url") or "http://127.0.0.1:4100/v1"),
            "--model",
            str(body.get("model") or "diffusiongemma-local"),
            "--tool-manifest-url",
            str(body.get("tool_manifest_url") or "http://127.0.0.1:8090/v1/agent/tool_manifest"),
            "--tool-runtime-url",
            str(body.get("tool_runtime_url") or "http://127.0.0.1:8090/v1/agent/tool"),
            "--max-steps",
            str(body_int(body, "max_steps", 2, 1, 8)),
            "--max-tokens",
            str(body_int(body, "max_tokens", 256, 16, 1024)),
            "--temperature",
            str(float(body.get("temperature", 0.0) or 0.0)),
            "--timeout",
            str(timeout),
        ])
        for tool in body_list(body, "tools", limit=32) or body_list(body, "tool", limit=32):
            cmd.extend(["--tool", tool])
        for tool in body_list(body, "exclude_tools", limit=32) or body_list(body, "exclude_tool", limit=32):
            cmd.extend(["--exclude-tool", tool])
        if body_bool(body, "stop_after_tool", False):
            cmd.append("--stop-after-tool")
        cmd.append("--json")
        result = bounded_command_payload("dg_agent", cmd, command_timeout, max_chars)
        return {**result, "repo": str(repo), "task": task, "mode": selected_mode, "requested_mode": requested_mode}

    cmd.extend([
        "--max-files",
        str(body_int(body, "max_files", 3, 1, 20)),
        "--max-snippet-chars",
        str(body_int(body, "max_snippet_chars", 1200, 200, 20000)),
        "--test-timeout",
        str(body_int(body, "test_timeout", 120, 10, 3600)),
        "--aider-timeout",
        str(body_int(body, "aider_timeout", 420, 30, 7200)),
        "--repair-attempts",
        str(body_int(body, "repair_attempts", 1, 0, 5)),
        "--wall-timeout",
        str(wall_timeout),
    ])
    test_cmd = str(body.get("test_cmd") or "").strip()
    if test_cmd:
        cmd.extend(["--test-cmd", test_cmd])
    if not body_bool(body, "auto_test", False):
        cmd.append("--no-auto-test")
    if not body_bool(body, "rollback_on_failure", True):
        cmd.append("--no-rollback")
    if body_bool(body, "allow_dirty", True):
        cmd.append("--allow-dirty")
    if body_bool(body, "no_deterministic_first", False):
        cmd.append("--no-deterministic-first")
    if dry_run or not execute:
        cmd.append("--dry-run")

    preview = {
        "ok": True,
        "status": "dry_run" if not execute or dry_run else "ready",
        "action": "dg_agent",
        "repo": str(repo),
        "task": task,
        "mode": selected_mode,
        "requested_mode": requested_mode,
        "execute": execute,
        "dry_run": dry_run or not execute,
        "execution_enabled": bool(ENABLE_AGENT_EXEC),
        "command": cmd,
        "command_text": shlex.join(cmd),
        "content": shlex.join(cmd),
        "text": shlex.join(cmd),
    }
    if not execute or dry_run:
        return preview
    if not ENABLE_AGENT_EXEC:
        return {
            **preview,
            "ok": False,
            "status": "blocked",
            "reason": "HTTP agent edit execution is disabled; set DG_AIDER_PROXY_ENABLE_AGENT_EXEC=1 and retry with execute=true and dry_run=false.",
        }
    result = bounded_command_payload("dg_agent", cmd, command_timeout, max_chars)
    return {**result, "repo": str(repo), "task": task, "mode": selected_mode, "requested_mode": requested_mode}


def deterministic_read_agent_action(repo: Path, task: str, body: dict[str, Any]) -> dict[str, Any] | None:
    requested_tools = set(body_list(body, "tools", limit=32) or body_list(body, "tool", limit=32))
    files = body_string_list(body, "files") or body_string_list(body, "file") or task_file_hints(task)
    max_chars = body_int(body, "max_chars", 200000, 1000, 1_000_000)
    started = time.time()

    if (not requested_tools or "dg_read_file" in requested_tools) and files:
        results = []
        chunks = []
        for file_name in files[:8]:
            result = agent_read_file_action({
                "repo": str(repo),
                "path": file_name,
                "start_line": 1,
                "max_lines": body_int(body, "max_lines", 160, 1, 5000),
                "max_chars": max_chars,
            })
            results.append(result)
            chunks.append(f"# {result['path']}\n{result['content']}")
        content = "\n\n".join(chunks)[:max_chars]
        return {
            "ok": True,
            "status": "success",
            "action": "dg_agent",
            "route": "deterministic_read_file",
            "tool_names": ["dg_read_file"],
            "results": results,
            "stdout": content,
            "text": content,
            "content": content,
            "stderr": "",
            "elapsed_seconds": round(time.time() - started, 3),
            "truncated": len("\n\n".join(chunks)) > max_chars,
        }

    task_lower = task.lower()
    if "dg_list_files" in requested_tools or any(word in task_lower for word in ("list files", "show files", "file list")):
        result = agent_list_files_action({"repo": str(repo), "limit": body_int(body, "limit", 200, 1, 5000)})
        return {
            **result,
            "action": "dg_agent",
            "route": "deterministic_list_files",
            "tool_names": ["dg_list_files"],
        }

    if "dg_search" in requested_tools or any(word in task_lower for word in ("search", "grep", "find")):
        query = str(body.get("query") or "").strip() or task_search_hint(task)
        result = agent_search_action({
            "repo": str(repo),
            "query": query,
            "max_matches": body_int(body, "max_matches", 80, 1, 1000),
            "max_chars": max_chars,
        })
        return {
            **result,
            "action": "dg_agent",
            "route": "deterministic_search",
            "tool_names": ["dg_search"],
        }

    if "dg_context" in requested_tools:
        result = agent_context_action({
            "repo": str(repo),
            "task": task,
            "files": files,
            "format": "json",
            "max_files": body_int(body, "max_files", 3, 1, 20),
            "max_snippet_chars": body_int(body, "max_snippet_chars", 1200, 200, 20000),
            "timeout": body_int(body, "timeout", AGENT_CONTEXT_TIMEOUT, 5, 600),
        })
        return {
            **result,
            "action": "dg_agent",
            "route": "deterministic_context",
            "tool_names": ["dg_context"],
        }

    return None


def build_agent_context_argv(body: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    repo = normalize_host_path(str(body.get("repo") or ".").strip() or ".")
    task = str(body.get("task") or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="task is required")
    if len(task) > 4000:
        raise HTTPException(status_code=413, detail="task is too long for the local context endpoint")
    response_format = str(body.get("format") or "json").strip().lower()
    if response_format not in {"json", "markdown"}:
        raise HTTPException(status_code=400, detail="format must be json or markdown")
    max_files = body_int(body, "max_files", 3, 1, 20)
    max_snippet_chars = body_int(body, "max_snippet_chars", 1200, 200, 20000)
    timeout = body_int(body, "timeout", AGENT_CONTEXT_TIMEOUT, 5, 600)
    files = body_string_list(body, "files")
    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "context",
        "--repo",
        repo,
        "--task",
        task,
        "--max-files",
        str(max_files),
        "--max-snippet-chars",
        str(max_snippet_chars),
    ]
    for path in files:
        cmd.extend(["--file", path])
    if response_format == "json":
        cmd.append("--json")
    return cmd, {
        "repo": repo,
        "task": task,
        "files": files,
        "format": response_format,
        "timeout": timeout,
    }


def agent_context_action(body: dict[str, Any]) -> dict[str, Any]:
    cmd, meta = build_agent_context_argv(body)
    payload = readonly_command_payload("dg_agent_context", cmd, int(meta["timeout"]) + 15, parse_json=meta["format"] == "json")
    return {**payload, **meta}


def build_agent_rag_context_argv(body: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    repo = normalize_host_path(str(body.get("repo") or ".").strip() or ".")
    task = str(body.get("task") or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="task is required")
    if len(task) > 4000:
        raise HTTPException(status_code=413, detail="task is too long for the local RAG endpoint")
    max_context_chars = body_int(body, "max_context_chars", 900, 200, 20000)
    max_files = body_int(body, "max_files", 3, 1, 20)
    max_tokens = body_int(body, "max_tokens", 128, 16, 512)
    timeout = body_int(body, "timeout", AGENT_CONTEXT_TIMEOUT, 5, 600)
    cmd = [
        str(DG_ROOT / "scripts" / "dg_agent.sh"),
        "rag",
        "--repo",
        repo,
        "--task",
        task,
        "--max-context-chars",
        str(max_context_chars),
        "--max-files",
        str(max_files),
        "--max-tokens",
        str(max_tokens),
        "--timeout",
        str(timeout),
        "--print-context",
    ]
    if body_bool(body, "debug", False):
        cmd.append("--debug")
    return cmd, {
        "repo": repo,
        "task": task,
        "max_context_chars": max_context_chars,
        "max_files": max_files,
        "debug": body_bool(body, "debug", False),
        "timeout": timeout,
    }


def agent_rag_context_action(body: dict[str, Any]) -> dict[str, Any]:
    cmd, meta = build_agent_rag_context_argv(body)
    payload = readonly_command_payload("dg_agent_rag_context", cmd, int(meta["timeout"]) + 15)
    return {**payload, **meta}


def parse_tool_runtime_request(body: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    tool_call_id = str(body.get("tool_call_id") or "")
    tool_call = body.get("tool_call")
    if isinstance(tool_call, dict):
        tool_call_id = str(tool_call.get("id") or tool_call_id)
        function = tool_call.get("function")
        if isinstance(function, dict):
            name = str(function.get("name") or body.get("name") or "")
            raw_args = function.get("arguments", body.get("arguments", {}))
        else:
            name = str(tool_call.get("name") or body.get("name") or "")
            raw_args = tool_call.get("arguments", body.get("arguments", {}))
    else:
        name = str(body.get("name") or "").strip()
        raw_args = body.get("arguments", {})

    if isinstance(raw_args, str):
        raw_args = raw_args.strip()
        if not raw_args:
            args: dict[str, Any] = {}
        else:
            try:
                parsed = json.loads(raw_args)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"tool arguments must be a JSON object: {exc}") from exc
            if not isinstance(parsed, dict):
                raise HTTPException(status_code=400, detail="tool arguments must decode to a JSON object")
            args = parsed
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        raise HTTPException(status_code=400, detail="arguments must be an object or JSON string")

    if not name:
        raise HTTPException(status_code=400, detail="tool name is required")
    return name, args, tool_call_id


def agent_tool_runtime_action(body: dict[str, Any]) -> dict[str, Any]:
    name, args, tool_call_id = parse_tool_runtime_request(body)
    if name == "dg_session":
        result = agent_session_action(args)
    elif name == "dg_repo_status":
        result = agent_repo_status_action(args)
    elif name == "dg_git_diff":
        result = agent_git_diff_action(args)
    elif name == "dg_list_files":
        result = agent_list_files_action(args)
    elif name == "dg_read_file":
        result = agent_read_file_action(args)
    elif name == "dg_search":
        result = agent_search_action(args)
    elif name == "dg_repo_pack":
        result = agent_repo_pack_action(args)
    elif name == "dg_repo_map":
        result = agent_repo_map_action(args)
    elif name == "dg_ast_grep":
        result = agent_ast_grep_action(args)
    elif name == "dg_code_outline":
        result = agent_code_outline_action(args)
    elif name == "dg_agent":
        result = agent_facade_action(args)
    elif name == "dg_agent_run_artifact":
        run = str(args.get("run") or "latest")
        artifact = str(args.get("artifact") or "agent_json")
        limit = body_int(args, "limit", 200_000, 1000, 1_000_000)
        report = load_agent_run_report(latest=run == "latest", run="" if run == "latest" else run)
        if report is None:
            result = {"ok": False, "status": "not_found", "error": f"agent run not found: {run}", "root": str(DEFAULT_AGENT_RUN_ROOT)}
        else:
            result = {"run": agent_run_summary(report), **read_agent_run_artifact(report, artifact, limit=limit)}
    elif name == "dg_context":
        result = agent_context_action(args)
    elif name == "dg_rag_context":
        result = agent_rag_context_action(args)
    elif name == "dg_session_artifact":
        session = str(args.get("session") or "latest")
        artifact = str(args.get("artifact") or "final_diff")
        limit = body_int(args, "limit", 200_000, 1000, 1_000_000)
        report = load_session_report(latest=session == "latest", session="" if session == "latest" else session)
        if report is None:
            result = {"ok": False, "status": "not_found", "error": f"session not found: {session}", "root": str(DEFAULT_SESSION_ROOT)}
        else:
            result = {"session": session_summary(report), **read_session_artifact(report, artifact, limit=limit)}
    elif name == "execute_command":
        command = str(args.get("command") or "").strip()
        result = {
            "ok": False,
            "status": "blocked",
            "tool": "execute_command",
            "command": command,
            "reason": "The HTTP tool runtime does not execute arbitrary shell commands. Use DG-specific tools such as dg_session, repo inspection tools, OSS repo tools, dg_context, dg_rag_context, or dg_session_artifact.",
        }
    else:
        result = {
            "ok": False,
            "status": "unsupported_tool",
            "error": f"unsupported tool: {name}",
            "supported_tools": HTTP_TOOL_NAMES,
        }

    content = json.dumps(result, ensure_ascii=False)
    return {
        "ok": bool(result.get("ok")) if isinstance(result, dict) and "ok" in result else True,
        "tool": name,
        "tool_call_id": tool_call_id,
        "result": result,
        "tool_response": {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        },
    }


def agent_session_action(body: dict[str, Any]) -> dict[str, Any]:
    cmd, meta = build_agent_session_argv(body)
    result: dict[str, Any] = {
        "status": "dry_run",
        "action": "dg_agent_session",
        "command": cmd,
        "command_text": shlex.join(cmd),
        **meta,
    }
    if not meta["execute"]:
        return result
    if not ENABLE_AGENT_EXEC:
        return {
            **result,
            "status": "blocked",
            "reason": "HTTP session execution is disabled; set DG_AIDER_PROXY_ENABLE_AGENT_EXEC=1 and retry with execute=true.",
        }

    repo = Path(str(meta["repo"])).expanduser()
    cwd = repo if repo.exists() and repo.is_dir() else DG_ROOT
    timeout = max(30, min(int(meta["timeout"]) + 30, AGENT_EXEC_TIMEOUT))
    started = time.time()
    run_cmd = adapt_subprocess_cmd(cmd)
    try:
        proc = subprocess.run(run_cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        elapsed = time.time() - started
        return {
            **result,
            "status": "success" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            **result,
            "status": "timeout",
            "returncode": 124,
            "elapsed_seconds": time.time() - started,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": f"session timed out after {exc.timeout}s",
        }


def session_reports(root: Path = DEFAULT_SESSION_ROOT) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if not root.exists():
        return reports
    for path in root.rglob("session.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_session_json"] = str(path)
            data["_mtime"] = path.stat().st_mtime
            reports.append(data)
        except Exception:
            continue
    reports.sort(key=lambda item: float(item.get("_mtime", 0)), reverse=True)
    return reports


def session_summary(report: dict[str, Any]) -> dict[str, Any]:
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    final_diff = Path(str(artifacts.get("final_diff", "")))
    return {
        "status": report.get("status"),
        "task": report.get("task"),
        "repo": report.get("repo"),
        "session_dir": report.get("session_dir"),
        "session_id": Path(str(report.get("session_dir") or "")).name,
        "session_json": report.get("_session_json") or artifacts.get("session_json"),
        "task_returncode": report.get("task_returncode"),
        "verify_returncode": report.get("verify_returncode"),
        "task_elapsed_sec": report.get("task_elapsed_sec"),
        "final_diff_bytes": final_diff.stat().st_size if final_diff.exists() else 0,
    }


def load_session_report(session: str = "", latest: bool = False) -> dict[str, Any] | None:
    reports = session_reports()
    if latest or not session:
        return reports[0] if reports else None
    if session.isdigit():
        index = int(session) - 1
        if 0 <= index < len(reports):
            return reports[index]
    for report in reports:
        summary = session_summary(report)
        if session in {str(summary.get("session_id") or ""), str(summary.get("session_dir") or ""), str(summary.get("session_json") or "")}:
            return report
    return None


def agent_run_reports(root: Path = DEFAULT_AGENT_RUN_ROOT) -> list[dict[str, Any]]:
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
    transcript = Path(normalize_host_path(str(artifacts.get("transcript", ""))))
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


def load_agent_run_report(run: str = "", latest: bool = False) -> dict[str, Any] | None:
    reports = agent_run_reports()
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
    path = Path(run)
    if path.is_dir():
        path = path / "agent.json"
    if not path.is_absolute():
        path = DEFAULT_AGENT_RUN_ROOT / path
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
    raw_path = str(artifacts.get(key) or "")
    if not raw_path and key == "agent_json":
        raw_path = str(report.get("_agent_json") or "")
    if not raw_path:
        run_dir = Path(str(report.get("run_dir") or ""))
        if run_dir:
            raw_path = str(run_dir / AGENT_RUN_ARTIFACT_FILENAMES[key])
    if not raw_path:
        return key, None
    path = Path(normalize_host_path(raw_path))
    run_dir_text = str(report.get("run_dir") or "")
    if run_dir_text:
        run_dir = Path(normalize_host_path(run_dir_text)).resolve()
        try:
            resolved = path.resolve()
        except Exception:
            return key, None
        if resolved != run_dir and run_dir not in resolved.parents:
            return key, None
    return key, path


def read_agent_run_artifact(report: dict[str, Any], artifact: str, limit: int = 200_000) -> dict[str, Any]:
    key, path = agent_run_artifact_path(report, artifact)
    if path is None:
        return {
            "ok": False,
            "error": f"unknown artifact: {artifact}",
            "available_artifacts": sorted(set(AGENT_RUN_ARTIFACT_FILENAMES) | set(AGENT_RUN_ARTIFACT_ALIASES)),
        }
    if not path.exists():
        return {"ok": False, "error": f"artifact missing: {key}", "path": str(path)}
    size_bytes = path.stat().st_size
    text = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > limit
    content = text[:limit]
    return {
        "ok": True,
        "artifact": key,
        "path": str(path),
        "bytes": size_bytes,
        "truncated": truncated,
        "text": content,
        "content": content,
    }


def session_artifact_path(report: dict[str, Any], artifact: str) -> tuple[str, Path | None]:
    key = SESSION_ARTIFACT_ALIASES.get(artifact, artifact)
    if key not in SESSION_ARTIFACT_FILENAMES:
        return key, None
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    raw_path = str(artifacts.get(key) or "")
    if not raw_path and key == "session_json":
        raw_path = str(report.get("_session_json") or "")
    if not raw_path:
        session_dir = Path(str(report.get("session_dir") or ""))
        if session_dir:
            raw_path = str(session_dir / SESSION_ARTIFACT_FILENAMES[key])
    if not raw_path:
        return key, None
    path = Path(normalize_host_path(raw_path))
    session_dir_text = str(report.get("session_dir") or "")
    if session_dir_text:
        session_dir = Path(normalize_host_path(session_dir_text)).resolve()
        try:
            resolved = path.resolve()
        except Exception:
            return key, None
        if resolved != session_dir and session_dir not in resolved.parents:
            return key, None
    return key, path


def read_session_artifact(report: dict[str, Any], artifact: str, limit: int = 200_000) -> dict[str, Any]:
    key, path = session_artifact_path(report, artifact)
    if path is None:
        return {
            "ok": False,
            "error": f"unknown artifact: {artifact}",
            "available_artifacts": sorted(set(SESSION_ARTIFACT_FILENAMES) | set(SESSION_ARTIFACT_ALIASES)),
        }
    if not path.exists():
        return {"ok": False, "error": f"artifact missing: {key}", "path": str(path)}
    size_bytes = path.stat().st_size
    text = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > limit
    content = text[:limit]
    return {
        "ok": True,
        "artifact": key,
        "path": str(path),
        "bytes": size_bytes,
        "truncated": truncated,
        "text": content,
        "content": content,
    }


def tool_name(tool: dict[str, Any]) -> str:
    if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
        return str(tool["function"].get("name") or "")
    return str(tool.get("name") or "")


def tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
        params = tool["function"].get("parameters")
    else:
        params = tool.get("parameters")
    return params if isinstance(params, dict) else {}


def command_argument_name(tool: dict[str, Any]) -> str:
    schema = tool_schema(tool)
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    for name in ("command", "cmd", "shell_command", "bash", "input"):
        if name in properties:
            return name
    return "command"


def select_command_tool(tools: list[Any]) -> dict[str, Any] | None:
    for raw_tool in tools:
        if not isinstance(raw_tool, dict):
            continue
        name = tool_name(raw_tool).lower()
        if any(marker in name for marker in ("bash", "shell", "command", "terminal", "exec", "run")):
            return raw_tool
        schema = tool_schema(raw_tool)
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        if any(key in properties for key in ("command", "cmd", "shell_command")):
            return raw_tool
    return None


def select_named_tool(tools: list[Any], names: set[str]) -> dict[str, Any] | None:
    for raw_tool in tools:
        if not isinstance(raw_tool, dict):
            continue
        if tool_name(raw_tool) in names:
            return raw_tool
    return None


def tool_call_name_map(messages: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for message in messages:
        if message.get("role") != "assistant":
            continue
        calls = message.get("tool_calls")
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, dict):
                continue
            call_id = str(call.get("id") or "")
            function = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = str(function.get("name") or call.get("name") or "")
            if call_id and name:
                names[call_id] = name
    return names


def tool_result_dict(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def compact_tool_content(text: str, limit: int = 5000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n... truncated {len(text) - limit} chars"


def summarize_one_tool_message(message: dict[str, Any], names: dict[str, str]) -> str:
    call_id = str(message.get("tool_call_id") or "")
    raw = message_text(message)
    data = tool_result_dict(raw)
    if data is None:
        tool = names.get(call_id, "tool")
        return f"{tool}: returned text\n\n{compact_tool_content(raw)}"

    outer_tool = str(data.get("tool") or "")
    result = data.get("result") if isinstance(data.get("result"), dict) else data
    tool = names.get(call_id) or outer_tool or str(result.get("action") or "tool")
    ok = result.get("ok", data.get("ok"))
    status = result.get("status", data.get("status", ""))
    header_parts = [tool]
    if ok is not None:
        header_parts.append(f"ok={bool(ok)}")
    if status:
        header_parts.append(f"status={status}")

    content = str(result.get("content") or result.get("text") or result.get("stdout") or "")
    if not content and isinstance(result.get("files"), list):
        content = "\n".join(str(item) for item in result["files"])
    if not content and isinstance(result.get("matches"), list):
        content = "\n".join(str(item) for item in result["matches"])
    if not content and result.get("command_text"):
        content = str(result.get("command_text"))
    if not content and result.get("error"):
        content = str(result.get("error"))
    if not content:
        content = json.dumps(result, ensure_ascii=False, indent=2)

    return f"{' '.join(header_parts)}\n\n{compact_tool_content(content)}"


def summarize_tool_messages(messages: list[dict[str, Any]]) -> str:
    names = tool_call_name_map(messages)
    tool_messages = [message for message in messages if message.get("role") == "tool"]
    if not tool_messages:
        return ""
    summaries = [summarize_one_tool_message(message, names) for message in tool_messages[-3:]]
    return "Tool result summary:\n\n" + "\n\n---\n\n".join(summaries)


def concise_tool_result(task: str, summary: str) -> str | None:
    """Answer a narrowly phrased read request without asking DG to summarize tools."""
    task_lower = task.lower()
    wants_only_expression = (
        "expression" in task_lower
        and "return" in task_lower
        and bool(re.search(r"\b(?:state|reply|answer)\s+only\b", task_lower))
    )
    if not wants_only_expression:
        return None

    matches = re.findall(r"(?m)^\s*(?:\d+:\s*)?return\s+(.+?)\s*$", summary)
    if not matches:
        return None
    expression = matches[-1].strip()
    if not expression or len(expression) > 240:
        return None
    return expression


def task_file_hints(task: str, limit: int = 8) -> list[str]:
    hints: list[str] = []
    for match in re.findall(r"[\w./\\-]+\.[A-Za-z0-9_]+", task):
        text = match.replace("\\", "/").strip("./")
        if text and text not in hints:
            hints.append(text)
    return hints[:limit]


def task_search_hint(task: str) -> str:
    quoted = re.search(r"[`'\"]([^`'\"]{2,120})[`'\"]", task)
    if quoted:
        return quoted.group(1).strip()
    match = re.search(r"\b(?:search|grep|find)\s+(?:for\s+)?([A-Za-z_][A-Za-z0-9_:.()/-]{2,120})", task, flags=re.I)
    if match:
        return match.group(1).strip()
    symbol = re.search(r"\b([A-Za-z_][A-Za-z0-9_]{2,}\([^)]{0,80}\)|[A-Za-z_][A-Za-z0-9_]{3,})\b", task)
    return symbol.group(1).strip() if symbol else task[:120].strip()


def dg_tool_arguments(tool: dict[str, Any], task: str) -> dict[str, Any] | None:
    name = tool_name(tool)
    task_lower = task.lower()
    files = task_file_hints(task)
    if name == "dg_repo_status":
        return {"repo": "."}
    if name == "dg_git_diff":
        args: dict[str, Any] = {"repo": ".", "stat": "stat" in task_lower}
        if "cached" in task_lower or "staged" in task_lower:
            args["cached"] = True
        if files:
            args["files"] = files
        return args
    if name == "dg_list_files":
        args = {"repo": ".", "limit": 200}
        glob_match = re.search(r"(\*\.[A-Za-z0-9_]+)", task)
        if glob_match:
            args["globs"] = [glob_match.group(1)]
        return args
    if name == "dg_read_file":
        if not files:
            return None
        return {"repo": ".", "path": files[0], "start_line": 1, "max_lines": 160}
    if name == "dg_search":
        args = {"repo": ".", "query": task_search_hint(task), "max_matches": 80}
        glob_match = re.search(r"(\*\.[A-Za-z0-9_]+)", task)
        if glob_match:
            args["globs"] = [glob_match.group(1)]
        return args
    if name == "dg_repo_pack":
        return {"repo": ".", "style": "markdown", "max_chars": 20000}
    if name == "dg_repo_map":
        args = {"repo": ".", "map_tokens": 2048, "map_only": True, "max_chars": 20000}
        if files:
            args["paths"] = files
        return args
    if name == "dg_ast_grep":
        args = {"repo": ".", "pattern": task_search_hint(task), "max_matches": 80}
        if "python" in task_lower or "*.py" in task_lower:
            args["lang"] = "python"
        if files:
            args["paths"] = files
        return args
    if name == "dg_code_outline":
        args = {"repo": ".", "items": "auto", "view": "auto", "max_items": 200}
        if "python" in task_lower or "*.py" in task_lower:
            args["lang"] = "python"
        if files:
            args["paths"] = files
        return args
    if name == "dg_agent":
        args = {
            "repo": ".",
            "task": task,
            "mode": "auto",
            "execute": False,
            "dry_run": True,
        }
        if files:
            args["files"] = files
        return args
    if name == "dg_session":
        args: dict[str, Any] = {
            "repo": ".",
            "task": task,
            "dry_run": True,
            "rollback_on_failure": True,
            "allow_dirty": True,
        }
        if files:
            args["files"] = files
        return args
    if name == "dg_context":
        args = {
            "repo": ".",
            "task": task,
            "format": "json",
            "max_files": 3,
            "max_snippet_chars": 1200,
        }
        if files:
            args["files"] = files
        return args
    if name == "dg_rag_context":
        return {
            "repo": ".",
            "task": task,
            "max_context_chars": 900,
            "max_files": 3,
            "max_tokens": 128,
        }
    if name == "dg_session_artifact":
        artifact = "final_diff"
        if "context" in task_lower:
            artifact = "context_md"
        elif "stdout" in task_lower or "output" in task_lower:
            artifact = "stdout"
        elif "stderr" in task_lower or "error" in task_lower or "log" in task_lower:
            artifact = "stderr"
        elif "plan" in task_lower:
            artifact = "plan"
        elif "report" in task_lower:
            artifact = "session_json"
        return {"session": "latest", "artifact": artifact}
    return None


def select_dg_tool(tools: list[Any], task: str) -> dict[str, Any] | None:
    task_lower = task.lower()
    if any(word in task_lower for word in ("git status", "repo status", "working tree", "untracked")):
        tool = select_named_tool(tools, {"dg_repo_status"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("git diff", "diff stat", "working diff", "staged diff", "cached diff")):
        tool = select_named_tool(tools, {"dg_git_diff"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("list files", "show files", "file list", "which files")):
        tool = select_named_tool(tools, {"dg_list_files"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("read file", "show file", "open file", "cat ")):
        tool = select_named_tool(tools, {"dg_read_file"})
        if tool is not None and dg_tool_arguments(tool, task) is not None:
            return tool
    if any(word in task_lower for word in ("grep", "search for", "rg ")):
        tool = select_named_tool(tools, {"dg_search"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("repo map", "repository map", "aider map")):
        tool = select_named_tool(tools, {"dg_repo_map"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("repo pack", "repository pack", "repomix", "pack repo")):
        tool = select_named_tool(tools, {"dg_repo_pack"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("code outline", "outline", "symbols", "symbol list", "structure")):
        tool = select_named_tool(tools, {"dg_code_outline"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("ast-grep", "ast grep", "structural search")):
        tool = select_named_tool(tools, {"dg_ast_grep"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("diff", "artifact", "session output", "latest session", "stdout", "stderr", "log")):
        tool = select_named_tool(tools, {"dg_session_artifact"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("edit", "fix", "change", "update", "implement", "modify", "patch", "repair")):
        tool = select_named_tool(tools, {"dg_session"})
        if tool is not None:
            return tool
        tool = select_named_tool(tools, {"dg_agent"})
        if tool is not None:
            return tool
    if any(word in task_lower for word in ("rag", "retrieve", "search", "find", "inspect", "explain", "where", "context")):
        tool = select_named_tool(tools, {"dg_rag_context", "dg_context"})
        if tool is not None:
            return tool
        tool = select_named_tool(tools, {"dg_agent"})
        if tool is not None:
            return tool
    return select_named_tool(tools, {"dg_context", "dg_rag_context", "dg_agent", "dg_session"})


def qwen_read_file_arguments(tool: dict[str, Any], task: str, repo: str) -> dict[str, Any] | None:
    """Build only the narrow file-read call understood by Qwen Code."""
    files = task_file_hints(task, limit=1)
    if not files:
        return None
    file_path = files[0]
    if re.match(r"^[A-Za-z]:[\\/]", repo):
        file_path = repo.rstrip("\\/") + "\\" + file_path.replace("/", "\\")
    schema = tool_schema(tool)
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    for name in ("file_path", "path", "filePath"):
        if name in properties:
            return {name: file_path}
    return None


def qwen_edit_request(task: str) -> bool:
    return bool(re.search(r"\b(?:edit|fix|change|update|implement|modify|patch|write|create|delete|remove|rename)\b", task, flags=re.I))


def tool_delegate(
    messages: list[dict[str, Any],],
    tools: list[Any],
    *,
    windows_opencode: bool = False,
    qwen_code: bool = False,
    qwen_repo: str = "",
) -> dict[str, Any] | None:
    tool = select_command_tool(tools)
    if any(message.get("role") == "tool" for message in messages):
        summary = summarize_tool_messages(messages)
        concise = concise_tool_result(latest_task(messages), summary) if (windows_opencode or qwen_code) else None
        return {
            "content": concise or summary,
            "tool_call": None,
        }

    task = qwen_user_task(messages) if qwen_code else latest_task(messages)
    if not task:
        if qwen_code:
            return {"content": "No user task is pending.", "tool_call": None}
        return None

    # The native Windows Qwen Code CLI exposes rich local tools, but this
    # proxy deliberately authorizes only an explicit read_file call. Edits
    # remain on the verified Aider path until Qwen's Windows runtime is stable.
    if qwen_code:
        trace_event(
            {
                "kind": "qwen_tool_delegate",
                "task": task[:600],
                "tool_names": [tool_name(item) for item in tools if isinstance(item, dict)][:80],
            }
        )
        if qwen_edit_request(task):
            return {
                "content": "Qwen Code integration is read-only on this host. Use the Aider local session for repository edits.",
                "tool_call": None,
            }
        read_file = select_named_tool(tools, {"read_file"})
        if read_file is not None:
            arguments = qwen_read_file_arguments(read_file, task, qwen_repo)
            if arguments is not None:
                return {
                    "content": None,
                    "tool_call": {
                        "id": "call_" + uuid.uuid4().hex[:24],
                        "type": "function",
                        "function": {
                            "name": tool_name(read_file),
                            "arguments": json.dumps(arguments, ensure_ascii=False),
                        },
                    },
                }
        return {
            "content": "Qwen Code read-only mode requires an explicit relative file path in the request.",
            "tool_call": None,
        }

    if tool is not None:
        command = build_windows_opencode_command(task) if windows_opencode else build_session_command(task)
        arg_name = command_argument_name(tool)
        return {
            "content": None,
            "tool_call": {
                "id": "call_" + uuid.uuid4().hex[:24],
                "type": "function",
                "function": {
                    "name": tool_name(tool),
                    "arguments": json.dumps({arg_name: command}, ensure_ascii=False),
                },
            },
        }

    tool = select_dg_tool(tools, task)
    if tool is None:
        return None
    args = dg_tool_arguments(tool, task)
    if args is None:
        return None
    return {
        "content": None,
        "tool_call": {
            "id": "call_" + uuid.uuid4().hex[:24],
            "type": "function",
            "function": {
                "name": tool_name(tool),
                "arguments": json.dumps(args, ensure_ascii=False),
            },
        },
    }


def responses_input_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "function_call_output":
                output = item.get("output", "")
                if output:
                    parts.append(str(output))
                continue
            content = item.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for chunk in content:
                    if isinstance(chunk, dict):
                        text = chunk.get("text") or chunk.get("input_text") or chunk.get("output_text")
                        if text:
                            parts.append(str(text))
                    elif isinstance(chunk, str):
                        parts.append(chunk)
        return "\n".join(part for part in parts if part)
    return str(value or "")


def responses_messages(body: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    instructions = body.get("instructions")
    if isinstance(instructions, str) and instructions.strip():
        messages.append({"role": "system", "content": instructions.strip()})
    text = responses_input_text(body.get("input"))
    if text.strip():
        role = "tool" if any(isinstance(item, dict) and item.get("type") == "function_call_output" for item in (body.get("input") or [])) else "user"
        messages.append({"role": role, "content": text.strip()})
    return messages


def response_base(model: str, body: dict[str, Any], output: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": "resp_" + uuid.uuid4().hex,
        "object": "response",
        "created_at": time.time(),
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "instructions": body.get("instructions"),
        "metadata": body.get("metadata") or {},
        "model": model,
        "output": output,
        "parallel_tool_calls": bool(body.get("parallel_tool_calls", True)),
        "temperature": body.get("temperature"),
        "tool_choice": body.get("tool_choice") or "auto",
        "tools": body.get("tools") or [],
        "top_p": body.get("top_p"),
        "max_output_tokens": body.get("max_output_tokens"),
        "previous_response_id": body.get("previous_response_id"),
        "reasoning": body.get("reasoning"),
        "text": body.get("text"),
        "truncation": body.get("truncation"),
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def responses_message_response(model: str, body: dict[str, Any], content: str) -> JSONResponse:
    return JSONResponse(
        response_base(
            model,
            body,
            [
                {
                    "id": "msg_" + uuid.uuid4().hex,
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": content, "annotations": []}],
                }
            ],
        )
    )


def responses_function_call_response(model: str, body: dict[str, Any], tool_call: dict[str, Any]) -> JSONResponse:
    function = tool_call["function"]
    return JSONResponse(
        response_base(
            model,
            body,
            [
                {
                    "id": "fc_" + uuid.uuid4().hex,
                    "type": "function_call",
                    "status": "completed",
                    "call_id": tool_call["id"],
                    "name": function["name"],
                    "arguments": function["arguments"],
                }
            ],
        )
    )


def backend_json_request(payload: dict[str, Any], raw_output: bool = False) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if raw_output:
        headers["X-DG-Raw-Output"] = "1"
    req = urllib.request.Request(
        f"{BACKEND_BASE}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
    )
    last_error = ""
    for attempt in range(1, max(1, BACKEND_RETRIES) + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                if not text.strip():
                    raise ValueError("backend returned an empty response body")
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"backend returned non-JSON response: {text[:500]}") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"backend HTTP {exc.code}: {detail}"
            trace_event({"kind": "backend_error", "attempt": attempt, "error": last_error})
        except Exception as exc:
            last_error = f"backend request failed: {exc}"
            trace_event({"kind": "backend_error", "attempt": attempt, "error": last_error})
        if attempt < BACKEND_RETRIES:
            time.sleep(0.25 * attempt)
    raise HTTPException(status_code=502, detail=last_error or "backend request failed")


def normalize_listing(raw: str, files: dict[str, str]) -> str:
    raw = sanitize_backend_text(raw)
    raw = re.sub(r"`{6,}([a-zA-Z0-9_+.-]+)", r"```\n```\1", raw)
    if not raw:
        return raw

    outputs: list[str] = []
    for path in files:
        escaped = re.escape(path)
        patterns = [
            rf"(?ims)(?:^|\n)(?:Filename:\s*)?{escaped}\s*\n(?:Code:\s*)?```[a-z0-9_+.-]*\n(.*?)\n```",
            rf"(?ims)(?:^|\n)Filename:\s*{escaped}\s*\nCode:\s*```[a-z0-9_+.-]*\n(.*?)\n```",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw)
            if match:
                code = textwrap.dedent(match.group(1)).strip("\n")
                lang = language_for(path)
                outputs.append(f"{path}\n```{lang}\n{code}\n```")
                break

    if outputs:
        return "\n\n".join(outputs)

    if len(files) == 1:
        path = next(iter(files))
        blocks = re.findall(r"(?ims)^[ \t]*```[a-z0-9_+.-]*\n(.*?)\n[ \t]*```", raw)
        if blocks:
            code = textwrap.dedent(blocks[-1]).strip("\n")
            lang = language_for(path)
            return f"{path}\n```{lang}\n{code}\n```"
        partial = re.findall(r"(?ims)```[a-z0-9_+.-]*\n(.*)$", raw)
        if partial:
            code = textwrap.dedent(partial[-1]).strip("\n` ")
            lang = language_for(path)
            return f"{path}\n```{lang}\n{code}\n```"

    return raw


def is_normalized_listing(text: str, files: dict[str, str]) -> bool:
    for path in files:
        escaped = re.escape(path)
        if re.search(rf"(?ms)^{escaped}\s*\n```[a-z0-9_+.-]*\n.*?\n```", text):
            return True
    return False


def python_string(value: str) -> str:
    return repr(value)


def numeric_literal(value: str) -> str:
    value = value.strip()
    try:
        parsed = float(value)
    except ValueError:
        return value
    if parsed.is_integer():
        return str(int(parsed))
    return value


def comparison_operator(phrase: str) -> str | None:
    normalized = re.sub(r"\s+", " ", phrase.strip().lower())
    return {
        ">=": ">=",
        "greater than or equal to": ">=",
        "greater or equal to": ">=",
        "at least": ">=",
        ">": ">",
        "greater than": ">",
        "<=": "<=",
        "less than or equal to": "<=",
        "less or equal to": "<=",
        "at most": "<=",
        "<": "<",
        "less than": "<",
        "==": "==",
        "equal to": "==",
        "equals": "==",
    }.get(normalized)


def derived_return_hint_from_task(task: str) -> str | None:
    exact = re.search(r"(?im)^Derived exact code constraint:\s*\n\s*(return\s+[^\n]+)", task)
    if exact:
        return exact.group(1).strip()

    behavior = re.search(
        r"return\s+['\"]([^'\"]+)['\"]\s+when\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
        r"(?:is\s+)?(greater than or equal to|greater or equal to|at least|>=|greater than|>|"
        r"less than or equal to|less or equal to|at most|<=|less than|<|equal to|equals|==)\s+"
        r"(-?\d+(?:\.\d+)?)\s*,?\s+otherwise\s+return\s+['\"]([^'\"]+)['\"]",
        task,
        flags=re.I | re.S,
    )
    if not behavior:
        return None
    true_value, param, op_phrase, threshold, false_value = behavior.groups()
    op = comparison_operator(op_phrase)
    if not op:
        return None
    return (
        f"return {python_string(true_value)} "
        f"if {param} {op} {numeric_literal(threshold)} "
        f"else {python_string(false_value)}"
    )


def exact_sample_return_hint(task: str, content: str) -> str | None:
    match = re.search(
        r"([A-Za-z_][A-Za-z0-9_]*)\(\s*['\"]([^'\"]+)['\"]\s*\)\s+returns\s+exactly\s+(.+?)(?=\s+Keep\b|\.?\s*$|\n)",
        task,
        flags=re.I | re.S,
    )
    if not match:
        return None
    func, sample_value, expected = match.groups()
    def_match = re.search(rf"(?m)^def\s+{re.escape(func)}\(([^)]*)\):", content)
    if not def_match:
        return None
    params = [part.strip().split("=")[0].strip() for part in def_match.group(1).split(",") if part.strip()]
    if len(params) != 1:
        return None
    param = params[0]
    template = expected.strip().strip("`'\"").replace(sample_value, "{" + param + "}")
    if "{" + param + "}" not in template:
        return None
    return f'return f"{template}"'


def expression_return_hint_from_task(task: str, content: str) -> str | None:
    """Derive a constrained arithmetic return replacement for one Python file."""
    match = re.search(
        r"\breturns?\s+(?:exactly\s+)?(.+?)\s+instead\s+of\s+(.+?)(?:[.!?]\s|[.!?]$|\n|$)",
        task,
        flags=re.I | re.S,
    )
    if not match:
        return None
    wanted, current = (value.strip().strip("`'\"") for value in match.groups())
    allowed = re.compile(r"[A-Za-z0-9_ \t()+\-*/%<>=!&|~.,]+$")
    if not wanted or not current or not allowed.fullmatch(wanted) or not allowed.fullmatch(current):
        return None

    functions = list(re.finditer(r"(?m)^\ufeff?\s*def\s+[A-Za-z_][A-Za-z0-9_]*\(([^)]*)\):", content))
    returns = re.findall(r"(?m)^\s*return\s+([^\r\n]+)$", content)
    if len(functions) != 1 or len(returns) != 1:
        return None
    params = {
        item.strip().split("=")[0].strip()
        for item in functions[0].group(1).split(",")
        if item.strip()
    }
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", wanted))
    if not identifiers.issubset(params | {"True", "False", "None"}):
        return None
    normalize = lambda value: re.sub(r"\s+", "", value)
    if normalize(returns[0]) != normalize(current):
        return None
    return f"return {wanted}"


def apply_return_hint_to_content(content: str, hint: str) -> str | None:
    pattern = re.compile(r"(?m)^(\s*)return\b[^\r\n]*$")
    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        return None
    match = matches[0]
    updated = content[: match.start()] + f"{match.group(1)}{hint}" + content[match.end() :]
    return updated if updated != content else None


def fallback_listing_from_task(task: str, files: dict[str, str]) -> str:
    if len(files) != 1:
        return ""
    path, content = next(iter(files.items()))
    if Path(path).suffix.lower() != ".py":
        return ""
    hint = (
        derived_return_hint_from_task(task)
        or exact_sample_return_hint(task, content)
        or expression_return_hint_from_task(task, content)
    )
    if not hint:
        return ""
    updated = apply_return_hint_to_content(content, hint)
    if not updated:
        return ""
    lang = language_for(path)
    return f"{path}\n```{lang}\n{updated.rstrip()}\n```"


def unchanged_listing(files: dict[str, str]) -> str:
    """Return a valid whole-file listing that cannot alter the selected files."""
    listings: list[str] = []
    for path, content in files.items():
        listings.append(f"{path}\n```{language_for(path)}\n{content.rstrip()}\n```")
    return "\n\n".join(listings)


def normalized_listing_is_safe(text: str, files: dict[str, str], task: str = "") -> bool:
    """Reject model leakage before an upstream whole-file editor writes it."""
    for path in files:
        escaped = re.escape(path)
        match = re.search(rf"(?ms)^{escaped}\s*\n```[a-z0-9_+.-]*\n(.*?)\n```", text)
        if not match:
            return False
        code = match.group(1)
        if "```" in code or "<|channel" in code or "<|message" in code:
            return False
        if files[path].strip() and not code.strip():
            return False
        if Path(path).suffix.lower() == ".py":
            try:
                compile(code.lstrip("\ufeff"), path, "exec")
            except (SyntaxError, ValueError, TypeError):
                return False
            original_defs = set(re.findall(r"(?m)^\ufeff?\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\(", files[path]))
            candidate_defs = set(re.findall(r"(?m)^\ufeff?\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\(", code))
            permits_removal = bool(re.search(r"\b(delete|remove)\b", task, flags=re.I))
            if original_defs and not permits_removal and not original_defs.issubset(candidate_defs):
                return False
    return True


def completion_response(model: str, content: str) -> JSONResponse:
    return JSONResponse(
        {
            "id": "chatcmpl-" + uuid.uuid4().hex,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )


def tool_call_completion_response(model: str, tool_call: dict[str, Any], stream: bool) -> JSONResponse | StreamingResponse:
    if stream:
        return streaming_tool_call_response(model, tool_call)
    return JSONResponse(
        {
            "id": "chatcmpl-" + uuid.uuid4().hex,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )


def streaming_completion_response(model: str, content: str) -> StreamingResponse:
    chunk_id = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    def event_stream():
        first = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant"},
                    "finish_reason": None,
                }
            ],
        }
        yield "data: " + json.dumps(first, ensure_ascii=False) + "\n\n"
        if content:
            body = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": content},
                        "finish_reason": None,
                    }
                ],
            }
            yield "data: " + json.dumps(body, ensure_ascii=False) + "\n\n"
        final = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }
        yield "data: " + json.dumps(final, ensure_ascii=False) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def streaming_tool_call_response(model: str, tool_call: dict[str, Any]) -> StreamingResponse:
    chunk_id = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    def event_stream():
        yield "data: " + json.dumps(
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": tool_call["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tool_call["function"]["name"],
                                        "arguments": tool_call["function"]["arguments"],
                                    },
                                }
                            ],
                        },
                        "finish_reason": None,
                    }
                ],
            },
            ensure_ascii=False,
        ) + "\n\n"
        yield "data: " + json.dumps(
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            },
            ensure_ascii=False,
        ) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def openai_compatible_response(model: str, content: str, stream: bool) -> JSONResponse | StreamingResponse:
    if stream:
        return streaming_completion_response(model, content)
    return completion_response(model, content)


def gateway_base_url() -> str:
    return f"http://{HOST}:{PORT}"


def model_card() -> dict[str, Any]:
    return {
        "id": PROXY_MODEL,
        "object": "model",
        "created": 0,
        "owned_by": "local",
        "backend_model": BACKEND_MODEL,
        "backend_base": BACKEND_BASE,
        "max_input_tokens": 768,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_file_chars": MAX_FILE_CHARS,
        "mode": "safe_agent_gateway",
        "generic_generation": bool(ENABLE_GENERIC_GENERATION),
        "recommended_for": [
            "bounded file edits through Aider-compatible prompts",
            "OpenAI Chat Completions clients with shell-command tool delegation",
            "OpenAI Responses API clients with function-call delegation",
            "mini-swe-agent style command-loop delegation",
        ],
        "not_recommended_for": [
            "large-context free-form chat",
            "native multi-tool reasoning inside the model",
            "repository-wide edits without dg_agent session/task wrappers",
        ],
        "tool_manifest_url": f"{gateway_base_url()}/v1/agent/tool_manifest",
    }


def mcp_resource_hints() -> list[str]:
    return [
        "dg://agent-hub/markdown",
        "dg://command-kit/markdown",
        "dg://ide-clients/markdown",
        "dg://codex-profile/config",
        "dg://client-handoff/markdown",
        "dg://sessions/latest",
        "dg://sessions/latest/diff",
    ]


def agent_routes() -> dict[str, Any]:
    root = str(DG_ROOT)
    return {
        "recommended_entrypoint": f"{root}/scripts/dg_agent.sh session --repo /repo --task '...' --rollback-on-failure",
        "routes": [
            {
                "id": "chat_completions",
                "use_for": "OpenAI-compatible chat clients and tool-call delegation",
                "method": "POST",
                "url": f"{gateway_base_url()}/v1/chat/completions",
                "model": PROXY_MODEL,
            },
            {
                "id": "responses",
                "use_for": "OpenAI Responses API clients with function-call delegation",
                "method": "POST",
                "url": f"{gateway_base_url()}/v1/responses",
                "model": PROXY_MODEL,
            },
            {
                "id": "session_api",
                "use_for": "dry-run or opt-in execution of artifacted dg_agent.sh session",
                "method": "POST",
                "url": f"{gateway_base_url()}/v1/agent/session",
                "input_schema": agent_session_input_schema(),
                "execution_enabled": bool(ENABLE_AGENT_EXEC),
            },
            {
                "id": "tool_runtime",
                "use_for": "execute DG-specific OpenAI tool calls over HTTP",
                "method": "POST",
                "url": f"{gateway_base_url()}/v1/agent/tool",
                "input_schema": agent_tool_runtime_input_schema(),
            },
            {
                "id": "context_api",
                "use_for": "build a compact repo context pack without MCP",
                "method": "POST",
                "url": f"{gateway_base_url()}/v1/agent/context",
                "input_schema": agent_context_input_schema(),
            },
            {
                "id": "rag_context_api",
                "use_for": "retrieve read-only rg-based RAG context without MCP or model calls",
                "method": "POST",
                "url": f"{gateway_base_url()}/v1/agent/rag",
                "input_schema": agent_rag_context_input_schema(),
            },
            {
                "id": "session_artifacts",
                "use_for": "read artifacted dg_agent.sh session results without MCP",
                "method": "GET",
                "url": f"{gateway_base_url()}/v1/agent/sessions",
            },
            {
                "id": "agent_runs",
                "use_for": "read high-level dg_agent run reports and transcripts without MCP",
                "method": "GET",
                "url": f"{gateway_base_url()}/v1/agent/runs",
            },
            {
                "id": "latest_session_diff",
                "use_for": "read the latest preserved final.diff artifact",
                "method": "GET",
                "url": f"{gateway_base_url()}/v1/agent/sessions/latest/diff",
            },
            {
                "id": "model_card",
                "use_for": "discover limits, safe-mode behavior, and wrapper recommendations",
                "method": "GET",
                "url": f"{gateway_base_url()}/v1/model_card",
            },
            {
                "id": "tool_manifest",
                "use_for": "discover OpenAI tool schemas and safe local action contracts",
                "method": "GET",
                "url": f"{gateway_base_url()}/v1/agent/tool_manifest",
            },
            {
                "id": "actions",
                "use_for": "discover the safe local action list without the full tool manifest",
                "method": "GET",
                "url": f"{gateway_base_url()}/v1/agent/actions",
            },
            {
                "id": "well_known_agent",
                "use_for": "generic agent discovery for local wrappers",
                "method": "GET",
                "url": f"{gateway_base_url()}/.well-known/agent.json",
            },
            {
                "id": "openapi",
                "use_for": "OpenAPI schema generated by FastAPI for custom clients",
                "method": "GET",
                "url": f"{gateway_base_url()}/openapi.json",
            },
            {
                "id": "mcp",
                "use_for": "repository tools, resources, prompts, and OSS wrappers",
                "transport": "stdio",
                "command": f"{root}/scripts/run_mcp_server.sh",
                "resources": mcp_resource_hints(),
            },
            {
                "id": "litellm",
                "use_for": "OpenAI-compatible IDE clients that expect a gateway proxy",
                "base_url": "http://127.0.0.1:4100/v1",
                "model": "diffusiongemma-local",
            },
        ],
    }


def agent_tool_manifest() -> dict[str, Any]:
    root = str(DG_ROOT)
    session_template = build_session_command("...")
    return {
        "schema_version": "dg.agent.tool_manifest.v1",
        "name": "DiffusionGemma local safe agent tool manifest",
        "base_url": gateway_base_url(),
        "model": PROXY_MODEL,
        "recommended_execution": {
            "kind": "delegate_to_dg_session",
            "command_template": session_template,
            "why": "Keeps arbitrary OSS-agent planning out of the fragile generic model path and uses artifacts plus rollback.",
        },
        "openai_chat_completions": {
            "endpoint": f"{gateway_base_url()}/v1/chat/completions",
            "model": PROXY_MODEL,
            "tools": chat_dg_tool_schemas(),
        },
        "openai_responses": {
            "endpoint": f"{gateway_base_url()}/v1/responses",
            "model": PROXY_MODEL,
            "tools": responses_dg_tool_schemas(),
            "streaming": False,
        },
        "http_session_api": {
            "endpoint": f"{gateway_base_url()}/v1/agent/session",
            "method": "POST",
            "input_schema": agent_session_input_schema(),
            "execution_enabled": bool(ENABLE_AGENT_EXEC),
            "default_mode": "dry_run",
        },
        "http_tool_runtime_api": {
            "endpoint": f"{gateway_base_url()}/v1/agent/tool",
            "method": "POST",
            "input_schema": agent_tool_runtime_input_schema(),
            "supported_tools": HTTP_TOOL_NAMES,
            "safe_mode": "execute_command is blocked from arbitrary shell execution; DG tools delegate to safe bounded endpoints.",
        },
        "http_agent_api": {
            "endpoint": f"{gateway_base_url()}/v1/agent/tool",
            "method": "POST",
            "tool_name": "dg_agent",
            "input_schema": agent_facade_input_schema(),
            "default_mode": "auto",
            "read_route": "scripts/dg_agent.sh agent --mode read",
            "edit_route": "scripts/dg_agent.sh agent --mode edit",
            "execution_enabled": bool(ENABLE_AGENT_EXEC),
        },
        "http_repo_tools": {
            "endpoint": f"{gateway_base_url()}/v1/agent/tool",
            "method": "POST",
            "mode": "read_only",
            "tools": {
                "dg_repo_status": repo_status_input_schema(),
                "dg_git_diff": git_diff_input_schema(),
                "dg_list_files": list_files_input_schema(),
                "dg_read_file": read_file_input_schema(),
                "dg_search": search_input_schema(),
                "dg_repo_pack": repo_pack_input_schema(),
                "dg_repo_map": repo_map_input_schema(),
                "dg_ast_grep": ast_grep_input_schema(),
                "dg_code_outline": code_outline_input_schema(),
            },
        },
        "http_oss_repo_tools": {
            "endpoint": f"{gateway_base_url()}/v1/agent/tool",
            "method": "POST",
            "mode": "read_only",
            "tool_names": OSS_REPO_TOOL_NAMES,
            "delegates_to": {
                "dg_repo_pack": "Repomix",
                "dg_repo_map": "Aider repo-map",
                "dg_ast_grep": "ast-grep",
                "dg_code_outline": "ast-grep based outline",
            },
        },
        "http_session_artifacts": {
            "list_endpoint": f"{gateway_base_url()}/v1/agent/sessions",
            "latest_endpoint": f"{gateway_base_url()}/v1/agent/sessions/latest",
            "latest_diff_endpoint": f"{gateway_base_url()}/v1/agent/sessions/latest/diff",
            "latest_artifact_template": f"{gateway_base_url()}/v1/agent/sessions/latest/artifacts/{{artifact}}",
            "available_artifacts": sorted(set(SESSION_ARTIFACT_FILENAMES) | set(SESSION_ARTIFACT_ALIASES)),
        },
        "http_agent_run_artifacts": {
            "list_endpoint": f"{gateway_base_url()}/v1/agent/runs",
            "latest_endpoint": f"{gateway_base_url()}/v1/agent/runs/latest",
            "latest_artifact_template": f"{gateway_base_url()}/v1/agent/runs/latest/artifacts/{{artifact}}",
            "available_artifacts": sorted(set(AGENT_RUN_ARTIFACT_FILENAMES) | set(AGENT_RUN_ARTIFACT_ALIASES)),
        },
        "http_context_api": {
            "endpoint": f"{gateway_base_url()}/v1/agent/context",
            "method": "POST",
            "input_schema": agent_context_input_schema(),
            "mode": "read_only",
            "delegates_to": f"{root}/scripts/dg_agent.sh context",
        },
        "http_rag_context_api": {
            "endpoint": f"{gateway_base_url()}/v1/agent/rag",
            "method": "POST",
            "input_schema": agent_rag_context_input_schema(),
            "mode": "read_only_retrieve_only",
            "delegates_to": f"{root}/scripts/dg_agent.sh rag --print-context",
        },
        "mini_swe_agent": {
            "action_block": "mswea_bash_command",
            "completion_marker": "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
            "delegated_command_contains": ["dg_agent.sh session", "--rollback-on-failure"],
        },
        "mcp": {
            "server_name": "diffusiongemma-local-agent",
            "transport": "stdio",
            "command": f"{root}/scripts/run_mcp_server.sh",
            "resources": mcp_resource_hints(),
            "recommended_optional_servers": ["repomix", "serena"],
        },
        "actions": [
            {
                "id": "run_dg_session",
                "endpoint": f"{gateway_base_url()}/v1/agent/session",
                "method": "POST",
                "input_schema": agent_session_input_schema(),
                "effect": "Builds or, when explicitly enabled, runs an artifacted dg_agent.sh session.",
                "safe_default": True,
                "execution_enabled": bool(ENABLE_AGENT_EXEC),
            },
            {
                "id": "execute_command_via_dg_session",
                "tool_name": "execute_command",
                "input_schema": command_tool_parameters(),
                "effect": "Runs the delegated shell command in the active repository.",
                "safe_default": True,
                "delegates_to": session_template,
            },
            {
                "id": "openai_dg_tool_schemas",
                "effect": "Expose copy-ready OpenAI Chat Completions and Responses API schemas for repo inspection, dg_session, dg_context, dg_rag_context, and dg_session_artifact.",
                "safe_default": True,
                "runtime_endpoint": f"{gateway_base_url()}/v1/agent/tool",
                "chat_tool_names": [item["function"]["name"] for item in chat_dg_tool_schemas()],
                "responses_tool_names": [item["name"] for item in responses_dg_tool_schemas()],
            },
            {
                "id": "execute_openai_tool_http",
                "effect": "Execute DG-specific OpenAI tool calls over HTTP and return a ready role=tool response payload.",
                "safe_default": True,
                "endpoint": f"{gateway_base_url()}/v1/agent/tool",
                "input_schema": agent_tool_runtime_input_schema(),
            },
            {
                "id": "run_high_level_agent_http",
                "tool_name": "dg_agent",
                "effect": "Use the high-level local agent facade over HTTP: read-only tasks run through tool-loop; edits default to dry-run unless HTTP execution is explicitly enabled.",
                "safe_default": True,
                "endpoint": f"{gateway_base_url()}/v1/agent/tool",
                "input_schema": agent_facade_input_schema(),
                "execution_enabled": bool(ENABLE_AGENT_EXEC),
            },
            {
                "id": "inspect_repo_http_tools",
                "effect": "Run bounded read-only repo inspection tools over HTTP for clients without MCP.",
                "safe_default": True,
                "endpoint": f"{gateway_base_url()}/v1/agent/tool",
                "tool_names": [*REPO_TOOL_NAMES, *OSS_REPO_TOOL_NAMES],
            },
            {
                "id": "inspect_repo_with_oss_http_tools",
                "effect": "Run upstream Repomix, Aider repo-map, and ast-grep/code-outline over HTTP for clients without MCP.",
                "safe_default": True,
                "endpoint": f"{gateway_base_url()}/v1/agent/tool",
                "tool_names": OSS_REPO_TOOL_NAMES,
            },
            {
                "id": "read_mcp_handoff",
                "effect": "Read MCP resources such as dg://agent-hub/markdown and dg://command-kit/markdown before choosing a route.",
                "safe_default": True,
                "resources": mcp_resource_hints(),
            },
            {
                "id": "read_session_artifact_http",
                "effect": "Read latest or indexed dg_agent.sh session artifacts over HTTP for clients without MCP.",
                "safe_default": True,
                "endpoints": {
                    "sessions": f"{gateway_base_url()}/v1/agent/sessions",
                    "latest_diff": f"{gateway_base_url()}/v1/agent/sessions/latest/diff",
                },
            },
            {
                "id": "read_agent_run_artifact_http",
                "tool_name": "dg_agent_run_artifact",
                "effect": "Read latest or indexed high-level dg_agent run artifacts and tool-loop transcripts over HTTP.",
                "safe_default": True,
                "endpoints": {
                    "runs": f"{gateway_base_url()}/v1/agent/runs",
                    "latest": f"{gateway_base_url()}/v1/agent/runs/latest",
                },
            },
            {
                "id": "build_context_http",
                "effect": "Build a compact rg-based repository context pack over HTTP without MCP.",
                "safe_default": True,
                "endpoint": f"{gateway_base_url()}/v1/agent/context",
                "input_schema": agent_context_input_schema(),
            },
            {
                "id": "retrieve_rag_context_http",
                "effect": "Retrieve read-only RAG context over HTTP without calling the model.",
                "safe_default": True,
                "endpoint": f"{gateway_base_url()}/v1/agent/rag",
                "input_schema": agent_rag_context_input_schema(),
            },
        ],
    }


def well_known_agent_manifest() -> dict[str, Any]:
    return {
        "schema_version": "dg.agent.v1",
        "name": "DiffusionGemma Local Agent Gateway",
        "description": "Local OpenAI-compatible safe gateway around DiffusionGemma with tool-call delegation, MCP resources, and OSS wrapper routes.",
        "base_url": gateway_base_url(),
        "model": PROXY_MODEL,
        "openapi_url": f"{gateway_base_url()}/openapi.json",
        "model_card_url": f"{gateway_base_url()}/v1/model_card",
        "capabilities_url": f"{gateway_base_url()}/v1/capabilities",
        "routes_url": f"{gateway_base_url()}/v1/agent/routes",
        "tool_manifest_url": f"{gateway_base_url()}/v1/agent/tool_manifest",
        "tool_runtime_url": f"{gateway_base_url()}/v1/agent/tool",
        "context_url": f"{gateway_base_url()}/v1/agent/context",
        "rag_context_url": f"{gateway_base_url()}/v1/agent/rag",
        "sessions_url": f"{gateway_base_url()}/v1/agent/sessions",
        "agent_runs_url": f"{gateway_base_url()}/v1/agent/runs",
        "mcp": agent_tool_manifest()["mcp"],
    }


def gateway_capabilities() -> dict[str, Any]:
    return {
        "ok": True,
        "name": "DiffusionGemma local safe agent gateway",
        "base_url": gateway_base_url(),
        "model": PROXY_MODEL,
        "backend": {"base_url": BACKEND_BASE, "model": BACKEND_MODEL},
        "limits": {
            "max_input_tokens": 768,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_file_chars": MAX_FILE_CHARS,
            "request_timeout_seconds": REQUEST_TIMEOUT,
            "backend_retries": BACKEND_RETRIES,
        },
        "openai_compat": {
            "chat_completions": True,
            "chat_streaming": True,
            "responses": True,
            "responses_streaming": False,
            "models": True,
            "tool_call_delegation": True,
            "native_model_tool_use": False,
        },
        "safe_mode": {
            "generic_generation": bool(ENABLE_GENERIC_GENERATION),
            "generic_default": "static safety response unless DG_AIDER_PROXY_ENABLE_GENERIC_GENERATION=1",
            "tool_delegation_command": build_session_command("..."),
            "http_session_execution": bool(ENABLE_AGENT_EXEC),
            "http_session_default": "dry_run; set DG_AIDER_PROXY_ENABLE_AGENT_EXEC=1 and execute=true for live execution",
        },
        "discovery": {
            "health": f"{gateway_base_url()}/healthz",
            "models": f"{gateway_base_url()}/v1/models",
            "model_card": f"{gateway_base_url()}/v1/model_card",
            "capabilities": f"{gateway_base_url()}/v1/capabilities",
            "routes": f"{gateway_base_url()}/v1/agent/routes",
            "session_api": f"{gateway_base_url()}/v1/agent/session",
            "tool_runtime": f"{gateway_base_url()}/v1/agent/tool",
            "context": f"{gateway_base_url()}/v1/agent/context",
            "rag_context": f"{gateway_base_url()}/v1/agent/rag",
            "sessions": f"{gateway_base_url()}/v1/agent/sessions",
            "latest_session": f"{gateway_base_url()}/v1/agent/sessions/latest",
            "latest_session_diff": f"{gateway_base_url()}/v1/agent/sessions/latest/diff",
            "agent_runs": f"{gateway_base_url()}/v1/agent/runs",
            "latest_agent_run": f"{gateway_base_url()}/v1/agent/runs/latest",
            "tool_manifest": f"{gateway_base_url()}/v1/agent/tool_manifest",
            "actions": f"{gateway_base_url()}/v1/agent/actions",
            "well_known_agent": f"{gateway_base_url()}/.well-known/agent.json",
            "openapi": f"{gateway_base_url()}/openapi.json",
        },
        "agent_routes": agent_routes()["routes"],
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "ok": True,
        "name": "DiffusionGemma local safe agent gateway",
        "health": "/healthz",
        "models": "/v1/models",
        "model_card": "/v1/model_card",
        "capabilities": "/v1/capabilities",
        "routes": "/v1/agent/routes",
    }


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "model": PROXY_MODEL,
        "backend_base": BACKEND_BASE,
        "backend_model": BACKEND_MODEL,
        "max_file_chars": MAX_FILE_CHARS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "generic_generation": bool(ENABLE_GENERIC_GENERATION),
        "model_card": "/v1/model_card",
        "capabilities": "/v1/capabilities",
        "routes": "/v1/agent/routes",
    }


@app.get("/v1/models")
def models() -> dict[str, Any]:
    card = model_card()
    return {"object": "list", "data": [card]}


@app.get("/v1/model_card")
def get_model_card() -> dict[str, Any]:
    return model_card()


@app.get("/v1/capabilities")
def capabilities() -> dict[str, Any]:
    return gateway_capabilities()


@app.get("/v1/agent/routes")
def get_agent_routes() -> dict[str, Any]:
    return agent_routes()


@app.get("/v1/agent/tool_manifest")
def get_agent_tool_manifest() -> dict[str, Any]:
    return agent_tool_manifest()


@app.get("/v1/agent/actions")
def get_agent_actions() -> dict[str, Any]:
    manifest = agent_tool_manifest()
    return {
        "schema_version": manifest["schema_version"],
        "model": manifest["model"],
        "actions": manifest["actions"],
    }


@app.post("/v1/agent/session")
def post_agent_session(body: dict[str, Any]) -> dict[str, Any]:
    return agent_session_action(body)


@app.post("/v1/agent/tool")
def post_agent_tool(body: dict[str, Any]) -> dict[str, Any]:
    return agent_tool_runtime_action(body)


@app.post("/v1/agent/context")
def post_agent_context(body: dict[str, Any]) -> dict[str, Any]:
    return agent_context_action(body)


@app.post("/v1/agent/rag")
def post_agent_rag_context(body: dict[str, Any]) -> dict[str, Any]:
    return agent_rag_context_action(body)


@app.get("/v1/agent/sessions")
def get_agent_sessions(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit), 100))
    reports = session_reports()
    return {
        "root": str(DEFAULT_SESSION_ROOT),
        "sessions": [session_summary(report) for report in reports[:limit]],
    }


@app.get("/v1/agent/sessions/latest")
def get_latest_agent_session() -> dict[str, Any]:
    report = load_session_report(latest=True)
    if report is None:
        return {"ok": False, "error": "no sessions found", "root": str(DEFAULT_SESSION_ROOT)}
    return {"ok": True, "summary": session_summary(report), "session": report}


@app.get("/v1/agent/sessions/latest/diff")
def get_latest_agent_session_diff() -> dict[str, Any]:
    report = load_session_report(latest=True)
    if report is None:
        return {"ok": False, "error": "no sessions found", "root": str(DEFAULT_SESSION_ROOT)}
    artifact = read_session_artifact(report, "final_diff")
    return {"session": session_summary(report), **artifact}


@app.get("/v1/agent/sessions/latest/artifacts/{artifact}")
def get_latest_agent_session_artifact(artifact: str) -> dict[str, Any]:
    report = load_session_report(latest=True)
    if report is None:
        return {"ok": False, "error": "no sessions found", "root": str(DEFAULT_SESSION_ROOT)}
    return {"session": session_summary(report), **read_session_artifact(report, artifact)}


@app.get("/v1/agent/sessions/{session_id}")
def get_agent_session(session_id: str) -> dict[str, Any]:
    report = load_session_report(session=session_id)
    if report is None:
        return {"ok": False, "error": f"session not found: {session_id}", "root": str(DEFAULT_SESSION_ROOT)}
    return {"ok": True, "summary": session_summary(report), "session": report}


@app.get("/v1/agent/sessions/{session_id}/artifacts/{artifact}")
def get_agent_session_artifact(session_id: str, artifact: str) -> dict[str, Any]:
    report = load_session_report(session=session_id)
    if report is None:
        return {"ok": False, "error": f"session not found: {session_id}", "root": str(DEFAULT_SESSION_ROOT)}
    return {"session": session_summary(report), **read_session_artifact(report, artifact)}


@app.get("/v1/agent/runs")
def get_agent_runs(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit), 100))
    reports = agent_run_reports()
    return {
        "ok": True,
        "root": str(DEFAULT_AGENT_RUN_ROOT),
        "runs": [agent_run_summary(report) for report in reports[:limit]],
    }


@app.get("/v1/agent/runs/latest")
def get_latest_agent_run() -> dict[str, Any]:
    report = load_agent_run_report(latest=True)
    if report is None:
        return {"ok": False, "error": "no agent runs found", "root": str(DEFAULT_AGENT_RUN_ROOT)}
    return {"ok": True, "summary": agent_run_summary(report), "run": report}


@app.get("/v1/agent/runs/latest/artifacts/{artifact}")
def get_latest_agent_run_artifact(artifact: str, limit: int = 200_000) -> dict[str, Any]:
    report = load_agent_run_report(latest=True)
    if report is None:
        return {"ok": False, "error": "no agent runs found", "root": str(DEFAULT_AGENT_RUN_ROOT)}
    limit = max(1_000, min(int(limit), 1_000_000))
    return {"run": agent_run_summary(report), **read_agent_run_artifact(report, artifact, limit=limit)}


@app.get("/v1/agent/runs/{run_id}")
def get_agent_run(run_id: str) -> dict[str, Any]:
    report = load_agent_run_report(run=run_id)
    if report is None:
        return {"ok": False, "error": f"agent run not found: {run_id}", "root": str(DEFAULT_AGENT_RUN_ROOT)}
    return {"ok": True, "summary": agent_run_summary(report), "run": report}


@app.get("/v1/agent/runs/{run_id}/artifacts/{artifact}")
def get_agent_run_artifact(run_id: str, artifact: str, limit: int = 200_000) -> dict[str, Any]:
    report = load_agent_run_report(run=run_id)
    if report is None:
        return {"ok": False, "error": f"agent run not found: {run_id}", "root": str(DEFAULT_AGENT_RUN_ROOT)}
    limit = max(1_000, min(int(limit), 1_000_000))
    return {"run": agent_run_summary(report), **read_agent_run_artifact(report, artifact, limit=limit)}


@app.get("/.well-known/agent.json")
def get_well_known_agent_manifest() -> dict[str, Any]:
    return well_known_agent_manifest()


@app.post("/v1/chat/completions", response_model=None)
def chat_completions(body: dict[str, Any], authorization: str | None = Header(default=None)) -> Any:
    messages = body.get("messages") or []
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be a list")

    compact_messages, files = compact_aider_prompt(messages)
    if compact_messages:
        task = latest_task(messages)
        trace_event({"kind": "compact_request", "messages": compact_messages, "files": list(files)})
        raw = call_backend(compact_messages, body)
        trace_event({"kind": "backend_raw", "raw": raw})
        content = normalize_listing(raw, files)
        if not is_normalized_listing(content, files) or not normalized_listing_is_safe(content, files, task):
            fallback = fallback_listing_from_task(task, files)
            if fallback:
                trace_event({"kind": "proxy_exact_repair", "reason": "malformed_or_unsafe_file_listing", "content": fallback})
                content = fallback
            else:
                content = unchanged_listing(files)
                trace_event({"kind": "proxy_unsafe_listing_noop", "content": content})
        trace_event({"kind": "proxy_response", "content": content})
        return openai_compatible_response(body.get("model") or PROXY_MODEL, content, bool(body.get("stream")))

    # Generic OpenAI-compatible traffic from OSS agents may include streaming
    # and tool schemas that the DG backend does not implement. Compact it into
    # a plain chat request instead of passing unsupported fields through.
    qwen_code = is_windows_qwen_client(authorization)
    tool_delegate_result = tool_delegate(
        messages,
        body.get("tools") if isinstance(body.get("tools"), list) else [],
        windows_opencode=is_windows_opencode_client(authorization),
        qwen_code=qwen_code,
        qwen_repo=qwen_repo_from_authorization(authorization) if qwen_code else "",
    )
    if tool_delegate_result is not None:
        trace_event({"kind": "tool_call_safe_delegate", "result": tool_delegate_result})
        tool_call = tool_delegate_result.get("tool_call")
        if isinstance(tool_call, dict):
            return tool_call_completion_response(
                body.get("model") or PROXY_MODEL,
                tool_call,
                bool(body.get("stream")),
            )
        return openai_compatible_response(
            body.get("model") or PROXY_MODEL,
            str(tool_delegate_result.get("content") or ""),
            bool(body.get("stream")),
        )

    mini_swe_content = safe_mini_swe_response(messages)
    if mini_swe_content is not None:
        trace_event({"kind": "mini_swe_safe_delegate", "content": mini_swe_content})
        return openai_compatible_response(body.get("model") or PROXY_MODEL, mini_swe_content, bool(body.get("stream")))

    if not ENABLE_GENERIC_GENERATION:
        trace_event(
            {
                "kind": "generic_safe_response",
                "had_tools": bool(body.get("tools")),
                "tool_names": [
                    tool_name(item)
                    for item in body.get("tools", [])
                    if isinstance(item, dict)
                ][:80],
                "stream": bool(body.get("stream")),
            }
        )
        raw = safe_generic_response(messages, bool(body.get("tools")), bool(body.get("stream")))
        return openai_compatible_response(body.get("model") or PROXY_MODEL, raw, bool(body.get("stream")))

    generic_messages = compact_generic_prompt(messages)
    trace_event(
        {
            "kind": "generic_request",
            "had_tools": bool(body.get("tools")),
            "stream": bool(body.get("stream")),
            "messages": generic_messages,
        }
    )
    try:
        # The DiffusionGemma visual backend is unstable with very tiny generic
        # completions. Keep OSS agent probes on the same safer token floor used
        # by the file-edit path.
        requested_tokens = int(body.get("max_tokens") or 128)
        generic_max_tokens = max(96, min(requested_tokens, 256))
        raw = call_backend(generic_messages, {**body, "max_tokens": generic_max_tokens})
    except HTTPException as exc:
        raw = (
            "Local DiffusionGemma compatibility mode could not complete this generic agent request. "
            f"Backend error: {exc.detail}. "
            "Use the Aider supervisor or task runner for reliable repository edits."
        )
    if not raw.strip():
        raw = (
            "Local DiffusionGemma compatibility mode returned an empty response. "
            "Use the Aider supervisor or task runner for reliable repository edits."
        )
    trace_event({"kind": "generic_response", "content": raw})
    return openai_compatible_response(body.get("model") or PROXY_MODEL, raw, bool(body.get("stream")))


@app.post("/v1/responses", response_model=None)
def responses_create(body: dict[str, Any], authorization: str | None = Header(default=None)) -> Any:
    if body.get("stream"):
        raise HTTPException(status_code=400, detail="Responses API streaming is not supported by the local DG safe proxy")

    model = body.get("model") or PROXY_MODEL
    messages = responses_messages(body)
    tools = body.get("tools") if isinstance(body.get("tools"), list) else []

    delegate = tool_delegate(messages, tools)
    if delegate is not None:
        trace_event({"kind": "responses_tool_call_safe_delegate", "result": delegate})
        tool_call = delegate.get("tool_call")
        if isinstance(tool_call, dict):
            return responses_function_call_response(model, body, tool_call)
        return responses_message_response(model, body, str(delegate.get("content") or ""))

    trace_event({"kind": "responses_safe_response", "had_tools": bool(tools)})
    return responses_message_response(
        model,
        body,
        safe_generic_response(messages, bool(tools), False),
    )


if __name__ == "__main__":
    if uvicorn is None:
        raise RuntimeError(f"FastAPI/uvicorn import failed: {FASTAPI_IMPORT_ERROR}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
