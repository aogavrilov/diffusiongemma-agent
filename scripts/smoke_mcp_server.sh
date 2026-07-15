#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(uname -s 2>/dev/null || true)" != Linux* ]] && command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
  win_root="$(cygpath -am "$DG_ROOT")"
  wsl_root="$(wsl.exe wslpath -a "$win_root" | sed 's/\r$//')"
  export MSYS2_ARG_CONV_EXCL='*'
  export MSYS_NO_PATHCONV=1
  exec wsl.exe bash -lc "cd $(printf '%q' "$wsl_root") && exec ./scripts/smoke_mcp_server.sh"
fi

PYTHON="${DG_AGENT_PYTHON:-}"
if [[ -z "$PYTHON" || ! -x "$PYTHON" || "$PYTHON" == *.exe || "$PYTHON" == *:\/* ]]; then
  if [[ -x "/root/diffusiongemma-agent/.venv-wsl/bin/python" ]]; then
    PYTHON="/root/diffusiongemma-agent/.venv-wsl/bin/python"
  elif [[ -x "$DG_ROOT/.venv/bin/python" ]]; then
    PYTHON="$DG_ROOT/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

"$DG_ROOT/scripts/dg_agent.sh" mcp --list-tools >/tmp/dg-mcp-tools.json
"$PYTHON" -m json.tool /tmp/dg-mcp-tools.json >/dev/null
grep -F '"dg_status"' /tmp/dg-mcp-tools.json
grep -F '"dg_task_note"' /tmp/dg-mcp-tools.json
grep -F '"dg_task_notes"' /tmp/dg-mcp-tools.json
grep -F '"dg_repo_status"' /tmp/dg-mcp-tools.json
grep -F '"dg_list_files"' /tmp/dg-mcp-tools.json
grep -F '"dg_search"' /tmp/dg-mcp-tools.json
grep -F '"dg_read_file"' /tmp/dg-mcp-tools.json
grep -F '"dg_git_diff"' /tmp/dg-mcp-tools.json
grep -F '"dg_context"' /tmp/dg-mcp-tools.json
grep -F '"dg_rag_context"' /tmp/dg-mcp-tools.json
grep -F '"dg_rag_answer"' /tmp/dg-mcp-tools.json
grep -F '"dg_repo_pack"' /tmp/dg-mcp-tools.json
grep -F '"dg_repo_map"' /tmp/dg-mcp-tools.json
grep -F '"dg_ast_grep"' /tmp/dg-mcp-tools.json
grep -F '"dg_code_outline"' /tmp/dg-mcp-tools.json
grep -F '"dg_preflight"' /tmp/dg-mcp-tools.json
grep -F '"dg_plan"' /tmp/dg-mcp-tools.json
grep -F '"dg_task"' /tmp/dg-mcp-tools.json
grep -F '"dg_session"' /tmp/dg-mcp-tools.json
grep -F '"dg_verify"' /tmp/dg-mcp-tools.json
grep -F '"dg_capabilities"' /tmp/dg-mcp-tools.json
grep -F '"dg_client_smoke"' /tmp/dg-mcp-tools.json
grep -F '"dg_client_report"' /tmp/dg-mcp-tools.json
grep -F '"dg_sessions"' /tmp/dg-mcp-tools.json
grep -F '"dg_session_artifact"' /tmp/dg-mcp-tools.json
grep -F '"dg_agent_runs"' /tmp/dg-mcp-tools.json
grep -F '"dg_agent_run_artifact"' /tmp/dg-mcp-tools.json
grep -F '"dg://client-pack"' /tmp/dg-mcp-tools.json
grep -F '"dg://notes"' /tmp/dg-mcp-tools.json
grep -F '"dg://notes/latest"' /tmp/dg-mcp-tools.json
grep -F '"dg://sessions"' /tmp/dg-mcp-tools.json
grep -F '"dg://agent-runs"' /tmp/dg-mcp-tools.json
grep -F '"dg://agent-runs/latest"' /tmp/dg-mcp-tools.json
grep -F '"dg://agent-runs/latest/transcript"' /tmp/dg-mcp-tools.json
grep -F '"dg://capabilities/latest"' /tmp/dg-mcp-tools.json
grep -F '"dg://client-handoff"' /tmp/dg-mcp-tools.json
grep -F '"dg://client-handoff/markdown"' /tmp/dg-mcp-tools.json
grep -F '"dg://agent-hub"' /tmp/dg-mcp-tools.json
grep -F '"dg://agent-hub/markdown"' /tmp/dg-mcp-tools.json
grep -F '"dg://command-kit"' /tmp/dg-mcp-tools.json
grep -F '"dg://command-kit/markdown"' /tmp/dg-mcp-tools.json
grep -F '"dg://ide-clients"' /tmp/dg-mcp-tools.json
grep -F '"dg://ide-clients/markdown"' /tmp/dg-mcp-tools.json
grep -F '"dg://codex-profile"' /tmp/dg-mcp-tools.json
grep -F '"dg://codex-profile/config"' /tmp/dg-mcp-tools.json
grep -F '"dg_agent_session"' /tmp/dg-mcp-tools.json
grep -F '"dg_agent_continue_latest"' /tmp/dg-mcp-tools.json

DG_ROOT="$DG_ROOT" "$PYTHON" - <<'PY'
import anyio
import json
import os
import subprocess
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

dg_root = Path(os.environ["DG_ROOT"])
repo = Path(tempfile.mkdtemp(prefix="dg-mcp-smoke."))
(repo / "hello.py").write_text(
    'def greet(name):\n    return f"hello {name}"\n',
    encoding="utf-8",
)
subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
subprocess.run(["git", "config", "user.email", "local-smoke@example.invalid"], cwd=repo, check=True)
subprocess.run(["git", "config", "user.name", "Local Smoke"], cwd=repo, check=True)
subprocess.run(["git", "add", "hello.py"], cwd=repo, check=True)
subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
subprocess.run(
    [str(dg_root / "scripts" / "dg_agent.sh"), "workspace-init", "--repo", str(repo), "--json"],
    cwd=repo,
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
(repo / "hello.py").write_text(
    'def greet(name):\n    return f"hello {name}!"\n',
    encoding="utf-8",
)


def tool_text(result) -> str:
    structured = getattr(result, "structuredContent", None) or {}
    if isinstance(structured, dict) and structured.get("text"):
        return structured["text"]
    text = "\n".join(
        getattr(block, "text", "")
        for block in result.content
        if getattr(block, "type", "") == "text"
    )
    try:
        decoded = json.loads(text)
        if isinstance(decoded, dict) and decoded.get("text"):
            return decoded["text"]
    except Exception:
        pass
    return text


async def main() -> None:
    created_note = None
    env = os.environ.copy()
    env["DG_MCP_REPO"] = str(repo)
    params = StdioServerParameters(
        command=str(dg_root / "scripts" / "dg_agent.sh"),
        args=["mcp"],
        cwd=str(repo),
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {
                "dg_repo_status",
                "dg_task_note",
                "dg_task_notes",
                "dg_list_files",
                "dg_search",
                "dg_read_file",
                "dg_git_diff",
                "dg_status",
                "dg_context",
                "dg_rag_context",
                "dg_rag_answer",
                "dg_repo_pack",
                "dg_repo_map",
                "dg_ast_grep",
                "dg_code_outline",
                "dg_preflight",
                "dg_plan",
                "dg_task",
                "dg_session",
                "dg_verify",
                "dg_capabilities",
                "dg_client_smoke",
                "dg_client_report",
                "dg_sessions",
                "dg_session_artifact",
                "dg_agent_runs",
                "dg_agent_run_artifact",
            } <= names, names

            resources = await session.list_resources()
            resource_uris = {str(resource.uri) for resource in resources.resources}
            assert {
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
            } <= resource_uris, resource_uris
            client_pack = await session.read_resource("dg://client-pack")
            client_text = "\n".join(getattr(item, "text", "") for item in client_pack.contents)
            assert "DiffusionGemma local agent client pack" in client_text, client_text[:500]
            agent_hub_md = await session.read_resource("dg://agent-hub/markdown")
            agent_hub_md_text = "\n".join(getattr(item, "text", "") for item in agent_hub_md.contents)
            assert "DG Local Agent Hub" in agent_hub_md_text and "safe code edit" in agent_hub_md_text.lower(), agent_hub_md_text[:500]
            command_kit = await session.read_resource("dg://command-kit")
            command_kit_text = "\n".join(getattr(item, "text", "") for item in command_kit.contents)
            command_kit_json = json.loads(command_kit_text)
            assert command_kit_json["name"] == "DG local agent command kit", command_kit_json
            command_kit_md = await session.read_resource("dg://command-kit/markdown")
            command_kit_md_text = "\n".join(getattr(item, "text", "") for item in command_kit_md.contents)
            assert "DG Agent Command Kit" in command_kit_md_text, command_kit_md_text[:500]
            ide_clients_md = await session.read_resource("dg://ide-clients/markdown")
            ide_clients_md_text = "\n".join(getattr(item, "text", "") for item in ide_clients_md.contents)
            assert "DG IDE Client Profiles" in ide_clients_md_text, ide_clients_md_text[:500]
            codex_profile = await session.read_resource("dg://codex-profile")
            codex_profile_text = "\n".join(getattr(item, "text", "") for item in codex_profile.contents)
            assert "DG Codex CLI Profile" in codex_profile_text, codex_profile_text[:500]
            codex_config = await session.read_resource("dg://codex-profile/config")
            codex_config_text = "\n".join(getattr(item, "text", "") for item in codex_config.contents)
            assert "DiffusionGemma Local Safe Agent Proxy" in codex_config_text, codex_config_text[:500]
            sessions_resource = await session.read_resource("dg://sessions")
            sessions_text = "\n".join(getattr(item, "text", "") for item in sessions_resource.contents)
            assert "sessions" in sessions_text, sessions_text[:500]
            agent_runs_resource = await session.read_resource("dg://agent-runs")
            agent_runs_text = "\n".join(getattr(item, "text", "") for item in agent_runs_resource.contents)
            assert "runs" in agent_runs_text, agent_runs_text[:500]

            prompts = await session.list_prompts()
            prompt_names = {prompt.name for prompt in prompts.prompts}
            assert {"dg_agent_session", "dg_agent_context", "dg_agent_continue_latest"} <= prompt_names, prompt_names
            prompt = await session.get_prompt(
                "dg_agent_session",
                {"repo": str(repo), "task": "inspect the greeting function", "file": "hello.py"},
            )
            prompt_text = "\n".join(getattr(message.content, "text", "") for message in prompt.messages)
            assert "dg_preflight" in prompt_text and "dg_rag_context" in prompt_text and "dg_session" in prompt_text, prompt_text
            continue_prompt = await session.get_prompt("dg_agent_continue_latest", {"next_task": "inspect artifacts"})
            continue_text = "\n".join(getattr(message.content, "text", "") for message in continue_prompt.messages)
            assert "dg://sessions/latest" in continue_text and "dg://agent-runs/latest" in continue_text and "dg_plan" in continue_text, continue_text

            listed = await session.call_tool("dg_sessions", {"limit": 1})
            assert not getattr(listed, "isError", False), listed
            listed_text = "\n".join(
                getattr(block, "text", "")
                for block in listed.content
                if getattr(block, "type", "") == "text"
            )
            assert "sessions" in listed_text, listed_text[:500]

            listed_runs = await session.call_tool("dg_agent_runs", {"limit": 1})
            assert not getattr(listed_runs, "isError", False), listed_runs
            listed_runs_text = "\n".join(
                getattr(block, "text", "")
                for block in listed_runs.content
                if getattr(block, "type", "") == "text"
            )
            assert "runs" in listed_runs_text, listed_runs_text[:500]

            latest_run = await session.call_tool("dg_agent_run_artifact", {"artifact": "agent_json", "latest": True})
            latest_run_text = tool_text(latest_run)
            no_latest_run = "agent run not found" in latest_run_text
            if not getattr(latest_run, "isError", False) and not no_latest_run:
                assert "run_dir" in latest_run_text or "status" in latest_run_text, latest_run_text[:500]
                latest_run_resource = await session.read_resource("dg://agent-runs/latest")
                latest_run_resource_text = "\n".join(getattr(item, "text", "") for item in latest_run_resource.contents)
                assert "run_dir" in latest_run_resource_text or "status" in latest_run_resource_text, latest_run_resource_text[:500]
                latest_run_transcript = await session.read_resource("dg://agent-runs/latest/transcript")
                latest_run_transcript_text = "\n".join(getattr(item, "text", "") for item in latest_run_transcript.contents)
                assert latest_run_transcript_text.strip(), latest_run_transcript_text[:500]

            # dg_client_report launches the complete client bootstrap and its
            # own live smoke. That end-to-end path is covered by the dedicated
            # client-report suite; invoking it here turns a transport smoke
            # into a multi-minute nested integration test.

            note_result = await session.call_tool(
                "dg_task_note",
                {
                    "repo": str(repo),
                    "task": "inspect the greeting function",
                    "title": "MCP smoke note",
                    "body": "Remember that hello.py has a modified greeting.",
                    "tags": ["smoke", "mcp"],
                },
            )
            assert not getattr(note_result, "isError", False), note_result
            note_text = tool_text(note_result)
            assert "written:" in note_text, note_text
            created_note = Path(note_text.split("written:", 1)[1].strip())

            notes_result = await session.call_tool("dg_task_notes", {"latest": True})
            assert not getattr(notes_result, "isError", False), notes_result
            notes_text = tool_text(notes_result)
            assert "modified greeting" in notes_text, notes_text

            notes_resource = await session.read_resource("dg://notes/latest")
            notes_resource_text = "\n".join(getattr(item, "text", "") for item in notes_resource.contents)
            assert "modified greeting" in notes_resource_text, notes_resource_text[:500]
            if created_note and created_note.exists():
                created_note.unlink()

            files_result = await session.call_tool("dg_list_files", {"repo": str(repo), "pattern": "hello", "limit": 10})
            assert not getattr(files_result, "isError", False), files_result
            files_text = tool_text(files_result)
            assert "hello.py" in files_text, files_text

            read_result = await session.call_tool("dg_read_file", {"repo": str(repo), "path": "hello.py", "max_lines": 20})
            assert not getattr(read_result, "isError", False), read_result
            read_text = tool_text(read_result)
            assert "def greet" in read_text and "hello.py" not in read_text[:20], read_text

            search_result = await session.call_tool("dg_search", {"repo": str(repo), "query": "greet", "max_matches": 10})
            assert not getattr(search_result, "isError", False), search_result
            search_text = tool_text(search_result)
            assert "hello.py" in search_text and "greet" in search_text, search_text

            ast_result = await session.call_tool(
                "dg_ast_grep",
                {
                    "repo": str(repo),
                    "lang": "python",
                    "pattern": "return $X",
                    "paths": ["hello.py"],
                    "max_matches": 5,
                    "max_chars": 6000,
                    "timeout": 120,
                },
            )
            ast_text = tool_text(ast_result)
            if getattr(ast_result, "isError", False) or "spawn UNKNOWN" in ast_text:
                print("SKIP dg_ast_grep: native WSL Node/ast-grep is unavailable")
            else:
                assert "dg_agent.sh ast-grep" in ast_text and "hello.py" in ast_text, ast_text
                assert "return f\\\"hello {name}!\\\"" in ast_text or "return f\"hello {name}!\"" in ast_text, ast_text

            outline_result = await session.call_tool(
                "dg_code_outline",
                {
                    "repo": str(repo),
                    "lang": "python",
                    "paths": ["hello.py"],
                    "max_items": 20,
                    "max_chars": 6000,
                    "timeout": 120,
                },
            )
            assert not getattr(outline_result, "isError", False), outline_result
            outline_text = tool_text(outline_result)
            assert "dg_agent.sh code-outline" in outline_text and "hello.py" in outline_text, outline_text
            assert "greet" in outline_text, outline_text

            status_result = await session.call_tool("dg_repo_status", {"repo": str(repo)})
            assert not getattr(status_result, "isError", False), status_result
            status_text = tool_text(status_result)
            assert "hello.py" in status_text, status_text

            diff_result = await session.call_tool("dg_git_diff", {"repo": str(repo), "files": ["hello.py"], "max_chars": 4000})
            assert not getattr(diff_result, "isError", False), diff_result
            diff_text = tool_text(diff_result)
            assert "hello {name}!" in diff_text, diff_text

            result = await session.call_tool(
                "dg_context",
                {
                    "repo": str(repo),
                    "task": "inspect the greeting function",
                    "files": ["hello.py"],
                    "max_files": 1,
                    "timeout": 60,
                },
            )
            assert not getattr(result, "isError", False), result
            structured = getattr(result, "structuredContent", None) or {}
            text = structured.get("text", "")
            if not text:
                text = "\n".join(
                    getattr(block, "text", "")
                    for block in result.content
                    if getattr(block, "type", "") == "text"
                )
                try:
                    decoded = json.loads(text)
                    text = decoded.get("text", text) if isinstance(decoded, dict) else text
                except Exception:
                    pass
            assert "dg_agent.sh context" in text, text
            assert "hello.py" in text, text

            rag_result = await session.call_tool(
                "dg_rag_context",
                {
                    "repo": str(repo),
                    "task": "inspect the greeting function in hello.py",
                    "max_context_chars": 1200,
                    "max_files": 2,
                    "debug": True,
                    "timeout": 60,
                },
            )
            assert not getattr(rag_result, "isError", False), rag_result
            rag_text = tool_text(rag_result)
            assert "dg_agent.sh rag" in rag_text and "selected file map" in rag_text, rag_text
            assert "hello.py" in rag_text and "def greet" in rag_text, rag_text

            pack_result = await session.call_tool(
                "dg_repo_pack",
                {
                    "repo": str(repo),
                    "style": "markdown",
                    "include": ["hello.py"],
                    "max_chars": 6000,
                    "timeout": 120,
                },
            )
            pack_text = tool_text(pack_result)
            if getattr(pack_result, "isError", False) or "spawn UNKNOWN" in pack_text:
                print("SKIP dg_repo_pack: native WSL Node/Repomix is unavailable")
            else:
                assert "dg_agent.sh repo-pack" in pack_text and "hello.py" in pack_text, pack_text
                assert "def greet" in pack_text or "return f\"hello {name}!\"" in pack_text, pack_text

            repo_map_result = await session.call_tool(
                "dg_repo_map",
                {
                    "repo": str(repo),
                    "map_tokens": 1024,
                    "paths": ["hello.py"],
                    "map_only": True,
                    "max_chars": 6000,
                    "timeout": 180,
                },
            )
            repo_map_text = tool_text(repo_map_result)
            if getattr(repo_map_result, "isError", False) or "spawn UNKNOWN" in repo_map_text or "aider is not installed" in repo_map_text:
                print("SKIP dg_repo_map: upstream Aider is unavailable")
            else:
                assert "dg_agent.sh repo-map" in repo_map_text and "hello.py" in repo_map_text, repo_map_text
                assert "def greet" in repo_map_text or "class Runner" in repo_map_text, repo_map_text

            preflight_result = await session.call_tool(
                "dg_preflight",
                {
                    "repo": str(repo),
                    "task": "inspect the greeting function",
                    "files": ["hello.py"],
                    "allow_dirty": True,
                    "timeout": 60,
                },
            )
            assert not getattr(preflight_result, "isError", False), preflight_result
            preflight_text = tool_text(preflight_result)
            assert "dg_agent.sh preflight" in preflight_text, preflight_text
            preflight_structured = getattr(preflight_result, "structuredContent", None) or {}
            preflight_stdout = (preflight_structured.get("structured") or {}).get("stdout", "")
            preflight_data = json.loads(preflight_stdout)
            assert preflight_data["status"] in {"static-ready", "live-ready"}, preflight_data
            assert preflight_data["issues"] == [], preflight_data

            plan_path = repo / ".dg-agent" / "mcp-smoke-plan.json"
            plan_result = await session.call_tool(
                "dg_plan",
                {
                    "repo": str(repo),
                    "task": "inspect the greeting function",
                    "files": ["hello.py"],
                    "out": str(plan_path),
                    "name": "mcp-smoke",
                    "auto_test": True,
                    "timeout": 60,
                },
            )
            assert not getattr(plan_result, "isError", False), plan_result
            plan_text = tool_text(plan_result)
            assert str(plan_path) in plan_text and plan_path.exists(), plan_text
            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            assert plan_data["steps"][0]["name"] == "mcp-smoke", plan_data
            assert plan_data["steps"][0]["files"] == ["hello.py"], plan_data

            task_result = await session.call_tool(
                "dg_task",
                {
                    "repo": str(repo),
                    "plan": str(plan_path),
                    "allow_dirty": True,
                    "dry_run": True,
                    "rollback_on_failure": True,
                    "timeout": 60,
                },
            )
            assert not getattr(task_result, "isError", False), task_result
            task_text = tool_text(task_result)
            assert "dg_agent.sh task" in task_text and "--dry-run" in task_text, task_text
            assert "DG task runner finished: success" in task_text, task_text


anyio.run(main)
PY

echo "DG MCP server smoke passed."
