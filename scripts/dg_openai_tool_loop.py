#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:4100/v1"
DEFAULT_MODEL = "diffusiongemma-local"
DEFAULT_TOOL_MANIFEST_URL = "http://127.0.0.1:8090/v1/agent/tool_manifest"
DEFAULT_TOOL_RUNTIME_URL = "http://127.0.0.1:8090/v1/agent/tool"
REPO_TOOL_NAMES = {
    "dg_repo_status",
    "dg_git_diff",
    "dg_list_files",
    "dg_read_file",
    "dg_search",
}
OSS_REPO_TOOL_NAMES = {
    "dg_repo_pack",
    "dg_repo_map",
    "dg_ast_grep",
    "dg_code_outline",
}
READ_ONLY_TOOL_NAMES = REPO_TOOL_NAMES | OSS_REPO_TOOL_NAMES | {
    "dg_context",
    "dg_rag_context",
    "dg_session_artifact",
    "dg_agent_run_artifact",
}
EXPLICIT_READ_ONLY_TOOL_NAMES = {"dg_agent_run_artifact"}
EXPLICIT_TOOL_NAMES = {"dg_agent_run_artifact"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer dummy",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {text}") from exc


def tool_schema_name(tool: dict[str, Any]) -> str:
    if isinstance(tool.get("function"), dict):
        return str(tool["function"].get("name") or "")
    return str(tool.get("name") or "")


def load_tools(
    manifest_url: str,
    timeout: int,
    *,
    include_execute_command: bool,
    include_tools: list[str],
    exclude_tools: list[str],
    read_only: bool,
) -> list[dict[str, Any]]:
    manifest = request_json("GET", manifest_url, timeout=timeout)
    tools = manifest.get("openai_chat_completions", {}).get("tools", [])
    if not isinstance(tools, list) or not tools:
        raise RuntimeError(f"no chat tools in manifest: {manifest_url}")
    if not include_execute_command:
        tools = [tool for tool in tools if tool_schema_name(tool) != "execute_command"]
    if not include_tools:
        tools = [tool for tool in tools if tool_schema_name(tool) not in EXPLICIT_TOOL_NAMES]
    if read_only:
        allowed_tools = set(READ_ONLY_TOOL_NAMES)
        if not include_tools:
            allowed_tools -= EXPLICIT_READ_ONLY_TOOL_NAMES
        tools = [tool for tool in tools if tool_schema_name(tool) in allowed_tools]
    if include_tools:
        include_set = set(include_tools)
        tools = [tool for tool in tools if tool_schema_name(tool) in include_set]
    if exclude_tools:
        exclude_set = set(exclude_tools)
        tools = [tool for tool in tools if tool_schema_name(tool) not in exclude_set]
    if not tools:
        raise RuntimeError(f"no usable chat tools in manifest: {manifest_url}")
    return tools


def tool_call_to_dict(tool_call: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": tool_call.get("id", ""),
        "type": tool_call.get("type", "function"),
        "function": {
            "name": tool_call.get("function", {}).get("name", ""),
            "arguments": tool_call.get("function", {}).get("arguments", "{}"),
        },
    }


def patch_tool_call_repo(tool_call: dict[str, Any], repo: str) -> dict[str, Any]:
    if not repo:
        return tool_call
    function = tool_call.get("function")
    if not isinstance(function, dict):
        return tool_call
    name = str(function.get("name") or "")
    if name not in REPO_TOOL_NAMES and name not in OSS_REPO_TOOL_NAMES and name not in {"dg_session", "dg_context", "dg_rag_context"}:
        return tool_call
    raw_args = function.get("arguments") or "{}"
    try:
        parsed = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except Exception:
        return tool_call
    if not isinstance(parsed, dict):
        return tool_call
    if not parsed.get("repo") or parsed.get("repo") == ".":
        parsed["repo"] = repo
        function["arguments"] = json.dumps(parsed, ensure_ascii=False)
    return tool_call


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
    match = re.search(r"\b(?:search|grep|find|where)\s+(?:for\s+)?(.{2,120})", task, flags=re.I)
    if match:
        return match.group(1).strip(" .")
    return task[:120].strip()


