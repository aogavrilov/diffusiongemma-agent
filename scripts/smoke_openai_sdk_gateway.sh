#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python_exists() {
  local candidate="$1"
  if [[ "$candidate" == */* ]]; then
    [[ -x "$candidate" ]] || return 1
  else
    command -v "$candidate" >/dev/null 2>&1 || return 1
  fi
  "$candidate" - <<'PY' >/dev/null 2>&1
print("ok")
PY
}

python_can_run_openai_sdk() {
  local candidate="$1"
  python_exists "$candidate" || return 1
  "$candidate" - <<'PY' >/dev/null 2>&1
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8090/v1", api_key="dummy")
_ = client.models
_ = client.chat.completions
_ = client.responses
PY
}

HTTP_PYTHON=""
for candidate in \
  "$DG_ROOT/.venv-litellm/bin/python" \
  "$DG_ROOT/.venv/bin/python" \
  "$DG_ROOT/.venv/Scripts/python.exe" \
  python \
  python3; do
  if python_exists "$candidate"; then
    HTTP_PYTHON="$candidate"
    break
  fi
done

if [[ -z "$HTTP_PYTHON" ]]; then
  echo "OpenAI SDK smoke needs a Python interpreter for HTTP endpoint checks." >&2
  exit 1
fi

SDK_PYTHON=""
for candidate in \
  "$DG_ROOT/.venv-litellm/bin/python" \
  "$DG_ROOT/.venv/bin/python" \
  "$DG_ROOT/.venv/Scripts/python.exe" \
  python \
  python3; do
  if python_can_run_openai_sdk "$candidate"; then
    SDK_PYTHON="$candidate"
    break
  fi
done

if [[ -z "$SDK_PYTHON" ]]; then
  if [[ -x "$DG_ROOT/scripts/install_litellm_local.sh" ]]; then
    "$DG_ROOT/scripts/install_litellm_local.sh" >/tmp/dg-litellm-install.log
    if python_can_run_openai_sdk "$DG_ROOT/.venv-litellm/bin/python"; then
      SDK_PYTHON="$DG_ROOT/.venv-litellm/bin/python"
    fi
  fi
fi

http_ok() {
  curl -fsS --max-time 5 "$1" >/dev/null
}

if ! http_ok "http://127.0.0.1:4100/healthz" || ! http_ok "http://127.0.0.1:8090/healthz"; then
  "$DG_ROOT/scripts/dg_agent.sh" up --wait-timeout 180 >/tmp/dg-openai-sdk-up.log
fi

http_ok "http://127.0.0.1:4100/healthz"
http_ok "http://127.0.0.1:8090/healthz"

if [[ -n "$SDK_PYTHON" ]]; then
timeout 150s "$SDK_PYTHON" - <<'PY' >/tmp/dg-openai-sdk-gateway-response.txt
import json
import urllib.request

from openai import OpenAI

PROXY_MODEL = "diffusiongemma-26b-a4b-it-iq4xs-aider-local"

client = OpenAI(
    base_url="http://127.0.0.1:8090/v1",
    api_key="dummy",
    timeout=120.0,
)

models = client.models.list()
ids = [model.id for model in models.data]
assert PROXY_MODEL in ids, ids

resp = client.chat.completions.create(
    model=PROXY_MODEL,
    messages=[
        {
            "role": "user",
            "content": "Reply with one short sentence: local gateway works.",
        }
    ],
    max_tokens=128,
    temperature=0.2,
)

text = (resp.choices[0].message.content or "").strip()
assert text, resp
bad = ("backend error", "internal server error", "traceback", "jsondecodeerror")
assert not any(item in text.lower() for item in bad), text
print(text[:1000])

tool_resp = client.chat.completions.create(
    model=PROXY_MODEL,
    messages=[
        {
            "role": "user",
            "content": "Edit calc.py so add(a, b) returns a - b.",
        }
    ],
    tools=[
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
    ],
    max_tokens=128,
)
choice = tool_resp.choices[0]
assert choice.finish_reason == "tool_calls", tool_resp
tool_calls = choice.message.tool_calls or []
assert len(tool_calls) == 1, tool_resp
tool_call = tool_calls[0]
assert tool_call.function.name == "execute_command", tool_call
assert "dg_agent.sh" in tool_call.function.arguments and "session" in tool_call.function.arguments, tool_call.function.arguments
assert "--rollback-on-failure" in tool_call.function.arguments, tool_call.function.arguments

response = client.responses.create(
    model=PROXY_MODEL,
    input="Edit calc.py so add(a, b) returns a - b.",
    tools=[
        {
            "type": "function",
            "name": "execute_command",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        }
    ],
)
function_calls = [item for item in response.output if item.type == "function_call"]
assert len(function_calls) == 1, response
call = function_calls[0]
assert call.name == "execute_command", call
assert "dg_agent.sh" in call.arguments and "session" in call.arguments, call.arguments
assert "--rollback-on-failure" in call.arguments, call.arguments

dg_context_resp = client.chat.completions.create(
    model=PROXY_MODEL,
    messages=[
        {
            "role": "user",
            "content": "Find scripts/aider_dg_proxy.py and explain tool_delegate.",
        }
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "dg_context",
                "description": "Build bounded repository context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "task": {"type": "string"},
                        "files": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["task"],
                },
            },
        }
    ],
    max_tokens=128,
)
dg_context_choice = dg_context_resp.choices[0]
assert dg_context_choice.finish_reason == "tool_calls", dg_context_resp
dg_context_calls = dg_context_choice.message.tool_calls or []
assert len(dg_context_calls) == 1, dg_context_resp
dg_context_call = dg_context_calls[0]
assert dg_context_call.function.name == "dg_context", dg_context_call
assert "scripts/aider_dg_proxy.py" in dg_context_call.function.arguments, dg_context_call.function.arguments

runtime_req = urllib.request.Request(
    "http://127.0.0.1:8090/v1/agent/tool",
    data=json.dumps({
        "tool_call": {
            "id": dg_context_call.id,
            "type": "function",
            "function": {
                "name": dg_context_call.function.name,
                "arguments": dg_context_call.function.arguments,
            },
        }
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(runtime_req, timeout=30) as resp:
    runtime_result = json.loads(resp.read().decode("utf-8"))
assert runtime_result["ok"] is True, runtime_result
assert runtime_result["tool"] == "dg_context", runtime_result
assert runtime_result["tool_response"]["role"] == "tool", runtime_result
assert runtime_result["tool_response"]["tool_call_id"] == dg_context_call.id, runtime_result
assert "scripts/aider_dg_proxy.py" in runtime_result["result"]["content"], runtime_result
PY
else
  cat >/tmp/dg-openai-sdk-gateway-response.txt <<'TXT'
OpenAI SDK client smoke skipped: no working Python OpenAI SDK is available.
The installed Windows SDK may import, but its jiter extension is blocked by local App Control policy.
TXT
fi

"$HTTP_PYTHON" - <<'PY'
import json
import tempfile
import urllib.request
from pathlib import Path

BACKEND_MODEL = "diffusiongemma-26b-a4b-it-iq3m-fullgpu"
PROXY_MODEL = "diffusiongemma-26b-a4b-it-iq4xs-aider-local"

checks = {
    "backend": "http://127.0.0.1:4100/healthz",
    "proxy": "http://127.0.0.1:8090/healthz",
    "backend_models": "http://127.0.0.1:4100/v1/models",
    "proxy_models": "http://127.0.0.1:8090/v1/models",
}
for name, url in checks.items():
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if name in ("backend", "proxy"):
        assert data.get("ok") is True, (name, data)
    elif name == "backend_models":
        ids = {item.get("id") for item in data.get("data", [])}
        assert BACKEND_MODEL in ids or "diffusiongemma-local" in ids, data
    else:
        assert any(item.get("id") == PROXY_MODEL for item in data.get("data", [])), data

for name, url in {
    "proxy_model_card": "http://127.0.0.1:8090/v1/model_card",
    "proxy_capabilities": "http://127.0.0.1:8090/v1/capabilities",
    "proxy_routes": "http://127.0.0.1:8090/v1/agent/routes",
    "proxy_tool_manifest": "http://127.0.0.1:8090/v1/agent/tool_manifest",
    "proxy_actions": "http://127.0.0.1:8090/v1/agent/actions",
    "proxy_sessions": "http://127.0.0.1:8090/v1/agent/sessions",
    "proxy_latest_session": "http://127.0.0.1:8090/v1/agent/sessions/latest",
    "proxy_latest_diff": "http://127.0.0.1:8090/v1/agent/sessions/latest/diff",
    "proxy_agent_runs": "http://127.0.0.1:8090/v1/agent/runs",
    "proxy_latest_agent_run": "http://127.0.0.1:8090/v1/agent/runs/latest",
    "proxy_well_known": "http://127.0.0.1:8090/.well-known/agent.json",
    "proxy_openapi": "http://127.0.0.1:8090/openapi.json",
}.items():
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if name == "proxy_model_card":
        assert data["mode"] == "safe_agent_gateway", data
        assert data["id"] == "diffusiongemma-26b-a4b-it-iq4xs-aider-local", data
        assert data["tool_manifest_url"].endswith("/v1/agent/tool_manifest"), data
    elif name == "proxy_capabilities":
        assert data["openai_compat"]["chat_completions"] is True, data
        assert data["openai_compat"]["responses"] is True, data
        assert data["openai_compat"]["tool_call_delegation"] is True, data
        assert data["discovery"]["session_api"].endswith("/v1/agent/session"), data
        assert data["discovery"]["tool_runtime"].endswith("/v1/agent/tool"), data
        assert data["discovery"]["context"].endswith("/v1/agent/context"), data
        assert data["discovery"]["rag_context"].endswith("/v1/agent/rag"), data
        assert data["discovery"]["sessions"].endswith("/v1/agent/sessions"), data
        assert data["discovery"]["latest_session_diff"].endswith("/v1/agent/sessions/latest/diff"), data
        assert data["discovery"]["agent_runs"].endswith("/v1/agent/runs"), data
        assert data["discovery"]["latest_agent_run"].endswith("/v1/agent/runs/latest"), data
        assert data["discovery"]["tool_manifest"].endswith("/v1/agent/tool_manifest"), data
    elif name == "proxy_routes":
        ids = {item.get("id") for item in data.get("routes", []) if isinstance(item, dict)}
        assert {"chat_completions", "responses", "session_api", "tool_runtime", "context_api", "rag_context_api", "session_artifacts", "agent_runs", "latest_session_diff", "tool_manifest", "actions", "well_known_agent", "openapi", "mcp", "litellm"} <= ids, data
    elif name == "proxy_tool_manifest":
        assert data["schema_version"] == "dg.agent.tool_manifest.v1", data
        assert data["http_session_api"]["endpoint"].endswith("/v1/agent/session"), data
        assert data["http_tool_runtime_api"]["endpoint"].endswith("/v1/agent/tool"), data
        assert "dg_context" in data["http_tool_runtime_api"]["supported_tools"], data
        assert {"dg_agent", "dg_repo_status", "dg_git_diff", "dg_list_files", "dg_read_file", "dg_search", "dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline"} <= set(data["http_tool_runtime_api"]["supported_tools"]), data
        assert data["http_agent_api"]["tool_name"] == "dg_agent", data
        assert "dg_search" in data["http_repo_tools"]["tools"], data
        assert "dg_code_outline" in data["http_oss_repo_tools"]["tool_names"], data
        assert data["http_session_artifacts"]["latest_diff_endpoint"].endswith("/v1/agent/sessions/latest/diff"), data
        assert "final_diff" in data["http_session_artifacts"]["available_artifacts"], data
        assert data["http_agent_run_artifacts"]["latest_endpoint"].endswith("/v1/agent/runs/latest"), data
        assert "transcript" in data["http_agent_run_artifacts"]["available_artifacts"], data
        assert data["http_context_api"]["endpoint"].endswith("/v1/agent/context"), data
        assert data["http_rag_context_api"]["endpoint"].endswith("/v1/agent/rag"), data
        assert data["openai_chat_completions"]["tools"][0]["function"]["name"] == "execute_command", data
        assert data["openai_responses"]["tools"][0]["name"] == "execute_command", data
        chat_names = {item["function"]["name"] for item in data["openai_chat_completions"]["tools"]}
        response_names = {item["name"] for item in data["openai_responses"]["tools"]}
        assert {"execute_command", "dg_agent", "dg_repo_status", "dg_git_diff", "dg_list_files", "dg_read_file", "dg_search", "dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline", "dg_session", "dg_context", "dg_rag_context", "dg_session_artifact", "dg_agent_run_artifact"} <= chat_names, data
        assert {"execute_command", "dg_agent", "dg_repo_status", "dg_git_diff", "dg_list_files", "dg_read_file", "dg_search", "dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline", "dg_session", "dg_context", "dg_rag_context", "dg_session_artifact", "dg_agent_run_artifact"} <= response_names, data
        recommended = data["recommended_execution"]["command_template"]
        assert "dg_agent.sh" in recommended and "session" in recommended, data
    elif name == "proxy_actions":
        action_ids = {item.get("id") for item in data.get("actions", []) if isinstance(item, dict)}
        assert {"run_dg_session", "run_high_level_agent_http", "execute_command_via_dg_session", "openai_dg_tool_schemas", "execute_openai_tool_http", "inspect_repo_http_tools", "inspect_repo_with_oss_http_tools", "read_mcp_handoff", "read_agent_run_artifact_http", "build_context_http", "retrieve_rag_context_http"} <= action_ids, data
    elif name == "proxy_well_known":
        assert data["schema_version"] == "dg.agent.v1", data
        assert data["tool_manifest_url"].endswith("/v1/agent/tool_manifest"), data
        assert data["tool_runtime_url"].endswith("/v1/agent/tool"), data
        assert data["context_url"].endswith("/v1/agent/context"), data
        assert data["rag_context_url"].endswith("/v1/agent/rag"), data
        assert data["sessions_url"].endswith("/v1/agent/sessions"), data
        assert data["agent_runs_url"].endswith("/v1/agent/runs"), data
    elif name == "proxy_sessions":
        assert "sessions" in data, data
        if data["sessions"]:
            assert data["sessions"][0]["session_dir"], data
    elif name == "proxy_latest_session":
        if data.get("ok") is False:
            assert data["error"] == "no sessions found", data
        else:
            assert data["ok"] is True, data
            assert data["summary"]["session_dir"], data
            assert data["session"]["session_dir"], data
    elif name == "proxy_latest_diff":
        if data.get("ok") is False:
            assert data["error"] in {"no sessions found", "artifact not found: final_diff"}, data
        else:
            assert data["ok"] is True, data
            assert data["artifact"] == "final_diff", data
            assert "content" in data, data
    elif name == "proxy_agent_runs":
        assert data["ok"] is True, data
        assert "runs" in data, data
    elif name == "proxy_latest_agent_run":
        if data.get("ok") is False:
            assert data["error"] == "no agent runs found", data
        else:
            assert data["ok"] is True, data
            assert data["summary"]["run_dir"], data
    else:
        assert "/v1/agent/tool_manifest" in data["paths"], data
        assert "/v1/agent/session" in data["paths"], data
        assert "/v1/agent/tool" in data["paths"], data
        assert "/v1/agent/context" in data["paths"], data
        assert "/v1/agent/rag" in data["paths"], data
        assert "/v1/agent/sessions" in data["paths"], data
        assert "/v1/agent/sessions/latest/diff" in data["paths"], data
        assert "/v1/agent/runs" in data["paths"], data
        assert "/v1/agent/runs/latest" in data["paths"], data

payload = {
    "repo": ".",
    "task": "Inspect calc.py and report what would change.",
    "files": ["calc.py"],
}
req = urllib.request.Request(
    "http://127.0.0.1:8090/v1/agent/session",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=5) as resp:
    session_preview = json.loads(resp.read().decode("utf-8"))
assert session_preview["status"] == "dry_run", session_preview
assert session_preview["dry_run"] is True, session_preview
assert session_preview["execute"] is False, session_preview
assert "--dry-run" in session_preview["command"], session_preview
assert "--rollback-on-failure" in session_preview["command"], session_preview

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    for tool_payload, expected in [
        ({"name": "dg_list_files", "arguments": {"repo": str(repo), "pattern": "calc", "limit": 20}}, "calc.py"),
        ({"name": "dg_read_file", "arguments": {"repo": str(repo), "path": "calc.py", "max_lines": 20}}, "def add"),
        ({"name": "dg_search", "arguments": {"repo": str(repo), "query": "def add", "max_matches": 10}}, "calc.py"),
        ({"name": "dg_code_outline", "arguments": {"repo": str(repo), "lang": "python", "paths": ["calc.py"], "max_items": 20, "max_chars": 4000, "timeout": 120}}, "add"),
        ({"name": "dg_agent", "arguments": {"repo": str(repo), "task": "Read file calc.py.", "mode": "read", "tools": ["dg_read_file"], "max_steps": 2, "timeout": 120, "max_chars": 20000}}, "def add"),
    ]:
        req = urllib.request.Request(
            "http://127.0.0.1:8090/v1/agent/tool",
            data=json.dumps(tool_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            runtime_repo_tool = json.loads(resp.read().decode("utf-8"))
        assert runtime_repo_tool["ok"] is True, runtime_repo_tool
        assert runtime_repo_tool["tool"] == tool_payload["name"], runtime_repo_tool
        assert expected in runtime_repo_tool["result"]["content"], runtime_repo_tool

    with urllib.request.urlopen("http://127.0.0.1:8090/v1/agent/runs/latest", timeout=5) as resp:
        latest_run = json.loads(resp.read().decode("utf-8"))
    if latest_run.get("ok") is True:
        assert latest_run["summary"]["run_dir"], latest_run
        req = urllib.request.Request(
            "http://127.0.0.1:8090/v1/agent/tool",
            data=json.dumps({"name": "dg_agent_run_artifact", "arguments": {"run": "latest", "artifact": "transcript", "limit": 200000}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            latest_run_artifact = json.loads(resp.read().decode("utf-8"))
        assert latest_run_artifact["ok"] is True, latest_run_artifact
        assert latest_run_artifact["tool"] == "dg_agent_run_artifact", latest_run_artifact
        assert latest_run_artifact["result"]["artifact"] == "transcript", latest_run_artifact
        assert isinstance(latest_run_artifact["result"]["content"], str), latest_run_artifact
    else:
        assert latest_run["error"] == "no agent runs found", latest_run

    context_payload = {
        "repo": str(repo),
        "task": "Find calc.py and explain add(a, b).",
        "files": ["calc.py"],
        "max_files": 2,
        "max_snippet_chars": 500,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8090/v1/agent/context",
        data=json.dumps(context_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        context_result = json.loads(resp.read().decode("utf-8"))
    assert context_result["ok"] is True, context_result
    assert context_result["context"]["selected_files"][0] == "calc.py", context_result
    assert "def add" in context_result["content"], context_result

    req = urllib.request.Request(
        "http://127.0.0.1:8090/v1/agent/tool",
        data=json.dumps({"name": "dg_context", "arguments": context_payload}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        runtime_context = json.loads(resp.read().decode("utf-8"))
    assert runtime_context["ok"] is True, runtime_context
    assert runtime_context["tool"] == "dg_context", runtime_context
    assert runtime_context["tool_response"]["role"] == "tool", runtime_context
    assert "def add" in runtime_context["result"]["content"], runtime_context

    rag_payload = {
        "repo": str(repo),
        "task": "Find calc.py and explain add(a, b).",
        "max_context_chars": 1000,
        "max_files": 2,
        "timeout": 20,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8090/v1/agent/rag",
        data=json.dumps(rag_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        rag_result = json.loads(resp.read().decode("utf-8"))
    assert rag_result["ok"] is True, rag_result
    assert "calc.py" in rag_result["content"], rag_result
    assert "def add" in rag_result["content"], rag_result
PY

echo "OpenAI SDK gateway smoke passed."
