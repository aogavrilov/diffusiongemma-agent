#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DG_ROOT"

PYTHON="$DG_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
    PYTHON="python"
  else
    PYTHON="python3"
  fi
fi

"$PYTHON" - <<'PY'
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts import aider_dg_proxy as proxy

card = proxy.model_card()
assert card["id"] == proxy.PROXY_MODEL, card
assert card["mode"] == "safe_agent_gateway", card
assert card["max_output_tokens"] == proxy.MAX_OUTPUT_TOKENS, card

capabilities = proxy.gateway_capabilities()
assert capabilities["ok"] is True, capabilities
assert capabilities["openai_compat"]["chat_completions"] is True, capabilities
assert capabilities["openai_compat"]["responses"] is True, capabilities
assert capabilities["openai_compat"]["tool_call_delegation"] is True, capabilities
assert capabilities["openai_compat"]["native_model_tool_use"] is False, capabilities
assert capabilities["discovery"]["model_card"].endswith("/v1/model_card"), capabilities
assert capabilities["discovery"]["session_api"].endswith("/v1/agent/session"), capabilities
assert capabilities["discovery"]["tool_runtime"].endswith("/v1/agent/tool"), capabilities
assert capabilities["discovery"]["context"].endswith("/v1/agent/context"), capabilities
assert capabilities["discovery"]["rag_context"].endswith("/v1/agent/rag"), capabilities
assert capabilities["discovery"]["sessions"].endswith("/v1/agent/sessions"), capabilities
assert capabilities["discovery"]["latest_session_diff"].endswith("/v1/agent/sessions/latest/diff"), capabilities
assert capabilities["discovery"]["agent_runs"].endswith("/v1/agent/runs"), capabilities
assert capabilities["discovery"]["latest_agent_run"].endswith("/v1/agent/runs/latest"), capabilities
assert capabilities["discovery"]["tool_manifest"].endswith("/v1/agent/tool_manifest"), capabilities
assert capabilities["discovery"]["well_known_agent"].endswith("/.well-known/agent.json"), capabilities

routes = proxy.agent_routes()
route_ids = {item["id"] for item in routes["routes"]}
assert {"chat_completions", "responses", "session_api", "tool_runtime", "context_api", "rag_context_api", "session_artifacts", "agent_runs", "latest_session_diff", "model_card", "tool_manifest", "actions", "well_known_agent", "openapi", "mcp", "litellm"} <= route_ids, routes
assert any("dg://agent-hub/markdown" in item.get("resources", []) for item in routes["routes"]), routes

tool_manifest = proxy.agent_tool_manifest()
assert tool_manifest["schema_version"] == "dg.agent.tool_manifest.v1", tool_manifest
assert tool_manifest["http_session_api"]["endpoint"].endswith("/v1/agent/session"), tool_manifest
assert tool_manifest["http_session_api"]["execution_enabled"] is False, tool_manifest
assert tool_manifest["http_tool_runtime_api"]["endpoint"].endswith("/v1/agent/tool"), tool_manifest
assert "dg_context" in tool_manifest["http_tool_runtime_api"]["supported_tools"], tool_manifest
assert {"dg_agent", "dg_repo_status", "dg_git_diff", "dg_list_files", "dg_read_file", "dg_search", "dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline"} <= set(tool_manifest["http_tool_runtime_api"]["supported_tools"]), tool_manifest
assert tool_manifest["http_agent_api"]["tool_name"] == "dg_agent", tool_manifest
assert "dg_read_file" in tool_manifest["http_repo_tools"]["tools"], tool_manifest
assert "dg_code_outline" in tool_manifest["http_oss_repo_tools"]["tool_names"], tool_manifest
assert tool_manifest["http_session_artifacts"]["latest_diff_endpoint"].endswith("/v1/agent/sessions/latest/diff"), tool_manifest
assert "final_diff" in tool_manifest["http_session_artifacts"]["available_artifacts"], tool_manifest
assert tool_manifest["http_agent_run_artifacts"]["latest_endpoint"].endswith("/v1/agent/runs/latest"), tool_manifest
assert "transcript" in tool_manifest["http_agent_run_artifacts"]["available_artifacts"], tool_manifest
assert tool_manifest["http_context_api"]["endpoint"].endswith("/v1/agent/context"), tool_manifest
assert tool_manifest["http_rag_context_api"]["endpoint"].endswith("/v1/agent/rag"), tool_manifest
chat_tool = tool_manifest["openai_chat_completions"]["tools"][0]
assert chat_tool["function"]["name"] == "execute_command", chat_tool
assert chat_tool["function"]["parameters"]["properties"]["command"]["type"] == "string", chat_tool
chat_tool_names = {item["function"]["name"] for item in tool_manifest["openai_chat_completions"]["tools"]}
expected_tool_names = {"execute_command", "dg_agent", "dg_repo_status", "dg_git_diff", "dg_list_files", "dg_read_file", "dg_search", "dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline", "dg_session", "dg_context", "dg_rag_context", "dg_session_artifact", "dg_agent_run_artifact"}
missing_chat_tools = expected_tool_names - chat_tool_names
assert not missing_chat_tools, sorted(missing_chat_tools)
response_tool = tool_manifest["openai_responses"]["tools"][0]
assert response_tool["name"] == "execute_command", response_tool
response_tool_names = {item["name"] for item in tool_manifest["openai_responses"]["tools"]}
missing_response_tools = expected_tool_names - response_tool_names
assert not missing_response_tools, sorted(missing_response_tools)
recommended_command = tool_manifest["recommended_execution"]["command_template"]
assert "dg_agent.sh" in recommended_command and "session" in recommended_command, tool_manifest
assert "--rollback-on-failure" in recommended_command, tool_manifest