def select_tool(tools: list[dict[str, Any]], names: set[str]) -> dict[str, Any] | None:
    for tool in tools:
        if tool_schema_name(tool) in names:
            return tool
    return None


def deterministic_tool_args(name: str, task: str, repo: str) -> dict[str, Any] | None:
    task_lower = task.lower()
    files = task_file_hints(task)
    if name in REPO_TOOL_NAMES or name in OSS_REPO_TOOL_NAMES or name in {"dg_context", "dg_rag_context"}:
        if not repo:
            return None
    if name == "dg_repo_status":
        return {"repo": repo}
    if name == "dg_git_diff":
        args: dict[str, Any] = {"repo": repo, "stat": "stat" in task_lower}
        if "cached" in task_lower or "staged" in task_lower:
            args["cached"] = True
        if files:
            args["files"] = files
        return args
    if name == "dg_list_files":
        args = {"repo": repo, "limit": 200}
        glob_match = re.search(r"(\*\.[A-Za-z0-9_]+)", task)
        if glob_match:
            args["globs"] = [glob_match.group(1)]
        return args
    if name == "dg_read_file":
        if not files:
            return None
        return {"repo": repo, "path": files[0], "start_line": 1, "max_lines": 160}
    if name == "dg_search":
        args = {"repo": repo, "query": task_search_hint(task), "max_matches": 80}
        glob_match = re.search(r"(\*\.[A-Za-z0-9_]+)", task)
        if glob_match:
            args["globs"] = [glob_match.group(1)]
        return args
    if name == "dg_repo_pack":
        return {"repo": repo, "style": "markdown", "max_chars": 20000}
    if name == "dg_repo_map":
        args = {"repo": repo, "map_tokens": 2048, "map_only": True, "max_chars": 20000}
        if files:
            args["paths"] = files
        return args
    if name == "dg_ast_grep":
        args = {"repo": repo, "pattern": task_search_hint(task), "max_matches": 80}
        if "python" in task_lower or "*.py" in task_lower or any(file.endswith(".py") for file in files):
            args["lang"] = "python"
        if files:
            args["paths"] = files
        return args
    if name == "dg_code_outline":
        args = {"repo": repo, "items": "auto", "view": "auto", "max_items": 200}
        if "python" in task_lower or "*.py" in task_lower or any(file.endswith(".py") for file in files):
            args["lang"] = "python"
        if files:
            args["paths"] = files
        return args
    if name == "dg_context":
        args = {"repo": repo, "task": task, "format": "json", "max_files": 3, "max_snippet_chars": 1200}
        if files:
            args["files"] = files
        return args
    if name == "dg_rag_context":
        return {"repo": repo, "task": task, "max_context_chars": 1200, "max_files": 4, "max_tokens": 128}
    return None


def deterministic_tool_call(args: argparse.Namespace, tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    available = {tool_schema_name(tool) for tool in tools}
    task_lower = args.task.lower()
    explicit = [name for name in args.tool if name in available]
    for name in explicit:
        tool_args = deterministic_tool_args(name, args.task, args.repo)
        if tool_args is not None:
            return build_tool_call(name, tool_args)

    if not args.read_only:
        return None
    candidates: list[str] = []
    if any(word in task_lower for word in ("git status", "repo status", "working tree", "untracked")):
        candidates.append("dg_repo_status")
    if any(word in task_lower for word in ("git diff", "diff stat", "working diff", "staged diff", "cached diff")):
        candidates.append("dg_git_diff")
    if any(word in task_lower for word in ("list files", "show files", "file list", "which files")):
        candidates.append("dg_list_files")
    if any(word in task_lower for word in ("read file", "show file", "open file", "cat ")) and task_file_hints(args.task):
        candidates.append("dg_read_file")
    if any(word in task_lower for word in ("code outline", "outline", "symbols", "symbol list", "structure")):
        candidates.append("dg_code_outline")
    if any(word in task_lower for word in ("repo map", "repository map", "aider map")):
        candidates.append("dg_repo_map")
    if any(word in task_lower for word in ("ast-grep", "ast grep", "structural search")):
        candidates.append("dg_ast_grep")
    if any(word in task_lower for word in ("search", "grep", "find", "inspect", "explain", "where", "context", "summarize")):
        candidates.extend(["dg_rag_context", "dg_context", "dg_search"])
    candidates.extend(["dg_rag_context", "dg_context"])

    for name in candidates:
        if name not in available:
            continue
        tool_args = deterministic_tool_args(name, args.task, args.repo)
        if tool_args is not None:
            return build_tool_call(name, tool_args)
    return None


def build_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "call_" + uuid.uuid4().hex[:24],
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args, ensure_ascii=False),
        },
    }


