#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage

DG_ROOT = Path(__file__).resolve().parents[1]
if str(DG_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(DG_ROOT / "scripts"))

from dg_mcp_server import (  # noqa: E402
    NOTE_ROOT,
    list_tools,
    normalize_host_path,
    note_summary,
    note_paths,
    tool_ast_grep,
    tool_capabilities,
    tool_code_outline,
    tool_context,
    tool_git_diff,
    tool_list_files,
    tool_plan,
    tool_preflight,
    tool_repo_map,
    tool_rag_answer,
    tool_rag_context,
    tool_read_file,
    tool_repo_pack,
    tool_repo_status,
    tool_search,
    tool_session,
    tool_session_artifact,
    tool_sessions,
    tool_agent_run_artifact,
    tool_agent_runs,
    tool_status,
    tool_task,
    tool_task_note,
    tool_task_notes,
    tool_verify,
    tool_client_report,
    tool_client_smoke,
)


mcp = FastMCP(
    "diffusiongemma-local-agent",
    instructions=(
        "Expose reliable local DiffusionGemma coding-agent commands as MCP tools. "
        "Use dg_preflight, dg_context, dg_rag_context, dg_repo_pack, dg_repo_map, dg_ast_grep, dg_code_outline, dg_plan, dg_task, "
        "dg_session, and dg_verify for bounded repository work with preserved artifacts."
    ),
)

LAST_CLIENT_HANDOFF_JSON: Path | None = None
LAST_CLIENT_HANDOFF_MD: Path | None = None
LAST_WORKSPACE_REPO: Path | None = None


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(
        str(item.get("text", ""))
        for item in result.get("content", [])
        if isinstance(item, dict) and item.get("type") == "text"
    ).strip()
    return {
        "ok": not bool(result.get("isError")),
        "text": text,
        "structured": result.get("structuredContent") or {},
    }


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def http_json(url: str, timeout: int = 2) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "url": url}


def latest_session_dir() -> Path | None:
    root = DG_ROOT / "runlogs" / "dg-agent-sessions"
    if not root.exists():
        return None
    dirs = [path for path in root.iterdir() if path.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda path: path.stat().st_mtime)


def latest_agent_run_dir() -> Path | None:
    root = DG_ROOT / "runlogs" / "dg-agent-runs"
    if not root.exists():
        return None
    dirs = [path for path in root.iterdir() if path.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda path: path.stat().st_mtime)


def read_text_file(path: Path, limit: int = 200_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}", "path": str(path)}, ensure_ascii=False)
    return text[:limit]


def client_handoff_paths() -> tuple[Path, Path]:
    json_path = LAST_CLIENT_HANDOFF_JSON
    md_path = LAST_CLIENT_HANDOFF_MD
    if json_path and md_path and (json_path.exists() or md_path.exists()):
        return json_path, md_path
    return Path.cwd() / ".dg-agent" / "client-handoff.json", Path.cwd() / ".dg-agent" / "CLIENT_HANDOFF.md"


def resolve_workspace_repo(repo: str = "") -> Path:
    if repo and repo != ".":
        return Path(normalize_host_path(repo)).expanduser().resolve()
    for key in ("DG_MCP_REPO", "DG_AGENT_REPO", "DG_AGENT_CALLER_CWD"):
        value = os.environ.get(key)
        if value:
            return Path(normalize_host_path(value)).expanduser().resolve()
    return Path.cwd().resolve()


def remember_workspace_repo(repo: str = "") -> None:
    global LAST_WORKSPACE_REPO
    LAST_WORKSPACE_REPO = resolve_workspace_repo(repo)


def current_workspace_repo() -> Path:
    if LAST_WORKSPACE_REPO is not None:
        return LAST_WORKSPACE_REPO
    if LAST_CLIENT_HANDOFF_JSON is not None:
        return LAST_CLIENT_HANDOFF_JSON.parent.parent
    return resolve_workspace_repo()


def workspace_agent_file(*parts: str) -> Path:
    return current_workspace_repo().joinpath(".dg-agent", *parts)


@mcp.tool()
def dg_status(timeout: int = 30) -> dict[str, Any]:
    """Check local DiffusionGemma backend, proxy, and LiteLLM health."""
    return compact_result(tool_status({"timeout": timeout}))


@mcp.tool()
def dg_task_note(
    task: str,
    body: str,
    title: str = "",
    repo: str = "",
    tags: list[str] | None = None,
    append_to: str = "",
) -> dict[str, Any]:
    """Write or append a durable Markdown task note under runlogs for MCP clients."""
    return compact_result(
        tool_task_note(
            {
                "task": task,
                "body": body,
                "title": title,
                "repo": repo,
                "tags": tags or [],
                "append_to": append_to,
            }
        )
    )