well_known = proxy.well_known_agent_manifest()
assert well_known["schema_version"] == "dg.agent.v1", well_known
assert well_known["tool_manifest_url"].endswith("/v1/agent/tool_manifest"), well_known
assert well_known["openapi_url"].endswith("/openapi.json"), well_known
assert well_known["tool_runtime_url"].endswith("/v1/agent/tool"), well_known
assert well_known["context_url"].endswith("/v1/agent/context"), well_known
assert well_known["rag_context_url"].endswith("/v1/agent/rag"), well_known
assert well_known["sessions_url"].endswith("/v1/agent/sessions"), well_known
assert well_known["agent_runs_url"].endswith("/v1/agent/runs"), well_known

session_preview = proxy.agent_session_action({
    "repo": ".",
    "task": "Inspect calc.py and report what would change.",
    "files": ["calc.py"],
})
assert session_preview["status"] == "dry_run", session_preview
assert session_preview["dry_run"] is True, session_preview
assert session_preview["execute"] is False, session_preview
assert "session" in session_preview["command"], session_preview
assert "--dry-run" in session_preview["command"], session_preview
assert "--rollback-on-failure" in session_preview["command"], session_preview

blocked_execution = proxy.agent_session_action({
    "repo": ".",
    "task": "Inspect calc.py and report what would change.",
    "execute": True,
    "dry_run": False,
})
assert blocked_execution["status"] == "blocked", blocked_execution
assert blocked_execution["execution_enabled"] is False, blocked_execution

context_delegate = proxy.tool_delegate(
    [{"role": "user", "content": "Find calc.py and explain add(a, b)."}],
    [item for item in tool_manifest["openai_chat_completions"]["tools"] if item["function"]["name"] == "dg_context"],
)
assert context_delegate["tool_call"]["function"]["name"] == "dg_context", context_delegate
context_args = json.loads(context_delegate["tool_call"]["function"]["arguments"])
assert context_args["task"].startswith("Find calc.py"), context_args
assert context_args["files"] == ["calc.py"], context_args

session_delegate = proxy.tool_delegate(
    [{"role": "user", "content": "Edit calc.py so add(a, b) returns a - b."}],
    [item for item in tool_manifest["openai_chat_completions"]["tools"] if item["function"]["name"] == "dg_session"],
)
assert session_delegate["tool_call"]["function"]["name"] == "dg_session", session_delegate
session_args = json.loads(session_delegate["tool_call"]["function"]["arguments"])
assert session_args["dry_run"] is True, session_args
assert session_args["rollback_on_failure"] is True, session_args
assert session_args["files"] == ["calc.py"], session_args