def runtime_content(runtime: dict[str, Any]) -> str:
    result = runtime.get("result", {}) if isinstance(runtime.get("result"), dict) else {}
    content = str(result.get("content") or result.get("text") or result.get("stdout") or "")
    if not content and isinstance(result.get("files"), list):
        content = "\n".join(str(item) for item in result["files"])
    if not content and isinstance(result.get("matches"), list):
        content = "\n".join(str(item) for item in result["matches"])
    if not content:
        content = json.dumps(result or runtime, ensure_ascii=False, indent=2)
    return content


def deterministic_final(runtime: dict[str, Any], tool_call: dict[str, Any]) -> str:
    name = tool_call.get("function", {}).get("name", "tool")
    result = runtime.get("result", {}) if isinstance(runtime.get("result"), dict) else {}
    status = result.get("status", "success" if runtime.get("ok") else "failed")
    return f"Deterministic {name} result ({status}):\n\n{runtime_content(runtime)}"


def run_loop(args: argparse.Namespace) -> dict[str, Any]:
    tools = load_tools(
        args.tool_manifest_url,
        args.timeout,
        include_execute_command=args.include_execute_command,
        include_tools=args.tool,
        exclude_tools=args.exclude_tool,
        read_only=args.read_only,
    )
    base_url = args.base_url.rstrip("/")
    chat_url = f"{base_url}/chat/completions"
    messages: list[dict[str, Any]] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.task})

    events: list[dict[str, Any]] = []
    final_content = ""
    started = time.time()

    if args.deterministic_first:
        direct_call = deterministic_tool_call(args, tools)
        if direct_call is not None:
            direct_call = patch_tool_call_repo(direct_call, args.repo)
            assistant_message = {"role": "assistant", "content": None, "tool_calls": [direct_call]}
            messages.append(assistant_message)
            runtime = request_json("POST", args.tool_runtime_url, {"tool_call": direct_call}, timeout=args.timeout)
            events.append({"step": 0, "kind": "tool_runtime", "deterministic": True, "tool_call": direct_call, "runtime": runtime})
            tool_response = runtime.get("tool_response")
            if not isinstance(tool_response, dict):
                tool_response = {
                    "role": "tool",
                    "tool_call_id": direct_call.get("id", ""),
                    "content": json.dumps(runtime, ensure_ascii=False),
                }
            messages.append(tool_response)
            final_content = deterministic_final(runtime, direct_call)
            elapsed = time.time() - started
            return {
                "status": "success" if runtime.get("ok") else "failed",
                "route": "deterministic_tool_runtime",
                "elapsed_seconds": elapsed,
                "base_url": base_url,
                "model": args.model,
                "tool_manifest_url": args.tool_manifest_url,
                "tool_runtime_url": args.tool_runtime_url,
                "tool_names": [tool_schema_name(tool) for tool in tools],
                "steps": 0,
                "final_content": final_content,
                "messages": messages,
                "events": events,
            }

    for step in range(1, args.max_steps + 1):
        payload = {
            "model": args.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
        }
        response = request_json("POST", chat_url, payload, timeout=args.timeout)
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        events.append({"step": step, "kind": "chat", "finish_reason": choice.get("finish_reason"), "message": message})

        if not tool_calls:
            final_content = str(message.get("content") or "")
            if final_content:
                messages.append({"role": "assistant", "content": final_content})
            break

        patched_calls = [patch_tool_call_repo(tool_call_to_dict(item), args.repo) for item in tool_calls if isinstance(item, dict)]
        assistant_message = {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": patched_calls,
        }
        messages.append(assistant_message)

        for item in assistant_message["tool_calls"]:
            runtime_payload = {"tool_call": item}
            runtime = request_json("POST", args.tool_runtime_url, runtime_payload, timeout=args.timeout)
            events.append({"step": step, "kind": "tool_runtime", "tool_call": item, "runtime": runtime})
            tool_response = runtime.get("tool_response")
            if not isinstance(tool_response, dict):
                tool_response = {
                    "role": "tool",
                    "tool_call_id": item.get("id", ""),
                    "content": json.dumps(runtime, ensure_ascii=False),
                }
            messages.append(tool_response)

        if args.stop_after_tool:
            break

    elapsed = time.time() - started
    return {
        "status": "success",
        "route": "openai_chat_tool_loop",
        "elapsed_seconds": elapsed,
        "base_url": base_url,
        "model": args.model,
        "tool_manifest_url": args.tool_manifest_url,
        "tool_runtime_url": args.tool_runtime_url,
        "tool_names": [tool_schema_name(tool) for tool in tools],
        "steps": len([event for event in events if event["kind"] == "chat"]),
        "final_content": final_content,
        "messages": messages,
        "events": events,
    }