@mcp.tool()
def dg_task_notes(note: str = "", latest: bool = False, limit: int = 20, max_chars: int = 20000) -> dict[str, Any]:
    """List or read durable Markdown task notes saved by MCP clients."""
    return compact_result(tool_task_notes({"note": note, "latest": latest, "limit": limit, "max_chars": max_chars}))


@mcp.tool()
def dg_repo_status(repo: str = ".", max_chars: int = 8000, timeout: int = 30) -> dict[str, Any]:
    """Inspect git status, diff stat, and untracked files for a repository."""
    return compact_result(tool_repo_status({"repo": repo, "max_chars": max_chars, "timeout": timeout}))


@mcp.tool()
def dg_list_files(
    repo: str = ".",
    pattern: str = "",
    globs: list[str] | None = None,
    limit: int = 200,
    timeout: int = 30,
) -> dict[str, Any]:
    """List repository files using ripgrep or git fallback, with optional glob filters."""
    return compact_result(
        tool_list_files({"repo": repo, "pattern": pattern, "globs": globs or [], "limit": limit, "timeout": timeout})
    )


@mcp.tool()
def dg_search(
    query: str,
    repo: str = ".",
    globs: list[str] | None = None,
    context: int = 0,
    max_matches: int = 80,
    max_chars: int = 12000,
    timeout: int = 30,
) -> dict[str, Any]:
    """Search a repository with ripgrep and return bounded line/column matches."""
    return compact_result(
        tool_search(
            {
                "repo": repo,
                "query": query,
                "globs": globs or [],
                "context": context,
                "max_matches": max_matches,
                "max_chars": max_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_read_file(
    path: str,
    repo: str = ".",
    start_line: int = 1,
    max_lines: int = 160,
    max_chars: int = 20000,
) -> dict[str, Any]:
    """Read a bounded, line-numbered slice of a file inside a repository."""
    return compact_result(
        tool_read_file(
            {
                "repo": repo,
                "path": path,
                "start_line": start_line,
                "max_lines": max_lines,
                "max_chars": max_chars,
            }
        )
    )


@mcp.tool()
def dg_git_diff(
    repo: str = ".",
    files: list[str] | None = None,
    cached: bool = False,
    stat: bool = False,
    max_chars: int = 20000,
    timeout: int = 30,
) -> dict[str, Any]:
    """Read a bounded git diff or diff stat for a repository."""
    return compact_result(
        tool_git_diff(
            {
                "repo": repo,
                "files": files or [],
                "cached": cached,
                "stat": stat,
                "max_chars": max_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_context(
    task: str,
    repo: str = ".",
    files: list[str] | None = None,
    max_files: int = 3,
    max_snippet_chars: int = 1200,
    timeout: int = 120,
) -> dict[str, Any]:
    """Build a compact rg-based context pack for a repository task."""
    return compact_result(
        tool_context(
            {
                "repo": repo,
                "task": task,
                "files": files or [],
                "max_files": max_files,
                "max_snippet_chars": max_snippet_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_rag_context(
    task: str,
    repo: str = ".",
    max_context_chars: int = 900,
    max_files: int = 3,
    debug: bool = False,
    timeout: int = 120,
) -> dict[str, Any]:
    """Retrieve a compact read-only RAG context for a repository task without calling the model."""
    return compact_result(
        tool_rag_context(
            {
                "repo": repo,
                "task": task,
                "max_context_chars": max_context_chars,
                "max_files": max_files,
                "debug": debug,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_rag_answer(
    task: str,
    repo: str = ".",
    base_url: str = "",
    model: str = "",
    max_context_chars: int = 650,
    max_files: int = 3,
    max_tokens: int = 128,
    debug: bool = False,
    timeout: int = 300,
) -> dict[str, Any]:
    """Ask the local model using a compact rg-retrieved repository context."""
    return compact_result(
        tool_rag_answer(
            {
                "repo": repo,
                "task": task,
                "base_url": base_url,
                "model": model,
                "max_context_chars": max_context_chars,
                "max_files": max_files,
                "max_tokens": max_tokens,
                "debug": debug,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_repo_pack(
    repo: str = ".",
    style: str = "markdown",
    include: list[str] | None = None,
    ignore: list[str] | None = None,
    compress: bool = False,
    include_diffs: bool = False,
    output_show_line_numbers: bool = False,
    remove_comments: bool = False,
    remove_empty_lines: bool = False,
    no_files: bool = False,
    no_security_check: bool = False,
    token_budget: int = 0,
    top_files_len: int = 5,
    max_chars: int = 20000,
    timeout: int = 180,
) -> dict[str, Any]:
    """Pack repository content with the upstream Repomix OSS tool and return bounded output."""
    return compact_result(
        tool_repo_pack(
            {
                "repo": repo,
                "style": style,
                "include": include or [],
                "ignore": ignore or [],
                "compress": compress,
                "include_diffs": include_diffs,
                "output_show_line_numbers": output_show_line_numbers,
                "remove_comments": remove_comments,
                "remove_empty_lines": remove_empty_lines,
                "no_files": no_files,
                "no_security_check": no_security_check,
                "token_budget": token_budget,
                "top_files_len": top_files_len,
                "max_chars": max_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_repo_map(
    repo: str = ".",
    map_tokens: int = 512,
    paths: list[str] | None = None,
    map_only: bool = True,
    base_url: str = "",
    model: str = "",
    max_chars: int = 20000,
    timeout: int = 180,
) -> dict[str, Any]:
    """Build a bounded upstream Aider repo-map for repository-scale code context."""
    return compact_result(
        tool_repo_map(
            {
                "repo": repo,
                "map_tokens": map_tokens,
                "paths": paths or [],
                "map_only": map_only,
                "base_url": base_url,
                "model": model,
                "max_chars": max_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_ast_grep(
    pattern: str = "",
    repo: str = ".",
    kind: str = "",
    selector: str = "",
    strictness: str = "",
    lang: str = "",
    context: int = 0,
    globs: list[str] | None = None,
    paths: list[str] | None = None,
    json: bool = True,
    files_with_matches: bool = False,
    max_matches: int = 80,
    max_chars: int = 20000,
    timeout: int = 120,
) -> dict[str, Any]:
    """Search repository code structurally with upstream ast-grep and bounded output."""
    return compact_result(
        tool_ast_grep(
            {
                "repo": repo,
                "pattern": pattern,
                "kind": kind,
                "selector": selector,
                "strictness": strictness,
                "lang": lang,
                "context": context,
                "globs": globs or [],
                "paths": paths or [],
                "json": json,
                "files_with_matches": files_with_matches,
                "max_matches": max_matches,
                "max_chars": max_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_code_outline(
    repo: str = ".",
    lang: str = "",
    items: str = "auto",
    view: str = "auto",
    type: str = "",
    match: str = "",
    pub_members: bool = False,
    globs: list[str] | None = None,
    paths: list[str] | None = None,
    json: bool = True,
    max_items: int = 200,
    max_chars: int = 20000,
    timeout: int = 120,
) -> dict[str, Any]:
    """Build a bounded symbol outline with upstream ast-grep outline."""
    return compact_result(
        tool_code_outline(
            {
                "repo": repo,
                "lang": lang,
                "items": items,
                "view": view,
                "type": type,
                "match": match,
                "pub_members": pub_members,
                "globs": globs or [],
                "paths": paths or [],
                "json": json,
                "max_items": max_items,
                "max_chars": max_chars,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_preflight(
    repo: str = ".",
    task: str = "",
    files: list[str] | None = None,
    allow_dirty: bool = False,
    timeout: int = 120,
) -> dict[str, Any]:
    """Check whether a target repository and local DG wrapper stack are ready for agent work."""
    return compact_result(
        tool_preflight(
            {
                "repo": repo,
                "task": task,
                "files": files or [],
                "allow_dirty": allow_dirty,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_plan(
    task: str,
    repo: str = ".",
    files: list[str] | None = None,
    out: str = "",
    name: str = "edit",
    test_cmd: str = "",
    auto_test: bool = False,
    max_files: int = 1,
    max_snippet_chars: int = 1200,
    test_timeout: int = 120,
    aider_timeout: int = 420,
    repair_attempts: int = 1,
    no_deterministic_first: bool = False,
    timeout: int = 120,
) -> dict[str, Any]:
    """Generate a JSON task-runner plan from a natural-language repository task."""
    return compact_result(
        tool_plan(
            {
                "repo": repo,
                "task": task,
                "files": files or [],
                "out": out,
                "name": name,
                "test_cmd": test_cmd,
                "auto_test": auto_test,
                "max_files": max_files,
                "max_snippet_chars": max_snippet_chars,
                "test_timeout": test_timeout,
                "aider_timeout": aider_timeout,
                "repair_attempts": repair_attempts,
                "no_deterministic_first": no_deterministic_first,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_task(
    plan: str,
    repo: str = ".",
    report: str = "",
    supervisor: str = "",
    step_report_dir: str = "",
    allow_dirty: bool = False,
    dry_run: bool = False,
    rollback_on_failure: bool = True,
    continue_on_failure: bool = False,
    timeout: int = 900,
) -> dict[str, Any]:
    """Execute an existing DG task-runner plan; use dry_run to inspect without editing."""
    return compact_result(
        tool_task(
            {
                "repo": repo,
                "plan": plan,
                "report": report,
                "supervisor": supervisor,
                "step_report_dir": step_report_dir,
                "allow_dirty": allow_dirty,
                "dry_run": dry_run,
                "rollback_on_failure": rollback_on_failure,
                "continue_on_failure": continue_on_failure,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_session(
    task: str,
    repo: str = ".",
    files: list[str] | None = None,
    test_cmd: str = "",
    auto_test: bool = False,
    allow_dirty: bool = False,
    dry_run: bool = False,
    max_files: int = 1,
    max_snippet_chars: int = 1200,
    test_timeout: int = 120,
    aider_timeout: int = 420,
    repair_attempts: int = 1,
    wall_timeout: int = 900,
    no_verify_after: bool = False,
) -> dict[str, Any]:
    """Run context -> plan -> task -> verify with rollback on failure and artifacts."""
    return compact_result(
        tool_session(
            {
                "repo": repo,
                "task": task,
                "files": files or [],
                "test_cmd": test_cmd,
                "auto_test": auto_test,
                "allow_dirty": allow_dirty,
                "dry_run": dry_run,
                "max_files": max_files,
                "max_snippet_chars": max_snippet_chars,
                "test_timeout": test_timeout,
                "aider_timeout": aider_timeout,
                "repair_attempts": repair_attempts,
                "wall_timeout": wall_timeout,
                "no_verify_after": no_verify_after,
            }
        )
    )


@mcp.tool()
def dg_verify(
    repo: str = ".",
    files: list[str] | None = None,
    test_cmd: str = "",
    timeout: int = 120,
) -> dict[str, Any]:
    """Run or infer a repository verification command."""
    return compact_result(
        tool_verify(
            {
                "repo": repo,
                "files": files or [],
                "test_cmd": test_cmd,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_capabilities(run_live: bool = False, timeout: int = 180) -> dict[str, Any]:
    """Read the latest DG wrapper capability report, or run a live probe."""
    return compact_result(tool_capabilities({"run_live": run_live, "timeout": timeout}))


@mcp.tool()
def dg_client_smoke(
    repo: str = ".",
    client: str = "cursor",
    target: str = "",
    force_init: bool = False,
    no_init: bool = False,
    no_rules: bool = False,
    no_oss_stack: bool = False,
    live: bool = False,
    timeout: int = 180,
) -> dict[str, Any]:
    """Prepare or validate a target repo for external IDE/agent clients."""
    remember_workspace_repo(repo)
    return compact_result(
        tool_client_smoke(
            {
                "repo": repo,
                "client": client,
                "target": target,
                "force_init": force_init,
                "no_init": no_init,
                "no_rules": no_rules,
                "no_oss_stack": no_oss_stack,
                "live": live,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_client_report(
    repo: str = ".",
    client: str = "cursor",
    target: str = "",
    force_init: bool = False,
    no_init: bool = False,
    no_rules: bool = False,
    no_oss_stack: bool = False,
    live: bool = False,
    no_write: bool = False,
    timeout: int = 240,
) -> dict[str, Any]:
    """Generate repo-local Markdown/JSON handoff files for external clients."""
    global LAST_CLIENT_HANDOFF_JSON, LAST_CLIENT_HANDOFF_MD
    remember_workspace_repo(repo)
    result = tool_client_report(
        {
            "repo": repo,
            "client": client,
            "target": target,
            "force_init": force_init,
            "no_init": no_init,
            "no_rules": no_rules,
            "no_oss_stack": no_oss_stack,
            "live": live,
            "no_write": no_write,
            "timeout": timeout,
        }
    )
    structured = result.get("structuredContent") or {}
    stdout = structured.get("stdout", "") if isinstance(structured, dict) else ""
    try:
        report = json.loads(stdout)
        outputs = report.get("outputs", {}) if isinstance(report, dict) else {}
        json_path = outputs.get("json", {}).get("path") if isinstance(outputs.get("json"), dict) else ""
        md_path = outputs.get("markdown", {}).get("path") if isinstance(outputs.get("markdown"), dict) else ""
        if json_path:
            LAST_CLIENT_HANDOFF_JSON = Path(json_path)
        if md_path:
            LAST_CLIENT_HANDOFF_MD = Path(md_path)
    except Exception:
        pass
    return compact_result(result)


@mcp.tool()
def dg_sessions(limit: int = 10, root: str = "", timeout: int = 60) -> dict[str, Any]:
    """List recent artifacted DG agent sessions."""
    return compact_result(tool_sessions({"limit": limit, "root": root, "timeout": timeout}))


@mcp.tool()
def dg_session_artifact(
    artifact: str = "session_json",
    session: str = "",
    latest: bool = True,
    path_only: bool = False,
    root: str = "",
    timeout: int = 60,
) -> dict[str, Any]:
    """Read a preserved artifact from a DG agent session, defaulting to the latest session."""
    return compact_result(
        tool_session_artifact(
            {
                "artifact": artifact,
                "session": session,
                "latest": latest,
                "path_only": path_only,
                "root": root,
                "timeout": timeout,
            }
        )
    )


@mcp.tool()
def dg_agent_runs(limit: int = 10, root: str = "") -> dict[str, Any]:
    """List recent high-level dg_agent runs and their preserved artifacts."""
    return compact_result(tool_agent_runs({"limit": limit, "root": root}))


@mcp.tool()
def dg_agent_run_artifact(
    artifact: str = "agent_json",
    run: str = "",
    latest: bool = True,
    path_only: bool = False,
    limit: int = 200_000,
    root: str = "",
) -> dict[str, Any]:
    """Read a preserved artifact from a high-level dg_agent run, defaulting to the latest run."""
    return compact_result(
        tool_agent_run_artifact(
            {
                "artifact": artifact,
                "run": run,
                "latest": latest,
                "path_only": path_only,
                "limit": limit,
                "root": root,
            }
        )
    )


@mcp.resource(
    "dg://client-pack",
    title="DiffusionGemma local client pack",
    description="Current local endpoints, profiles, launchers, and model limits.",
    mime_type="application/json",
)
def resource_client_pack() -> str:
    return json.dumps(
        read_json_file(DG_ROOT / "configs" / "client_profiles" / "agent-client-pack.json"),
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource(
    "dg://status",
    title="DiffusionGemma local stack status",
    description="Live backend, Aider proxy, and LiteLLM health snapshots.",
    mime_type="application/json",
)
def resource_status() -> str:
    return json.dumps(
        {
            "backend": http_json("http://127.0.0.1:4100/healthz"),
            "proxy": http_json("http://127.0.0.1:8090/healthz"),
            "litellm_models": http_json("http://127.0.0.1:4100/v1/models"),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource(
    "dg://usage",
    title="DiffusionGemma local agent usage",
    description="Practical commands for using the local agent wrapper stack.",
    mime_type="text/markdown",
)
def resource_usage() -> str:
    return """# DiffusionGemma Local Agent Usage

Recommended reliable edit path:

```bash
scripts/dg_agent.sh agent --repo /repo --task "..." --file path --test-cmd "..."
scripts/dg_agent.sh session --repo /repo --task "..." --file path --auto-test --rollback-on-failure
```

MCP tools:

- `dg_repo_status`: inspect git status, diff stat, and untracked files.
- `dg_list_files`: list repository files with optional filters.
- `dg_search`: ripgrep search with bounded results.
- `dg_read_file`: read bounded line-numbered file slices.
- `dg_git_diff`: inspect bounded diffs before/after edits.
- `dg_task_note`: save durable Markdown task notes outside the target repo.
- `dg_task_notes`: list or read saved task notes.
- `dg_context`: build bounded repository context.
- `dg_rag_context`: retrieve compact read-only RAG context without calling the model.
- `dg_rag_answer`: ask the local model over compact retrieved context.
- `dg_repo_pack`: pack filtered repository content with upstream Repomix.
- `dg_repo_map`: bounded upstream Aider repo-map for repository-scale code context.
- `dg_ast_grep`: structural code search with upstream ast-grep.
- `dg_code_outline`: bounded symbol outline with upstream ast-grep outline.
- `dg_preflight`: check repo/workspace/wrapper readiness before edits.
- `dg_plan`: generate a JSON task-runner plan for review or execution.
- `dg_task`: execute an existing plan; use `dry_run` before risky edits.
- `dg_session`: run context -> plan -> task -> verify with artifacts and rollback.
- `dg_verify`: run or infer deterministic verification.
- `dg_status`: check the local stack.
- `dg_capabilities`: inspect wrapper capability probes.
- `dg_client_smoke`: prepare or validate this repo for external IDE/agent clients.
- `dg_client_report`: write `.dg-agent/CLIENT_HANDOFF.md` and `.dg-agent/client-handoff.json`.
- `dg_agent_runs`: list high-level `dg_agent` read/edit facade runs.
- `dg_agent_run_artifact`: read high-level `dg_agent` run reports, transcripts, stdout, or stderr.

For MCP-capable Goose:

```bash
scripts/dg_agent.sh goose-mcp -- info -v
scripts/dg_agent.sh goose-acp
scripts/dg_agent.sh goose-serve -- --host 127.0.0.1 --port 3294
```
"""


@mcp.resource(
    "dg://notes",
    title="DG MCP task notes",
    description="Recent durable Markdown task notes saved by MCP clients.",
    mime_type="application/json",
)
def resource_notes() -> str:
    notes = [note_summary(path) for path in note_paths()[:50]]
    return json.dumps({"root": str(NOTE_ROOT), "notes": notes}, ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://notes/latest",
    title="Latest DG MCP task note",
    description="Most recent durable Markdown task note saved by an MCP client.",
    mime_type="text/markdown",
)
def resource_latest_note() -> str:
    paths = note_paths()
    if not paths:
        return "no task notes found\n"
    return read_text_file(paths[0])


@mcp.resource(
    "dg://sessions",
    title="Recent DG agent sessions",
    description="Recent artifacted DG agent sessions as JSON.",
    mime_type="application/json",
)
def resource_sessions() -> str:
    result = tool_sessions({"limit": 20, "timeout": 60})
    structured = result.get("structuredContent") or {}
    stdout = structured.get("stdout", "") if isinstance(structured, dict) else ""
    try:
        return json.dumps(json.loads(stdout), ensure_ascii=False, indent=2)
    except Exception:
        return json.dumps({"ok": False, "raw": stdout, "result": structured}, ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://sessions/latest",
    title="Latest DG agent session",
    description="Latest preserved session.json artifact.",
    mime_type="application/json",
)
def resource_latest_session() -> str:
    session_dir = latest_session_dir()
    if session_dir is None:
        return json.dumps({"ok": False, "error": "no sessions found"}, ensure_ascii=False, indent=2)
    return json.dumps(read_json_file(session_dir / "session.json"), ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://sessions/latest/diff",
    title="Latest DG agent session final diff",
    description="The final.diff artifact from the latest DG agent session.",
    mime_type="text/x-diff",
)
def resource_latest_session_diff() -> str:
    session_dir = latest_session_dir()
    if session_dir is None:
        return "no sessions found\n"
    return read_text_file(session_dir / "final.diff")


@mcp.resource(
    "dg://agent-runs",
    title="Recent high-level DG agent runs",
    description="Recent dg_agent read/edit facade runs as JSON.",
    mime_type="application/json",
)
def resource_agent_runs() -> str:
    result = tool_agent_runs({"limit": 20})
    structured = result.get("structuredContent") or {}
    stdout = structured.get("stdout", "") if isinstance(structured, dict) else ""
    try:
        return json.dumps(json.loads(stdout), ensure_ascii=False, indent=2)
    except Exception:
        return json.dumps({"ok": False, "raw": stdout, "result": structured}, ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://agent-runs/latest",
    title="Latest high-level DG agent run",
    description="Latest preserved agent.json artifact from dg_agent.",
    mime_type="application/json",
)
def resource_latest_agent_run() -> str:
    run_dir = latest_agent_run_dir()
    if run_dir is None:
        return json.dumps({"ok": False, "error": "no agent runs found"}, ensure_ascii=False, indent=2)
    return json.dumps(read_json_file(run_dir / "agent.json"), ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://agent-runs/latest/transcript",
    title="Latest high-level DG agent run transcript",
    description="The tool-loop transcript from the latest dg_agent run.",
    mime_type="application/json",
)
def resource_latest_agent_run_transcript() -> str:
    run_dir = latest_agent_run_dir()
    if run_dir is None:
        return json.dumps({"ok": False, "error": "no agent runs found"}, ensure_ascii=False, indent=2)
    return read_text_file(run_dir / "tool-loop.json")


@mcp.resource(
    "dg://capabilities/latest",
    title="Latest DG wrapper capability report",
    description="Latest saved capability probe report.",
    mime_type="application/json",
)
def resource_latest_capabilities() -> str:
    return json.dumps(
        read_json_file(DG_ROOT / "runlogs" / "dg-agent-capabilities" / "latest.json"),
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource(
    "dg://client-handoff",
    title="DG client handoff report",
    description="Repo-local client handoff JSON generated by dg_client_report.",
    mime_type="application/json",
)
def resource_client_handoff() -> str:
    json_path, _ = client_handoff_paths()
    return json.dumps(read_json_file(json_path), ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://client-handoff/markdown",
    title="DG client handoff markdown",
    description="Repo-local Markdown handoff generated by dg_client_report.",
    mime_type="text/markdown",
)
def resource_client_handoff_markdown() -> str:
    _, md_path = client_handoff_paths()
    return read_text_file(md_path)


@mcp.resource(
    "dg://agent-hub",
    title="DG local agent hub",
    description="Repo-local JSON hub describing the best wrapper route for each task.",
    mime_type="application/json",
)
def resource_agent_hub() -> str:
    return json.dumps(read_json_file(workspace_agent_file("agent-hub.json")), ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://agent-hub/markdown",
    title="DG local agent hub Markdown",
    description="Repo-local first-read handoff for humans and external agents.",
    mime_type="text/markdown",
)
def resource_agent_hub_markdown() -> str:
    return read_text_file(workspace_agent_file("AGENT_HUB.md"))


@mcp.resource(
    "dg://command-kit",
    title="DG agent command kit",
    description="Repo-local JSON command kit for reusable external-agent workflows.",
    mime_type="application/json",
)
def resource_command_kit() -> str:
    return json.dumps(read_json_file(workspace_agent_file("command-kit.json")), ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://command-kit/markdown",
    title="DG agent command kit Markdown",
    description="Repo-local command guide for reusable external-agent workflows.",
    mime_type="text/markdown",
)
def resource_command_kit_markdown() -> str:
    return read_text_file(workspace_agent_file("COMMANDS.md"))


@mcp.resource(
    "dg://ide-clients",
    title="DG IDE client snippets",
    description="Repo-local JSON snippets for Continue, Cline, Roo, Kilo, and OpenAI-compatible clients.",
    mime_type="application/json",
)
def resource_ide_clients() -> str:
    return json.dumps(read_json_file(workspace_agent_file("ide-client-snippets.json")), ensure_ascii=False, indent=2)


@mcp.resource(
    "dg://ide-clients/markdown",
    title="DG IDE client profile guide",
    description="Repo-local IDE profile guide for connecting external clients to the local model.",
    mime_type="text/markdown",
)
def resource_ide_clients_markdown() -> str:
    return read_text_file(workspace_agent_file("IDE_CLIENTS.md"))


@mcp.resource(
    "dg://codex-profile",
    title="DG Codex CLI profile guide",
    description="Repo-local Codex CLI handoff for the local safe agent proxy.",
    mime_type="text/markdown",
)
def resource_codex_profile() -> str:
    return read_text_file(workspace_agent_file("CODEX.md"))


@mcp.resource(
    "dg://codex-profile/config",
    title="DG Codex CLI config template",
    description="Repo-local Codex CLI config template pointing at the local safe agent proxy.",
    mime_type="text/x-toml",
)
def resource_codex_profile_config() -> str:
    return read_text_file(workspace_agent_file("codex.config.toml"))


@mcp.prompt(
    name="dg_agent_session",
    title="Run a reliable local coding-agent session",
    description="Prompt an MCP client to use retrieval/context, session or plan/task, and verify for a repository task.",
)
def prompt_agent_session(task: str, repo: str = ".", file: str = "") -> list[UserMessage]:
    file_hint = f"\nEditable file hint: {file}" if file else ""
    return [
        UserMessage(
            "Use the local DiffusionGemma MCP tools for this coding task.\n"
            f"Repo: {repo}\n"
            f"Task: {task}{file_hint}\n\n"
            "Workflow:\n"
            "1. Call dg_repo_status, dg_list_files, dg_repo_map, dg_code_outline, dg_search, dg_ast_grep, or dg_read_file if you need local repo inspection.\n"
            "2. Call dg_preflight, then dg_context, dg_rag_context, dg_repo_map, dg_code_outline, dg_ast_grep, or dg_repo_pack with tight include filters if needed.\n"
            "3. For one-shot bounded edits, call dg_session. For stepwise control, call dg_plan then dg_task.\n"
            "4. Call dg_git_diff and dg_verify with an explicit or inferred test command when possible.\n"
            "5. Report changed files, verification result, and artifact paths."
        )
    ]


@mcp.prompt(
    name="dg_agent_context",
    title="Build bounded repo context",
    description="Prompt an MCP client to gather a compact context pack before editing.",
)
def prompt_context(task: str, repo: str = ".", file: str = "") -> list[UserMessage]:
    file_hint = f" and include `{file}`" if file else ""
    return [
        UserMessage(
            f"Call dg_preflight, then dg_context or dg_rag_context for repo `{repo}` with task `{task}`{file_hint}. "
            "Use dg_repo_map for Aider-style repository sketches, dg_code_outline for symbol maps, dg_ast_grep for AST-pattern code search, and dg_repo_pack with include filters when a client needs an OSS packed context artifact. "
            "Use the returned snippets and ranked files as the only working context unless more files are explicitly needed."
        )
    ]


@mcp.prompt(
    name="dg_agent_continue_latest",
    title="Continue from the latest DG agent session",
    description="Prompt an MCP client to inspect latest session artifacts before continuing work.",
)
def prompt_continue_latest(next_task: str = "") -> list[UserMessage]:
    suffix = f"\nNext task: {next_task}" if next_task else ""
    return [
        UserMessage(
            "Before continuing, read MCP resources `dg://sessions/latest`, "
            "`dg://sessions/latest/diff`, `dg://notes/latest`, and `dg://capabilities/latest`. "
            "Also read `dg://agent-runs/latest` or `dg://agent-runs/latest/transcript` when you need the last high-level agent facade run. "
            "Use `dg_session_artifact` or `dg_agent_run_artifact` for any additional preserved artifacts. "
            "Then continue with `dg_client_report`, `dg_preflight`, `dg_context`, `dg_rag_context`, `dg_repo_map`, `dg_code_outline`, `dg_ast_grep`, `dg_repo_pack`, `dg_plan`, `dg_task`, `dg_session`, and `dg_verify` as needed."
            f"{suffix}"
        )
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Official-SDK MCP server exposing local DiffusionGemma tools.")
    parser.add_argument("--stdio", action="store_true", help="Run stdio MCP server (default)")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="", help="MCP transport")
    parser.add_argument("--http", action="store_true", help="Shortcut for --transport streamable-http")
    parser.add_argument("--sse", action="store_true", help="Shortcut for --transport sse")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE bind host")
    parser.add_argument("--port", type=int, default=8765, help="HTTP/SSE bind port")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP endpoint path")
    parser.add_argument("--sse-path", default="/sse", help="SSE endpoint path")
    parser.add_argument("--message-path", default="/messages/", help="SSE message endpoint path")
    parser.add_argument("--json-response", action="store_true", help="Use JSON responses for streamable HTTP")
    parser.add_argument("--stateless-http", action="store_true", help="Run streamable HTTP without session state")
    parser.add_argument("--list-tools", action="store_true", help="Print tool list JSON and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_tools:
        print(
            json.dumps(
                {
                    "tools": list_tools(),
                    "resources": [
                        "dg://client-pack",
                        "dg://status",
                        "dg://usage",
                        "dg://notes",
                        "dg://notes/latest",
                        "dg://sessions",
                        "dg://sessions/latest",
                        "dg://sessions/latest/diff",
                        "dg://agent-runs",
                        "dg://agent-runs/latest",
                        "dg://agent-runs/latest/transcript",
                        "dg://capabilities/latest",
                        "dg://client-handoff",
                        "dg://client-handoff/markdown",
                        "dg://agent-hub",
                        "dg://agent-hub/markdown",
                        "dg://command-kit",
                        "dg://command-kit/markdown",
                        "dg://ide-clients",
                        "dg://ide-clients/markdown",
                        "dg://codex-profile",
                        "dg://codex-profile/config",
                    ],
                    "prompts": ["dg_agent_session", "dg_agent_context", "dg_agent_continue_latest"],
                    "server": "sdk",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    transport = args.transport or "stdio"
    if args.http:
        transport = "streamable-http"
    if args.sse:
        transport = "sse"
    if args.stdio:
        transport = "stdio"

    if transport in {"streamable-http", "sse"}:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.settings.streamable_http_path = args.path
        mcp.settings.sse_path = args.sse_path
        mcp.settings.message_path = args.message_path
        mcp.settings.json_response = bool(args.json_response)
        mcp.settings.stateless_http = bool(args.stateless_http)

    mcp.run(transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