artifact_delegate = proxy.tool_delegate(
    [{"role": "user", "content": "Show the latest session diff."}],
    [item for item in tool_manifest["openai_chat_completions"]["tools"] if item["function"]["name"] == "dg_session_artifact"],
)
assert artifact_delegate["tool_call"]["function"]["name"] == "dg_session_artifact", artifact_delegate
artifact_args = json.loads(artifact_delegate["tool_call"]["function"]["arguments"])
assert artifact_args["artifact"] == "final_diff", artifact_args

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    git_available = subprocess.run(["git", "--version"], text=True, capture_output=True).returncode == 0
    if git_available:
        subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
        subprocess.run(["git", "add", "calc.py"], cwd=repo, text=True, capture_output=True, check=True)

    runtime_list = proxy.agent_tool_runtime_action({
        "name": "dg_list_files",
        "arguments": {"repo": str(repo), "pattern": "calc", "limit": 20},
    })
    assert runtime_list["ok"] is True, runtime_list
    assert runtime_list["tool"] == "dg_list_files", runtime_list
    assert runtime_list["result"]["files"] == ["calc.py"], runtime_list

    runtime_read = proxy.agent_tool_runtime_action({
        "name": "dg_read_file",
        "arguments": {"repo": str(repo), "path": "calc.py", "max_lines": 20},
    })
    assert runtime_read["ok"] is True, runtime_read
    assert runtime_read["result"]["path"] == "calc.py", runtime_read
    assert "def add" in runtime_read["result"]["content"], runtime_read

    final_after_tool = proxy.tool_delegate(
        [
            {"role": "user", "content": "Read file calc.py."},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_read",
                        "type": "function",
                        "function": {"name": "dg_read_file", "arguments": json.dumps({"repo": str(repo), "path": "calc.py"})},
                    }
                ],
            },
            runtime_read["tool_response"] | {"tool_call_id": "call_read"},
        ],
        [item for item in tool_manifest["openai_chat_completions"]["tools"] if item["function"]["name"] == "dg_read_file"],
    )
    assert final_after_tool["tool_call"] is None, final_after_tool
    assert "Tool result summary" in final_after_tool["content"], final_after_tool
    assert "def add" in final_after_tool["content"], final_after_tool

    runtime_search = proxy.agent_tool_runtime_action({
        "name": "dg_search",
        "arguments": {"repo": str(repo), "query": "def add", "max_matches": 10},
    })
    assert runtime_search["ok"] is True, runtime_search
    assert runtime_search["result"]["matches"], runtime_search
    assert "calc.py" in runtime_search["result"]["content"], runtime_search

    runtime_agent_preview = proxy.agent_tool_runtime_action({
        "name": "dg_agent",
        "arguments": {
            "repo": str(repo),
            "task": "Fix calc.py so add(a, b) returns a - b.",
            "mode": "edit",
        },
    })
    assert runtime_agent_preview["ok"] is True, runtime_agent_preview
    assert runtime_agent_preview["tool"] == "dg_agent", runtime_agent_preview
    assert runtime_agent_preview["result"]["status"] == "dry_run", runtime_agent_preview
    assert "--mode edit" in runtime_agent_preview["result"]["command_text"], runtime_agent_preview
    assert "--dry-run" in runtime_agent_preview["result"]["command"], runtime_agent_preview

    if git_available:
        runtime_status = proxy.agent_tool_runtime_action({
            "name": "dg_repo_status",
            "arguments": {"repo": str(repo), "max_chars": 4000},
        })
        assert runtime_status["ok"] is True, runtime_status
        assert "calc.py" in runtime_status["result"]["content"], runtime_status

        runtime_diff = proxy.agent_tool_runtime_action({
            "name": "dg_git_diff",
            "arguments": {"repo": str(repo), "cached": True, "max_chars": 4000},
        })
        assert runtime_diff["ok"] is True, runtime_diff
        assert "def add" in runtime_diff["result"]["content"], runtime_diff

    context = proxy.agent_context_action({
        "repo": str(repo),
        "task": "Find calc.py and explain add(a, b).",
        "files": ["calc.py"],
        "max_files": 2,
        "max_snippet_chars": 500,
    })
    assert context["ok"] is True, context
    assert context["context"]["selected_files"][0] == "calc.py", context
    assert "def add" in context["content"], context

    rag_context = proxy.agent_rag_context_action({
        "repo": str(repo),
        "task": "Find calc.py and explain add(a, b).",
        "max_context_chars": 1000,
        "max_files": 2,
        "timeout": 20,
    })
    assert rag_context["ok"] is True, rag_context
    assert "calc.py" in rag_context["content"], rag_context
    assert "def add" in rag_context["content"], rag_context

    runtime_context = proxy.agent_tool_runtime_action({
        "name": "dg_context",
        "arguments": {
            "repo": str(repo),
            "task": "Find calc.py and explain add(a, b).",
            "files": ["calc.py"],
            "max_files": 2,
            "max_snippet_chars": 500,
        },
    })
    assert runtime_context["ok"] is True, runtime_context
    assert runtime_context["tool"] == "dg_context", runtime_context
    assert runtime_context["tool_response"]["role"] == "tool", runtime_context
    assert runtime_context["result"]["context"]["selected_files"][0] == "calc.py", runtime_context

    runtime_tool_call = proxy.agent_tool_runtime_action({
        "tool_call": {
            "id": "call_test_context",
            "type": "function",
            "function": {
                "name": "dg_rag_context",
                "arguments": json.dumps({
                    "repo": str(repo),
                    "task": "Find calc.py and explain add(a, b).",
                    "max_context_chars": 1000,
                    "max_files": 2,
                    "timeout": 20,
                }),
            },
        }
    })
    assert runtime_tool_call["ok"] is True, runtime_tool_call
    assert runtime_tool_call["tool"] == "dg_rag_context", runtime_tool_call
    assert runtime_tool_call["tool_response"]["tool_call_id"] == "call_test_context", runtime_tool_call