def print_text(report: dict[str, Any]) -> None:
    print(f"Status: {report['status']}")
    print(f"Model: {report['model']}")
    print(f"Steps: {report['steps']}")
    print(f"Tools: {', '.join(report.get('tool_names') or [])}")
    print(f"Elapsed: {report['elapsed_seconds']:.3f}s")
    print("")
    for event in report["events"]:
        if event["kind"] == "chat":
            print(f"[chat step {event['step']}] finish={event.get('finish_reason')}")
            tool_calls = event.get("message", {}).get("tool_calls") or []
            for call in tool_calls:
                fn = call.get("function", {})
                print(f"  tool_call {call.get('id', '')}: {fn.get('name', '')} {fn.get('arguments', '')[:300]}")
            content = event.get("message", {}).get("content")
            if content:
                print(str(content).strip())
        elif event["kind"] == "tool_runtime":
            runtime = event.get("runtime", {})
            result = runtime.get("result", {}) if isinstance(runtime.get("result"), dict) else {}
            print(f"[tool step {event['step']}] {runtime.get('tool')} ok={runtime.get('ok')} status={result.get('status', '')}")
            content = str(result.get("content") or result.get("text") or "")
            if content:
                print(content[:1200].rstrip())
    if report.get("final_content"):
        print("\nFinal:")
        print(report["final_content"].strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small OpenAI-compatible DG tool loop.")
    parser.add_argument("--task", required=True)
    parser.add_argument("--repo", default="")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--tool-manifest-url", default=DEFAULT_TOOL_MANIFEST_URL)
    parser.add_argument("--tool-runtime-url", default=DEFAULT_TOOL_RUNTIME_URL)
    parser.add_argument("--system", default="Use DG-specific tools when helpful.")
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--stop-after-tool", action="store_true")
    parser.add_argument("--no-deterministic-first", dest="deterministic_first", action="store_false", help="Disable direct rule-based read-only tool routing before model calls.")
    parser.add_argument("--include-execute-command", action="store_true", help="Include the legacy execute_command schema. Off by default to prefer DG-specific tools.")
    parser.add_argument("--tool", action="append", default=[], help="Limit the manifest to this tool name. Repeatable.")
    parser.add_argument("--exclude-tool", action="append", default=[], help="Remove this tool name from the manifest. Repeatable.")
    parser.add_argument("--read-only", action="store_true", help="Expose only read-only repo/context/artifact tools.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default="")
    parser.set_defaults(deterministic_first=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_loop(args)
    if args.out:
        path = Path(args.out).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
        if args.out:
            print(f"\nTranscript: {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