blocked_shell = proxy.agent_tool_runtime_action({
    "name": "execute_command",
    "arguments": {"command": "rm -rf /tmp/example"},
})
assert blocked_shell["ok"] is False, blocked_shell
assert blocked_shell["result"]["status"] == "blocked", blocked_shell

reports = proxy.session_reports()
if reports:
    latest = reports[0]
    summary = proxy.session_summary(latest)
    assert summary["session_dir"], summary
    diff_artifact = proxy.read_session_artifact(latest, "diff")
    assert diff_artifact["ok"] is True, diff_artifact
    assert diff_artifact["artifact"] == "final_diff", diff_artifact
    runtime_artifact = proxy.agent_tool_runtime_action({
        "name": "dg_session_artifact",
        "arguments": {"session": "latest", "artifact": "diff"},
    })
    assert runtime_artifact["ok"] is True, runtime_artifact
    assert runtime_artifact["result"]["artifact"] == "final_diff", runtime_artifact

run_dir = proxy.DEFAULT_AGENT_RUN_ROOT / "smoke-agent-run-artifact"
if run_dir.exists():
    shutil.rmtree(run_dir)
run_dir.mkdir(parents=True)
try:
    transcript = run_dir / "tool-loop.json"
    stdout = run_dir / "stdout.log"
    stderr = run_dir / "stderr.log"
    transcript.write_text('{"status": "success", "content": "def add"}\n', encoding="utf-8")
    stdout.write_text("agent stdout\n", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    report = {
        "status": "success",
        "mode": "read",
        "route": "openai_tool_loop_read_only",
        "task": "Read calc.py",
        "repo": ".",
        "run_dir": str(run_dir),
        "returncode": 0,
        "elapsed_sec": 0.1,
        "steps": 1,
        "tool_names": ["dg_read_file"],
        "artifacts": {
            "transcript": str(transcript),
            "stdout": str(stdout),
            "stderr": str(stderr),
        },
    }
    (run_dir / "agent.json").write_text(json.dumps(report), encoding="utf-8")
    loaded = proxy.load_agent_run_report(run="smoke-agent-run-artifact")
    assert loaded is not None, proxy.agent_run_reports()
    run_artifact = proxy.read_agent_run_artifact(loaded, "transcript")
    assert run_artifact["ok"] is True, run_artifact
    assert run_artifact["artifact"] == "transcript", run_artifact
    assert "def add" in run_artifact["content"], run_artifact
    runtime_run_artifact = proxy.agent_tool_runtime_action({
        "name": "dg_agent_run_artifact",
        "arguments": {"run": "smoke-agent-run-artifact", "artifact": "tool-loop"},
    })
    assert runtime_run_artifact["ok"] is True, runtime_run_artifact
    assert runtime_run_artifact["result"]["artifact"] == "transcript", runtime_run_artifact
    assert "def add" in runtime_run_artifact["result"]["content"], runtime_run_artifact
finally:
    shutil.rmtree(run_dir, ignore_errors=True)

models = proxy.models()
assert models["object"] == "list", models
assert models["data"][0]["id"] == proxy.PROXY_MODEL, models
assert models["data"][0]["mode"] == "safe_agent_gateway", models
assert models["data"][0]["tool_manifest_url"].endswith("/v1/agent/tool_manifest"), models

files = {"hello.py": 'def greet(name):\n    return f"hello {name}"\n'}
task = "Fix hello.py so greet('Ada') returns exactly hello, Ada! Keep the function name and signature unchanged."
listing = proxy.fallback_listing_from_task(task, files)
assert proxy.is_normalized_listing(listing, files), listing
assert 'return f"hello, {name}!"' in listing, listing

files = {"score.py": 'def label_score(score):\n    return "TODO"\n'}
task = (
    "Edit score.py. Implement label_score(score): return 'high' when score is greater than or equal to 90, "
    "otherwise return 'normal'. Keep the same function name.\n\n"
    "Derived exact code constraint:\n"
    "return 'high' if score >= 90 else 'normal'"
)
listing = proxy.fallback_listing_from_task(task, files)
assert proxy.is_normalized_listing(listing, files), listing
assert "return 'high' if score >= 90 else 'normal'" in listing, listing

malformed = "thought\n* Input file: `score.py`\n  * __:"
assert not proxy.is_normalized_listing(proxy.normalize_listing(malformed, files), files)
raw_channel = "<|channel>thought\ninternal notes\n<|channel>final\nscore.py\n```python\nprint('ok')\n```"
cleaned = proxy.sanitize_backend_text(raw_channel)
assert "<|channel>" not in cleaned, cleaned
assert proxy.is_normalized_listing(proxy.normalize_listing(raw_channel, files), files), raw_channel

mini_messages = [
    {
        "role": "system",
        "content": (
            "Every response must contain exactly one bash action block:\n"
            "```mswea_bash_command\ncommand\n```\n"
            "End with COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT."
        ),
    },
    {
        "role": "user",
        "content": "Please solve this issue: Update calc.py so add handles ints.\n\nUse short bash commands.",
    },
]
delegate = proxy.safe_mini_swe_response(mini_messages)
assert delegate is not None, delegate
assert delegate.count("```mswea_bash_command") == 1, delegate
assert "dg_agent.sh" in delegate and "session" in delegate, delegate
assert "--repo" in delegate and "$(pwd)" in delegate, delegate
assert "--rollback-on-failure" in delegate, delegate
assert "Update calc.py so add handles ints" in delegate, delegate

finish = proxy.safe_mini_swe_response(mini_messages + [{"role": "assistant", "content": delegate}])
assert finish == "```mswea_bash_command\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n```", finish

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    }
]
tool_result = proxy.tool_delegate(
    [{"role": "user", "content": "Edit calc.py so add(a, b) returns a - b."}],
    tools,
)
assert tool_result is not None, tool_result
tool_call = tool_result["tool_call"]
assert tool_call["function"]["name"] == "execute_command", tool_call
arguments = json.loads(tool_call["function"]["arguments"])
assert "dg_agent.sh" in arguments["command"] and "session" in arguments["command"], arguments
assert "--repo" in arguments["command"] and "$(pwd)" in arguments["command"], arguments
assert "--rollback-on-failure" in arguments["command"], arguments

after_tool = proxy.tool_delegate(
    [
        {"role": "user", "content": "Edit calc.py."},
        {"role": "tool", "tool_call_id": tool_call["id"], "content": "Session status: success"},
    ],
    tools,
)
assert after_tool["tool_call"] is None, after_tool
assert "Tool result summary" in after_tool["content"], after_tool
assert "Session status: success" in after_tool["content"], after_tool

messages = proxy.responses_messages({
    "instructions": "Use available tools.",
    "input": "Edit calc.py so add(a, b) returns a - b.",
})
assert messages[-1]["role"] == "user", messages
assert "calc.py" in messages[-1]["content"], messages
resp_delegate = proxy.tool_delegate(messages, [{"type": "function", "name": "execute_command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}])
assert resp_delegate and resp_delegate["tool_call"], resp_delegate

print("Aider proxy adapter smoke passed.")
PY
