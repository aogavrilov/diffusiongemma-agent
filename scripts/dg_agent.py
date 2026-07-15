#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import shutil
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION_ROOT = DG_ROOT / "runlogs" / "dg-agent-sessions"
DEFAULT_AGENT_ROOT = DG_ROOT / "runlogs" / "dg-agent-runs"
DEFAULT_MINI_SWE_ROOT = DG_ROOT / "runlogs" / "mini-swe-agent"
CLIENT_PACK_MANIFEST = DG_ROOT / "configs" / "client_profiles" / "agent-client-pack.json"
CLIENT_PROFILE_DIR = DG_ROOT / "configs" / "client_profiles"
AIDER_PROFILE = DG_ROOT / "configs" / "aider.dg-fast.conf.yml"
AIDER_WORKSPACE_PROFILE = CLIENT_PROFILE_DIR / "aider.dg-workspace.conf.yml"
AIDER_MODEL_SETTINGS = DG_ROOT / "configs" / "aider.dg-model-settings.yml"
AIDER_MODEL_METADATA = DG_ROOT / "configs" / "aider.dg-model-metadata.json"
OPENHANDS_PROFILE = CLIENT_PROFILE_DIR / "openhands.dg.toml"
OPENHANDS_ENV = CLIENT_PROFILE_DIR / "openhands.env"
QWEN_CODE_MCP_PROFILE = CLIENT_PROFILE_DIR / "qwen-code.mcp.json"
AUTOGEN_PROFILE = CLIENT_PROFILE_DIR / "autogen.dg.json"
SMOLAGENTS_PROFILE = CLIENT_PROFILE_DIR / "smolagents.dg.json"
LANGGRAPH_PROFILE = CLIENT_PROFILE_DIR / "langgraph.dg.json"
CREWAI_PROFILE = CLIENT_PROFILE_DIR / "crewai.dg.json"
OPEN_INTERPRETER_PROFILE = CLIENT_PROFILE_DIR / "open-interpreter.dg.json"
LLAMAINDEX_PROFILE = CLIENT_PROFILE_DIR / "llamaindex.dg.json"
HAYSTACK_PROFILE = CLIENT_PROFILE_DIR / "haystack.dg.json"
SWE_AGENT_PROFILE = CLIENT_PROFILE_DIR / "swe-agent.dg.yaml"
MINI_SWE_AGENT_PROFILE = CLIENT_PROFILE_DIR / "mini-swe-agent.dg.yaml"
MCP_SERVER_PROFILE = CLIENT_PROFILE_DIR / "mcp-server.json"
MCP_CLIENT_SNIPPETS_PROFILE = CLIENT_PROFILE_DIR / "mcp-client-snippets.json"
CLAUDE_CODE_MCP_PROFILE = CLIENT_PROFILE_DIR / "claude-code.mcp.json"
CLAUDE_DESKTOP_MCP_PROFILE = CLIENT_PROFILE_DIR / "claude-desktop-mcp.json"
CURSOR_MCP_PROFILE = CLIENT_PROFILE_DIR / "cursor.mcp.json"
VSCODE_MCP_PROFILE = CLIENT_PROFILE_DIR / "vscode.mcp.json"
GOOSE_MCP_PROFILE = CLIENT_PROFILE_DIR / "goose-mcp.dg.yaml"
LITELLM_LOCAL_MODEL_REGISTRY = CLIENT_PROFILE_DIR / "litellm-local-model-registry.json"
OPENCODE_MCP_PROFILE = DG_ROOT / "configs" / "opencode.dg-mcp.json"
OPENCODE_COMPACT_PROFILE = DG_ROOT / "configs" / "opencode.dg-agent.json"
AGENT_INSTRUCTIONS_PROFILE = CLIENT_PROFILE_DIR / "agent-instructions.md"
AGENTS_RULES_PROFILE = CLIENT_PROFILE_DIR / "AGENTS.dg.md"
CLAUDE_RULES_PROFILE = CLIENT_PROFILE_DIR / "CLAUDE.dg.md"
COPILOT_RULES_PROFILE = CLIENT_PROFILE_DIR / "copilot-instructions.dg.md"
VSCODE_INSTRUCTIONS_PROFILE = CLIENT_PROFILE_DIR / "diffusiongemma.instructions.md"
CURSOR_RULES_PROFILE = CLIENT_PROFILE_DIR / "cursor-rules.dg.mdc"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SESSION_ARTIFACT_FILENAMES = {
    "context_md": "context.md",
    "context_json": "context.json",
    "plan": "plan.json",
    "task_report": "task-report.json",
    "verify_report": "verify.json",
    "before_status": "before.status.txt",
    "after_status": "after.status.txt",
    "before_diff": "before.diff",
    "final_diff": "final.diff",
    "task_stdout": "task.stdout.log",
    "task_stderr": "task.stderr.log",
    "session_json": "session.json",
}

SESSION_ARTIFACT_ALIASES = {
    "context": "context_md",
    "context.json": "context_json",
    "context.md": "context_md",
    "diff": "final_diff",
    "final": "final_diff",
    "final.diff": "final_diff",
    "plan_json": "plan",
    "plan.json": "plan",
    "task": "task_report",
    "task.json": "task_report",
    "task-report.json": "task_report",
    "verify": "verify_report",
    "verify.json": "verify_report",
    "before": "before_status",
    "after": "after_status",
    "before.diff": "before_diff",
    "stdout": "task_stdout",
    "stderr": "task_stderr",
    "session": "session_json",
    "session.json": "session_json",
}

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

AGENT_EDIT_KEYWORDS = {
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
}
AGENT_READ_KEYWORDS = {
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
}
AGENT_EDIT_MARKERS = {
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
AGENT_READ_MARKERS = {
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

MINI_SWE_ARTIFACT_ALIASES = {
    "report": "report",
    "report.json": "report",
    "stdout": "stdout",
    "stdout.log": "stdout",
    "stderr": "stderr",
    "stderr.log": "stderr",
    "command": "command",
    "command.sh": "command",
    "trajectory": "trajectory",
    "trajectory.json": "trajectory",
}

WRAPPER_COMPONENTS = {
    "aider": {
        "name": "Aider",
        "install_script": "install_aider_local.sh",
        "smoke_suite": "",
        "checks": [".venv-aider/bin/aider"],
    },
    "agentapi": {
        "name": "AgentAPI",
        "install_script": "install_agentapi_local.sh",
        "smoke_suite": "agentapi",
        "checks": [".tools/agentapi/agentapi"],
    },
    "opencode": {
        "name": "OpenCode",
        "install_script": "install_opencode_local.sh",
        "smoke_suite": "opencode-provider",
        "checks": [".tools/opencode/node_modules/.bin/opencode"],
    },
    "goose": {
        "name": "Goose",
        "install_script": "install_goose_local.sh",
        "smoke_suite": "goose",
        "checks": [".tools/goose/bin/goose"],
    },
    "litellm": {
        "name": "LiteLLM",
        "install_script": "install_litellm_local.sh",
        "smoke_suite": "gateway-clients",
        "checks": [".venv-litellm/bin/litellm"],
    },
    "mcp": {
        "name": "Model Context Protocol Python SDK",
        "install_script": "install_mcp_sdk_local.sh",
        "smoke_suite": "mcp",
        "checks": [".venv/lib/python3.12/site-packages/mcp", "scripts/dg_mcp_sdk_server.py"],
    },
    "serena": {
        "name": "Serena",
        "install_script": "install_serena_local.sh",
        "smoke_suite": "serena-mcp",
        "checks": ["scripts/run_serena_mcp.sh", "scripts/serena_cli.py"],
    },
}

EXTERNAL_AGENT_COMPONENTS = {
    "autogen": {
        "name": "AutoGen AgentChat",
        "install_script": "install_autogen_local.sh",
        "smoke_suite": "autogen",
        "checks": [".venv-autogen/bin/python", "scripts/dg_autogen_runner.py"],
    },
    "smolagents": {
        "name": "Hugging Face smolagents",
        "install_script": "install_smolagents_local.sh",
        "smoke_suite": "smolagents",
        "checks": [".venv-smolagents/bin/python", "scripts/dg_smolagents_runner.py"],
    },
    "langgraph": {
        "name": "LangGraph",
        "install_script": "install_langgraph_local.sh",
        "smoke_suite": "langgraph",
        "checks": [[".venv-langgraph/bin/python", ".venv-langgraph-wsl/bin/python", ".venv-langgraph/Scripts/python.exe"], "scripts/dg_langgraph_runner.py"],
    },
    "crewai": {
        "name": "CrewAI",
        "install_script": "install_crewai_local.sh",
        "smoke_suite": "crewai",
        "checks": [".venv-crewai/bin/python", "scripts/dg_crewai_runner.py"],
    },
    "open-interpreter": {
        "name": "Open Interpreter",
        "install_script": "install_open_interpreter_local.sh",
        "smoke_suite": "open-interpreter",
        "checks": [".venv-open-interpreter/bin/python", "scripts/dg_open_interpreter_runner.py"],
    },
    "llamaindex": {
        "name": "LlamaIndex",
        "install_script": "install_llamaindex_local.sh",
        "smoke_suite": "llamaindex",
        "checks": [".venv-llamaindex/bin/python", "scripts/dg_llamaindex_runner.py"],
    },
    "haystack": {
        "name": "Haystack",
        "install_script": "install_haystack_local.sh",
        "smoke_suite": "haystack",
        "checks": [".venv-haystack/bin/python", "scripts/dg_haystack_runner.py"],
    },
    "openhands": {
        "name": "OpenHands",
        "install_script": "install_openhands_local.sh",
        "smoke_suite": "external-agents",
        "checks": [".tools/external-agents/bin/openhands"],
    },
    "mini-swe-agent": {
        "name": "mini-swe-agent",
        "install_script": "install_mini_swe_agent_local.sh",
        "smoke_suite": "external-agents",
        "checks": [".tools/external-agents/bin/mini"],
    },
    "qwen-code": {
        "name": "Qwen Code",
        "install_script": "install_qwen_code_local.sh",
        "smoke_suite": "qwen-code",
        "checks": [".tools/qwen-code/node_modules/.bin/qwen"],
    },
    "swe-agent": {
        "name": "SWE-agent",
        "install_script": "install_swe_agent_local.sh",
        "smoke_suite": "external-agents",
        "checks": [".venv-swe-agent/bin/sweagent"],
    },
}


def run_cmd(args: list[str], cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    if os.name == "nt" and args and str(args[0]).endswith(".sh"):
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        bash = str(git_bash) if git_bash.exists() else ""
        if not bash:
            candidate = shutil.which("bash") or ""
            if candidate and "WindowsApps" not in candidate:
                bash = candidate
        if bash:
            args = [bash, Path(args[0]).resolve().as_posix(), *args[1:]]
    proc = subprocess.Popen(
        args,
        cwd=str(cwd or DG_ROOT),
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # A smoke may launch an MCP stdio server. Give the command its own
        # process group so a timeout cannot orphan that server on WSL/Linux.
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()
            stdout, stderr = proc.communicate()
        stderr = (stderr or "").rstrip() + f"\ncommand timed out after {timeout}s\n"
        return subprocess.CompletedProcess(args, 124, stdout or "", stderr)
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def exec_cmd(args: list[str], cwd: Path | None = None) -> int:
    if os.name == "nt" and args and str(args[0]).endswith(".sh"):
        bash = ""
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if git_bash.exists():
            bash = str(git_bash)
        else:
            candidate = shutil.which("bash") or ""
            if candidate and "WindowsApps" not in candidate:
                bash = candidate
        if bash:
            script = Path(args[0]).resolve().as_posix()
            proc = subprocess.run([bash, script, *args[1:]], cwd=str(cwd or DG_ROOT), check=False)
            return proc.returncode
    proc = subprocess.run(args, cwd=str(cwd or DG_ROOT), check=False)
    return proc.returncode


def http_json(url: str, timeout: int = 3) -> tuple[bool, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(text) if text.strip() else {}
    except Exception as exc:
        return False, str(exc)


def path_exists(path: Path) -> bool:
    """Treat AppLocker-denied optional runtimes as unavailable, not fatal."""
    try:
        return path.exists()
    except OSError as exc:
        # Windows cannot follow some WSL-created venv launcher reparse points
        # (WinError 1920), but the path itself is still a valid runtime target
        # once the wrapper enters WSL.
        if getattr(exc, "winerror", None) == 1920:
            try:
                path.stat(follow_symlinks=False)
                return True
            except OSError:
                return False
        return False


def powershell_executable() -> str:
    """Locate Windows PowerShell from both native Windows and WSL."""
    resolved = shutil.which("powershell.exe")
    if resolved:
        return resolved
    if os.name != "nt":
        for candidate in (
            Path("/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe"),
            Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"),
        ):
            if path_exists(candidate):
                return str(candidate)
    return ""


def version_cmd(args: list[str], timeout: int = 20) -> dict[str, Any]:
    path = Path(args[0])
    if "/" in args[0] or args[0].startswith("."):
        exists = path_exists(DG_ROOT / path) if not path.is_absolute() else path_exists(path)
        if not exists:
            return {"ok": False, "detail": "missing"}
    try:
        proc = run_cmd(args, timeout=timeout)
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return {"ok": proc.returncode == 0, "detail": out.splitlines()[-1] if out else f"rc={proc.returncode}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def serena_runtime_status() -> dict[str, Any]:
    runner = DG_ROOT / "scripts" / "run_serena_mcp.sh"
    if not path_exists(runner):
        return {"ok": False, "detail": "missing runner"}
    if os.name == "nt":
        wsl = shutil.which("wsl.exe") or shutil.which("wsl")
        if not wsl:
            return {"ok": False, "detail": "WSL is unavailable"}
        proc = subprocess.run(
            [wsl, "--exec", "bash", windows_path_to_wsl(runner), "--check-installed"],
            text=True,
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    else:
        proc = run_cmd([str(runner), "--check-installed"], timeout=120)
    out = (proc.stdout + "\n" + proc.stderr).strip()
    detail = out.splitlines()[0] if out else f"rc={proc.returncode}"
    command = next((line for line in out.splitlines() if line.startswith("Serena command:")), "")
    if command:
        detail = f"{detail}; {command}"
    return {"ok": proc.returncode == 0, "detail": detail}


def mcp_sdk_runtime_status() -> dict[str, Any]:
    """Check the interpreter that actually serves MCP, including WSL on Windows."""
    code = "import importlib.metadata; print(importlib.metadata.version('mcp'))"
    if os.name == "nt":
        wsl = shutil.which("wsl.exe") or shutil.which("wsl")
        python = os.environ.get("DG_AGENT_PYTHON", "/root/diffusiongemma-agent/.venv-wsl/bin/python")
        if not wsl:
            return {"ok": False, "detail": "WSL is unavailable"}
        command = f"{shlex.quote(python)} -c {shlex.quote(code)}"
        try:
            proc = subprocess.run(
                [wsl, "--exec", "bash", "-lc", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}
    else:
        candidates = [
            os.environ.get("DG_AGENT_PYTHON", ""),
            "/root/diffusiongemma-agent/.venv-wsl/bin/python",
            str(DG_ROOT / ".venv-wsl" / "bin" / "python"),
            str(DG_ROOT / ".venv" / "bin" / "python"),
        ]
        python = next((candidate for candidate in candidates if candidate and Path(candidate).exists()), "")
        if not python:
            return {"ok": False, "detail": "missing active MCP Python runtime"}
        try:
            proc = subprocess.run(
                [python, "-c", code],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    detail = (proc.stdout or proc.stderr).strip()
    return {"ok": proc.returncode == 0, "detail": detail or f"rc={proc.returncode}"}


def langgraph_runtime_status() -> dict[str, Any]:
    """Check the LangGraph runtime that actually works on this host."""
    runner = DG_ROOT / "scripts" / "run_langgraph_local.sh"
    if not path_exists(runner):
        return {"ok": False, "detail": "missing runner", "path": ""}
    code = (
        "import importlib.metadata; "
        "from langchain_openai import ChatOpenAI; "
        "from langgraph.prebuilt import create_react_agent; "
        "print(importlib.metadata.version('langgraph'))"
    )
    if os.name == "nt":
        wsl = shutil.which("wsl.exe") or shutil.which("wsl")
        if not wsl:
            return {"ok": False, "detail": "WSL is unavailable", "path": ""}
        wsl_root = windows_path_to_wsl(DG_ROOT)
        python = "./.venv-langgraph-wsl/bin/python"
        command = f"cd {shlex.quote(wsl_root)} && {python} -c {shlex.quote(code)}"
        try:
            proc = subprocess.run(
                [wsl, "--exec", "bash", "-lc", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
        except Exception as exc:
            return {"ok": False, "detail": str(exc), "path": python}
        detail = (proc.stdout or proc.stderr).strip()
        return {
            "ok": proc.returncode == 0,
            "detail": f"WSL LangGraph {detail}" if proc.returncode == 0 and detail else detail or f"rc={proc.returncode}",
            "path": str(DG_ROOT / ".venv-langgraph-wsl" / "bin" / "python"),
        }

    candidates = [
        os.environ.get("DG_LANGGRAPH_PYTHON", ""),
        str(DG_ROOT / ".venv-langgraph-wsl" / "bin" / "python"),
        str(DG_ROOT / ".venv-langgraph" / "bin" / "python"),
        str(DG_ROOT / ".venv-langgraph" / "Scripts" / "python.exe"),
    ]
    python = next((candidate for candidate in candidates if candidate and Path(candidate).exists()), "")
    if not python:
        return {"ok": False, "detail": "missing active LangGraph Python runtime", "path": ""}
    try:
        proc = subprocess.run(
            [python, "-c", code],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "detail": str(exc), "path": python}
    detail = (proc.stdout or proc.stderr).strip()
    return {"ok": proc.returncode == 0, "detail": detail or f"rc={proc.returncode}", "path": python}


def aider_runtime_status() -> dict[str, Any]:
    """Check the dedicated Python 3.12 runtime used by run_aider_local.sh."""
    runner = DG_ROOT / "scripts" / "run_aider_local.sh"
    if not runner.exists():
        return {"ok": False, "detail": "missing runner"}
    if os.name == "nt":
        wsl = shutil.which("wsl.exe") or shutil.which("wsl")
        python = os.environ.get("DG_AIDER_PYTHON", "/root/diffusiongemma-agent/.venv-aider/bin/python")
        if not wsl:
            return {"ok": False, "detail": "WSL is unavailable"}
        command = [wsl, "--exec", python, "-m", "aider", "--version"]
    else:
        default_python = Path("/root/diffusiongemma-agent/.venv-aider/bin/python")
        if not default_python.exists():
            default_python = DG_ROOT / ".venv-aider" / "bin" / "python"
        python = os.environ.get("DG_AIDER_PYTHON", str(default_python))
        if not Path(python).exists():
            return {"ok": False, "detail": f"missing python: {python}"}
        command = [python, "-m", "aider", "--version"]
    try:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}
    detail = (proc.stdout or proc.stderr).strip()
    return {"ok": proc.returncode == 0, "detail": detail or f"rc={proc.returncode}"}


def opencode_runtime_path() -> Path | None:
    candidates = [
        DG_ROOT / ".tools" / "opencode" / "node_modules" / ".bin" / "opencode.cmd",
        DG_ROOT / ".tools" / "opencode" / "node_modules" / ".bin" / "opencode.exe",
        DG_ROOT / ".tools" / "opencode" / "node_modules" / ".bin" / "opencode",
    ]
    return next((path for path in candidates if path_exists(path)), None)


def opencode_runtime_status() -> dict[str, Any]:
    binary = opencode_runtime_path()
    if binary is None:
        return {"ok": False, "detail": "missing", "path": ""}
    windows_launcher = DG_ROOT / "scripts" / "run_opencode_windows.ps1"
    powershell = powershell_executable()
    if windows_launcher.exists() and powershell:
        version = version_cmd(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                wsl_path_to_windows(windows_launcher),
                "--version",
            ],
            timeout=30,
        )
        return {"ok": bool(version["ok"]), "detail": version["detail"], "path": str(binary)}
    version = version_cmd([str(binary), "--version"], timeout=30)
    return {"ok": bool(version["ok"]), "detail": version["detail"], "path": str(binary)}


def qwen_code_runtime_path() -> Path | None:
    candidates = [
        DG_ROOT / ".tools" / "qwen-code" / "node_modules" / ".bin" / "qwen.cmd",
        DG_ROOT / ".tools" / "qwen-code" / "node_modules" / ".bin" / "qwen",
    ]
    return next((path for path in candidates if path_exists(path)), None)


def qwen_code_runtime_status() -> dict[str, Any]:
    binary = qwen_code_runtime_path()
    if binary is None:
        return {"ok": False, "detail": "missing", "path": ""}
    launcher = DG_ROOT / "scripts" / "run_qwen_code_windows.ps1"
    powershell = powershell_executable()
    if launcher.exists() and powershell:
        version = version_cmd(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                wsl_path_to_windows(launcher),
                "--version",
            ],
            timeout=30,
        )
        return {"ok": bool(version["ok"]), "detail": version["detail"], "path": str(binary)}
    version = version_cmd([str(binary), "--version"], timeout=30)
    return {"ok": bool(version["ok"]), "detail": version["detail"], "path": str(binary)}


def venv_python_path(name: str) -> Path:
    venv = DG_ROOT / f".venv-{name}"
    candidates = [venv / "bin" / "python", venv / "Scripts" / "python.exe"]
    return next((path for path in candidates if path_exists(path)), candidates[0])


def component_report() -> dict[str, Any]:
    backend_ok, backend = http_json("http://127.0.0.1:4100/healthz")
    proxy_ok, proxy = http_json("http://127.0.0.1:8090/healthz")
    agentapi_status_ok, agentapi_status = http_json("http://127.0.0.1:3284/status")
    litellm_running_ok, litellm_models = http_json("http://127.0.0.1:4100/v1/models")

    opencode_bin = opencode_runtime_path()
    qwen_code_bin = qwen_code_runtime_path()
    node_bin = DG_ROOT / ".tools" / "node" / "bin" / "node"
    system_node = shutil.which("node.exe" if os.name == "nt" else "node") or ""
    agentapi_bin = DG_ROOT / ".tools" / "agentapi" / "agentapi"
    goose_bin = DG_ROOT / ".tools" / "goose" / "bin" / "goose"
    litellm_bin = DG_ROOT / ".venv-litellm" / "bin" / "litellm"
    mcp_sdk_server = DG_ROOT / "scripts" / "dg_mcp_sdk_server.py"
    mcp_legacy_server = DG_ROOT / "scripts" / "dg_mcp_server.py"
    mcp_runner = DG_ROOT / "scripts" / "run_mcp_server.sh"
    repomix_mcp_runner = DG_ROOT / "scripts" / "run_repomix_mcp.sh"
    serena_runner = DG_ROOT / "scripts" / "run_serena_mcp.sh"
    mcp_version = mcp_sdk_runtime_status()
    aider_version = aider_runtime_status()
    serena_version = serena_runtime_status()
    langgraph_runtime = langgraph_runtime_status()
    local_openhands_bin = DG_ROOT / ".tools" / "external-agents" / "bin" / "openhands"
    local_mini_swe_agent_bin = DG_ROOT / ".tools" / "external-agents" / "bin" / "mini"
    local_swe_agent_bin = DG_ROOT / ".venv-swe-agent" / "bin" / "sweagent"
    local_qwen_code_bin = qwen_code_bin
    autogen_python = venv_python_path("autogen")
    smolagents_python = venv_python_path("smolagents")
    langgraph_python = venv_python_path("langgraph")
    crewai_python = venv_python_path("crewai")
    open_interpreter_python = venv_python_path("open-interpreter")
    llamaindex_python = venv_python_path("llamaindex")
    haystack_python = venv_python_path("haystack")
    openhands_bin = str(local_openhands_bin) if path_exists(local_openhands_bin) else (shutil.which("openhands") or "")
    swe_agent_bin = str(local_swe_agent_bin) if path_exists(local_swe_agent_bin) else (shutil.which("sweagent") or shutil.which("swe-agent") or "")
    mini_swe_agent_bin = str(local_mini_swe_agent_bin) if path_exists(local_mini_swe_agent_bin) else (shutil.which("mini") or shutil.which("mini-swe-agent") or "")
    qwen_code_bin_str = str(local_qwen_code_bin) if local_qwen_code_bin else (shutil.which("qwen") or "")
    qwen_code_version = qwen_code_runtime_status()
    autogen_available = path_exists(autogen_python)
    smolagents_available = path_exists(smolagents_python)
    langgraph_available = bool(langgraph_runtime["ok"])
    crewai_available = path_exists(crewai_python)
    open_interpreter_available = path_exists(open_interpreter_python)
    llamaindex_available = path_exists(llamaindex_python)
    haystack_available = path_exists(haystack_python)
    autogen_version = (
        version_cmd([str(autogen_python), "-c", "import importlib.metadata; print(importlib.metadata.version('autogen-agentchat'))"], timeout=30)
        if autogen_available
        else {"ok": False, "detail": "missing"}
    )
    smolagents_version = (
        version_cmd([str(smolagents_python), "-c", "import importlib.metadata; print(importlib.metadata.version('smolagents'))"], timeout=30)
        if smolagents_available
        else {"ok": False, "detail": "missing"}
    )
    langgraph_version = langgraph_runtime if langgraph_available else {"ok": False, "detail": langgraph_runtime["detail"]}
    crewai_version = (
        version_cmd([str(crewai_python), "-c", "import importlib.metadata; print(importlib.metadata.version('crewai'))"], timeout=30)
        if crewai_available
        else {"ok": False, "detail": "missing"}
    )
    open_interpreter_version = (
        version_cmd([str(open_interpreter_python), "-c", "import importlib.metadata; print(importlib.metadata.version('open-interpreter'))"], timeout=30)
        if open_interpreter_available
        else {"ok": False, "detail": "missing"}
    )
    llamaindex_version = (
        version_cmd([str(llamaindex_python), "-c", "import importlib.metadata; print(importlib.metadata.version('llama-index-core'))"], timeout=30)
        if llamaindex_available
        else {"ok": False, "detail": "missing"}
    )
    haystack_version = (
        version_cmd([str(haystack_python), "-c", "import importlib.metadata; print(importlib.metadata.version('haystack-ai'))"], timeout=30)
        if haystack_available
        else {"ok": False, "detail": "missing"}
    )

    return {
        "root": str(DG_ROOT),
        "backend": {"ok": backend_ok, "url": "http://127.0.0.1:4100", "detail": backend},
        "proxy": {"ok": proxy_ok, "url": "http://127.0.0.1:8090", "detail": proxy},
        "agentapi": {
            "installed": path_exists(agentapi_bin),
            "version": version_cmd([str(agentapi_bin), "--version"]) if path_exists(agentapi_bin) else {"ok": False, "detail": "missing"},
            "running": agentapi_status_ok,
            "url": "http://127.0.0.1:3284",
            "chat": "http://127.0.0.1:3284/chat",
            "status": agentapi_status,
        },
        "aider": {
            "installed": bool(aider_version["ok"] and path_exists(DG_ROOT / "scripts" / "run_aider_local.sh")),
            "version": aider_version,
            "runner": str(DG_ROOT / "scripts" / "run_aider_local.sh"),
        },
        "opencode": {
            "installed": bool(opencode_bin and path_exists(opencode_bin)),
            "version": version_cmd([str(opencode_bin), "--version"], timeout=30) if opencode_bin else {"ok": False, "detail": "missing"},
            "node": version_cmd([str(node_bin), "--version"]) if path_exists(node_bin) else (version_cmd([system_node, "--version"]) if system_node else {"ok": False, "detail": "missing"}),
        },
        "qwen_code": {
            "installed": bool(qwen_code_bin_str),
            "version": qwen_code_version,
            "binary": qwen_code_bin_str,
            "profile": str(QWEN_CODE_MCP_PROFILE),
        },
        "autogen": {
            "installed": bool(autogen_available and path_exists(DG_ROOT / "scripts" / "dg_autogen_runner.py")),
            "version": autogen_version,
            "python": str(autogen_python),
            "profile": str(AUTOGEN_PROFILE),
        },
        "smolagents": {
            "installed": bool(smolagents_available and path_exists(DG_ROOT / "scripts" / "dg_smolagents_runner.py")),
            "version": smolagents_version,
            "python": str(smolagents_python),
            "profile": str(SMOLAGENTS_PROFILE),
        },
        "langgraph": {
            "installed": bool(langgraph_available and path_exists(DG_ROOT / "scripts" / "dg_langgraph_runner.py")),
            "version": langgraph_version,
            "python": str(langgraph_runtime.get("path") or langgraph_python),
            "profile": str(LANGGRAPH_PROFILE),
        },
        "crewai": {
            "installed": bool(crewai_available and path_exists(DG_ROOT / "scripts" / "dg_crewai_runner.py")),
            "version": crewai_version,
            "python": str(crewai_python),
            "profile": str(CREWAI_PROFILE),
        },
        "open_interpreter": {
            "installed": bool(open_interpreter_available and path_exists(DG_ROOT / "scripts" / "dg_open_interpreter_runner.py")),
            "version": open_interpreter_version,
            "python": str(open_interpreter_python),
            "profile": str(OPEN_INTERPRETER_PROFILE),
        },
        "llamaindex": {
            "installed": bool(llamaindex_available and path_exists(DG_ROOT / "scripts" / "dg_llamaindex_runner.py")),
            "version": llamaindex_version,
            "python": str(llamaindex_python),
            "profile": str(LLAMAINDEX_PROFILE),
        },
        "haystack": {
            "installed": bool(haystack_available and path_exists(DG_ROOT / "scripts" / "dg_haystack_runner.py")),
            "version": haystack_version,
            "python": str(haystack_python),
            "profile": str(HAYSTACK_PROFILE),
        },
        "goose": {
            "installed": path_exists(goose_bin),
            "version": version_cmd([str(goose_bin), "--version"], timeout=30) if path_exists(goose_bin) else {"ok": False, "detail": "missing"},
            "provider": "openai",
            "model": "diffusiongemma-26b-a4b-it-iq4xs-aider-local",
            "host": "http://127.0.0.1:8090",
        },
        "litellm": {
            "installed": path_exists(litellm_bin),
            "version": version_cmd([str(litellm_bin), "--version"], timeout=30) if path_exists(litellm_bin) else {"ok": False, "detail": "missing"},
            "config": str(DG_ROOT / "configs" / "litellm.dg.yaml"),
            "running": litellm_running_ok,
            "url": "http://127.0.0.1:4100",
            "models": litellm_models,
            "model": "diffusiongemma-local",
        },
        "mcp": {
            "installed": bool(mcp_version["ok"] and path_exists(mcp_sdk_server) and path_exists(mcp_runner)),
            "version": mcp_version,
            "server": str(mcp_sdk_server),
            "legacy_server": str(mcp_legacy_server),
            "runner": str(mcp_runner),
            "profile": str(MCP_SERVER_PROFILE),
            "smoke": "scripts/dg_agent.sh smoke --suite mcp",
        },
        "serena": {
            "installed": bool(serena_version["ok"] and path_exists(serena_runner)),
            "version": serena_version,
            "binary": "resolved by scripts/run_serena_mcp.sh",
            "runner": str(serena_runner),
            "command": "scripts/run_serena_mcp.sh",
            "smoke": "scripts/dg_agent.sh smoke --suite serena-mcp",
        },
        "client_profiles": {
            "openai_compatible": str(DG_ROOT / "configs" / "client_profiles" / "openai-compatible.local.json"),
            "continue": str(DG_ROOT / "configs" / "client_profiles" / "continue.config.yaml"),
            "env": str(DG_ROOT / "configs" / "client_profiles" / "openai.env"),
            "openhands": str(OPENHANDS_PROFILE),
            "openhands_env": str(OPENHANDS_ENV),
            "qwen_code_mcp": str(QWEN_CODE_MCP_PROFILE),
            "autogen": str(AUTOGEN_PROFILE),
            "smolagents": str(SMOLAGENTS_PROFILE),
            "langgraph": str(LANGGRAPH_PROFILE),
            "crewai": str(CREWAI_PROFILE),
            "open_interpreter": str(OPEN_INTERPRETER_PROFILE),
            "llamaindex": str(LLAMAINDEX_PROFILE),
            "haystack": str(HAYSTACK_PROFILE),
            "swe_agent": str(SWE_AGENT_PROFILE),
            "mini_swe_agent": str(MINI_SWE_AGENT_PROFILE),
            "mcp": str(MCP_SERVER_PROFILE),
            "goose_mcp": str(GOOSE_MCP_PROFILE),
            "litellm_model_registry": str(LITELLM_LOCAL_MODEL_REGISTRY),
        },
        "external_agents": {
            "openhands": {"installed": bool(openhands_bin), "binary": openhands_bin, "profile": str(OPENHANDS_PROFILE)},
            "autogen": {"installed": autogen_available, "binary": str(autogen_python) if autogen_available else "", "profile": str(AUTOGEN_PROFILE)},
            "smolagents": {"installed": smolagents_available, "binary": str(smolagents_python) if smolagents_available else "", "profile": str(SMOLAGENTS_PROFILE)},
            "langgraph": {"installed": langgraph_available, "binary": str(langgraph_python) if langgraph_available else "", "profile": str(LANGGRAPH_PROFILE)},
            "crewai": {"installed": crewai_available, "binary": str(crewai_python) if crewai_available else "", "profile": str(CREWAI_PROFILE)},
            "open_interpreter": {"installed": open_interpreter_available, "binary": str(open_interpreter_python) if open_interpreter_available else "", "profile": str(OPEN_INTERPRETER_PROFILE)},
            "llamaindex": {"installed": llamaindex_available, "binary": str(llamaindex_python) if llamaindex_available else "", "profile": str(LLAMAINDEX_PROFILE)},
            "haystack": {"installed": haystack_available, "binary": str(haystack_python) if haystack_available else "", "profile": str(HAYSTACK_PROFILE)},
            "qwen_code": {"installed": bool(qwen_code_bin_str), "binary": qwen_code_bin_str, "profile": str(QWEN_CODE_MCP_PROFILE)},
            "swe_agent": {"installed": bool(swe_agent_bin), "binary": swe_agent_bin, "profile": str(SWE_AGENT_PROFILE)},
            "mini_swe_agent": {"installed": bool(mini_swe_agent_bin), "binary": mini_swe_agent_bin, "profile": str(MINI_SWE_AGENT_PROFILE)},
        },
        "scripts": {
            name: path_exists(DG_ROOT / "scripts" / name)
            for name in [
                "run_task_runner.sh",
                "run_supervisor_agent.sh",
                "run_persistent_supervisor.sh",
                "run_agentapi_aider.sh",
                "run_autogen_local.sh",
                "run_smolagents_local.sh",
                "run_langgraph_local.sh",
                "run_crewai_local.sh",
                "run_open_interpreter_local.sh",
                "run_llamaindex_local.sh",
                "run_haystack_local.sh",
                "run_opencode_local.sh",
                "run_opencode_agent_local.sh",
                "run_opencode_mcp_local.sh",
                "run_opencode_acp_local.sh",
                "run_goose_local.sh",
                "run_goose_mcp_local.sh",
                "run_openhands_local.sh",
                "run_openhands_acp_local.sh",
                "run_openhands_mcp_setup.sh",
                "run_qwen_code_local.sh",
                "run_swe_agent_local.sh",
                "run_mini_swe_agent_local.sh",
                "dg_mini_swe_runner.py",
                "dg_autogen_runner.py",
                "dg_smolagents_runner.py",
                "dg_langgraph_runner.py",
                "dg_crewai_runner.py",
                "dg_open_interpreter_runner.py",
                "dg_llamaindex_runner.py",
                "dg_haystack_runner.py",
                "dg_persistent_supervisor.py",
                "smoke_persistent_supervisor.sh",
                "install_uv_local.sh",
                "install_autogen_local.sh",
                "install_smolagents_local.sh",
                "install_langgraph_local.sh",
                "install_crewai_local.sh",
                "install_open_interpreter_local.sh",
                "install_llamaindex_local.sh",
                "install_haystack_local.sh",
                "install_mcp_sdk_local.sh",
                "install_serena_local.sh",
                "install_openhands_local.sh",
                "install_qwen_code_local.sh",
                "install_swe_agent_local.sh",
                "install_mini_swe_agent_local.sh",
                "run_mcp_server.sh",
                "run_mcp_http_server.sh",
                "run_repomix_mcp.sh",
                "run_serena_mcp.sh",
                "dg_mcp_sdk_server.py",
                "dg_mcp_server.py",
                "run_litellm_gateway.sh",
                "run_litellm_gateway_foreground.sh",
                "run_stack_watchdog.sh",
                "rag_code_agent.py",
                "dg_agent_capabilities.py",
                "smoke_task_runner.sh",
                "smoke_dg_agent_capabilities.sh",
                "smoke_dg_agent_edit.sh",
                "smoke_dg_agent_context_plan.sh",
                "smoke_dg_agent_auto_test.sh",
                "smoke_dg_agent_verify.sh",
                "smoke_dg_agent_session.sh",
                "smoke_dg_agent_sessions.sh",
                "smoke_dg_agent_session_artifacts.sh",
                "smoke_dg_agent_agent.sh",
                "smoke_aider_proxy_adapter.sh",
                "smoke_dg_agent_wrappers.sh",
                "smoke_autogen_local.sh",
                "smoke_smolagents_local.sh",
                "smoke_langgraph_local.sh",
                "smoke_crewai_local.sh",
                "smoke_open_interpreter_local.sh",
                "smoke_llamaindex_local.sh",
                "smoke_haystack_local.sh",
                "smoke_dg_agent_bootstrap.sh",
                "smoke_dg_agent_client_pack.sh",
                "smoke_dg_agent_workspace_init.sh",
                "smoke_client_init.sh",
                "smoke_client_smoke.sh",
                "smoke_agent_bridge.sh",
                "smoke_external_agent_profiles.sh",
                "smoke_mini_swe_runner.sh",
                "smoke_dg_agent_preflight.sh",
                "smoke_dg_agent_run.sh",
                "smoke_agentapi_aider.sh",
                "smoke_opencode_local.sh",
                "smoke_opencode_agent_local.sh",
                "smoke_opencode_run_fallback.sh",
                "smoke_opencode_mcp_local.sh",
                "smoke_opencode_acp_local.sh",
                "smoke_goose_local.sh",
                "smoke_goose_mcp_local.sh",
                "smoke_goose_acp_local.sh",
                "smoke_openhands_acp_local.sh",
                "smoke_openhands_mcp_local.sh",
                "smoke_qwen_code_local.sh",
                "smoke_litellm_gateway.sh",
                "smoke_gateway_clients.sh",
                "smoke_openai_sdk_gateway.sh",
                "smoke_mcp_server.sh",
                "smoke_mcp_http_server.sh",
                "smoke_serena_mcp.sh",
                "smoke_ast_grep.sh",
                "smoke_code_outline.sh",
                "smoke_stack_watchdog.sh",
                "smoke_stack_control.sh",
            ]
        },
        "recommended": {
            "reliable_edits": "scripts/run_task_runner.sh",
            "single_file_edits": "scripts/run_supervisor_agent.sh",
            "autonomous_controller": "scripts/dg_agent.sh autonomous -- --repo /repo --task \"...\"",
            "web_api": "scripts/run_agentapi_aider.sh",
            "primary_terminal_agent": "scripts/dg_agent.sh opencode-agent -- /repo",
            "codex_like_experiment": "scripts/run_opencode_local.sh",
            "mcp_agent_experiment": "scripts/run_goose_local.sh",
            "goose_with_mcp_tools": "scripts/dg_agent.sh goose-mcp -- info -v",
            "mcp_tool_server": "scripts/dg_agent.sh mcp",
            "serena_mcp_server": "scripts/run_serena_mcp.sh",
            "rag_context": "scripts/dg_agent.sh rag --repo /repo --task \"...\" --print-context",
            "oss_repo_pack": "scripts/dg_agent.sh repo-pack --repo /repo --style markdown --stdout",
            "aider_repo_map": "scripts/dg_agent.sh repo-map --repo /repo --map-tokens 512",
            "structural_search": "scripts/dg_agent.sh ast-grep --repo /repo --lang python --pattern 'return $X' --json",
            "code_outline": "scripts/dg_agent.sh code-outline --repo /repo --lang python --json",
            "heavy_agent_experiments": "scripts/run_openhands_local.sh / scripts/run_mini_swe_agent_local.sh",
            "artifacted_mini_swe": "scripts/dg_agent.sh mini-swe-run --repo /repo --task \"...\"",
            "openai_gateway": "scripts/run_litellm_gateway.sh",
        },
    }


def print_text_report(report: dict[str, Any]) -> None:
    def mark(ok: bool) -> str:
        return "ok" if ok else "fail"

    print("DG local agent stack")
    print(f"root: {report['root']}")
    print(f"backend 4100: {mark(bool(report['backend']['ok']))}")
    if report["backend"]["ok"]:
        detail = report["backend"]["detail"]
        print(f"  model: {detail.get('model')} maxtok={detail.get('maxtok')} ngl={detail.get('ngl')}")
    else:
        print(f"  {report['backend']['detail']}")
    print(f"proxy 8090: {mark(bool(report['proxy']['ok']))}")
    if report["proxy"]["ok"]:
        detail = report["proxy"]["detail"]
        print(f"  model: {detail.get('model')} backend={detail.get('backend_model')}")
    else:
        print(f"  {report['proxy']['detail']}")
    print(f"aider: {mark(bool(report['aider']['installed']))} {report['aider']['version']['detail']}")
    print(f"agentapi: {mark(bool(report['agentapi']['installed']))} {report['agentapi']['version']['detail']}")
    print(f"agentapi running: {mark(bool(report['agentapi']['running']))} {report['agentapi']['chat']}")
    print(f"opencode: {mark(bool(report['opencode']['installed']))} {report['opencode']['version']['detail']}")
    print(f"node: {mark(bool(report['opencode']['node']['ok']))} {report['opencode']['node']['detail']}")
    print(f"goose: {mark(bool(report['goose']['installed']))} {report['goose']['version']['detail']}")
    print(f"litellm: {mark(bool(report['litellm']['installed']))} {report['litellm']['version']['detail']}")
    print(f"litellm running: {mark(bool(report['litellm']['running']))} {report['litellm']['url']}")
    print(f"mcp sdk: {mark(bool(report['mcp']['installed']))} {report['mcp']['version']['detail']}")
    print(f"serena mcp: {mark(bool(report['serena']['installed']))} {report['serena']['version']['detail']}")
    print(f"autogen: {mark(bool(report['external_agents']['autogen']['installed']))} {report['external_agents']['autogen']['binary'] or 'missing'}")
    print(f"smolagents: {mark(bool(report['external_agents']['smolagents']['installed']))} {report['external_agents']['smolagents']['binary'] or 'missing'}")
    print(f"langgraph: {mark(bool(report['external_agents']['langgraph']['installed']))} {report['external_agents']['langgraph']['binary'] or 'missing'}")
    print(f"crewai: {mark(bool(report['external_agents']['crewai']['installed']))} {report['external_agents']['crewai']['binary'] or 'missing'}")
    print(f"open-interpreter: {mark(bool(report['external_agents']['open_interpreter']['installed']))} {report['external_agents']['open_interpreter']['binary'] or 'missing'}")
    print(f"llamaindex: {mark(bool(report['external_agents']['llamaindex']['installed']))} {report['external_agents']['llamaindex']['binary'] or 'missing'}")
    print(f"haystack: {mark(bool(report['external_agents']['haystack']['installed']))} {report['external_agents']['haystack']['binary'] or 'missing'}")
    print(f"openhands cli: {mark(bool(report['external_agents']['openhands']['installed']))} {report['external_agents']['openhands']['binary'] or 'missing'}")
    print(f"qwen code cli: {mark(bool(report['external_agents']['qwen_code']['installed']))} {report['external_agents']['qwen_code']['binary'] or 'missing'}")
    print(f"swe-agent cli: {mark(bool(report['external_agents']['swe_agent']['installed']))} {report['external_agents']['swe_agent']['binary'] or 'missing'}")
    print(f"mini-swe-agent cli: {mark(bool(report['external_agents']['mini_swe_agent']['installed']))} {report['external_agents']['mini_swe_agent']['binary'] or 'missing'}")
    print(f"client profiles: {report['client_profiles']['openai_compatible']}")
    missing = [name for name, exists in report["scripts"].items() if not exists]
    print(f"scripts: {'ok' if not missing else 'missing ' + ', '.join(missing)}")
    print()
    print("Recommended commands:")
    print("  agent mode:     scripts/dg_agent.sh agent --repo /repo --task \"...\" --file path")
    print("  natural edit:   scripts/dg_agent.sh edit --repo /repo --task \"...\" --file path --test-cmd \"...\" --rollback-on-failure")
    print("  full session:   scripts/dg_agent.sh session --repo /repo --task \"...\" --file path --auto-test --rollback-on-failure")
    print("  reliable edits: scripts/dg_agent.sh task --repo /repo --plan plan.json --report /tmp/report.json --rollback-on-failure")
    print("  rag context:    scripts/dg_agent.sh rag --repo /repo --task \"...\" --print-context")
    print("  repo pack:      scripts/dg_agent.sh repo-pack --repo /repo --style markdown --stdout")
    print("  repo map:       scripts/dg_agent.sh repo-map --repo /repo --map-tokens 512")
    print("  ast-grep:       scripts/dg_agent.sh ast-grep --repo /repo --lang python --pattern 'return $X' --json")
    print("  code outline:   scripts/dg_agent.sh code-outline --repo /repo --lang python --json")
    print("  web/API agent:  scripts/dg_agent.sh web --repo /repo --port 3284")
    print("  ACP bridge:     scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp")
    print("  opencode TUI:   scripts/dg_agent.sh opencode -- /repo")
    print("  goose agent:    scripts/dg_agent.sh goose -- run --no-profile --max-turns 1 --text \"...\"")
    print("  mcp tools:      scripts/dg_agent.sh mcp --list-tools")
    print("  serena MCP:     scripts/run_serena_mcp.sh")
    print("  openhands:      scripts/dg_agent.sh openhands -- --repo /repo --task \"...\" --dry-run")
    print("  openhands MCP:  scripts/dg_agent.sh openhands-mcp -- --repo /repo --reset")
    print("  qwen-code:      scripts/dg_agent.sh qwen-code -- --repo /repo --dry-run")
    print("  autogen:        scripts/dg_agent.sh autogen -- --repo /repo --dry-run")
    print("  smolagents:     scripts/dg_agent.sh smolagents -- --repo /repo --dry-run")
    print("  langgraph:      scripts/dg_agent.sh langgraph -- --repo /repo --dry-run")
    print("  crewai:         scripts/dg_agent.sh crewai -- --repo /repo --dry-run")
    print("  open-interpreter: scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run")
    print("  llamaindex:     scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run")
    print("  haystack:       scripts/dg_agent.sh haystack -- --repo /repo --dry-run")
    print("  autonomous:     scripts/dg_agent.sh autonomous -- --repo /repo --task \"...\"")
    print("  mini-swe-agent: scripts/dg_agent.sh mini-swe-agent -- --repo /repo --task \"...\" --dry-run")
    print("  litellm API:    scripts/dg_agent.sh litellm")


def wrapper_matrix() -> dict[str, Any]:
    report = component_report()
    missing_external_names = [
        name
        for name, installed in [
            ("OpenHands", bool(report["external_agents"]["openhands"]["installed"])),
            ("AutoGen AgentChat", bool(report["external_agents"]["autogen"]["installed"])),
            ("Hugging Face smolagents", bool(report["external_agents"]["smolagents"]["installed"])),
            ("LangGraph", bool(report["external_agents"]["langgraph"]["installed"])),
            ("CrewAI", bool(report["external_agents"]["crewai"]["installed"])),
            ("Open Interpreter", bool(report["external_agents"]["open_interpreter"]["installed"])),
            ("LlamaIndex", bool(report["external_agents"]["llamaindex"]["installed"])),
            ("Haystack", bool(report["external_agents"]["haystack"]["installed"])),
            ("Qwen Code", bool(report["external_agents"]["qwen_code"]["installed"])),
            ("SWE-agent", bool(report["external_agents"]["swe_agent"]["installed"])),
            ("mini-swe-agent", bool(report["external_agents"]["mini_swe_agent"]["installed"])),
        ]
        if not installed
    ]
    return {
        "default": {
            "name": "DG agent mode",
            "status": "recommended",
            "command": "scripts/dg_agent.sh agent --repo /repo --task \"...\" --file path",
            "uses": ["Aider-compatible edit path", "task runner", "repo context pack", "verification", "session artifacts"],
            "why": "Best current reliability for this small-context DiffusionGemma runtime.",
        },
        "ready_made_oss": [
            {
                "name": "Aider",
                "role": "Primary file edit engine",
                "installed": bool(report["aider"]["installed"]),
                "command": "scripts/run_aider_local.sh /repo",
                "recommended_for": "file-level coding edits",
                "notes": "Used underneath the reliable task/session path.",
            },
            {
                "name": "Persistent supervisor",
                "role": "Checkpointed controller over Haystack retrieval and DG sessions",
                "installed": bool(report["scripts"].get("run_persistent_supervisor.sh") and report["external_agents"]["haystack"]["installed"]),
                "command": "scripts/dg_agent.sh autonomous -- --repo /repo --task \"...\"",
                "recommended_for": "bounded multi-attempt tasks with persistent state and test-feedback retries",
                "notes": "Never enables generic model tool calls; all edits remain on the verified session/Aider route.",
            },
            {
                "name": "AgentAPI",
                "role": "Web/API surface over Aider",
                "installed": bool(report["agentapi"]["installed"]),
                "running": bool(report["agentapi"]["running"]),
                "command": "scripts/dg_agent.sh web --repo /repo --port 3284",
                "recommended_for": "browser/API interaction with the Aider path",
                "notes": "Useful as an external UI surface, not the strongest automation layer.",
            },
            {
                "name": "OpenCode compact delegate",
                "role": "Primary bounded Codex-like terminal workflow",
                "installed": bool(report["opencode"]["installed"]),
                "command": "scripts/dg_agent.sh opencode-agent -- /repo",
                "recommended_for": "interactive read and scoped-edit tasks with verified artifacts",
                "notes": "OpenCode's Bash tool is routed to the deterministic DG read/session workflow; live read and edit Git checks pass.",
            },
            {
                "name": "OpenCode generic",
                "role": "Codex-like terminal agent experiment",
                "installed": bool(report["opencode"]["installed"]),
                "command": "scripts/dg_agent.sh opencode -- /repo",
                "recommended_for": "interactive terminal UX experiments",
                "notes": "Provider discovery and bounded run smoke exist; reliable edits should stay on dg_agent.sh agent/task.",
            },
            {
                "name": "ACP agent bridge",
            "role": "One-shot ACP server over upstream OpenCode/Goose",
                "installed": bool(report["opencode"]["installed"] or report["goose"]["installed"] or report["external_agents"]["openhands"]["installed"]),
                "command": "scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp",
                "recommended_for": "ACP-capable clients that need a running local agent server",
                "notes": "Prepares the repo with client-init, then reports or starts OpenCode ACP, Goose ACP, or OpenHands ACP over the local DG profile.",
            },
            {
                "name": "Goose",
                "role": "MCP-capable agent shell experiment",
                "installed": bool(report["goose"]["installed"]),
                "command": "scripts/dg_agent.sh goose -- run --no-profile --max-turns 1 --text \"...\"",
                "recommended_for": "MCP/session/review experiments",
                "notes": "Native tool-calling remains weak with the current DG profile.",
            },
            {
                "name": "LiteLLM",
                "role": "OpenAI-compatible gateway",
                "installed": bool(report["litellm"]["installed"]),
                "running": bool(report["litellm"]["running"]),
                "base_url": "http://127.0.0.1:4100/v1",
                "model": "diffusiongemma-local",
                "recommended_for": "IDE clients, OpenAI SDK, Continue/Cline/Roo-style integrations",
                "notes": "Generic chat runs in safe compatibility mode by default; real edits use agent/session/task.",
            },
            {
                "name": "MCP Python SDK server",
                "role": "Official MCP stdio tool bridge",
                "installed": bool(report["mcp"]["installed"]),
                "command": "scripts/dg_agent.sh mcp",
                "config": str(MCP_SERVER_PROFILE),
                "recommended_for": "MCP-capable IDEs and OSS agent shells",
                "notes": "Exposes repo inspection, preflight, context, plan, task, session, verify and health/capability tools over the official SDK.",
            },
            {
                "name": "Serena",
                "role": "Upstream semantic/LSP MCP server",
                "installed": bool(report["serena"]["installed"]),
                "command": "scripts/run_serena_mcp.sh",
                "recommended_for": "symbol search, references, diagnostics, safe symbol edits, and IDE-grade semantic navigation",
                "notes": "Runs as an optional MCP server alongside DG MCP; clients can mount both instead of forcing the small model to read broad repository context.",
            },
            {
                "name": "OpenHands",
                "role": "Heavy autonomous dev-agent shell over LiteLLM Proxy",
                "installed": bool(report["external_agents"]["openhands"]["installed"]),
                "command": "scripts/dg_agent.sh openhands -- --repo /repo --task \"...\"",
                "recommended_for": "controlled external-agent experiments",
                "notes": "Uses configs/client_profiles/openhands.dg.toml and the LiteLLM proxy model name.",
            },
            {
                "name": "OpenHands ACP",
                "role": "ACP stdio agent server over OpenHands",
                "installed": bool(report["external_agents"]["openhands"]["installed"] and report["scripts"].get("run_openhands_acp_local.sh")),
                "command": "scripts/dg_agent.sh openhands-acp",
                "recommended_for": "ACP-capable clients that prefer OpenHands over OpenCode/Goose",
                "notes": "Uses the working upstream `openhands acp` subcommand with the DG LiteLLM profile.",
            },
            {
                "name": "OpenHands + MCP",
                "role": "OpenHands built-in MCP config with DG, Repomix, and Serena servers",
                "installed": bool(report["external_agents"]["openhands"]["installed"] and report["scripts"].get("run_openhands_mcp_setup.sh")),
                "command": "scripts/dg_agent.sh openhands-mcp -- --repo /repo --reset",
                "recommended_for": "OpenHands experiments that need repo tools and semantic navigation without writing a new agent loop",
                "notes": "Writes an isolated repo-local OpenHands persistence dir at .dg-agent/openhands-persistence/mcp.json.",
            },
            {
                "name": "AutoGen AgentChat",
                "role": "Open-source Python multi-agent framework over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["autogen"]["installed"] and report["scripts"].get("run_autogen_local.sh")),
                "command": "scripts/dg_agent.sh autogen -- --repo /repo --dry-run",
                "recommended_for": "Python framework experiments, multi-agent prototypes, and controlled model-client testing",
                "notes": "Uses autogen-agentchat plus autogen-ext[openai] with configs/client_profiles/autogen.dg.json.",
            },
            {
                "name": "Hugging Face smolagents",
                "role": "Open-source CodeAgent framework over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["smolagents"]["installed"] and report["scripts"].get("run_smolagents_local.sh")),
                "command": "scripts/dg_agent.sh smolagents -- --repo /repo --dry-run",
                "recommended_for": "CodeAgent framework experiments and small controlled model-client tests",
                "notes": "Uses smolagents CodeAgent plus OpenAIModel with configs/client_profiles/smolagents.dg.json.",
            },
            {
                "name": "LangGraph",
                "role": "Open-source graph-agent framework over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["langgraph"]["installed"] and report["scripts"].get("run_langgraph_local.sh")),
                "command": "scripts/dg_agent.sh langgraph -- --repo /repo --dry-run",
                "recommended_for": "graph-agent framework experiments and controlled stateful agent prototypes",
                "notes": "Uses LangGraph/LangChain plus ChatOpenAI with configs/client_profiles/langgraph.dg.json.",
            },
            {
                "name": "CrewAI",
                "role": "Open-source multi-agent crew framework over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["crewai"]["installed"] and report["scripts"].get("run_crewai_local.sh")),
                "command": "scripts/dg_agent.sh crewai -- --repo /repo --dry-run",
                "recommended_for": "multi-agent crew framework experiments and short role/task prototypes",
                "notes": "Uses CrewAI Agent/Task/Crew/LLM with configs/client_profiles/crewai.dg.json.",
            },
            {
                "name": "Open Interpreter",
                "role": "Open-source code-execution shell over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["open_interpreter"]["installed"] and report["scripts"].get("run_open_interpreter_local.sh")),
                "command": "scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run",
                "recommended_for": "short interactive code-execution experiments with safe_mode=ask and auto_run=false",
                "notes": "Uses open-interpreter with configs/client_profiles/open-interpreter.dg.json; keep reliable edits on dg_agent.sh agent/task.",
            },
            {
                "name": "LlamaIndex",
                "role": "Open-source RAG/agent framework over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["llamaindex"]["installed"] and report["scripts"].get("run_llamaindex_local.sh")),
                "command": "scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run",
                "recommended_for": "RAG/query-engine and ReActAgent/AgentWorkflow framework experiments with OpenAILike",
                "notes": "Uses llama-index-core plus llama-index-llms-openai-like with configs/client_profiles/llamaindex.dg.json.",
            },
            {
                "name": "Haystack",
                "role": "Open-source BM25 RAG pipeline over the local OpenAI-compatible model",
                "installed": bool(report["external_agents"]["haystack"]["installed"] and report["scripts"].get("run_haystack_local.sh")),
                "command": "scripts/dg_agent.sh haystack -- --repo /repo --dry-run",
                "recommended_for": "retrieval-first repository Q&A when the model context is small",
                "notes": "Uses haystack-ai InMemoryDocumentStore, InMemoryBM25Retriever, and OpenAIChatGenerator with configs/client_profiles/haystack.dg.json.",
            },
            {
                "name": "Qwen Code",
                "role": "Open-source terminal agent for explicit read-only file inspection",
                "installed": bool(report["external_agents"]["qwen_code"]["installed"] and (report["scripts"].get("run_qwen_code_local.sh") or (DG_ROOT / "scripts" / "run_qwen_code_windows.ps1").exists())),
                "command": "scripts/dg_agent.sh qwen-code -- --repo /repo --dry-run",
                "recommended_for": "read-only terminal inspection experiments with an explicit file path",
                "notes": "Unified runner prefers the WSL MCP route with DG, Repomix, and Serena; native Windows fallback stays read-only on the safe GPU gateway.",
            },
            {
                "name": "mini-swe-agent",
                "role": "Small SWE-style coding agent over LiteLLM/OpenAI-compatible endpoint",
                "installed": bool(report["external_agents"]["mini_swe_agent"]["installed"]),
                "command": "scripts/dg_agent.sh mini-swe-agent -- --repo /repo --task \"...\"",
                "recommended_for": "short benchmark-style local experiments",
                "notes": "Uses configs/client_profiles/mini-swe-agent.dg.yaml with a short step limit.",
            },
            {
                "name": "SWE-agent",
                "role": "Classic SWE benchmark-style coding agent",
                "installed": bool(report["external_agents"]["swe_agent"]["installed"]),
                "command": "scripts/dg_agent.sh swe-agent -- --repo /repo --task \"...\"",
                "recommended_for": "compatibility experiments with classic SWE-agent configs",
                "notes": "Maintenance-mode upstream; prefer mini-swe-agent for new local experiments.",
            },
            {
                "name": "Continue/Cline/Roo/Kilo profiles",
                "role": "IDE clients through LiteLLM",
                "installed": True,
                "config": str(DG_ROOT / "configs" / "client_profiles"),
                "recommended_for": "manual IDE-assisted workflows",
                "notes": "Keep context small and prefer explicit file hints.",
            },
        ],
        "not_installed_candidates": [
            {
                "name": ", ".join(missing_external_names),
                "role": "Optional external CLI installs",
                "route": "install missing upstream CLIs, then use the checked-in DG profiles and dg_agent.sh launchers",
                "reason_not_default": "Heavy autonomous tool loops remain less reliable than bounded Aider/task-runner edits on this model.",
                "install": "scripts/dg_agent.sh bootstrap --external --install",
            },
        ] if missing_external_names else [],
        "runtime": {
            "backend_ok": bool(report["backend"]["ok"]),
            "proxy_ok": bool(report["proxy"]["ok"]),
            "litellm_ok": bool(report["litellm"]["running"]),
            "model": report["litellm"]["model"],
            "base_url": report["litellm"]["url"] + "/v1",
        },
    }


def print_wrappers_report(data: dict[str, Any]) -> None:
    default = data["default"]
    print("DG OSS wrapper stack")
    print(f"default: {default['name']} ({default['status']})")
    print(f"command: {default['command']}")
    print(f"why: {default['why']}")
    print()
    print("Ready-made OSS layers:")
    for item in data["ready_made_oss"]:
        status = "installed" if item.get("installed") else "missing"
        running = ""
        if "running" in item:
            running = ", running" if item.get("running") else ", stopped"
        print(f"- {item['name']}: {status}{running}")
        print(f"  role: {item['role']}")
        if item.get("command"):
            print(f"  command: {item['command']}")
        if item.get("base_url"):
            print(f"  endpoint: {item['base_url']} model={item.get('model')}")
        if item.get("config"):
            print(f"  config: {item['config']}")
        print(f"  use: {item['recommended_for']}")
    print()
    if data["not_installed_candidates"]:
        print("Candidates to install as optional experiments:")
        for item in data["not_installed_candidates"]:
            print(f"- {item['name']}: {item['role']}")
            print(f"  route: {item['route']}")
            print(f"  install: {item.get('install', '')}")
            print(f"  limit: {item['reason_not_default']}")
    else:
        print("Optional external OSS agents: installed; keep OpenHands/Qwen/AutoGen/smolagents/LangGraph/CrewAI/Open Interpreter/LlamaIndex/Haystack/SWE-family wrappers as experiments.")
    runtime = data["runtime"]
    print()
    print(f"runtime: backend={runtime['backend_ok']} proxy={runtime['proxy_ok']} litellm={runtime['litellm_ok']}")


def wrapper_component_catalog(include_external: bool = False) -> dict[str, dict[str, Any]]:
    catalog = dict(WRAPPER_COMPONENTS)
    if include_external:
        catalog.update(EXTERNAL_AGENT_COMPONENTS)
    return catalog


def wrapper_component_audit(include_external: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, spec in wrapper_component_catalog(include_external).items():
        install_script = DG_ROOT / "scripts" / str(spec["install_script"])
        check_rows: list[dict[str, Any]] = []
        installed_parts: list[bool] = []
        for rel in spec["checks"]:
            if isinstance(rel, (list, tuple)):
                alternatives = [DG_ROOT / str(item) for item in rel]
                exists = any(path_exists(path) for path in alternatives)
                installed_parts.append(exists)
                check_rows.append(
                    {
                        "path": " | ".join(str(path) for path in alternatives),
                        "exists": exists,
                        "alternatives": [{"path": str(path), "exists": path_exists(path)} for path in alternatives],
                    }
                )
            else:
                path = DG_ROOT / str(rel)
                exists = path_exists(path)
                installed_parts.append(exists)
                check_rows.append({"path": str(path), "exists": exists})
        installed = all(installed_parts)
        if key == "aider":
            runtime = aider_runtime_status()
            check_rows.append(
                {
                    "path": "active Aider runtime (WSL Python 3.12)",
                    "exists": bool(runtime["ok"]),
                    "detail": runtime["detail"],
                }
            )
            installed = bool(runtime["ok"]) and path_exists(DG_ROOT / "scripts" / "run_aider_local.sh")
        if key == "mcp":
            runtime = mcp_sdk_runtime_status()
            check_rows.append(
                {
                    "path": "active MCP runtime (WSL on Windows)",
                    "exists": bool(runtime["ok"]),
                    "detail": runtime["detail"],
                }
            )
            # The SDK is intentionally installed in the WSL runtime because
            # native Windows Python DLL loading is blocked on this machine.
            installed = bool(runtime["ok"]) and path_exists(DG_ROOT / "scripts" / "dg_mcp_sdk_server.py")
        if key == "serena":
            runtime = serena_runtime_status()
            check_rows.append(
                {
                    "path": "active Serena runtime",
                    "exists": bool(runtime["ok"]),
                    "detail": runtime["detail"],
                }
            )
            installed = bool(runtime["ok"]) and path_exists(DG_ROOT / "scripts" / "run_serena_mcp.sh")
        if key == "langgraph":
            runtime = langgraph_runtime_status()
            check_rows.append(
                {
                    "path": runtime.get("path") or "active LangGraph runtime",
                    "exists": bool(runtime["ok"]),
                    "detail": runtime["detail"],
                }
            )
            installed = bool(runtime["ok"]) and path_exists(DG_ROOT / "scripts" / "dg_langgraph_runner.py")
        if key == "opencode":
            runtime = opencode_runtime_status()
            check_rows.append(
                {
                    "path": runtime["path"] or "active OpenCode runtime",
                    "exists": bool(runtime["ok"]),
                    "detail": runtime["detail"],
                }
            )
            installed = bool(runtime["ok"])
        if key == "qwen-code":
            runtime = qwen_code_runtime_status()
            check_rows.append(
                {
                    "path": runtime["path"] or "active Qwen Code runtime",
                    "exists": bool(runtime["ok"]),
                    "detail": runtime["detail"],
                }
            )
            installed = bool(runtime["ok"])
        rows.append(
            {
                "id": key,
                "name": spec["name"],
                "installed": installed,
                "checks": check_rows,
                "install_script": str(install_script),
                "install_script_exists": path_exists(install_script),
                "smoke_suite": spec["smoke_suite"],
                "external": key in EXTERNAL_AGENT_COMPONENTS,
            }
        )
    return rows


def selected_wrapper_components(only: list[str], include_external: bool = False) -> list[str]:
    catalog = wrapper_component_catalog(include_external)
    if not only:
        return list(catalog)
    selected: list[str] = []
    for item in only:
        for part in item.split(","):
            key = part.strip().lower()
            if not key:
                continue
            if key not in catalog and key in EXTERNAL_AGENT_COMPONENTS:
                catalog.update(EXTERNAL_AGENT_COMPONENTS)
            if key not in catalog:
                raise ValueError(f"unknown wrapper component: {key}")
            if key not in selected:
                selected.append(key)
    return selected


def run_wrapper_bootstrap(args: argparse.Namespace) -> int:
    try:
        selected = selected_wrapper_components(args.only, args.external)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    include_external = args.external or any(item in EXTERNAL_AGENT_COMPONENTS for item in selected)
    before = wrapper_component_audit(include_external)
    selected_set = set(selected)
    install_results: list[dict[str, Any]] = []
    smoke_results: list[dict[str, Any]] = []

    if args.install:
        before_by_id = {row["id"]: row for row in before}
        for key in selected:
            row = before_by_id[key]
            if row["installed"] and not args.refresh:
                install_results.append({"id": key, "status": "skipped", "reason": "already installed"})
                continue
            script = Path(row["install_script"])
            if not script.exists():
                install_results.append({"id": key, "status": "failed", "reason": f"missing {script}"})
                continue
            proc = run_cmd([str(script)], timeout=args.install_timeout)
            install_results.append(
                {
                    "id": key,
                    "status": "success" if proc.returncode == 0 else "failed",
                    "returncode": proc.returncode,
                    "stdout_tail": proc.stdout[-4000:],
                    "stderr_tail": proc.stderr[-4000:],
                }
            )
            if proc.returncode != 0 and not args.keep_going:
                after = wrapper_component_audit()
                result = {"before": before, "after": after, "install_results": install_results, "smoke_results": smoke_results}
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print_bootstrap_report(result)
                return proc.returncode

    if args.smoke_static:
        proc = run_cmd([str(DG_ROOT / "scripts" / "smoke_dg_agent_wrappers.sh")], timeout=args.smoke_timeout)
        smoke_results.append(
            {
                "suite": "wrappers",
                "status": "success" if proc.returncode == 0 else "failed",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-4000:],
            }
        )
        if proc.returncode != 0 and not args.keep_going:
            after = wrapper_component_audit()
            result = {"before": before, "after": after, "install_results": install_results, "smoke_results": smoke_results}
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print_bootstrap_report(result)
            return proc.returncode

    if args.smoke_installed:
        catalog = wrapper_component_catalog(include_external)
        for key in selected:
            suite = str(catalog[key]["smoke_suite"])
            if not suite:
                continue
            proc = run_cmd([str(DG_ROOT / "scripts" / "dg_agent.sh"), "smoke", "--suite", suite, "--timeout", str(args.smoke_timeout)], timeout=args.smoke_timeout + 15)
            smoke_results.append(
                {
                    "suite": suite,
                    "component": key,
                    "status": "success" if proc.returncode == 0 else "failed",
                    "returncode": proc.returncode,
                    "stdout_tail": proc.stdout[-4000:],
                    "stderr_tail": proc.stderr[-4000:],
                }
            )
            if proc.returncode != 0 and not args.keep_going:
                after = wrapper_component_audit()
                result = {"before": before, "after": after, "install_results": install_results, "smoke_results": smoke_results}
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print_bootstrap_report(result)
                return proc.returncode

    after = wrapper_component_audit(include_external)
    filtered_before = [row for row in before if row["id"] in selected_set]
    filtered_after = [row for row in after if row["id"] in selected_set]
    result = {
        "selected": selected,
        "install_requested": args.install,
        "refresh": args.refresh,
        "before": filtered_before,
        "after": filtered_after,
        "install_results": install_results,
        "smoke_results": smoke_results,
        "notes": [
            "Default bootstrap is audit-only and does not download packages.",
            "Use --install to run existing install_*_local.sh scripts.",
            "Use --external to include optional OpenHands/Qwen/AutoGen/smolagents/LangGraph/CrewAI/Open Interpreter/LlamaIndex/Haystack/SWE-family CLI installers.",
            "Use --smoke-static for checks that do not require loading the model backend.",
        ],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_bootstrap_report(result)
    failures = [item for item in install_results + smoke_results if item.get("status") == "failed"]
    return 1 if failures else 0


def print_bootstrap_report(result: dict[str, Any]) -> None:
    print("DG OSS wrapper bootstrap")
    print(f"selected: {', '.join(result.get('selected', []))}")
    print(f"install requested: {bool(result.get('install_requested'))}")
    print()
    print("Audit:")
    for row in result.get("after", []):
        status = "installed" if row.get("installed") else "missing"
        print(f"- {row.get('id')}: {status}")
        for check in row.get("checks", []):
            mark = "ok" if check.get("exists") else "missing"
            print(f"  {mark}: {check.get('path')}")
    if result.get("install_results"):
        print()
        print("Install results:")
        for item in result["install_results"]:
            print(f"- {item.get('id')}: {item.get('status')}")
            if item.get("reason"):
                print(f"  {item.get('reason')}")
    if result.get("smoke_results"):
        print()
        print("Smoke results:")
        for item in result["smoke_results"]:
            print(f"- {item.get('suite')}: {item.get('status')} rc={item.get('returncode')}")
    print()
    print("Next:")
    print("  audit only:       scripts/dg_agent.sh bootstrap")
    print("  install missing:  scripts/dg_agent.sh bootstrap --install")
    print("  external audit:   scripts/dg_agent.sh bootstrap --external")
    print("  static smoke:     scripts/dg_agent.sh bootstrap --smoke-static")


def build_client_pack() -> dict[str, Any]:
    litellm_base = "http://127.0.0.1:4100/v1"
    litellm_proxy_base = "http://127.0.0.1:4100"
    proxy_base = "http://127.0.0.1:8090/v1"
    litellm_model = "diffusiongemma-local"
    openai_model = f"openai/{litellm_model}"
    proxy_model = "diffusiongemma-26b-a4b-it-iq4xs-aider-local"
    return {
        "name": "DiffusionGemma local agent client pack",
        "manifest_file": str(CLIENT_PACK_MANIFEST),
        "recommended_entrypoint": {
            "command": "scripts/dg_agent.sh agent --repo /repo --task \"...\" --mode auto",
            "why": "Auto-routes read-only inspection through OpenAI tool-loop repo tools and edits through bounded Aider-compatible sessions with verification, rollback, and artifacts.",
        },
        "limits": {
            "max_input_tokens": 768,
            "max_output_tokens": 256,
            "recommended_task_shape": "file-level or small multi-file tasks with explicit --file hints",
            "generic_chat": "safe compatibility mode by default; use agent/session/task for real edits",
        },
        "endpoints": {
            "litellm": {
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "use_for": "OpenAI-compatible IDE clients, OpenAI SDK, optional external agent shells",
            },
            "aider_proxy": {
                "base_url": proxy_base,
                "api_key": "dummy",
                "model": proxy_model,
                "use_for": "Aider, OpenCode, Goose local wrappers",
            },
        },
        "profiles": {
            "local_agent": {
                "status": "highest-level local CLI facade",
                "route": "Use this first for local tasks. --mode auto picks read-only OpenAI tool-loop for inspection tasks and artifacted session for edits.",
                "command": "scripts/dg_agent.sh agent --repo /repo --task \"...\" --mode auto",
                "read_command": "scripts/dg_agent.sh agent --repo /repo --task \"...\" --mode read",
                "edit_command": "scripts/dg_agent.sh agent --repo /repo --task \"...\" --mode edit --file path",
                "modes": ["auto", "read", "edit"],
                "read_route": "openai_tool_loop_read_only",
                "edit_route": "session",
                "artifacts": ["runlogs/dg-agent-runs/*/agent.json", "runlogs/dg-agent-runs/*/tool-loop.json", "runlogs/dg-agent-sessions/*/session.json"],
                "artifact_commands": {
                    "list_runs": "scripts/dg_agent.sh agent-runs list",
                    "show_latest_run": "scripts/dg_agent.sh agent-runs show --latest",
                    "latest_transcript": "scripts/dg_agent.sh agent-runs artifact transcript --latest",
                },
            },
            "openai_sdk": {
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "env_file": str(DG_ROOT / "configs" / "client_profiles" / "openai.env"),
            },
            "openai_tool_loop": {
                "status": "reference OpenAI-compatible tool loop",
                "route": "Fetch DG tool schemas from the gateway, call Chat Completions through LiteLLM, execute tool_calls through /v1/agent/tool, append role=tool results, summarize them, and preserve a transcript.",
                "command": "scripts/dg_agent.sh tool-loop --repo /repo --task \"...\" --out runlogs/tool-loop/latest.json",
                "script": str(DG_ROOT / "scripts" / "dg_openai_tool_loop.py"),
                "base_url": litellm_base,
                "model": litellm_model,
                "tool_manifest_url": "http://127.0.0.1:8090/v1/agent/tool_manifest",
                "tool_runtime_url": "http://127.0.0.1:8090/v1/agent/tool",
                "tools": [
                    "execute_command",
                    "dg_repo_status",
                    "dg_git_diff",
                    "dg_list_files",
                    "dg_read_file",
                    "dg_search",
                    "dg_repo_pack",
                    "dg_repo_map",
                    "dg_ast_grep",
                    "dg_code_outline",
                    "dg_agent",
                    "dg_session",
                    "dg_context",
                    "dg_rag_context",
                    "dg_session_artifact",
                    "dg_agent_run_artifact",
                ],
                "flags": ["--tool NAME", "--exclude-tool NAME", "--read-only", "--stop-after-tool"],
            },
            "agent_gateway": {
                "status": "OpenAI-compatible safe agent gateway",
                "route": "Use the local safe proxy for Chat Completions, Responses API, tool-call delegation, and wrapper discovery.",
                "base_url": proxy_base,
                "api_key": "dummy",
                "model": proxy_model,
                "discovery": {
                    "health": "http://127.0.0.1:8090/healthz",
                    "models": "http://127.0.0.1:8090/v1/models",
                    "model_card": "http://127.0.0.1:8090/v1/model_card",
                    "capabilities": "http://127.0.0.1:8090/v1/capabilities",
                    "routes": "http://127.0.0.1:8090/v1/agent/routes",
                    "session_api": "http://127.0.0.1:8090/v1/agent/session",
                    "tool_runtime": "http://127.0.0.1:8090/v1/agent/tool",
                    "context": "http://127.0.0.1:8090/v1/agent/context",
                    "rag_context": "http://127.0.0.1:8090/v1/agent/rag",
                    "sessions": "http://127.0.0.1:8090/v1/agent/sessions",
                    "latest_session": "http://127.0.0.1:8090/v1/agent/sessions/latest",
                    "latest_session_diff": "http://127.0.0.1:8090/v1/agent/sessions/latest/diff",
                    "tool_manifest": "http://127.0.0.1:8090/v1/agent/tool_manifest",
                    "actions": "http://127.0.0.1:8090/v1/agent/actions",
                    "agent_runs": "http://127.0.0.1:8090/v1/agent/runs",
                    "latest_agent_run": "http://127.0.0.1:8090/v1/agent/runs/latest",
                    "well_known_agent": "http://127.0.0.1:8090/.well-known/agent.json",
                    "openapi": "http://127.0.0.1:8090/openapi.json",
                },
                "supports": [
                    "chat_completions",
                    "chat_streaming",
                    "responses",
                    "tool_call_delegation",
                    "http_session_action_api",
                    "http_tool_runtime_api",
                    "http_repo_inspection_tools",
                    "http_session_artifact_api",
                    "http_agent_run_artifact_api",
                    "http_context_api",
                    "http_rag_context_api",
                    "openai_tool_schema_manifest",
                    "openai_dg_tool_schemas",
                    "well_known_agent_manifest",
                    "mini_swe_command_delegate",
                    "aider_file_listing_adapter",
                ],
                "generic_generation": "disabled by default; use session/task wrappers for reliable edits",
            },
            "codex_cli": {
                "status": "project-local Codex CLI profile",
                "route": "Use Codex CLI with the local safe agent proxy as an OpenAI-compatible chat provider.",
                "installer": "scripts/dg_agent.sh codex-profile --repo /repo --target all",
                "workspace_launcher": ".dg-agent/bin/codex-profile --target all",
                "workspace_files": [
                    ".dg-agent/CODEX.md",
                    ".dg-agent/codex.config.toml",
                    ".dg-agent/codex.env",
                    ".dg-agent/commands/dg-codex.md",
                ],
                "project_files": [".codex/config.toml"],
                "base_url": proxy_base,
                "api_key_env": "OPENAI_API_KEY",
                "api_key_value": "dummy",
                "model": proxy_model,
                "wire_api": "chat",
            },
            "aider": {
                "command": "scripts/run_aider_local.sh --repo /repo",
                "config": str(AIDER_PROFILE),
                "workspace_config_template": str(AIDER_WORKSPACE_PROFILE),
                "workspace_config": ".dg-agent/aider.dg-fast.conf.yml",
                "manual_command": "aider --config .dg-agent/aider.dg-fast.conf.yml path/to/file",
                "model_settings": str(AIDER_MODEL_SETTINGS),
                "model_metadata": str(AIDER_MODEL_METADATA),
                "env": {
                    "AIDER_OPENAI_API_BASE": proxy_base,
                    "AIDER_OPENAI_API_KEY": "dummy",
                    "DG_AIDER_MODEL": f"openai/{proxy_model}",
                    "DG_AIDER_EDIT_FORMAT": "whole",
                    "DG_AIDER_MAP_TOKENS": "0",
                    "DG_AIDER_MAX_CHAT_HISTORY_TOKENS": "512",
                },
            },
            "rag": {
                "status": "read-only retrieval wrapper",
                "route": "Use rg-based file ranking and snippets to compensate for the small local model context.",
                "command": "scripts/dg_agent.sh rag --repo /repo --task \"...\" --print-context",
                "script": str(DG_ROOT / "scripts" / "rag_code_agent.py"),
                "mcp_tools": ["dg_rag_context", "dg_rag_answer"],
                "recommended_limits": {"max_context_chars": 650, "max_files": 3, "max_tokens": 128},
            },
            "repomix": {
                "status": "optional OSS repository packer",
                "route": "Use upstream Repomix through local npx to pack repositories for AI clients.",
                "command": "scripts/dg_agent.sh repo-pack --repo /repo --style markdown --stdout",
                "upstream": "https://github.com/yamadashy/repomix",
                "package": "repomix",
                "native_mcp_command": "scripts/run_repomix_mcp.sh",
                "mcp_tools": ["dg_repo_pack"],
                "recommended_flags": ["--compress", "--include-diffs", "--token-budget"],
            },
            "repo_map": {
                "status": "optional OSS Aider repository map",
                "route": "Use upstream Aider's repo-map to give agents a compact symbol-aware repository sketch.",
                "command": "scripts/dg_agent.sh repo-map --repo /repo --map-tokens 512",
                "upstream": "https://github.com/Aider-AI/aider",
                "package": "aider-chat",
                "native_command": "scripts/run_aider_local.sh --repo /repo --show-repo-map",
                "mcp_tools": ["dg_repo_map"],
                "recommended_flags": ["--map-tokens", "--map-only", "--max-chars"],
            },
            "ast_grep": {
                "status": "optional OSS structural code search",
                "route": "Use upstream ast-grep to search code by AST patterns before asking the small-context model.",
                "command": "scripts/dg_agent.sh ast-grep --repo /repo --lang python --pattern 'return $X' --json",
                "upstream": "https://github.com/ast-grep/ast-grep",
                "package": "@ast-grep/cli",
                "native_command": "scripts/run_ast_grep.sh",
                "mcp_tools": ["dg_ast_grep"],
                "recommended_flags": ["--lang", "--pattern", "--json", "--files-with-matches"],
            },
            "code_outline": {
                "status": "optional OSS code symbol outline",
                "route": "Use upstream ast-grep outline to map files, classes, functions, imports, and members before reading code.",
                "command": "scripts/dg_agent.sh code-outline --repo /repo --lang python --json",
                "upstream": "https://github.com/ast-grep/ast-grep",
                "package": "@ast-grep/cli",
                "native_command": "scripts/run_ast_grep.sh outline",
                "mcp_tools": ["dg_code_outline"],
                "recommended_flags": ["--lang", "--view", "--items", "--json", "--max-items"],
            },
            "serena_mcp": {
                "status": "optional OSS semantic/LSP MCP server",
                "route": "Mount upstream Serena alongside DG MCP when a client needs symbol-aware navigation, references, diagnostics, and safe symbol edits.",
                "command": "scripts/run_serena_mcp.sh",
                "upstream": "https://github.com/oraios/serena",
                "package": "serena-agent",
                "transport": "stdio",
                "native_command": "scripts/run_serena_mcp.sh",
                "install_command": "scripts/install_serena_local.sh",
                "server_name": "serena",
                "tools": [
                    "get_symbols_overview",
                    "find_symbol",
                    "find_referencing_symbols",
                    "find_implementations",
                    "find_declaration",
                    "get_diagnostics_for_file",
                    "rename_symbol",
                    "safe_delete_symbol",
                    "replace_symbol_body",
                    "insert_before_symbol",
                    "insert_after_symbol",
                    "initial_instructions",
                ],
                "recommended_flags": ["--project-from-cwd", "--context claude-code", "--transport streamable-http"],
            },
            "opencode": {
                "command": "scripts/dg_agent.sh opencode -- /repo",
                "config": str(DG_ROOT / "configs" / "opencode.dg.json"),
                "provider": "diffusiongemma-local",
                "model": f"diffusiongemma-local/{proxy_model}",
            },
            "opencode_agent": {
                "status": "Primary bounded OpenCode terminal workflow",
                "route": "Use upstream OpenCode as the terminal UI and route its single Bash call to the verified DG read/session workflow. This avoids native tool selection by the diffusion model.",
                "command": "scripts/dg_agent.sh opencode-agent -- /repo",
                "config": str(OPENCODE_COMPACT_PROFILE),
                "provider": "diffusiongemma-local",
                "model": f"diffusiongemma-local/{proxy_model}",
                "tools": ["bash"],
                "timeout_env": "OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS=450000",
                "semantic_navigation": "Use the separate Serena MCP profile or repo-map/code-outline before broad tasks.",
            },
            "opencode_mcp": {
                "status": "OpenCode profile with DG MCP and Repomix MCP servers",
                "route": "Run OpenCode with DG workflow tools and upstream repository packing configured in opencode.dg-mcp.json. Use the separate Serena MCP profile in IDE clients for semantic/LSP tools.",
                "command": "scripts/dg_agent.sh opencode-mcp -- /repo",
                "config": str(OPENCODE_MCP_PROFILE),
                "provider": "diffusiongemma-local",
                "model": f"diffusiongemma-local/{proxy_model}",
                "mcp_servers": ["dg_agent", "repomix"],
            },
            "opencode_acp": {
                "status": "OpenCode ACP server with DG MCP and Repomix MCP servers",
                "route": "Run OpenCode's upstream ACP server against the local DG provider and MCP tools.",
                "command": "scripts/dg_agent.sh opencode-acp -- --cwd /repo --hostname 127.0.0.1 --port 3295",
                "config": str(OPENCODE_MCP_PROFILE),
                "provider": "diffusiongemma-local",
                "model": f"diffusiongemma-local/{proxy_model}",
                "base_profile": "opencode_mcp",
                "transport": "acp-http",
                "default_url": "http://127.0.0.1:3295",
                "mcp_servers": ["dg_agent", "repomix"],
            },
            "goose": {
                "command": "scripts/dg_agent.sh goose -- run --no-profile --max-turns 1 --text \"...\"",
                "env": {
                    "GOOSE_PROVIDER": "openai",
                    "GOOSE_MODEL": proxy_model,
                    "OPENAI_HOST": "http://127.0.0.1:8090",
                    "OPENAI_API_KEY": "dummy",
                },
            },
            "goose_mcp": {
                "status": "MCP-capable Goose profile",
                "route": "Run Goose with DG MCP and Serena semantic/LSP MCP mounted as stdio extensions.",
                "command": "scripts/dg_agent.sh goose-mcp -- info -v",
                "config": str(GOOSE_MCP_PROFILE),
                "home": str(DG_ROOT / ".tools" / "goose-dg-mcp-home"),
                "extension": "dg_agent",
                "extensions": ["dg_agent", "serena"],
                "tools": [
                    "dg_task_note",
                    "dg_task_notes",
                    "dg_repo_status",
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
                ],
                "env": {
                    "GOOSE_PROVIDER": "openai",
                    "GOOSE_MODEL": proxy_model,
                    "OPENAI_HOST": "http://127.0.0.1:8090",
                    "OPENAI_API_KEY": "dummy",
                },
            },
            "goose_acp": {
                "status": "ACP stdio agent server",
                "route": "Run Goose as an ACP agent server on stdio with the DG MCP tools mounted.",
                "command": "scripts/dg_agent.sh goose-acp",
                "base_profile": "goose_mcp",
                "transport": "stdio",
                "config": str(GOOSE_MCP_PROFILE),
            },
            "goose_serve": {
                "status": "ACP HTTP/WebSocket agent server",
                "route": "Run Goose serve with the DG MCP tools mounted.",
                "command": "scripts/dg_agent.sh goose-serve -- --host 127.0.0.1 --port 3294",
                "base_profile": "goose_mcp",
                "transport": "http-websocket",
                "default_url": "http://127.0.0.1:3294",
                "config": str(GOOSE_MCP_PROFILE),
            },
            "openhands_acp": {
                "status": "ACP stdio agent server",
                "route": "Run OpenHands as an ACP stdio server with the local DG LiteLLM profile.",
                "command": "scripts/dg_agent.sh openhands-acp",
                "base_profile": "openhands",
                "transport": "stdio",
                "config": str(OPENHANDS_PROFILE),
                "env_file": str(OPENHANDS_ENV),
                "notes": "Uses `openhands acp --override-with-envs`; do not use the standalone openhands-acp entrypoint.",
            },
            "openhands_mcp": {
                "status": "OpenHands MCP tool setup",
                "route": "Configure OpenHands built-in MCP servers for DG, Repomix, and Serena in repo-local persistence.",
                "command": "scripts/dg_agent.sh openhands-mcp -- --repo /repo --reset",
                "workspace_launcher": ".dg-agent/bin/openhands-mcp --reset",
                "persistence_dir": ".dg-agent/openhands-persistence",
                "config": ".dg-agent/openhands-persistence/mcp.json",
                "servers": ["diffusiongemma-local-agent", "repomix", "serena"],
                "base_profile": "openhands",
                "notes": "Uses `openhands mcp add` instead of hand-writing OpenHands config.",
            },
            "qwen_code": {
                "status": "optional read-only terminal inspection experiment",
                "route": "Run Qwen Code CLI against the local GPU gateway; prefer the WSL MCP route, with native Windows safe-proxy fallback.",
                "command": "scripts/dg_agent.sh qwen-code -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/qwen-code --dry-run",
                "runner": str(DG_ROOT / "scripts" / "run_qwen_code_local.sh"),
                "native_windows_runner": str(DG_ROOT / "scripts" / "run_qwen_code_windows.ps1"),
                "config": str(QWEN_CODE_MCP_PROFILE),
                "workspace_config": ".dg-agent/qwen-code.mcp.json",
                "base_url": "http://127.0.0.1:4100/v1",
                "model": "diffusiongemma-local",
                "native_windows_base_url": "http://127.0.0.1:8090/v1",
                "native_windows_model": "diffusiongemma-26b-a4b-it-iq4xs-aider-local",
                "auth_type": "openai",
                "mode": "read-only inspection; edits stay on Aider/session/task",
                "mcp_servers": ["diffusiongemma-local-agent", "repomix", "serena"],
                "recommended_flags": ["--prompt \"Read path/to/file.py. Summarize ...\""],
            },
            "autogen": {
                "status": "optional external framework experiment",
                "route": "Use Microsoft AutoGen AgentChat with the local OpenAI-compatible model client profile.",
                "command": "scripts/dg_agent.sh autogen -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/autogen --dry-run",
                "config": str(AUTOGEN_PROFILE),
                "workspace_config": ".dg-agent/autogen.dg.json",
                "package": "autogen-agentchat + autogen-ext[openai]",
                "model_client": "autogen_ext.models.openai.OpenAIChatCompletionClient",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "model_info": {
                    "vision": False,
                    "function_calling": False,
                    "json_output": False,
                    "family": "unknown",
                    "structured_output": False,
                },
            },
            "smolagents": {
                "status": "optional external framework experiment",
                "route": "Use Hugging Face smolagents CodeAgent with the local OpenAI-compatible model profile.",
                "command": "scripts/dg_agent.sh smolagents -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/smolagents --dry-run",
                "config": str(SMOLAGENTS_PROFILE),
                "workspace_config": ".dg-agent/smolagents.dg.json",
                "package": "smolagents[toolkit] + openai",
                "agent": "smolagents.CodeAgent",
                "model_class": "smolagents.OpenAIModel",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "max_steps": 2,
                "notes": "Framework compatibility route; keep reliable edits on agent/session/task.",
            },
            "langgraph": {
                "status": "optional external framework experiment",
                "route": "Use LangGraph/LangChain agent graph with the local OpenAI-compatible model profile.",
                "command": "scripts/dg_agent.sh langgraph -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/langgraph --dry-run",
                "config": str(LANGGRAPH_PROFILE),
                "workspace_config": ".dg-agent/langgraph.dg.json",
                "package": "langgraph + langchain + langchain-openai",
                "agent_factory": "langchain.agents.create_agent",
                "fallback_agent_factory": "langgraph.prebuilt.create_react_agent",
                "model_class": "langchain_openai.ChatOpenAI",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "notes": "Framework compatibility route; keep reliable edits on agent/session/task.",
            },
            "crewai": {
                "status": "optional external framework experiment",
                "route": "Use CrewAI Agent/Task/Crew with the local OpenAI-compatible model profile.",
                "command": "scripts/dg_agent.sh crewai -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/crewai --dry-run",
                "config": str(CREWAI_PROFILE),
                "workspace_config": ".dg-agent/crewai.dg.json",
                "package": "crewai",
                "classes": {
                    "agent": "crewai.Agent",
                    "task": "crewai.Task",
                    "crew": "crewai.Crew",
                    "llm": "crewai.LLM",
                },
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": f"openai/{litellm_model}",
                "process": "sequential",
                "notes": "Framework compatibility route; keep reliable edits on agent/session/task.",
            },
            "open_interpreter": {
                "status": "optional external shell experiment",
                "route": "Use Open Interpreter's upstream code-execution shell with the local OpenAI-compatible model profile.",
                "command": "scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/open-interpreter --dry-run",
                "config": str(OPEN_INTERPRETER_PROFILE),
                "workspace_config": ".dg-agent/open-interpreter.dg.json",
                "package": "open-interpreter",
                "agent": "interpreter.interpreter",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": f"openai/{litellm_model}",
                "context_window": 768,
                "max_tokens": 256,
                "auto_run": False,
                "safe_mode": "ask",
                "notes": "Shell/code-execution compatibility route; keep reliable edits on agent/session/task.",
            },
            "llamaindex": {
                "status": "optional external framework experiment",
                "route": "Use LlamaIndex OpenAILike with AgentWorkflow repo tools over the local OpenAI-compatible model profile.",
                "command": "scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/llamaindex --dry-run",
                "config": str(LLAMAINDEX_PROFILE),
                "workspace_config": ".dg-agent/llamaindex.dg.json",
                "package": "llama-index-core + llama-index-llms-openai-like",
                "llm_class": "llama_index.llms.openai_like.OpenAILike",
                "agent_workflow_class": "llama_index.core.agent.workflow.AgentWorkflow",
                "agent_class": "llama_index.core.agent.workflow.ReActAgent",
                "function_agent_class": "llama_index.core.agent.workflow.FunctionAgent",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "context_window": 768,
                "max_tokens": 256,
                "is_chat_model": True,
                "is_function_calling_model": False,
                "tools": ["list_files", "read_file", "search_repo"],
                "notes": "RAG/agent framework compatibility route; keep reliable edits on agent/session/task.",
            },
            "haystack": {
                "status": "optional external RAG framework experiment",
                "route": "Use Haystack InMemoryDocumentStore and BM25 retrieval before calling the local OpenAI-compatible model profile.",
                "command": "scripts/dg_agent.sh haystack -- --repo /repo --dry-run",
                "workspace_launcher": ".dg-agent/bin/haystack --dry-run",
                "config": str(HAYSTACK_PROFILE),
                "workspace_config": ".dg-agent/haystack.dg.json",
                "package": "haystack-ai",
                "document_store": "haystack.document_stores.in_memory.InMemoryDocumentStore",
                "retriever": "haystack.components.retrievers.in_memory.InMemoryBM25Retriever",
                "generator": "haystack.components.generators.chat.OpenAIChatGenerator",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
                "top_k": 4,
                "max_files": 120,
                "max_file_chars": 4000,
                "max_tokens": 256,
                "notes": "Retrieval-first RAG route for repo Q&A; keep reliable edits on agent/session/task.",
            },
            "agent_bridge": {
                "status": "one-shot ACP bridge over OSS agent servers",
                "route": "Initialize the target repo and expose it through an upstream ACP agent server instead of writing a new agent loop.",
                "command": "scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp",
                "default_server": "opencode-acp",
                "servers": {
                    "opencode-acp": {
                        "base_profile": "opencode_acp",
                        "transport": "http",
                        "default_url": "http://127.0.0.1:3295",
                        "command": "scripts/dg_agent.sh opencode-acp -- --cwd /repo --hostname 127.0.0.1 --port 3295",
                    },
                    "goose-serve": {
                        "base_profile": "goose_serve",
                        "transport": "http-websocket",
                        "default_url": "http://127.0.0.1:3294",
                        "command": "scripts/dg_agent.sh goose-serve -- --host 127.0.0.1 --port 3294",
                    },
                    "goose-acp": {
                        "base_profile": "goose_acp",
                        "transport": "stdio",
                        "command": "scripts/dg_agent.sh goose-acp",
                    },
                    "openhands-acp": {
                        "base_profile": "openhands_acp",
                        "transport": "stdio",
                        "command": "scripts/dg_agent.sh openhands-acp",
                    },
                },
                "init": "scripts/dg_agent.sh client-init --repo /repo --client cursor",
                "workspace_launcher": ".dg-agent/bin/agent-bridge --server opencode-acp",
            },
            "agent_hub": {
                "status": "repo-local handoff for humans and external agents",
                "route": "Open .dg-agent/AGENT_HUB.md or .dg-agent/agent-hub.json to choose the strongest local wrapper for the current task.",
                "files": [".dg-agent/AGENT_HUB.md", ".dg-agent/agent-hub.json"],
                "launcher": ".dg-agent/bin/hub",
                "recommended_first_read": ".dg-agent/AGENT_HUB.md",
            },
            "client_smoke": {
                "status": "target-repo readiness smoke for external clients",
                "route": "Prepare or verify a repo before connecting Cursor, Claude, VS Code, OpenCode ACP, or Goose ACP.",
                "command": "scripts/dg_agent.sh client-smoke --repo /repo --client cursor",
                "live_command": "scripts/dg_agent.sh client-smoke --repo /repo --client cursor --live",
                "checks": ["workspace", "hub", "mcp_client_config", "agent_rules", "launchers", "optional_live_endpoints"],
                "workspace_launcher": ".dg-agent/bin/client-smoke --client cursor",
            },
            "client_report": {
                "status": "target-repo handoff report for external clients",
                "route": "Generate a portable Markdown/JSON handoff after client-init/client-smoke so external agents know which local routes are ready.",
                "command": "scripts/dg_agent.sh client-report --repo /repo --client cursor",
                "live_command": "scripts/dg_agent.sh client-report --repo /repo --client cursor --live",
                "outputs": [".dg-agent/CLIENT_HANDOFF.md", ".dg-agent/client-handoff.json"],
                "workspace_launcher": ".dg-agent/bin/client-report --client cursor",
            },
            "continue": {
                "config": str(DG_ROOT / "configs" / "client_profiles" / "continue.config.yaml"),
                "provider": "openai",
                "apiBase": litellm_base,
                "apiKey": "dummy",
                "model": litellm_model,
            },
            "cline": {
                "provider": "OpenAI Compatible",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
            },
            "roo_code": {
                "provider": "OpenAI Compatible",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
            },
            "kilo_code": {
                "provider": "OpenAI Compatible",
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": litellm_model,
            },
            "ide_clients": {
                "status": "copy-ready IDE agent client profiles",
                "route": "Use existing Continue, Cline, Roo Code, and Kilo Code clients through the local LiteLLM/OpenAI endpoint, with an optional safe proxy route for command-like tool clients.",
                "workspace_files": [
                    ".dg-agent/IDE_CLIENTS.md",
                    ".dg-agent/ide-client-snippets.json",
                    ".dg-agent/openai-compatible.local.json",
                    ".dg-agent/openai.env",
                    ".dg-agent/continue.config.yaml",
                    ".dg-agent/kilo-code.config.json",
                ],
                "clients": ["continue", "cline", "roo_code", "kilo_code"],
                "chat_endpoint": {"base_url": litellm_base, "model": litellm_model, "api_key": "dummy"},
                "safe_agent_endpoint": {"base_url": proxy_base, "model": proxy_model, "api_key": "dummy"},
                "snippets": ".dg-agent/ide-client-snippets.json",
                "handoff": ".dg-agent/IDE_CLIENTS.md",
            },
            "openhands": {
                "status": "optional external experiment",
                "route": "Use OpenHands LiteLLM Proxy provider pointed at the local LiteLLM gateway.",
                "command": "scripts/dg_agent.sh openhands -- --repo /repo --task \"...\"",
                "config": str(OPENHANDS_PROFILE),
                "env_file": str(OPENHANDS_ENV),
                "base_url": litellm_proxy_base,
                "api_key": "dummy",
                "model": f"litellm_proxy/{litellm_model}",
                "limits": {"max_input_tokens": 768, "max_output_tokens": 256},
            },
            "swe_agent": {
                "status": "optional external experiment",
                "route": "Use the LiteLLM/OpenAI-compatible model config pointed at the local LiteLLM endpoint.",
                "command": "scripts/dg_agent.sh swe-agent -- --repo /repo --task \"...\"",
                "config": str(SWE_AGENT_PROFILE),
                "model_registry": str(LITELLM_LOCAL_MODEL_REGISTRY),
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": openai_model,
                "notes": "Classic SWE-agent is maintenance-mode upstream; prefer mini_swe_agent for new experiments.",
            },
            "mini_swe_agent": {
                "status": "optional external experiment",
                "route": "Use mini-swe-agent with LiteLLM/OpenAI-compatible provider and a short step limit.",
                "command": "scripts/dg_agent.sh mini-swe-agent -- --repo /repo --task \"...\"",
                "config": str(MINI_SWE_AGENT_PROFILE),
                "model_registry": str(LITELLM_LOCAL_MODEL_REGISTRY),
                "base_url": litellm_base,
                "api_key": "dummy",
                "model": openai_model,
                "cost_tracking": "ignore_errors",
            },
            "mcp": {
                "status": "official SDK stdio tool server",
                "route": "Expose reliable DG agent commands as MCP tools for MCP-capable IDEs and OSS agents.",
                "command": "scripts/dg_agent.sh mcp",
                "config": str(MCP_SERVER_PROFILE),
                "transport": "stdio",
                "sdk": "modelcontextprotocol/python-sdk",
                "legacy_fallback": "scripts/dg_agent.sh mcp --legacy",
                "tools": [
                    "dg_task_note",
                    "dg_task_notes",
                    "dg_repo_status",
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
                    "dg_sessions",
                    "dg_session_artifact",
                    "dg_agent_runs",
                    "dg_agent_run_artifact",
                    "dg_client_smoke",
                    "dg_client_report",
                ],
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
            },
            "mcp_http": {
                "status": "official SDK streamable HTTP tool server",
                "route": "Expose the same DG MCP tools over a local HTTP endpoint for MCP clients that cannot spawn stdio servers.",
                "command": "scripts/dg_agent.sh mcp-http -- --host 127.0.0.1 --port 8765",
                "url": "http://127.0.0.1:8765/mcp",
                "transport": "streamable-http",
                "sdk": "modelcontextprotocol/python-sdk",
                "base_profile": "mcp",
                "tools": [
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
                    "dg_agent_runs",
                    "dg_agent_run_artifact",
                    "dg_client_smoke",
                    "dg_client_report",
                ],
            },
            "mcp_clients": {
                "status": "copy-ready MCP client configs",
                "route": "Mount the DG MCP stdio server in existing MCP-capable clients instead of writing a new agent loop.",
                "installer": "scripts/dg_agent.sh mcp-client-config --repo /repo --client cursor",
                "installer_with_repomix": "scripts/dg_agent.sh mcp-client-config --repo /repo --client cursor --with-repomix",
                "installer_with_serena": "scripts/dg_agent.sh mcp-client-config --repo /repo --client cursor --with-serena",
                "installer_with_all_optional": "scripts/dg_agent.sh mcp-client-config --repo /repo --client cursor --with-repomix --with-serena",
                "installer_with_oss_stack": "scripts/dg_agent.sh mcp-client-config --repo /repo --client cursor --with-oss-stack",
                "one_shot_installer": "scripts/dg_agent.sh client-init --repo /repo --client cursor",
                "recommended_bundle": {
                    "name": "dg-repomix-serena",
                    "servers": ["diffusiongemma-local-agent", "repomix", "serena"],
                    "description": "Recommended MCP bundle: DG workflow tools, upstream Repomix repository packing, and upstream Serena semantic/LSP tools.",
                },
                "server_name": "diffusiongemma-local-agent",
                "server_command": "/root/diffusiongemma-agent/scripts/run_mcp_server.sh",
                "snippets": str(MCP_CLIENT_SNIPPETS_PROFILE),
                "optional_servers": {
                    "repomix": {
                        "server_name": "repomix",
                        "command": str(DG_ROOT / "scripts" / "run_repomix_mcp.sh"),
                        "args": [],
                        "description": "Native upstream Repomix MCP server for repository packing.",
                    },
                    "serena": {
                        "server_name": "serena",
                        "command": str(DG_ROOT / "scripts" / "run_serena_mcp.sh"),
                        "args": [],
                        "description": "Native upstream Serena MCP server for semantic/LSP code tools.",
                    }
                },
                "configs": {
                    "claude_code": str(CLAUDE_CODE_MCP_PROFILE),
                    "claude_desktop": str(CLAUDE_DESKTOP_MCP_PROFILE),
                    "cursor": str(CURSOR_MCP_PROFILE),
                    "vscode": str(VSCODE_MCP_PROFILE),
                },
                "targets": {
                    "claude_code": ".mcp.json",
                    "claude_desktop": "claude_desktop_config.json",
                    "cursor": ".cursor/mcp.json",
                    "vscode": ".vscode/mcp.json",
                },
            },
            "client_init": {
                "status": "one-shot IDE/agent client bootstrap",
                "route": "Initialize .dg-agent, install the recommended DG+Repomix+Serena MCP bundle, and write client instruction files in one command.",
                "command": "scripts/dg_agent.sh client-init --repo /repo --client cursor",
                "default_bundle": "dg-repomix-serena",
                "steps": [
                    "workspace-init",
                    "mcp-client-config --with-oss-stack",
                    "agent-rules --target all",
                    "agent-commands --target all",
                ],
                "clients": ["claude-code", "claude-desktop", "cursor", "vscode"],
                "workspace_launcher": ".dg-agent/bin/client-init --client cursor",
            },
            "agent_rules": {
                "status": "copy-ready project instruction files",
                "route": "Tell existing IDE/agent clients to use DG MCP repo tools, bounded sessions, notes, and verification.",
                "installer": "scripts/dg_agent.sh agent-rules --repo /repo --target all",
                "templates": {
                    "generic": str(AGENT_INSTRUCTIONS_PROFILE),
                    "agents": str(AGENTS_RULES_PROFILE),
                    "claude": str(CLAUDE_RULES_PROFILE),
                    "copilot": str(COPILOT_RULES_PROFILE),
                    "vscode": str(VSCODE_INSTRUCTIONS_PROFILE),
                    "cursor": str(CURSOR_RULES_PROFILE),
                },
                "targets": {
                    "agents": "AGENTS.md",
                    "claude": "CLAUDE.md",
                    "copilot": ".github/copilot-instructions.md",
                    "vscode": ".github/instructions/diffusiongemma.instructions.md",
                    "cursor": ".cursor/rules/diffusiongemma-local-agent.mdc",
                },
            },
            "agent_commands": {
                "status": "repo-local workflow command kit for external agent clients",
                "route": "Expose short, reusable DG workflows as Markdown snippets plus a Claude Code project skill.",
                "installer": "scripts/dg_agent.sh agent-commands --repo /repo --target all",
                "workspace_launcher": ".dg-agent/bin/agent-commands --target all",
                "workspace_files": [
                    ".dg-agent/COMMANDS.md",
                    ".dg-agent/command-kit.json",
                    ".dg-agent/commands/dg-report.md",
                    ".dg-agent/commands/dg-smoke.md",
                    ".dg-agent/commands/dg-context.md",
                    ".dg-agent/commands/dg-plan-task.md",
                    ".dg-agent/commands/dg-agent.md",
                    ".dg-agent/commands/dg-verify.md",
                    ".dg-agent/commands/dg-mcp-handoff.md",
                    ".dg-agent/commands/dg-codex.md",
                    ".dg-agent/claude-skill/SKILL.md",
                ],
                "project_files": [".claude/skills/dg-local-agent/SKILL.md"],
            },
        },
        "repo_local_files": {
            "openai_compatible": str(DG_ROOT / "configs" / "client_profiles" / "openai-compatible.local.json"),
            "openai_env": str(DG_ROOT / "configs" / "client_profiles" / "openai.env"),
            "aider": str(AIDER_PROFILE),
            "aider_workspace": str(AIDER_WORKSPACE_PROFILE),
            "aider_model_settings": str(AIDER_MODEL_SETTINGS),
            "aider_model_metadata": str(AIDER_MODEL_METADATA),
            "continue": str(DG_ROOT / "configs" / "client_profiles" / "continue.config.yaml"),
            "openhands": str(OPENHANDS_PROFILE),
            "openhands_env": str(OPENHANDS_ENV),
            "qwen_code_mcp": str(QWEN_CODE_MCP_PROFILE),
            "autogen": str(AUTOGEN_PROFILE),
            "smolagents": str(SMOLAGENTS_PROFILE),
            "langgraph": str(LANGGRAPH_PROFILE),
            "crewai": str(CREWAI_PROFILE),
            "open_interpreter": str(OPEN_INTERPRETER_PROFILE),
            "llamaindex": str(LLAMAINDEX_PROFILE),
            "haystack": str(HAYSTACK_PROFILE),
            "swe_agent": str(SWE_AGENT_PROFILE),
            "mini_swe_agent": str(MINI_SWE_AGENT_PROFILE),
            "mcp": str(MCP_SERVER_PROFILE),
            "mcp_client_snippets": str(MCP_CLIENT_SNIPPETS_PROFILE),
            "claude_code_mcp": str(CLAUDE_CODE_MCP_PROFILE),
            "claude_desktop_mcp": str(CLAUDE_DESKTOP_MCP_PROFILE),
            "cursor_mcp": str(CURSOR_MCP_PROFILE),
            "vscode_mcp": str(VSCODE_MCP_PROFILE),
            "goose_mcp": str(GOOSE_MCP_PROFILE),
            "agent_instructions": str(AGENT_INSTRUCTIONS_PROFILE),
            "agents_rules": str(AGENTS_RULES_PROFILE),
            "claude_rules": str(CLAUDE_RULES_PROFILE),
            "copilot_rules": str(COPILOT_RULES_PROFILE),
            "vscode_instructions": str(VSCODE_INSTRUCTIONS_PROFILE),
            "cursor_rules": str(CURSOR_RULES_PROFILE),
            "codex_handoff": ".dg-agent/CODEX.md",
            "codex_config_template": ".dg-agent/codex.config.toml",
            "codex_env": ".dg-agent/codex.env",
            "agent_commands": ".dg-agent/COMMANDS.md",
            "agent_command_kit": ".dg-agent/command-kit.json",
            "claude_skill_template": ".dg-agent/claude-skill/SKILL.md",
            "openai_compatible": str(CLIENT_PROFILE_DIR / "openai-compatible.local.json"),
            "openai_env": str(CLIENT_PROFILE_DIR / "openai.env"),
            "ide_clients": ".dg-agent/IDE_CLIENTS.md",
            "ide_client_snippets": ".dg-agent/ide-client-snippets.json",
            "kilo_code_config": ".dg-agent/kilo-code.config.json",
            "litellm_model_registry": str(LITELLM_LOCAL_MODEL_REGISTRY),
            "opencode": str(DG_ROOT / "configs" / "opencode.dg.json"),
            "opencode_agent": str(OPENCODE_COMPACT_PROFILE),
            "opencode_mcp": str(OPENCODE_MCP_PROFILE),
            "litellm": str(DG_ROOT / "configs" / "litellm.dg.yaml"),
        },
    }


def client_pack_env(pack: dict[str, Any]) -> str:
    endpoint = pack["endpoints"]["litellm"]
    pairs = [
        ("OPENAI_BASE_URL", endpoint["base_url"]),
        ("OPENAI_API_KEY", endpoint["api_key"]),
        ("OPENAI_MODEL", endpoint["model"]),
        ("LITELLM_BASE_URL", endpoint["base_url"]),
        ("LITELLM_API_KEY", endpoint["api_key"]),
        ("LITELLM_MODEL", endpoint["model"]),
    ]
    pairs.extend(pack["profiles"]["aider"]["env"].items())
    pairs.extend(pack["profiles"]["goose"]["env"].items())
    pairs.extend(
        [
            ("OPENHANDS_CONFIG", pack["profiles"]["openhands"]["config"]),
            ("OPENHANDS_ENV", pack["profiles"]["openhands"]["env_file"]),
            ("QWEN_CODE_MCP_CONFIG", pack["profiles"]["qwen_code"]["config"]),
            ("QWEN_CODE_COMMAND", pack["profiles"]["qwen_code"]["command"]),
            ("AUTOGEN_CONFIG", pack["profiles"]["autogen"]["config"]),
            ("AUTOGEN_COMMAND", pack["profiles"]["autogen"]["command"]),
            ("AUTOGEN_MODEL", pack["profiles"]["autogen"]["model"]),
            ("SMOLAGENTS_CONFIG", pack["profiles"]["smolagents"]["config"]),
            ("SMOLAGENTS_COMMAND", pack["profiles"]["smolagents"]["command"]),
            ("SMOLAGENTS_MODEL", pack["profiles"]["smolagents"]["model"]),
            ("LANGGRAPH_CONFIG", pack["profiles"]["langgraph"]["config"]),
            ("LANGGRAPH_COMMAND", pack["profiles"]["langgraph"]["command"]),
            ("LANGGRAPH_MODEL", pack["profiles"]["langgraph"]["model"]),
            ("CREWAI_CONFIG", pack["profiles"]["crewai"]["config"]),
            ("CREWAI_COMMAND", pack["profiles"]["crewai"]["command"]),
            ("CREWAI_MODEL", pack["profiles"]["crewai"]["model"]),
            ("OPEN_INTERPRETER_CONFIG", pack["profiles"]["open_interpreter"]["config"]),
            ("OPEN_INTERPRETER_COMMAND", pack["profiles"]["open_interpreter"]["command"]),
            ("OPEN_INTERPRETER_MODEL", pack["profiles"]["open_interpreter"]["model"]),
            ("LLAMAINDEX_CONFIG", pack["profiles"]["llamaindex"]["config"]),
            ("LLAMAINDEX_COMMAND", pack["profiles"]["llamaindex"]["command"]),
            ("LLAMAINDEX_MODEL", pack["profiles"]["llamaindex"]["model"]),
            ("HAYSTACK_CONFIG", pack["profiles"]["haystack"]["config"]),
            ("HAYSTACK_COMMAND", pack["profiles"]["haystack"]["command"]),
            ("HAYSTACK_MODEL", pack["profiles"]["haystack"]["model"]),
            ("LLM_MODEL", pack["profiles"]["openhands"]["model"]),
            ("LLM_BASE_URL", pack["profiles"]["openhands"]["base_url"]),
            ("LLM_API_KEY", pack["profiles"]["openhands"]["api_key"]),
            ("LLM_DROP_PARAMS", "true"),
            ("LLM_DISABLE_VISION", "true"),
            ("LLM_CACHING_PROMPT", "false"),
            ("SWE_AGENT_CONFIG", pack["profiles"]["swe_agent"]["config"]),
            ("MINI_SWE_AGENT_CONFIG", pack["profiles"]["mini_swe_agent"]["config"]),
            ("DG_MCP_CONFIG", pack["profiles"]["mcp"]["config"]),
            ("DG_MCP_CLIENT_SNIPPETS", pack["profiles"]["mcp_clients"]["snippets"]),
            ("DG_CLIENT_INIT_COMMAND", pack["profiles"]["client_init"]["command"]),
            ("DG_LOCAL_AGENT_COMMAND", pack["profiles"]["local_agent"]["command"]),
            ("DG_AGENT_BRIDGE_COMMAND", pack["profiles"]["agent_bridge"]["command"]),
            ("DG_WORKSPACE_AGENT_HUB", ".dg-agent/AGENT_HUB.md"),
            ("DG_CLIENT_SMOKE_COMMAND", pack["profiles"]["client_smoke"]["command"]),
            ("DG_CLIENT_REPORT_COMMAND", pack["profiles"]["client_report"]["command"]),
            ("DG_CODEX_PROFILE_COMMAND", pack["profiles"]["codex_cli"]["installer"]),
            ("DG_CODEX_CONFIG_TEMPLATE", pack["profiles"]["codex_cli"]["workspace_files"][1]),
            ("DG_AGENT_COMMANDS_COMMAND", pack["profiles"]["agent_commands"]["installer"]),
            ("DG_IDE_CLIENTS_HANDOFF", pack["profiles"]["ide_clients"]["handoff"]),
            ("DG_IDE_CLIENT_SNIPPETS", pack["profiles"]["ide_clients"]["snippets"]),
            ("DG_SAFE_AGENT_BASE_URL", pack["profiles"]["ide_clients"]["safe_agent_endpoint"]["base_url"]),
            ("DG_SAFE_AGENT_MODEL", pack["profiles"]["ide_clients"]["safe_agent_endpoint"]["model"]),
            ("DG_AGENT_INSTRUCTIONS", pack["profiles"]["agent_rules"]["templates"]["generic"]),
            ("DG_REPO_MAP_COMMAND", "scripts/dg_agent.sh repo-map"),
            ("DG_AST_GREP_COMMAND", pack["profiles"]["ast_grep"]["native_command"]),
            ("DG_CODE_OUTLINE_COMMAND", "scripts/dg_agent.sh code-outline"),
            ("DG_SERENA_MCP_COMMAND", pack["profiles"]["serena_mcp"]["native_command"]),
            ("GOOSE_MCP_CONFIG", pack["profiles"]["goose_mcp"]["config"]),
            ("LITELLM_MODEL_REGISTRY_PATH", pack["profiles"]["mini_swe_agent"]["model_registry"]),
            ("SWE_AGENT_MODEL", pack["profiles"]["swe_agent"]["model"]),
            ("SWE_AGENT_API_BASE", pack["profiles"]["swe_agent"]["base_url"]),
        ]
    )
    seen: set[str] = set()
    lines: list[str] = []
    for key, value in pairs:
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def print_client_pack_report(pack: dict[str, Any]) -> None:
    print(pack["name"])
    print(f"default: {pack['recommended_entrypoint']['command']}")
    print(f"manifest: {pack['manifest_file']}")
    print()
    print("Endpoints:")
    for name, endpoint in pack["endpoints"].items():
        print(f"- {name}: {endpoint['base_url']} model={endpoint['model']}")
    print()
    print("Profiles:")
    for name, profile in pack["profiles"].items():
        command = profile.get("command") or profile.get("config") or profile.get("route") or profile.get("provider")
        print(f"- {name}: {command}")
    print()
    print("Limits:")
    print(f"- input tokens: {pack['limits']['max_input_tokens']}")
    print(f"- output tokens: {pack['limits']['max_output_tokens']}")


def run_client_pack(args: argparse.Namespace) -> int:
    pack = build_client_pack()
    if args.env:
        print(client_pack_env(pack), end="")
        return 0
    if args.write:
        CLIENT_PACK_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        CLIENT_PACK_MANIFEST.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(CLIENT_PACK_MANIFEST)
        return 0
    if args.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print_client_pack_report(pack)
    return 0


def ide_client_snippets_json(pack: dict[str, Any]) -> dict[str, Any]:
    chat = pack["profiles"]["ide_clients"]["chat_endpoint"]
    safe = pack["profiles"]["ide_clients"]["safe_agent_endpoint"]
    limits = pack["limits"]
    return {
        "name": "DiffusionGemma local IDE client snippets",
        "generated_by": "scripts/dg_agent.sh workspace-init",
        "guidance": [
            "Use chat_endpoint for normal chat/edit clients.",
            "Use safe_agent_endpoint for command-like tool clients that should delegate repository edits to dg_agent.sh session/task.",
            "Prefer MCP and .dg-agent/bin launchers for repository-wide context instead of expanding the model prompt.",
        ],
        "limits": limits,
        "endpoints": {
            "chat": {
                "provider": "OpenAI Compatible",
                "base_url": chat["base_url"],
                "api_key": chat["api_key"],
                "model": chat["model"],
                "max_input_tokens": limits["max_input_tokens"],
                "max_output_tokens": limits["max_output_tokens"],
            },
            "safe_agent_proxy": {
                "provider": "OpenAI Compatible",
                "base_url": safe["base_url"],
                "api_key": safe["api_key"],
                "model": safe["model"],
                "max_input_tokens": limits["max_input_tokens"],
                "max_output_tokens": limits["max_output_tokens"],
                "notes": "Use this route for clients that expose command-like tools such as execute_command(command=...).",
            },
        },
        "clients": {
            "continue": {
                "config_file": ".dg-agent/continue.config.yaml",
                "provider": "openai",
                "apiBase": chat["base_url"],
                "apiKey": chat["api_key"],
                "model": chat["model"],
                "roles": ["chat", "edit", "apply"],
            },
            "cline": {
                "api_provider": "OpenAI Compatible",
                "base_url": safe["base_url"],
                "api_key": safe["api_key"],
                "model": safe["model"],
                "fallback_chat_base_url": chat["base_url"],
                "fallback_chat_model": chat["model"],
            },
            "roo_code": {
                "api_provider": "OpenAI Compatible",
                "base_url": safe["base_url"],
                "api_key": safe["api_key"],
                "model": safe["model"],
                "fallback_chat_base_url": chat["base_url"],
                "fallback_chat_model": chat["model"],
            },
            "kilo_code": {
                "template_file": ".dg-agent/kilo-code.config.json",
                "api_provider": "OpenAI Compatible",
                "base_url": safe["base_url"],
                "api_key": safe["api_key"],
                "model": safe["model"],
                "fallback_chat_base_url": chat["base_url"],
                "fallback_chat_model": chat["model"],
            },
        },
        "mcp": {
            "recommended_bundle": ["diffusiongemma-local-agent", "repomix", "serena"],
            "config_files": [".dg-agent/mcp-client-snippets.json", ".dg-agent/cursor.mcp.json", ".dg-agent/vscode.mcp.json"],
        },
    }


def codex_config_toml(pack: dict[str, Any]) -> str:
    profile = pack["profiles"]["codex_cli"]
    return f"""# DiffusionGemma local Codex CLI profile.
# Generated by scripts/dg_agent.sh workspace-init.
# Run with:
#   export OPENAI_API_KEY=dummy
#   codex

model = "{profile["model"]}"
model_provider = "diffusiongemma-local-safe-agent"

[model_providers.diffusiongemma-local-safe-agent]
name = "DiffusionGemma Local Safe Agent Proxy"
base_url = "{profile["base_url"]}"
env_key = "{profile["api_key_env"]}"
wire_api = "{profile["wire_api"]}"

[model_providers.diffusiongemma-local-chat]
name = "DiffusionGemma Local Chat"
base_url = "{pack["endpoints"]["litellm"]["base_url"]}"
env_key = "{profile["api_key_env"]}"
wire_api = "chat"
"""


def codex_env(pack: dict[str, Any]) -> str:
    profile = pack["profiles"]["codex_cli"]
    return "\n".join(
        [
            f"{profile['api_key_env']}={profile['api_key_value']}",
            f"CODEX_MODEL={profile['model']}",
            f"CODEX_BASE_URL={profile['base_url']}",
            "",
        ]
    )


def codex_handoff_md(pack: dict[str, Any]) -> str:
    profile = pack["profiles"]["codex_cli"]
    return f"""# DG Codex CLI Profile

Use this when you want Codex CLI to talk to the local DiffusionGemma agent
stack through an OpenAI-compatible endpoint.

## Install

```bash
.dg-agent/bin/codex-profile --target all
```

This writes `.codex/config.toml` from `.dg-agent/codex.config.toml`.

## Environment

```bash
source .dg-agent/codex.env
```

The key is `dummy`; the local proxy only needs the header shape.

## Default Route

```text
base_url: {profile["base_url"]}
model: {profile["model"]}
wire_api: {profile["wire_api"]}
```

Use the safe agent proxy route for command-like workflows. For plain chat,
switch `model_provider` in `.codex/config.toml` to
`diffusiongemma-local-chat`.
"""


def kilo_code_config_json(pack: dict[str, Any]) -> dict[str, Any]:
    snippets = ide_client_snippets_json(pack)
    safe = snippets["endpoints"]["safe_agent_proxy"]
    chat = snippets["endpoints"]["chat"]
    limits = snippets["limits"]
    return {
        "description": "Kilo Code openai-compatible custom provider template for the local DiffusionGemma stack. Copy the relevant provider/model entries into Kilo Code config if the UI cannot import this file directly.",
        "recommended": "diffusiongemma-local-safe-agent",
        "providers": {
            "diffusiongemma-local-safe-agent": {
                "type": "openai-compatible",
                "name": "DiffusionGemma Local Safe Agent Proxy",
                "baseUrl": safe["base_url"],
                "apiKey": safe["api_key"],
                "model": safe["model"],
                "limit": {
                    "context": limits["max_input_tokens"],
                    "output": limits["max_output_tokens"],
                },
                "notes": "Prefer this profile when Kilo Code will request command-like tool execution.",
            },
            "diffusiongemma-local-chat": {
                "type": "openai-compatible",
                "name": "DiffusionGemma Local Chat",
                "baseUrl": chat["base_url"],
                "apiKey": chat["api_key"],
                "model": chat["model"],
                "limit": {
                    "context": limits["max_input_tokens"],
                    "output": limits["max_output_tokens"],
                },
                "notes": "Use for simple chat/edit flows that do not need command delegation.",
            },
        },
    }


def ide_clients_md(pack: dict[str, Any]) -> str:
    snippets = ide_client_snippets_json(pack)
    chat = snippets["endpoints"]["chat"]
    safe = snippets["endpoints"]["safe_agent_proxy"]
    limits = snippets["limits"]
    return f"""# DG IDE Client Profiles

Use these profiles for existing IDE agents instead of writing a new client loop.
Keep repo context small; use `.dg-agent/bin/context`, MCP, Repomix, and Serena
for repository navigation.

## Routes

| Route | Base URL | Model | Use |
| --- | --- | --- | --- |
| Chat/edit | `{chat["base_url"]}` | `{chat["model"]}` | Continue and simple OpenAI-compatible chat/edit |
| Safe agent proxy | `{safe["base_url"]}` | `{safe["model"]}` | Cline/Roo/Kilo-style command-like tool delegation |

Limits: `{limits["max_input_tokens"]}` input tokens, `{limits["max_output_tokens"]}` output tokens.

## Continue

Use `.dg-agent/continue.config.yaml`.

## Cline

```text
API provider: OpenAI Compatible
Base URL: {safe["base_url"]}
API key: {safe["api_key"]}
Model: {safe["model"]}
```

For simple chat-only use, switch Base URL to `{chat["base_url"]}` and Model to
`{chat["model"]}`.

## Roo Code

```text
API provider: OpenAI Compatible
Base URL: {safe["base_url"]}
API key: {safe["api_key"]}
Model: {safe["model"]}
```

For simple chat-only use, switch Base URL to `{chat["base_url"]}` and Model to
`{chat["model"]}`.

## Kilo Code

Use `.dg-agent/kilo-code.config.json` as the custom OpenAI-compatible provider
template.

## Qwen Code

```bash
.dg-agent/bin/qwen-code --dry-run
```

Uses the unified Qwen Code launcher. On Git Bash/WSL it mounts the DG MCP,
Repomix, and Serena servers through `.dg-agent/qwen-code.mcp.json`; the native
Windows fallback remains read-only on the safe GPU gateway. Use an explicit file
path in the prompt and keep modifications on the Aider/session path.

## MCP

For clients that can mount MCP servers, prefer `.dg-agent/mcp-client-snippets.json`
or run:

```bash
.dg-agent/bin/mcp-client-config --client cursor --with-oss-stack
```

Machine-readable snippets: `.dg-agent/ide-client-snippets.json`.
"""


def workspace_agent_hub_json(repo: Path, pack: dict[str, Any]) -> dict[str, Any]:
    proxy = pack["endpoints"]["aider_proxy"]
    litellm = pack["endpoints"]["litellm"]
    return {
        "name": "DG local agent hub",
        "repo": str(repo),
        "model_limits": pack["limits"],
        "endpoints": {
            "litellm": litellm,
            "aider_proxy": proxy,
        },
        "recommended_routes": [
            {
                "id": "safe_code_edit",
                "use_for": "file-level or small multi-file code changes with verification",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh agent --repo {repo} --task \"...\" --file path",
                "why": "bounded context, artifacted session path, verification, rollback-capable task runner",
            },
            {
                "id": "reviewable_plan",
                "use_for": "multi-step changes where the plan should be inspected first",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh plan --repo {repo} --task \"...\" --file path --auto-test",
                "next": f"{DG_ROOT}/scripts/dg_agent.sh task --repo {repo} --plan plan.json --rollback-on-failure",
            },
            {
                "id": "mcp_ide",
                "use_for": "MCP-capable IDEs and agent shells",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh client-init --repo {repo} --client cursor",
                "openhands_command": f"{DG_ROOT}/scripts/dg_agent.sh openhands-mcp -- --repo {repo} --reset",
                "servers": ["diffusiongemma-local-agent", "repomix", "serena"],
            },
            {
                "id": "acp_agent_server",
                "use_for": "ACP-capable clients that need a running local agent server",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh agent-bridge --repo {repo} --server opencode-acp",
                "start": f"{DG_ROOT}/scripts/dg_agent.sh agent-bridge --repo {repo} --server opencode-acp --start",
                "url": "http://127.0.0.1:3295",
                "alternatives": [
                    f"{DG_ROOT}/scripts/dg_agent.sh agent-bridge --repo {repo} --server goose-acp",
                    f"{DG_ROOT}/scripts/dg_agent.sh agent-bridge --repo {repo} --server openhands-acp",
                ],
            },
            {
                "id": "qwen_code_terminal",
                "use_for": "Qwen Code read-only terminal inspection with an explicit file path",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh qwen-code -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/qwen-code --dry-run",
            },
            {
                "id": "autogen_framework",
                "use_for": "AutoGen AgentChat Python framework experiments over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh autogen -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/autogen --dry-run",
            },
            {
                "id": "smolagents_codeagent",
                "use_for": "Hugging Face smolagents CodeAgent experiments over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh smolagents -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/smolagents --dry-run",
            },
            {
                "id": "langgraph_agent",
                "use_for": "LangGraph/LangChain graph-agent experiments over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh langgraph -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/langgraph --dry-run",
            },
            {
                "id": "crewai_crew",
                "use_for": "CrewAI multi-agent crew experiments over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh crewai -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/crewai --dry-run",
            },
            {
                "id": "open_interpreter_shell",
                "use_for": "Open Interpreter code-execution shell experiments over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh open-interpreter -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/open-interpreter --dry-run",
            },
            {
                "id": "llamaindex_framework",
                "use_for": "LlamaIndex RAG/ReActAgent experiments over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh llamaindex -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/llamaindex --dry-run",
            },
            {
                "id": "haystack_rag",
                "use_for": "Haystack BM25 RAG repository Q&A over the local OpenAI-compatible model profile",
                "command": f"{DG_ROOT}/scripts/dg_agent.sh haystack -- --repo {repo} --dry-run",
                "workspace_launcher": ".dg-agent/bin/haystack --dry-run",
            },
            {
                "id": "read_only_context",
                "use_for": "small-context inspection before asking the model",
                "commands": [
                    f"{DG_ROOT}/scripts/dg_agent.sh rag --repo {repo} --task \"...\" --print-context --max-files 3",
                    f"{DG_ROOT}/scripts/dg_agent.sh repo-map --repo {repo} --map-tokens 512",
                    f"{DG_ROOT}/scripts/dg_agent.sh code-outline --repo {repo} --lang python --json",
                ],
            },
        ],
        "repo_local_files": {
            "hub_markdown": ".dg-agent/AGENT_HUB.md",
            "hub_json": ".dg-agent/agent-hub.json",
            "client_handoff_markdown": ".dg-agent/CLIENT_HANDOFF.md",
            "client_handoff_json": ".dg-agent/client-handoff.json",
            "client_pack": ".dg-agent/client-pack.json",
            "env": ".dg-agent/env.sh",
            "mcp_snippets": ".dg-agent/mcp-client-snippets.json",
            "rules": ".dg-agent/agent-instructions.md",
        },
        "fallback_order": [
            "agent/session/task for real edits",
            "MCP tools for IDE-driven context and orchestration",
            "Aider direct profile for single-file edits",
            "LiteLLM/OpenAI-compatible endpoint for manual chat only",
        ],
    }


def workspace_agent_hub_md(repo: Path, pack: dict[str, Any]) -> str:
    data = workspace_agent_hub_json(repo, pack)
    litellm = data["endpoints"]["litellm"]
    proxy = data["endpoints"]["aider_proxy"]
    return f"""# DG Local Agent Hub

Repo:

```text
{repo}
```

Use this file as the first handoff for humans, IDE agents, and OSS agent shells.
The local model has a small effective context, so prefer tool-backed routes over
raw chat.

## Best Routes

| Need | Route |
| --- | --- |
| Safe code edit | `.dg-agent/bin/agent --task "..." --file path` |
| Review a plan first | `.dg-agent/bin/plan --task "..." --file path --auto-test` then `.dg-agent/bin/task --plan plan.json --rollback-on-failure` |
| MCP-capable IDE/client | `.dg-agent/bin/client-init --client cursor` |
| ACP-capable client/server | `.dg-agent/bin/agent-bridge --server opencode-acp` |
| Qwen Code terminal agent | `.dg-agent/bin/qwen-code --dry-run` |
| AutoGen AgentChat framework | `.dg-agent/bin/autogen --dry-run` |
| smolagents CodeAgent framework | `.dg-agent/bin/smolagents --dry-run` |
| LangGraph graph-agent framework | `.dg-agent/bin/langgraph --dry-run` |
| CrewAI multi-agent framework | `.dg-agent/bin/crewai --dry-run` |
| Open Interpreter shell | `.dg-agent/bin/open-interpreter --dry-run` |
| LlamaIndex RAG/agent framework | `.dg-agent/bin/llamaindex --dry-run` |
| Haystack BM25 RAG pipeline | `.dg-agent/bin/haystack --dry-run` |
| Read-only repo context | `.dg-agent/bin/rag --task "..." --print-context --max-files 3` |
| Symbol/navigation context | `.dg-agent/bin/repo-map --map-tokens 512` and `.dg-agent/bin/code-outline --lang python --json` |
| Verify changes | `.dg-agent/bin/verify --file path` |

## Endpoints

```text
LiteLLM/OpenAI-compatible:
  base_url: {litellm["base_url"]}
  api_key: {litellm["api_key"]}
  model: {litellm["model"]}

Aider/OpenCode/Goose proxy:
  base_url: {proxy["base_url"]}
  api_key: {proxy["api_key"]}
  model: {proxy["model"]}
```

## MCP And ACP

```bash
.dg-agent/bin/mcp --list-tools
.dg-agent/bin/mcp-client-config --client cursor --with-oss-stack
.dg-agent/bin/serena-mcp --help-local
.dg-agent/bin/agent-bridge --server opencode-acp
.dg-agent/bin/agent-bridge --server goose-serve
.dg-agent/bin/agent-bridge --server openhands-acp
.dg-agent/bin/qwen-code --dry-run
```

Default MCP bundle: `diffusiongemma-local-agent`, `repomix`, `serena`.

Default ACP endpoint:

```text
http://127.0.0.1:3295
```

## Rules

- Use `agent/session/task` for real edits.
- Use MCP tools and repo-pack/repo-map/code-outline before asking the model to reason over repo structure.
- Keep prompts file-scoped when possible; pass explicit `--file` hints.
- Use `verify` or `task --rollback-on-failure` before treating edits as done.
- Avoid raw generic chat for code changes; route through the proxy-backed wrappers.

Machine-readable version: `.dg-agent/agent-hub.json`.
"""


def agent_command_specs(repo: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": "dg-report",
            "title": "Generate Client Handoff",
            "use_for": "prepare an IDE or agent session before work",
            "command": ".dg-agent/bin/client-report --client cursor --live",
            "mcp": "dg_client_report(repo='.', client='cursor', live=True)",
            "outputs": [".dg-agent/CLIENT_HANDOFF.md", ".dg-agent/client-handoff.json"],
        },
        {
            "id": "dg-smoke",
            "title": "Check Client Readiness",
            "use_for": "validate MCP config, rules, launchers, and live endpoints",
            "command": ".dg-agent/bin/client-smoke --client cursor --live",
            "mcp": "dg_client_smoke(repo='.', client='cursor', live=True)",
        },
        {
            "id": "dg-context",
            "title": "Collect Bounded Context",
            "use_for": "inspect a repo without pasting large context into the model",
            "commands": [
                '.dg-agent/bin/rag --task "..." --print-context --max-files 3',
                ".dg-agent/bin/repo-map --map-tokens 512",
                ".dg-agent/bin/code-outline --lang python --json",
            ],
            "mcp": "dg_rag_context + dg_repo_map + dg_code_outline",
        },
        {
            "id": "dg-plan-task",
            "title": "Plan Then Execute",
            "use_for": "review a multi-step change before applying it",
            "commands": [
                '.dg-agent/bin/plan --task "..." --file path --auto-test --out plan.json',
                ".dg-agent/bin/task --plan plan.json --rollback-on-failure",
            ],
            "mcp": "dg_plan -> dg_task",
        },
        {
            "id": "dg-agent",
            "title": "One-Shot Bounded Edit",
            "use_for": "small file-level changes with artifacts and verification",
            "command": '.dg-agent/bin/agent --task "..." --file path',
            "mcp": "dg_session(repo='.', task='...', files=['path'], auto_test=True)",
        },
        {
            "id": "dg-verify",
            "title": "Verify Current Changes",
            "use_for": "run or infer deterministic verification",
            "command": ".dg-agent/bin/verify --file path",
            "mcp": "dg_verify(repo='.', files=['path'])",
        },
        {
            "id": "dg-mcp-handoff",
            "title": "Use MCP Handoff",
            "use_for": "let an MCP-capable client bootstrap itself",
            "commands": [
                "call MCP tool dg_client_report",
                "read MCP resource dg://client-handoff",
                "read MCP resource dg://client-handoff/markdown",
            ],
            "mcp": "dg_client_report + dg://client-handoff",
        },
        {
            "id": "dg-codex",
            "title": "Install Codex CLI Profile",
            "use_for": "let Codex CLI use the local safe agent proxy",
            "command": ".dg-agent/bin/codex-profile --target all",
            "outputs": [".codex/config.toml"],
            "mcp": "not needed; Codex reads .codex/config.toml",
        },
    ]


def agent_command_kit_json(repo: Path, pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "DG local agent command kit",
        "repo": str(repo),
        "generated_by": "scripts/dg_agent.sh workspace-init",
        "model_limits": pack["limits"],
        "preferred_order": [
            "dg-report",
            "dg-context",
            "dg-plan-task",
            "dg-verify",
        ],
        "commands": agent_command_specs(repo),
        "project_installers": {
            "all": ".dg-agent/bin/agent-commands --target all",
            "claude_skill": ".dg-agent/bin/agent-commands --target claude-skill",
        },
        "mcp": {
            "tools": ["dg_client_smoke", "dg_client_report", "dg_rag_context", "dg_plan", "dg_task", "dg_session", "dg_verify"],
            "resources": [
                "dg://agent-hub",
                "dg://agent-hub/markdown",
                "dg://command-kit",
                "dg://command-kit/markdown",
                "dg://ide-clients",
                "dg://ide-clients/markdown",
                "dg://codex-profile",
                "dg://codex-profile/config",
                "dg://client-handoff",
                "dg://client-handoff/markdown",
            ],
        },
    }


def agent_command_md(item: dict[str, Any]) -> str:
    commands = item.get("commands") or [item.get("command", "")]
    command_lines = "\n".join(command for command in commands if command)
    outputs = "\n".join(f"- `{path}`" for path in item.get("outputs", [])) or "- none"
    return f"""# {item["title"]}

Use for: {item["use_for"]}

```bash
{command_lines}
```

MCP route:

```text
{item.get("mcp", "")}
```

Outputs:

{outputs}
"""


def agent_commands_md(repo: Path, pack: dict[str, Any]) -> str:
    specs = agent_command_specs(repo)
    rows = "\n".join(
        f"| `{item['id']}` | {item['use_for']} | `{(item.get('command') or (item.get('commands') or [''])[0])}` |"
        for item in specs
    )
    return f"""# DG Agent Command Kit

Repo:

```text
{repo}
```

Use these short workflows instead of raw chat. They are designed for small local
model context and route external clients through repo tools, MCP, and verified
agent sessions.

| Command | Use For | First Step |
| --- | --- | --- |
{rows}

## Install Project Commands

```bash
.dg-agent/bin/agent-commands --target all
```

This installs `.claude/skills/dg-local-agent/SKILL.md` for Claude Code while
keeping the generic command kit under `.dg-agent/`.

## MCP First

For MCP-capable clients, prefer:

```text
dg_client_report -> dg://client-handoff -> dg_rag_context/dg_plan/dg_session/dg_verify
```
"""


def claude_skill_md(repo: Path) -> str:
    return f"""---
name: dg-local-agent
description: Use the local DiffusionGemma agent stack for bounded repo context, planning, edits, verification, and client handoff.
---

# DG Local Agent Skill

Use this skill when working in this repository with the local DiffusionGemma
agent stack.

Repo:

```text
{repo}
```

Start every new task with one of these routes:

```bash
.dg-agent/bin/client-report --client cursor --live
.dg-agent/bin/rag --task "..." --print-context --max-files 3
.dg-agent/bin/plan --task "..." --file path --auto-test --out plan.json
.dg-agent/bin/task --plan plan.json --rollback-on-failure
.dg-agent/bin/agent --task "..." --file path
.dg-agent/bin/verify --file path
```

If MCP is available, use these tools/resources first:

```text
dg_client_report
dg://agent-hub
dg://agent-hub/markdown
dg://command-kit
dg://command-kit/markdown
dg://ide-clients
dg://ide-clients/markdown
dg://codex-profile
dg://codex-profile/config
dg://client-handoff
dg://client-handoff/markdown
dg_rag_context
dg_plan
dg_task
dg_session
dg_verify
```

Rules:

- Prefer `.dg-agent/bin/client-report --client cursor --live` before attaching a new external client.
- Prefer bounded retrieval (`rag`, `repo-map`, `code-outline`, `dg_rag_context`) before asking the model to reason over code.
- Prefer `plan -> task --rollback-on-failure` for multi-step edits.
- Prefer `agent` or `dg_session` for small file-level edits.
- Always verify with `.dg-agent/bin/verify` or `dg_verify` before treating work as done.
- Do not paste the whole repository into the model; use the repo-local tools.
"""


def workspace_readme(repo: Path) -> str:
    return f"""# DG Local Agent Workspace

Target repo:

```text
{repo}
```

Default coding-agent command:

```bash
/root/diffusiongemma-agent/scripts/dg_agent.sh agent \\
  --repo {repo} \\
  --task "..." \\
  --file path/to/file
```

Load local client environment:

```bash
set -a
. .dg-agent/env.sh
set +a
```

Useful commands:

```bash
/root/diffusiongemma-agent/scripts/dg_agent.sh context --repo {repo} --task "..." --max-files 3
/root/diffusiongemma-agent/scripts/dg_agent.sh rag --repo {repo} --task "..." --print-context --max-files 3
/root/diffusiongemma-agent/scripts/dg_agent.sh repo-pack --repo {repo} --include "src/**" --style markdown --stdout
/root/diffusiongemma-agent/scripts/dg_agent.sh repo-map --repo {repo} --map-tokens 512
/root/diffusiongemma-agent/scripts/dg_agent.sh ast-grep --repo {repo} --lang python --pattern 'return $X' --json
/root/diffusiongemma-agent/scripts/dg_agent.sh code-outline --repo {repo} --lang python --json
/root/diffusiongemma-agent/scripts/dg_agent.sh client-init --repo {repo} --client cursor
/root/diffusiongemma-agent/scripts/dg_agent.sh client-smoke --repo {repo} --client cursor
/root/diffusiongemma-agent/scripts/dg_agent.sh client-report --repo {repo} --client cursor --live
/root/diffusiongemma-agent/scripts/dg_agent.sh agent-commands --repo {repo} --target all
/root/diffusiongemma-agent/scripts/dg_agent.sh codex-profile --repo {repo} --target all
/root/diffusiongemma-agent/scripts/dg_agent.sh agent-bridge --repo {repo} --server opencode-acp
/root/diffusiongemma-agent/scripts/dg_agent.sh agent-bridge --repo {repo} --server openhands-acp
/root/diffusiongemma-agent/scripts/dg_agent.sh openhands-mcp -- --repo {repo} --reset
/root/diffusiongemma-agent/scripts/dg_agent.sh qwen-code -- --repo {repo} --dry-run
/root/diffusiongemma-agent/scripts/dg_agent.sh plan --repo {repo} --task "..." --file path --auto-test
/root/diffusiongemma-agent/scripts/dg_agent.sh verify --repo {repo} --file path
/root/diffusiongemma-agent/scripts/dg_agent.sh capabilities --latest
/root/diffusiongemma-agent/scripts/dg_agent.sh sessions list
/root/diffusiongemma-agent/scripts/dg_agent.sh agent-runs list
/root/diffusiongemma-agent/scripts/dg_agent.sh agent-runs artifact transcript --latest
```

Repo-local launchers:

```bash
.dg-agent/bin/status
.dg-agent/bin/doctor
.dg-agent/bin/up
.dg-agent/bin/down
.dg-agent/bin/preflight --task "..." --file path/to/file
.dg-agent/bin/capabilities --latest
.dg-agent/bin/plan --task "..." --file path/to/file --auto-test
.dg-agent/bin/edit --task "..." --file path/to/file --auto-test
.dg-agent/bin/task --plan plan.json --rollback-on-failure
.dg-agent/bin/supervisor --task "..." --file path/to/file
.dg-agent/bin/web --port 3284
.dg-agent/bin/run --task "..." --file path/to/file --start
.dg-agent/bin/agent --task "..." --file path/to/file
.dg-agent/bin/context --task "..." --max-files 3
.dg-agent/bin/rag --task "..." --print-context --max-files 3
.dg-agent/bin/repo-pack --include "src/**" --style markdown --stdout
.dg-agent/bin/repo-map --map-tokens 512
.dg-agent/bin/ast-grep --lang python --pattern 'return $X' --json
.dg-agent/bin/code-outline --lang python --json
.dg-agent/bin/client-init --client cursor
.dg-agent/bin/client-smoke --client cursor
.dg-agent/bin/client-report --client cursor --live
.dg-agent/bin/agent-commands --target all
.dg-agent/bin/codex-profile --target all
.dg-agent/bin/agent-bridge --server opencode-acp
.dg-agent/bin/agent-bridge --server openhands-acp
.dg-agent/bin/hub
.dg-agent/bin/verify --file path/to/file
.dg-agent/bin/sessions list
.dg-agent/bin/agent-runs list
.dg-agent/bin/agent-runs artifact transcript --latest
.dg-agent/bin/aider --help
.dg-agent/bin/aider app.py --message "Make the smallest patch"
.dg-agent/bin/opencode --help
.dg-agent/bin/opencode-agent --help
.dg-agent/bin/opencode-mcp --help
.dg-agent/bin/opencode-acp --help
.dg-agent/bin/goose --help
.dg-agent/bin/goose-mcp --help-local
.dg-agent/bin/goose-acp --help
.dg-agent/bin/goose-serve --help
.dg-agent/bin/openhands --help-local
.dg-agent/bin/openhands-acp --help-local
.dg-agent/bin/openhands-mcp --reset
.dg-agent/bin/qwen-code --dry-run
.dg-agent/bin/autogen --dry-run
.dg-agent/bin/smolagents --dry-run
.dg-agent/bin/langgraph --dry-run
.dg-agent/bin/crewai --dry-run
.dg-agent/bin/open-interpreter --dry-run
.dg-agent/bin/llamaindex --dry-run
.dg-agent/bin/haystack --dry-run
.dg-agent/bin/swe-agent --help-local
.dg-agent/bin/mini-swe-agent --help-local
.dg-agent/bin/mini-swe-run --task "..." --dry-run
.dg-agent/bin/mini-swe-runs list
.dg-agent/bin/mcp --list-tools
.dg-agent/bin/mcp-http --help-local
.dg-agent/bin/serena-mcp --help-local
.dg-agent/bin/mcp-client-config --client cursor
.dg-agent/bin/mcp-client-config --client cursor --with-serena
.dg-agent/bin/mcp-client-config --client cursor --with-oss-stack
.dg-agent/bin/agent-rules --target all
```

OpenAI-compatible endpoint:

```text
base_url: http://127.0.0.1:4100/v1
api_key: dummy
model: diffusiongemma-local
```

Aider/OpenCode/Goose local proxy:

```text
base_url: http://127.0.0.1:8090/v1
api_key: dummy
model: diffusiongemma-26b-a4b-it-iq4xs-aider-local
```

Files in this directory:

- `client-pack.json`: full local profile manifest
- `AGENT_HUB.md` and `agent-hub.json`: first-read handoff for humans and external agents
- `COMMANDS.md`, `command-kit.json`, and `commands/`: reusable short workflows for external agents
- `claude-skill/SKILL.md`: Claude Code project skill template installed by `agent-commands`
- `CODEX.md`, `codex.config.toml`, and `codex.env`: Codex CLI local model profile template installed by `codex-profile`
- `IDE_CLIENTS.md`, `ide-client-snippets.json`, `openai-compatible.local.json`, `openai.env`, and `kilo-code.config.json`: copy-ready Continue/Cline/Roo/Kilo/OpenAI-compatible profiles
- `env.sh`: shell vars for OpenAI-compatible clients, Aider, and Goose
- `aider.dg-fast.conf.yml`: upstream Aider config for the local DG proxy
- `aider.dg-model-settings.yml` and `aider.dg-model-metadata.json`: Aider local model metadata
- `continue.config.yaml`: Continue profile copy
- `opencode.dg.json`: OpenCode profile copy
- `opencode.dg-agent.json`: compact OpenCode profile that delegates its single Bash tool to the verified DG workflow
- `opencode.dg-mcp.json`: OpenCode profile copy with DG MCP and native Repomix MCP servers
- `goose-mcp.dg.yaml`: Goose profile copy with the DG MCP stdio extension
- `mcp-client-snippets.json`: copy-ready MCP config snippets for Claude Code, Claude Desktop, Cursor, and VS Code
- `claude-code.mcp.json`: project `.mcp.json` template for Claude Code
- `claude-desktop-mcp.json`: Claude Desktop `mcpServers` template
- `cursor.mcp.json`: Cursor `.cursor/mcp.json` template
- `vscode.mcp.json`: VS Code `.vscode/mcp.json` template
- `agent-instructions.md`: generic DG/MCP agent rules
- `AGENTS.dg.md`: block template for `AGENTS.md`
- `CLAUDE.dg.md`: block template for `CLAUDE.md`
- `copilot-instructions.dg.md`: block template for GitHub Copilot instructions
- `diffusiongemma.instructions.md`: VS Code instructions template
- `cursor-rules.dg.mdc`: Cursor rules template
- `openhands.dg.toml` and `openhands.env`: OpenHands LiteLLM Proxy profile
- `bin/openhands-acp`: OpenHands ACP stdio server launcher using `openhands acp`
- `bin/openhands-mcp`: OpenHands MCP setup for DG, Repomix, and Serena servers
- `qwen-code.mcp.json` and `bin/qwen-code`: Qwen Code launcher with WSL MCP route and read-only native Windows fallback
- `autogen.dg.json` and `bin/autogen`: Microsoft AutoGen AgentChat profile
- `smolagents.dg.json` and `bin/smolagents`: Hugging Face smolagents CodeAgent profile
- `langgraph.dg.json` and `bin/langgraph`: LangGraph/LangChain graph-agent profile
- `crewai.dg.json` and `bin/crewai`: CrewAI Agent/Task/Crew profile
- `open-interpreter.dg.json` and `bin/open-interpreter`: Open Interpreter code-execution shell profile
- `llamaindex.dg.json` and `bin/llamaindex`: LlamaIndex OpenAILike/AgentWorkflow profile
- `haystack.dg.json` and `bin/haystack`: Haystack BM25 RAG profile
- `swe-agent.dg.yaml`: classic SWE-agent LiteLLM/OpenAI-compatible profile
- `mini-swe-agent.dg.yaml`: mini-swe-agent profile with short local loop limits
- `mcp-server.json`: MCP stdio server profile for MCP-capable IDEs and wrappers
- `bin/mcp-http`: streamable HTTP MCP server launcher for clients that cannot spawn stdio
- `bin/agent-runs`: preserved high-level `agent` run reports and transcripts
- `bin/serena-mcp`: upstream Serena MCP launcher for semantic/LSP code tools
- `litellm-local-model-registry.json`: tiny-cost local model registry for SWE-style tools
- `bin/`: repo-local launchers for the local DG wrapper stack
"""


def workspace_launcher(name: str) -> str:
    dg = shlex.quote(str(DG_ROOT))
    if name == "run":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh run --repo "$REPO" "$@"
"""
    if name == "agent":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh agent --repo "$REPO" "$@"
"""
    if name == "autonomous":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh autonomous -- --repo "$REPO" "$@"
"""
    if name == "context":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh context --repo "$REPO" "$@"
"""
    if name == "rag":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh rag --repo "$REPO" "$@"
"""
    if name == "repo-pack":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh repo-pack --repo "$REPO" "$@"
"""
    if name == "repo-map":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh repo-map --repo "$REPO" "$@"
"""
    if name == "ast-grep":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh ast-grep --repo "$REPO" "$@"
"""
    if name == "code-outline":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh code-outline --repo "$REPO" "$@"
"""
    if name == "client-init":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh client-init --repo "$REPO" "$@"
"""
    if name == "client-smoke":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh client-smoke --repo "$REPO" "$@"
"""
    if name == "client-report":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh client-report --repo "$REPO" "$@"
"""
    if name == "agent-commands":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh agent-commands --repo "$REPO" "$@"
"""
    if name == "codex-profile":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh codex-profile --repo "$REPO" "$@"
"""
    if name == "agent-bridge":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh agent-bridge --repo "$REPO" "$@"
"""
    if name == "hub":
        return """#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${1:-}" == "--json" ]]; then
  exec cat "$REPO/.dg-agent/agent-hub.json"
fi
exec cat "$REPO/.dg-agent/AGENT_HUB.md"
"""
    if name == "plan":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh plan --repo "$REPO" "$@"
"""
    if name == "edit":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh edit --repo "$REPO" "$@"
"""
    if name == "task":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh task --repo "$REPO" "$@"
"""
    if name == "verify":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh verify --repo "$REPO" "$@"
"""
    if name == "status":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh status "$@"
"""
    if name == "doctor":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh doctor "$@"
"""
    if name == "up":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh up "$@"
"""
    if name == "down":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh down "$@"
"""
    if name == "preflight":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh preflight --repo "$REPO" "$@"
"""
    if name == "capabilities":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh capabilities "$@"
"""
    if name == "sessions":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh sessions "$@"
"""
    if name == "agent-runs":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh agent-runs "$@"
"""
    if name == "supervisor":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
if [[ "${{1:-}}" == "-h" || "${{1:-}}" == "--help" ]]; then
  exec {dg}/scripts/run_supervisor_agent.sh --help
fi
exec {dg}/scripts/dg_agent.sh supervisor --repo "$REPO" "$@"
"""
    if name == "web":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh web -- --repo "$REPO" "$@"
"""
    if name == "aider":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_aider_local.sh --repo "$REPO" "$@"
"""
    if name == "opencode":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/dg_agent.sh opencode -- "$@"
"""
    if name == "opencode-agent":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/dg_agent.sh opencode-agent -- "$@"
"""
    if name == "opencode-mcp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/dg_agent.sh opencode-mcp -- "$@"
"""
    if name == "opencode-acp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/dg_agent.sh opencode-acp -- "$@"
"""
    if name == "goose":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/run_goose_local.sh "$@"
"""
    if name == "goose-mcp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/run_goose_mcp_local.sh "$@"
"""
    if name == "goose-acp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/run_goose_mcp_local.sh --acp "$@"
"""
    if name == "goose-serve":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/run_goose_mcp_local.sh --serve "$@"
"""
    if name == "openhands":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_openhands_local.sh --repo "$REPO" "$@"
"""
    if name == "openhands-acp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/run_openhands_acp_local.sh --repo "$REPO" "$@"
"""
    if name == "openhands-mcp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_openhands_mcp_setup.sh --repo "$REPO" "$@"
"""
    if name == "qwen-code":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh qwen-code -- --repo "$REPO" "$@"
"""
    if name == "autogen":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_autogen_local.sh --repo "$REPO" "$@"
"""
    if name == "smolagents":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_smolagents_local.sh --repo "$REPO" "$@"
"""
    if name == "langgraph":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_langgraph_local.sh --repo "$REPO" "$@"
"""
    if name == "crewai":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_crewai_local.sh --repo "$REPO" "$@"
"""
    if name == "open-interpreter":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_open_interpreter_local.sh --repo "$REPO" "$@"
"""
    if name == "llamaindex":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_llamaindex_local.sh --repo "$REPO" "$@"
"""
    if name == "haystack":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_haystack_local.sh --repo "$REPO" "$@"
"""
    if name == "swe-agent":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_swe_agent_local.sh --repo "$REPO" "$@"
"""
    if name == "mini-swe-agent":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/run_mini_swe_agent_local.sh --repo "$REPO" "$@"
"""
    if name == "mini-swe-run":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh mini-swe-run --repo "$REPO" "$@"
"""
    if name == "mini-swe-runs":
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec {dg}/scripts/dg_agent.sh mini-swe-runs "$@"
"""
    if name == "mcp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
export DG_MCP_REPO="$REPO"
exec {dg}/scripts/dg_agent.sh mcp "$@"
"""
    if name == "mcp-http":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
export DG_MCP_REPO="$REPO"
exec {dg}/scripts/run_mcp_http_server.sh "$@"
"""
    if name == "serena-mcp":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$REPO"
exec {dg}/scripts/run_serena_mcp.sh "$@"
"""
    if name == "mcp-client-config":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh mcp-client-config --repo "$REPO" "$@"
"""
    if name == "agent-rules":
        return f"""#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
exec {dg}/scripts/dg_agent.sh agent-rules --repo "$REPO" "$@"
"""
    raise ValueError(f"unknown workspace launcher: {name}")


def write_workspace_file(path: Path, content: str, force: bool) -> dict[str, Any]:
    existed = path.exists()
    if existed:
        current = path.read_text(encoding="utf-8", errors="replace")
        if current == content:
            return {"path": str(path), "status": "unchanged"}
        if not force:
            return {"path": str(path), "status": "blocked", "reason": "exists with different content; pass --force"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "status": "updated" if existed else "written"}


def ensure_workspace_git_exclude(repo: Path) -> dict[str, Any]:
    git_dir = run_cmd(["git", "rev-parse", "--git-dir"], cwd=repo, timeout=10)
    if git_dir.returncode != 0:
        return {"status": "skipped", "reason": "not a git repository"}

    git_path = run_cmd(["git", "rev-parse", "--git-path", "info/exclude"], cwd=repo, timeout=10)
    if git_path.returncode != 0 or not git_path.stdout.strip():
        return {"status": "skipped", "reason": "cannot resolve git info/exclude"}

    exclude_path = Path(git_path.stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = (repo / exclude_path).resolve()
    exclude_path.parent.mkdir(parents=True, exist_ok=True)

    existing = exclude_path.read_text(encoding="utf-8", errors="replace") if exclude_path.exists() else ""
    patterns = {line.strip() for line in existing.splitlines()}
    required_patterns = [".dg-agent/", ".serena/"]
    missing_patterns = [pattern for pattern in required_patterns if pattern not in patterns]
    if not missing_patterns:
        return {"status": "unchanged", "path": str(exclude_path), "patterns": required_patterns}

    suffix = "" if not existing or existing.endswith("\n") else "\n"
    prefix = "" if "# DG local agent workspace" in existing else "# DG local agent workspace\n"
    with_comment = existing + suffix + prefix + "\n".join(missing_patterns) + "\n"
    exclude_path.write_text(with_comment, encoding="utf-8")
    return {"status": "updated", "path": str(exclude_path), "patterns": required_patterns, "added": missing_patterns}


def run_workspace_init(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    pack = build_client_pack()
    workspace = repo / ".dg-agent"
    files = {
        "client-pack.json": json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
        "AGENT_HUB.md": workspace_agent_hub_md(repo, pack),
        "agent-hub.json": json.dumps(workspace_agent_hub_json(repo, pack), ensure_ascii=False, indent=2) + "\n",
        "COMMANDS.md": agent_commands_md(repo, pack),
        "command-kit.json": json.dumps(agent_command_kit_json(repo, pack), ensure_ascii=False, indent=2) + "\n",
        "commands/dg-report.md": agent_command_md(agent_command_specs(repo)[0]),
        "commands/dg-smoke.md": agent_command_md(agent_command_specs(repo)[1]),
        "commands/dg-context.md": agent_command_md(agent_command_specs(repo)[2]),
        "commands/dg-plan-task.md": agent_command_md(agent_command_specs(repo)[3]),
        "commands/dg-agent.md": agent_command_md(agent_command_specs(repo)[4]),
        "commands/dg-verify.md": agent_command_md(agent_command_specs(repo)[5]),
        "commands/dg-mcp-handoff.md": agent_command_md(agent_command_specs(repo)[6]),
        "commands/dg-codex.md": agent_command_md(agent_command_specs(repo)[7]),
        "claude-skill/SKILL.md": claude_skill_md(repo),
        "CODEX.md": codex_handoff_md(pack),
        "codex.config.toml": codex_config_toml(pack),
        "codex.env": codex_env(pack),
        "IDE_CLIENTS.md": ide_clients_md(pack),
        "ide-client-snippets.json": json.dumps(ide_client_snippets_json(pack), ensure_ascii=False, indent=2) + "\n",
        "openai-compatible.local.json": (CLIENT_PROFILE_DIR / "openai-compatible.local.json").read_text(encoding="utf-8"),
        "openai.env": (CLIENT_PROFILE_DIR / "openai.env").read_text(encoding="utf-8"),
        "kilo-code.config.json": json.dumps(kilo_code_config_json(pack), ensure_ascii=False, indent=2) + "\n",
        "env.sh": client_pack_env(pack),
        "README.md": workspace_readme(repo),
        "aider.dg-fast.conf.yml": AIDER_WORKSPACE_PROFILE.read_text(encoding="utf-8"),
        "aider.dg-model-settings.yml": AIDER_MODEL_SETTINGS.read_text(encoding="utf-8"),
        "aider.dg-model-metadata.json": AIDER_MODEL_METADATA.read_text(encoding="utf-8"),
        "continue.config.yaml": (DG_ROOT / "configs" / "client_profiles" / "continue.config.yaml").read_text(encoding="utf-8"),
        "opencode.dg.json": (DG_ROOT / "configs" / "opencode.dg.json").read_text(encoding="utf-8"),
        "opencode.dg-agent.json": OPENCODE_COMPACT_PROFILE.read_text(encoding="utf-8"),
        "opencode.dg-mcp.json": OPENCODE_MCP_PROFILE.read_text(encoding="utf-8"),
        "openhands.dg.toml": OPENHANDS_PROFILE.read_text(encoding="utf-8"),
        "openhands.env": OPENHANDS_ENV.read_text(encoding="utf-8"),
        "qwen-code.mcp.json": QWEN_CODE_MCP_PROFILE.read_text(encoding="utf-8"),
        "autogen.dg.json": AUTOGEN_PROFILE.read_text(encoding="utf-8"),
        "smolagents.dg.json": SMOLAGENTS_PROFILE.read_text(encoding="utf-8"),
        "langgraph.dg.json": LANGGRAPH_PROFILE.read_text(encoding="utf-8"),
        "crewai.dg.json": CREWAI_PROFILE.read_text(encoding="utf-8"),
        "open-interpreter.dg.json": OPEN_INTERPRETER_PROFILE.read_text(encoding="utf-8"),
        "llamaindex.dg.json": LLAMAINDEX_PROFILE.read_text(encoding="utf-8"),
        "haystack.dg.json": HAYSTACK_PROFILE.read_text(encoding="utf-8"),
        "swe-agent.dg.yaml": SWE_AGENT_PROFILE.read_text(encoding="utf-8"),
        "mini-swe-agent.dg.yaml": MINI_SWE_AGENT_PROFILE.read_text(encoding="utf-8"),
        "mcp-server.json": json.dumps(
            {"mcpServers": {"diffusiongemma-local-agent": primary_mcp_server_config("mcpServers", repo)}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "mcp-client-snippets.json": MCP_CLIENT_SNIPPETS_PROFILE.read_text(encoding="utf-8"),
        "claude-code.mcp.json": CLAUDE_CODE_MCP_PROFILE.read_text(encoding="utf-8"),
        "claude-desktop-mcp.json": CLAUDE_DESKTOP_MCP_PROFILE.read_text(encoding="utf-8"),
        "cursor.mcp.json": CURSOR_MCP_PROFILE.read_text(encoding="utf-8"),
        "vscode.mcp.json": VSCODE_MCP_PROFILE.read_text(encoding="utf-8"),
        "agent-instructions.md": AGENT_INSTRUCTIONS_PROFILE.read_text(encoding="utf-8"),
        "AGENTS.dg.md": AGENTS_RULES_PROFILE.read_text(encoding="utf-8"),
        "CLAUDE.dg.md": CLAUDE_RULES_PROFILE.read_text(encoding="utf-8"),
        "copilot-instructions.dg.md": COPILOT_RULES_PROFILE.read_text(encoding="utf-8"),
        "diffusiongemma.instructions.md": VSCODE_INSTRUCTIONS_PROFILE.read_text(encoding="utf-8"),
        "cursor-rules.dg.mdc": CURSOR_RULES_PROFILE.read_text(encoding="utf-8"),
        "goose-mcp.dg.yaml": GOOSE_MCP_PROFILE.read_text(encoding="utf-8"),
        "litellm-local-model-registry.json": LITELLM_LOCAL_MODEL_REGISTRY.read_text(encoding="utf-8"),
        "bin/run": workspace_launcher("run"),
        "bin/agent": workspace_launcher("agent"),
        "bin/autonomous": workspace_launcher("autonomous"),
        "bin/context": workspace_launcher("context"),
        "bin/rag": workspace_launcher("rag"),
        "bin/repo-pack": workspace_launcher("repo-pack"),
        "bin/repo-map": workspace_launcher("repo-map"),
        "bin/ast-grep": workspace_launcher("ast-grep"),
        "bin/code-outline": workspace_launcher("code-outline"),
        "bin/client-init": workspace_launcher("client-init"),
        "bin/client-smoke": workspace_launcher("client-smoke"),
        "bin/client-report": workspace_launcher("client-report"),
        "bin/agent-commands": workspace_launcher("agent-commands"),
        "bin/codex-profile": workspace_launcher("codex-profile"),
        "bin/agent-bridge": workspace_launcher("agent-bridge"),
        "bin/hub": workspace_launcher("hub"),
        "bin/plan": workspace_launcher("plan"),
        "bin/edit": workspace_launcher("edit"),
        "bin/task": workspace_launcher("task"),
        "bin/verify": workspace_launcher("verify"),
        "bin/status": workspace_launcher("status"),
        "bin/doctor": workspace_launcher("doctor"),
        "bin/up": workspace_launcher("up"),
        "bin/down": workspace_launcher("down"),
        "bin/preflight": workspace_launcher("preflight"),
        "bin/capabilities": workspace_launcher("capabilities"),
        "bin/sessions": workspace_launcher("sessions"),
        "bin/agent-runs": workspace_launcher("agent-runs"),
        "bin/supervisor": workspace_launcher("supervisor"),
        "bin/web": workspace_launcher("web"),
        "bin/aider": workspace_launcher("aider"),
        "bin/opencode": workspace_launcher("opencode"),
        "bin/opencode-agent": workspace_launcher("opencode-agent"),
        "bin/opencode-mcp": workspace_launcher("opencode-mcp"),
        "bin/opencode-acp": workspace_launcher("opencode-acp"),
        "bin/goose": workspace_launcher("goose"),
        "bin/goose-mcp": workspace_launcher("goose-mcp"),
        "bin/goose-acp": workspace_launcher("goose-acp"),
        "bin/goose-serve": workspace_launcher("goose-serve"),
        "bin/openhands": workspace_launcher("openhands"),
        "bin/openhands-acp": workspace_launcher("openhands-acp"),
        "bin/openhands-mcp": workspace_launcher("openhands-mcp"),
        "bin/qwen-code": workspace_launcher("qwen-code"),
        "bin/autogen": workspace_launcher("autogen"),
        "bin/smolagents": workspace_launcher("smolagents"),
        "bin/langgraph": workspace_launcher("langgraph"),
        "bin/crewai": workspace_launcher("crewai"),
        "bin/open-interpreter": workspace_launcher("open-interpreter"),
        "bin/llamaindex": workspace_launcher("llamaindex"),
        "bin/haystack": workspace_launcher("haystack"),
        "bin/swe-agent": workspace_launcher("swe-agent"),
        "bin/mini-swe-agent": workspace_launcher("mini-swe-agent"),
        "bin/mini-swe-run": workspace_launcher("mini-swe-run"),
        "bin/mini-swe-runs": workspace_launcher("mini-swe-runs"),
        "bin/mcp": workspace_launcher("mcp"),
        "bin/mcp-http": workspace_launcher("mcp-http"),
        "bin/serena-mcp": workspace_launcher("serena-mcp"),
        "bin/mcp-client-config": workspace_launcher("mcp-client-config"),
        "bin/agent-rules": workspace_launcher("agent-rules"),
    }

    results = [write_workspace_file(workspace / name, content, args.force) for name, content in files.items()]
    launcher_names = [
        "bin/run",
        "bin/agent",
        "bin/autonomous",
        "bin/context",
        "bin/rag",
        "bin/repo-pack",
        "bin/repo-map",
        "bin/ast-grep",
        "bin/code-outline",
        "bin/client-init",
        "bin/client-smoke",
        "bin/client-report",
        "bin/agent-commands",
        "bin/codex-profile",
        "bin/agent-bridge",
        "bin/hub",
        "bin/plan",
        "bin/edit",
        "bin/task",
        "bin/verify",
        "bin/status",
        "bin/doctor",
        "bin/up",
        "bin/down",
        "bin/preflight",
        "bin/capabilities",
        "bin/sessions",
        "bin/agent-runs",
        "bin/supervisor",
        "bin/web",
        "bin/aider",
        "bin/opencode",
        "bin/opencode-agent",
        "bin/opencode-mcp",
        "bin/opencode-acp",
        "bin/goose",
        "bin/goose-mcp",
        "bin/goose-acp",
        "bin/goose-serve",
        "bin/openhands",
        "bin/openhands-acp",
        "bin/openhands-mcp",
        "bin/qwen-code",
        "bin/autogen",
        "bin/smolagents",
        "bin/langgraph",
        "bin/crewai",
        "bin/open-interpreter",
        "bin/llamaindex",
        "bin/haystack",
        "bin/swe-agent",
        "bin/mini-swe-agent",
        "bin/mini-swe-run",
        "bin/mini-swe-runs",
        "bin/mcp",
        "bin/mcp-http",
        "bin/serena-mcp",
        "bin/mcp-client-config",
        "bin/agent-rules",
    ]
    for name in launcher_names:
        path = workspace / name
        if path.exists():
            path.chmod(path.stat().st_mode | 0o755)
    git_exclude = ensure_workspace_git_exclude(repo)
    status = "success" if all(item["status"] != "blocked" for item in results) else "blocked"
    report = {
        "repo": str(repo),
        "workspace_dir": str(workspace),
        "status": status,
        "force": args.force,
        "files": results,
        "git_exclude": git_exclude,
        "next": {
            "load_env": "set -a; . .dg-agent/env.sh; set +a",
            "agent": f"{DG_ROOT}/scripts/dg_agent.sh agent --repo {repo} --task \"...\" --file path",
            "client_pack": str(workspace / "client-pack.json"),
        },
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG workspace init: {status}")
        print(f"repo: {repo}")
        print(f"workspace: {workspace}")
        for item in results:
            line = f"- {item['status']}: {item['path']}"
            if item.get("reason"):
                line += f" ({item['reason']})"
            print(line)
        if git_exclude.get("path"):
            patterns = ",".join(git_exclude.get("patterns") or [str(git_exclude.get("pattern", ""))])
            print(f"git exclude: {git_exclude['status']} {git_exclude['path']} patterns={patterns}")
        print(f"next: {report['next']['agent']}")
    return 0 if status == "success" else 1


def mcp_client_definition(client: str) -> dict[str, Any]:
    definitions = {
        "claude-code": {
            "profile": CLAUDE_CODE_MCP_PROFILE,
            "target": ".mcp.json",
            "section": "mcpServers",
        },
        "claude-desktop": {
            "profile": CLAUDE_DESKTOP_MCP_PROFILE,
            "target": "claude_desktop_config.json",
            "section": "mcpServers",
        },
        "cursor": {
            "profile": CURSOR_MCP_PROFILE,
            "target": ".cursor/mcp.json",
            "section": "mcpServers",
        },
        "vscode": {
            "profile": VSCODE_MCP_PROFILE,
            "target": ".vscode/mcp.json",
            "section": "servers",
        },
    }
    return definitions[client]


def repomix_mcp_config(section: str) -> dict[str, Any]:
    config: dict[str, Any] = {
        "command": str(DG_ROOT / "scripts" / "run_repomix_mcp.sh"),
        "args": [],
        "env": {},
    }
    if section == "servers":
        config = {"type": "stdio", **config}
    return config


def serena_mcp_config(section: str) -> dict[str, Any]:
    config: dict[str, Any] = {
        "command": str(DG_ROOT / "scripts" / "run_serena_mcp.sh"),
        "args": [],
        "env": {},
    }
    if section == "servers":
        config = {"type": "stdio", **config}
    return config


def windows_path_to_wsl(path: Path) -> str:
    raw = str(path.resolve())
    if os.name == "nt" and len(raw) >= 3 and raw[1:3] == ":\\":
        return f"/mnt/{raw[0].lower()}/{raw[3:].replace(chr(92), '/')}"
    return raw


def wsl_path_to_windows(path: Path) -> str:
    raw = str(path.resolve())
    match = re.match(r"^/mnt/([A-Za-z])/(.*)$", raw)
    if match:
        drive, tail = match.groups()
        return f"{drive.upper()}:\\{tail.replace('/', chr(92))}"
    return raw


def caller_working_directory() -> Path:
    """Return the directory from which the shell launcher was invoked."""
    raw = os.environ.get("DG_AGENT_CALLER_CWD", "").strip()
    if raw:
        candidate = Path(raw).expanduser()
        try:
            if candidate.is_dir():
                return candidate.resolve()
        except OSError:
            pass
    return Path.cwd()


def shell_path_to_wsl(value: str) -> str:
    """Map Windows/MSYS path arguments to WSL paths for Linux-native wrappers."""
    if os.name != "nt":
        return value
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return windows_path_to_wsl(Path(value))
    msys_match = re.match(r"^/([A-Za-z])/(.*)$", value)
    if msys_match:
        drive, tail = msys_match.groups()
        return f"/mnt/{drive.lower()}/{tail}"
    if value.startswith("/mnt/"):
        return value
    if value.startswith("/") and not value.startswith("//"):
        cygpath_candidates = [
            shutil.which("cygpath") or "",
            "C:/Program Files/Git/usr/bin/cygpath.exe",
        ]
        for cygpath in cygpath_candidates:
            if not cygpath or not Path(cygpath).exists():
                continue
            try:
                proc = subprocess.run(
                    [cygpath, "-aw", value],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    check=False,
                )
            except Exception:
                continue
            candidate = proc.stdout.strip()
            if proc.returncode == 0 and re.match(r"^[A-Za-z]:[\\/]", candidate):
                return windows_path_to_wsl(Path(candidate))
    return value


def qwen_code_command(raw_args: list[str]) -> list[str]:
    windows_launcher = DG_ROOT / "scripts" / "run_qwen_code_windows.ps1"
    powershell = powershell_executable()
    running_under_msys = bool(os.environ.get("MSYSTEM") or os.environ.get("MINGW_PREFIX") or os.environ.get("MINGW_CHOST"))
    if os.name != "nt":
        return [str(DG_ROOT / "scripts" / "run_qwen_code_local.sh"), *raw_args]

    if windows_launcher.exists() and powershell and not running_under_msys:
        mapped_args: list[str] = []
        path_next = False
        for value in raw_args:
            if path_next:
                mapped_args.append(wsl_path_to_windows(Path(value)) if os.name != "nt" and value.startswith("/mnt/") else value)
                path_next = False
                continue
            mapped_args.append(value)
            if value == "--repo":
                path_next = True
        return [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            wsl_path_to_windows(windows_launcher),
            *mapped_args,
        ]

    wsl = shutil.which("wsl.exe") or shutil.which("wsl")
    if not wsl:
        raise RuntimeError("Neither the Windows Qwen Code runner nor WSL is available")

    mapped_args: list[str] = []
    has_repo = False
    path_next = False
    for value in raw_args:
        if path_next:
            mapped_args.append(shell_path_to_wsl(value))
            path_next = False
            continue
        mapped_args.append(value)
        if value in {"--repo", "--mcp-config"}:
            has_repo = has_repo or value == "--repo"
            path_next = True
    if not has_repo:
        mapped_args = ["--repo", windows_path_to_wsl(Path.cwd()), *mapped_args]
    return [
        wsl,
        "--exec",
        "bash",
        windows_path_to_wsl(DG_ROOT / "scripts" / "run_qwen_code_local.sh"),
        *mapped_args,
    ]


def agent_python_command(script: Path, args: list[str]) -> list[str]:
    """Run a DG Python helper in the same runtime that serves the gateway."""
    if os.name != "nt":
        python = os.environ.get("DG_AGENT_PYTHON", str(DG_ROOT / ".venv" / "bin" / "python"))
        return [python, str(script), *args]

    wsl = shutil.which("wsl.exe") or shutil.which("wsl")
    if not wsl:
        raise RuntimeError("WSL is unavailable for the DG agent runtime")
    python = os.environ.get("DG_AGENT_PYTHON", "/root/diffusiongemma-agent/.venv-wsl/bin/python")
    mapped_args: list[str] = []
    for value in args:
        if re.match(r"^[A-Za-z]:[\\/]", value):
            mapped_args.append(windows_path_to_wsl(Path(value)))
        else:
            mapped_args.append(value)
    return [wsl, "--exec", python, windows_path_to_wsl(script), *mapped_args]


def primary_mcp_server_config(section: str, repo: Path) -> dict[str, Any]:
    wsl_root = windows_path_to_wsl(DG_ROOT)
    wsl_repo = windows_path_to_wsl(repo)
    wsl_python = os.environ.get("DG_AGENT_PYTHON", "/root/diffusiongemma-agent/.venv-wsl/bin/python")
    script = str(DG_ROOT / "scripts" / "run_mcp_server.sh")

    if wsl_root.startswith("/mnt/"):
        command = "wsl.exe" if os.name == "nt" else "bash"
        command_text = (
            f"DG_AGENT_PYTHON={shlex.quote(wsl_python)} "
            f"DG_MCP_REPO={shlex.quote(wsl_repo)} "
            f"exec {shlex.quote(wsl_root + '/scripts/run_mcp_server.sh')}"
        )
        config: dict[str, Any] = {
            "command": command,
            "args": ["--exec", "bash", "-lc", command_text] if os.name == "nt" else ["-lc", command_text],
            "env": {},
        }
    else:
        config = {
            "command": script,
            "args": [],
            "env": {"DG_MCP_REPO": str(repo)},
        }
    if section == "servers":
        config = {"type": "stdio", **config}
    return config


def inject_primary_mcp_repo_env(template: dict[str, Any], section: str, repo: Path) -> dict[str, Any]:
    servers = template.get(section)
    if not isinstance(servers, dict) or "diffusiongemma-local-agent" not in servers:
        return template
    servers["diffusiongemma-local-agent"] = primary_mcp_server_config(section, repo)
    return template


def merge_mcp_client_config(
    target: Path,
    template: dict[str, Any],
    section: str,
    force: bool,
    dry_run: bool,
    with_repomix: bool = False,
    with_serena: bool = False,
) -> dict[str, Any]:
    primary_server_name = "diffusiongemma-local-agent"
    servers_to_merge: list[tuple[str, dict[str, Any]]] = [(primary_server_name, template[section][primary_server_name])]
    if with_repomix:
        servers_to_merge.append(("repomix", repomix_mcp_config(section)))
    if with_serena:
        servers_to_merge.append(("serena", serena_mcp_config(section)))
    existing: dict[str, Any] = {}
    existed = target.exists()
    if existed:
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            if not force:
                return {"status": "blocked", "path": str(target), "reason": f"invalid JSON: {exc}"}
            loaded = {}
        if not isinstance(loaded, dict):
            if not force:
                return {"status": "blocked", "path": str(target), "reason": "existing JSON is not an object"}
            loaded = {}
        existing = loaded

    section_value = existing.get(section, {})
    if not isinstance(section_value, dict):
        if not force:
            return {"status": "blocked", "path": str(target), "reason": f"existing {section} is not an object"}
        section_value = {}

    changed = False
    for server_name, server_config in servers_to_merge:
        previous = section_value.get(server_name)
        if previous == server_config:
            continue
        if previous is not None and previous != server_config and not force:
            return {
                "status": "blocked",
                "path": str(target),
                "server": server_name,
                "servers": [name for name, _ in servers_to_merge],
                "reason": f"{server_name} already exists; use --force to replace",
            }
        section_value[server_name] = server_config
        changed = True

    existing[section] = section_value
    if changed and not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not changed:
        status = "unchanged"
    elif dry_run:
        status = "would_update" if existed else "would_write"
    else:
        status = "updated" if existed else "written"
    return {
        "status": status,
        "path": str(target),
        "server": primary_server_name,
        "servers": [name for name, _ in servers_to_merge],
        "section": section,
    }


def run_mcp_client_config(args: argparse.Namespace) -> int:
    definition = mcp_client_definition(args.client)
    template = json.loads(definition["profile"].read_text(encoding="utf-8"))
    if args.print_template:
        print(json.dumps(template, ensure_ascii=False, indent=2))
        return 0

    repo = Path(args.repo).resolve()
    if args.target:
        target = Path(args.target).expanduser().resolve()
    else:
        if not repo.exists() or not repo.is_dir():
            print(f"repo does not exist: {repo}", file=sys.stderr)
            return 2
        target = repo / definition["target"]

    template = inject_primary_mcp_repo_env(template, definition["section"], repo)
    with_repomix = args.with_repomix or args.with_oss_stack
    with_serena = args.with_serena or args.with_oss_stack
    report = merge_mcp_client_config(target, template, definition["section"], args.force, args.dry_run, with_repomix, with_serena)
    report.update({"client": args.client, "template": str(definition["profile"]), "target_hint": definition["target"]})
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        line = f"MCP client config {report['status']}: {report['path']}"
        if report.get("reason"):
            line += f" ({report['reason']})"
        print(line)
    return 0 if report["status"] not in {"blocked"} else 1


AGENT_RULE_BLOCK_START = "<!-- BEGIN DG LOCAL AGENT INSTRUCTIONS -->"
AGENT_RULE_BLOCK_END = "<!-- END DG LOCAL AGENT INSTRUCTIONS -->"


def agent_rule_definitions() -> dict[str, dict[str, Any]]:
    return {
        "agents": {
            "template": AGENTS_RULES_PROFILE,
            "target": "AGENTS.md",
            "mode": "block",
        },
        "claude": {
            "template": CLAUDE_RULES_PROFILE,
            "target": "CLAUDE.md",
            "mode": "block",
        },
        "copilot": {
            "template": COPILOT_RULES_PROFILE,
            "target": ".github/copilot-instructions.md",
            "mode": "block",
        },
        "vscode": {
            "template": VSCODE_INSTRUCTIONS_PROFILE,
            "target": ".github/instructions/diffusiongemma.instructions.md",
            "mode": "file",
        },
        "cursor": {
            "template": CURSOR_RULES_PROFILE,
            "target": ".cursor/rules/diffusiongemma-local-agent.mdc",
            "mode": "file",
        },
    }


def merge_marked_block(existing: str, block: str) -> str:
    wrapped = f"{AGENT_RULE_BLOCK_START}\n{block.rstrip()}\n{AGENT_RULE_BLOCK_END}\n"
    if AGENT_RULE_BLOCK_START in existing and AGENT_RULE_BLOCK_END in existing:
        prefix, rest = existing.split(AGENT_RULE_BLOCK_START, 1)
        _, suffix = rest.split(AGENT_RULE_BLOCK_END, 1)
        parts = []
        if prefix.strip():
            parts.append(prefix.rstrip())
        parts.append(wrapped.rstrip())
        if suffix.strip():
            parts.append(suffix.lstrip())
        return "\n\n".join(parts) + "\n"
    if not existing.strip():
        return wrapped
    return existing.rstrip() + "\n\n" + wrapped


def install_agent_rule(repo: Path, target_id: str, force: bool, dry_run: bool) -> dict[str, Any]:
    definition = agent_rule_definitions()[target_id]
    template = definition["template"].read_text(encoding="utf-8")
    target = (repo / definition["target"]).resolve()
    if target != repo and repo not in target.parents:
        return {"target": target_id, "status": "blocked", "path": str(target), "reason": "target escapes repo"}
    existed = target.exists()

    if definition["mode"] == "block":
        existing = target.read_text(encoding="utf-8", errors="replace") if existed else ""
        content = merge_marked_block(existing, template)
    else:
        content = template
        if existed:
            current = target.read_text(encoding="utf-8", errors="replace")
            if current != content and not force:
                return {
                    "target": target_id,
                    "status": "blocked",
                    "path": str(target),
                    "reason": "exists with different content; pass --force",
                }

    if existed and target.read_text(encoding="utf-8", errors="replace") == content:
        status = "unchanged"
    else:
        status = "updated" if existed else "written"
        if dry_run:
            status = "would_update" if existed else "would_write"
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    return {
        "target": target_id,
        "status": status,
        "path": str(target),
        "mode": definition["mode"],
        "template": str(definition["template"]),
    }


def run_agent_rules(args: argparse.Namespace) -> int:
    definitions = agent_rule_definitions()
    target = args.target
    if args.print_template:
        if target == "all":
            print(json.dumps({name: definition["template"].read_text(encoding="utf-8") for name, definition in definitions.items()}, ensure_ascii=False, indent=2))
        else:
            print(definitions[target]["template"].read_text(encoding="utf-8"), end="")
        return 0

    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    targets = list(definitions) if target == "all" else [target]
    results = [install_agent_rule(repo, name, args.force, args.dry_run) for name in targets]
    status = "success" if all(item["status"] != "blocked" for item in results) else "blocked"
    report = {"repo": str(repo), "status": status, "force": args.force, "dry_run": args.dry_run, "files": results}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG agent rules: {status}")
        for item in results:
            line = f"- {item['status']}: {item['path']}"
            if item.get("reason"):
                line += f" ({item['reason']})"
            print(line)
    return 0 if status == "success" else 1


def agent_command_definitions(repo: Path) -> dict[str, dict[str, Any]]:
    return {
        "claude-skill": {
            "target": ".claude/skills/dg-local-agent/SKILL.md",
            "content": claude_skill_md(repo),
            "description": "Claude Code project skill for the DG local agent command kit.",
        },
    }


def run_agent_commands(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    definitions = agent_command_definitions(repo)
    targets = list(definitions) if args.target == "all" else [args.target]
    results: list[dict[str, Any]] = []
    for target_id in targets:
        definition = definitions[target_id]
        path = repo / definition["target"]
        content = definition["content"]
        if args.print_template:
            results.append({"target": target_id, "status": "template", "path": str(path), "content": content})
            continue
        existed = path.exists()
        status = "unchanged" if existed and path.read_text(encoding="utf-8", errors="replace") == content else ("updated" if existed else "written")
        if status != "unchanged" and args.dry_run:
            status = "would_update" if existed else "would_write"
        elif status != "unchanged":
            result = write_workspace_file(path, content, args.force)
            status = result["status"]
            if result.get("reason"):
                results.append({"target": target_id, **result, "description": definition["description"]})
                continue
        results.append({"target": target_id, "status": status, "path": str(path), "description": definition["description"]})

    if args.print_template:
        if args.json:
            print(json.dumps({"repo": str(repo), "status": "success", "templates": results}, ensure_ascii=False, indent=2))
        else:
            for item in results:
                print(item["content"], end="" if item["content"].endswith("\n") else "\n")
        return 0

    status = "success" if all(item["status"] not in {"blocked", "failed"} for item in results) else "blocked"
    report = {"repo": str(repo), "status": status, "target": args.target, "force": args.force, "dry_run": args.dry_run, "files": results}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG agent commands: {status}")
        for item in results:
            line = f"- {item['status']}: {item['path']}"
            if item.get("reason"):
                line += f" ({item['reason']})"
            print(line)
    return 0 if status == "success" else 1


def codex_profile_definitions(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "config": {
            "target": ".codex/config.toml",
            "content": codex_config_toml(pack),
            "description": "Codex CLI project config for the DG local safe agent proxy.",
        },
    }


def run_codex_profile(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    pack = build_client_pack()
    definitions = codex_profile_definitions(pack)
    targets = list(definitions) if args.target == "all" else [args.target]
    results: list[dict[str, Any]] = []
    for target_id in targets:
        definition = definitions[target_id]
        path = repo / definition["target"]
        content = definition["content"]
        if args.print_template:
            results.append({"target": target_id, "status": "template", "path": str(path), "content": content})
            continue
        existed = path.exists()
        status = "unchanged" if existed and path.read_text(encoding="utf-8", errors="replace") == content else ("updated" if existed else "written")
        if status != "unchanged" and args.dry_run:
            status = "would_update" if existed else "would_write"
        elif status != "unchanged":
            result = write_workspace_file(path, content, args.force)
            status = result["status"]
            if result.get("reason"):
                results.append({"target": target_id, **result, "description": definition["description"]})
                continue
        results.append({"target": target_id, "status": status, "path": str(path), "description": definition["description"]})

    if args.print_template:
        if args.json:
            print(json.dumps({"repo": str(repo), "status": "success", "templates": results}, ensure_ascii=False, indent=2))
        else:
            for item in results:
                print(item["content"], end="" if item["content"].endswith("\n") else "\n")
        return 0

    status = "success" if all(item["status"] not in {"blocked", "failed"} for item in results) else "blocked"
    report = {
        "repo": str(repo),
        "status": status,
        "target": args.target,
        "force": args.force,
        "dry_run": args.dry_run,
        "files": results,
        "env": ".dg-agent/codex.env",
        "handoff": ".dg-agent/CODEX.md",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG Codex profile: {status}")
        for item in results:
            line = f"- {item['status']}: {item['path']}"
            if item.get("reason"):
                line += f" ({item['reason']})"
            print(line)
    return 0 if status == "success" else 1


def tail_text(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def run_json_subcommand(step: str, argv: list[str], timeout: int = 120) -> dict[str, Any]:
    cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), *argv, "--json"]
    proc = run_cmd(cmd, timeout=timeout)
    report: dict[str, Any]
    try:
        loaded = json.loads(proc.stdout)
        report = loaded if isinstance(loaded, dict) else {"value": loaded}
    except json.JSONDecodeError as exc:
        report = {
            "status": "failed",
            "reason": f"invalid JSON output: {exc}",
            "stdout_tail": tail_text(proc.stdout),
            "stderr_tail": tail_text(proc.stderr),
        }
    status = str(report.get("status") or ("success" if proc.returncode == 0 else "failed"))
    if proc.returncode != 0 and status not in {"blocked", "failed"}:
        status = "failed"
    item = {
        "step": step,
        "status": status,
        "returncode": proc.returncode,
        "command": shlex.join(cmd),
        "report": report,
    }
    if proc.returncode != 0 and "stderr_tail" not in report:
        item["stderr_tail"] = tail_text(proc.stderr)
    return item


def run_client_init(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    with_repomix = bool(args.with_repomix)
    with_serena = bool(args.with_serena)
    unavailable_optional: list[dict[str, str]] = []
    if not args.no_oss_stack:
        with_repomix = True
        serena_status = serena_runtime_status()
        with_serena = bool(serena_status["ok"])
        if not with_serena:
            unavailable_optional.append({"name": "serena", "reason": str(serena_status["detail"])})

    steps: list[dict[str, Any]] = []
    if args.no_workspace:
        steps.append({"step": "workspace-init", "status": "skipped", "reason": "--no-workspace"})
    elif args.dry_run:
        steps.append(
            {
                "step": "workspace-init",
                "status": "would_run",
                "command": shlex.join([str(DG_ROOT / "scripts" / "dg_agent.sh"), "workspace-init", "--repo", str(repo)]),
                "reason": "workspace-init has no dry-run mode",
            }
        )
    else:
        workspace_argv = ["workspace-init", "--repo", str(repo)]
        if args.force:
            workspace_argv.append("--force")
        steps.append(run_json_subcommand("workspace-init", workspace_argv, timeout=120))

    mcp_argv = ["mcp-client-config", "--repo", str(repo), "--client", args.client]
    if args.target:
        mcp_argv.extend(["--target", args.target])
    if args.force:
        mcp_argv.append("--force")
    if args.dry_run:
        mcp_argv.append("--dry-run")
    if with_repomix:
        mcp_argv.append("--with-repomix")
    if with_serena:
        mcp_argv.append("--with-serena")
    steps.append(run_json_subcommand("mcp-client-config", mcp_argv, timeout=120))

    if args.no_rules:
        steps.append({"step": "agent-rules", "status": "skipped", "reason": "--no-rules"})
        steps.append({"step": "agent-commands", "status": "skipped", "reason": "--no-rules"})
    else:
        rules_argv = ["agent-rules", "--repo", str(repo), "--target", args.rules_target]
        if args.force:
            rules_argv.append("--force")
        if args.dry_run:
            rules_argv.append("--dry-run")
        steps.append(run_json_subcommand("agent-rules", rules_argv, timeout=120))
        commands_argv = ["agent-commands", "--repo", str(repo), "--target", "all"]
        if args.force:
            commands_argv.append("--force")
        if args.dry_run:
            commands_argv.append("--dry-run")
        steps.append(run_json_subcommand("agent-commands", commands_argv, timeout=120))

    failure_statuses = {"blocked", "failed"}
    status = "success" if all(step.get("status") not in failure_statuses and step.get("returncode", 0) == 0 for step in steps) else "blocked"
    bundle_servers = ["diffusiongemma-local-agent"]
    if with_repomix:
        bundle_servers.append("repomix")
    if with_serena:
        bundle_servers.append("serena")
    report = {
        "repo": str(repo),
        "status": status,
        "client": args.client,
        "target": args.target,
        "force": args.force,
        "dry_run": args.dry_run,
        "bundle": {
            "name": (
                "dg-repomix-serena"
                if bundle_servers == ["diffusiongemma-local-agent", "repomix", "serena"]
                else "dg-repomix"
                if bundle_servers == ["diffusiongemma-local-agent", "repomix"]
                else "custom"
            ),
            "servers": bundle_servers,
            "unavailable_optional": unavailable_optional,
        },
        "steps": steps,
        "next": {
            "open_client_config": steps[1].get("report", {}).get("path") if len(steps) > 1 else "",
            "workspace": str(repo / ".dg-agent"),
            "launcher": str(repo / ".dg-agent" / "bin" / "client-init"),
        },
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG client init: {status}")
        print(f"repo: {repo}")
        print(f"client: {args.client}")
        print(f"bundle: {','.join(bundle_servers)}")
        for step in steps:
            line = f"- {step['step']}: {step['status']}"
            path = step.get("report", {}).get("path") if isinstance(step.get("report"), dict) else ""
            if path:
                line += f" {path}"
            if step.get("reason"):
                line += f" ({step['reason']})"
            print(line)
    return 0 if status == "success" else 1


def check_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "failed", "path": str(path), "reason": "missing"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "failed", "path": str(path), "reason": f"invalid JSON: {exc}"}
    return {"status": "passed", "path": str(path), "data": data}


def check_file_exists(name: str, path: Path) -> dict[str, Any]:
    return {"name": name, "path": str(path), "status": "passed" if path.exists() else "failed"}


def load_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "invalid", "path": str(path), "reason": str(exc)}
    return {"status": "loaded", "path": str(path), "data": data}


def run_client_smoke(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    actions: list[dict[str, Any]] = []
    if args.no_init:
        actions.append({"step": "client-init", "status": "skipped", "reason": "--no-init"})
    else:
        init_argv = ["client-init", "--repo", str(repo), "--client", args.client]
        if args.force_init:
            init_argv.append("--force")
        if args.no_rules:
            init_argv.append("--no-rules")
        if args.no_oss_stack:
            init_argv.append("--no-oss-stack")
        if args.target:
            init_argv.extend(["--target", args.target])
        actions.append(run_json_subcommand("client-init", init_argv, timeout=180))

    checks: list[dict[str, Any]] = []
    workspace = workspace_state(repo)
    checks.append(
        {
            "name": "workspace",
            "status": "passed" if workspace["complete"] else "failed",
            "dir": workspace["dir"],
            "missing_files": [item["path"] for item in workspace["files"] if not item["exists"]],
            "non_executable_launchers": [item["path"] for item in workspace["launchers"] if not item["executable"]],
        }
    )

    hub_md = repo / ".dg-agent" / "AGENT_HUB.md"
    hub_json = repo / ".dg-agent" / "agent-hub.json"
    checks.append(check_file_exists("agent_hub_markdown", hub_md))
    hub_check = check_json_file(hub_json)
    if hub_check["status"] == "passed":
        data = hub_check.get("data", {})
        route_ids = [item.get("id") for item in data.get("recommended_routes", []) if isinstance(item, dict)]
        required_routes = {"safe_code_edit", "mcp_ide", "acp_agent_server", "read_only_context"}
        hub_check["routes"] = route_ids
        hub_check["status"] = "passed" if required_routes <= set(route_ids) else "failed"
        if hub_check["status"] == "failed":
            hub_check["reason"] = "missing required route ids"
        hub_check.pop("data", None)
    checks.append({"name": "agent_hub_json", **hub_check})

    definition = mcp_client_definition(args.client)
    target = Path(args.target).expanduser().resolve() if args.target else repo / definition["target"]
    mcp_check = check_json_file(target)
    if mcp_check["status"] == "passed":
        cfg = mcp_check.pop("data", {})
        section = definition["section"]
        servers = cfg.get(section, {}) if isinstance(cfg, dict) else {}
        names = set(servers) if isinstance(servers, dict) else set()
        required = {"diffusiongemma-local-agent"}
        if not args.no_oss_stack:
            required.add("repomix")
            if serena_runtime_status()["ok"]:
                required.add("serena")
        missing = sorted(required - names)
        mcp_check.update({"section": section, "servers": sorted(names), "required": sorted(required)})
        if missing:
            mcp_check.update({"status": "failed", "missing": missing})
    checks.append({"name": "mcp_client_config", "client": args.client, **mcp_check})

    rule_checks = []
    if args.no_rules:
        rule_checks.append({"name": "agent_rules", "status": "skipped", "reason": "--no-rules"})
    else:
        for name, definition_item in agent_rule_definitions().items():
            rule_checks.append(check_file_exists(name, repo / definition_item["target"]))
    checks.append(
        {
            "name": "agent_rules",
            "status": "passed" if rule_checks and all(item["status"] == "passed" for item in rule_checks) else ("skipped" if args.no_rules else "failed"),
            "files": rule_checks,
        }
    )

    if args.no_rules:
        checks.append({"name": "agent_commands", "status": "skipped", "reason": "--no-rules"})
    else:
        command_checks = [
            check_file_exists("claude_skill", repo / ".claude" / "skills" / "dg-local-agent" / "SKILL.md"),
            check_file_exists("command_kit", repo / ".dg-agent" / "command-kit.json"),
            check_file_exists("commands_markdown", repo / ".dg-agent" / "COMMANDS.md"),
        ]
        checks.append(
            {
                "name": "agent_commands",
                "status": "passed" if all(item["status"] == "passed" for item in command_checks) else "failed",
                "files": command_checks,
            }
        )

    launcher_checks = []
    for name, argv in {
        "hub": ["--json"],
        "client-init": ["--help"],
        "client-smoke": ["--help"],
        "client-report": ["--help"],
        "agent-commands": ["--help"],
        "agent-bridge": ["--help"],
        "mcp": ["--list-tools"],
        "serena-mcp": ["--help-local"],
    }.items():
        path = repo / ".dg-agent" / "bin" / name
        if not path.exists() or not os.access(path, os.X_OK):
            launcher_checks.append({"name": name, "status": "failed", "reason": "missing or not executable", "path": str(path)})
            continue
        proc = run_cmd([str(path), *argv], cwd=repo, timeout=45)
        launcher_checks.append(
            {
                "name": name,
                "status": "passed" if proc.returncode == 0 and (proc.stdout + proc.stderr).strip() else "failed",
                "returncode": proc.returncode,
                "stdout_bytes": len(proc.stdout),
                "stderr_bytes": len(proc.stderr),
            }
        )
    checks.append(
        {
            "name": "launchers",
            "status": "passed" if all(item["status"] == "passed" for item in launcher_checks) else "failed",
            "launchers": launcher_checks,
        }
    )

    if args.live:
        live_checks = []
        for name, url in [
            ("backend", "http://127.0.0.1:4100/healthz"),
            ("proxy", "http://127.0.0.1:8090/healthz"),
            ("litellm", "http://127.0.0.1:4100/v1/models"),
        ]:
            ok, detail = http_json(url, timeout=3)
            live_checks.append({"name": name, "status": "passed" if ok else "failed", "url": url, "detail": detail})
        checks.append(
            {
                "name": "live_endpoints",
                "status": "passed" if all(item["status"] == "passed" for item in live_checks) else "failed",
                "endpoints": live_checks,
            }
        )

    failed_actions = [item for item in actions if item.get("status") in {"blocked", "failed"} or item.get("returncode", 0) != 0]
    failed_checks = [item for item in checks if item.get("status") == "failed"]
    status = "success" if not failed_actions and not failed_checks else "failed"
    report = {
        "status": status,
        "repo": str(repo),
        "client": args.client,
        "target": str(target),
        "live": args.live,
        "actions": actions,
        "checks": checks,
        "next": {
            "hub": str(repo / ".dg-agent" / "AGENT_HUB.md"),
            "mcp_config": str(target),
            "agent_bridge": f"{repo}/.dg-agent/bin/agent-bridge --server opencode-acp",
        },
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG client smoke: {status}")
        print(f"repo: {repo}")
        print(f"client: {args.client}")
        for check in checks:
            print(f"- {check['name']}: {check['status']}")
        if failed_checks:
            print("failed checks:")
            for check in failed_checks:
                print(f"- {check['name']}: {check.get('reason', '')}")
    return 0 if status == "success" else 1


def summarize_capabilities_latest(path: Path) -> dict[str, Any]:
    loaded = load_json_optional(path)
    if loaded["status"] != "loaded":
        return loaded
    data = loaded.get("data", {})
    scenarios = data.get("scenarios", []) if isinstance(data, dict) else []
    failed = [
        item.get("name", "")
        for item in scenarios
        if isinstance(item, dict) and item.get("status") not in {"passed", "success", "skipped"}
    ]
    return {
        "status": "loaded",
        "path": str(path),
        "report_status": data.get("status") if isinstance(data, dict) else None,
        "scenario_count": len(scenarios),
        "failed_scenarios": [name for name in failed if name],
    }


def extract_client_config_summary(path: Path, client: str) -> dict[str, Any]:
    definition = mcp_client_definition(client)
    loaded = load_json_optional(path)
    if loaded["status"] != "loaded":
        return loaded
    cfg = loaded.get("data", {})
    section = definition["section"]
    servers = cfg.get(section, {}) if isinstance(cfg, dict) else {}
    names = sorted(servers) if isinstance(servers, dict) else []
    loaded.pop("data", None)
    loaded.update({"section": section, "servers": names})
    return loaded


def client_handoff_markdown(report: dict[str, Any]) -> str:
    smoke = report.get("client_smoke", {}).get("report", {})
    checks = {item.get("name"): item for item in smoke.get("checks", []) if isinstance(item, dict)}
    commands = report.get("commands", {})
    outputs = report.get("outputs", {})
    client_config = report.get("client_config", {})
    capabilities = report.get("capabilities_latest", {})
    hub = report.get("hub", {})
    routes = []
    if hub.get("status") == "loaded":
        data = hub.get("data", {})
        routes = [item.get("id", "") for item in data.get("recommended_routes", []) if isinstance(item, dict)]
    route_line = ", ".join([item for item in routes if item]) or "not available"
    check_lines = []
    for name in ["workspace", "agent_hub_markdown", "agent_hub_json", "mcp_client_config", "agent_rules", "launchers", "live_endpoints"]:
        if name in checks:
            check_lines.append(f"- {name}: {checks[name].get('status', 'unknown')}")
    checks_md = "\n".join(check_lines) if check_lines else "- client-smoke did not return checks"
    servers = ", ".join(client_config.get("servers", [])) or "not available"
    failed_caps = ", ".join(capabilities.get("failed_scenarios", [])) or "none"
    live_note = "included" if report.get("live") else "not requested"
    output_json = outputs.get("json", {}).get("path", ".dg-agent/client-handoff.json")
    output_md = outputs.get("markdown", {}).get("path", ".dg-agent/CLIENT_HANDOFF.md")
    return f"""# DG Client Handoff

Repo:

```text
{report.get("repo")}
```

Status: `{report.get("status")}`
Client: `{report.get("client")}`
Generated: `{report.get("generated_at")}`
Live endpoint checks: `{live_note}`

## Ready Commands

```bash
{commands.get("client_smoke", "")}
{commands.get("agent_hub", "")}
{commands.get("mcp_tools", "")}
{commands.get("agent_session", "")}
{commands.get("agent_bridge", "")}
```

## Checks

{checks_md}

## MCP Client Config

```text
path: {client_config.get("path", "not available")}
section: {client_config.get("section", "not available")}
servers: {servers}
```

## Routes

```text
{route_line}
```

## Capability Snapshot

```text
path: {capabilities.get("path", "not available")}
status: {capabilities.get("report_status", capabilities.get("status", "not available"))}
scenarios: {capabilities.get("scenario_count", "not available")}
failed: {failed_caps}
```

## Files

```text
markdown: {output_md}
json: {output_json}
hub: .dg-agent/AGENT_HUB.md
hub_json: .dg-agent/agent-hub.json
```

For real edits, prefer `.dg-agent/bin/agent`, `.dg-agent/bin/run`,
`.dg-agent/bin/plan` -> `.dg-agent/bin/task`, or MCP tools over raw chat.
"""


def run_client_report(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    smoke_argv = ["client-smoke", "--repo", str(repo), "--client", args.client]
    if args.target:
        smoke_argv.extend(["--target", args.target])
    if args.force_init:
        smoke_argv.append("--force-init")
    if args.no_init:
        smoke_argv.append("--no-init")
    if args.no_rules:
        smoke_argv.append("--no-rules")
    if args.no_oss_stack:
        smoke_argv.append("--no-oss-stack")
    if args.live:
        smoke_argv.append("--live")
    smoke_action = run_json_subcommand("client-smoke", smoke_argv, timeout=240 if args.live else 180)
    smoke_report = smoke_action.get("report", {}) if isinstance(smoke_action.get("report"), dict) else {}

    definition = mcp_client_definition(args.client)
    target = Path(args.target).expanduser().resolve() if args.target else repo / definition["target"]
    if smoke_report.get("target"):
        target = Path(str(smoke_report["target"]))

    hub_path = repo / ".dg-agent" / "agent-hub.json"
    hub = load_json_optional(hub_path)
    client_config = extract_client_config_summary(target, args.client)
    capabilities = summarize_capabilities_latest(DG_ROOT / "runlogs" / "dg-agent-capabilities" / "latest.json")
    workspace = workspace_state(repo)

    failed = smoke_action.get("status") != "success"
    status = "failed" if failed else "success"
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commands = {
        "client_smoke": f".dg-agent/bin/client-smoke --client {args.client}" + (" --live" if args.live else ""),
        "client_report": f".dg-agent/bin/client-report --client {args.client}" + (" --live" if args.live else ""),
        "agent_hub": ".dg-agent/bin/hub",
        "mcp_tools": ".dg-agent/bin/mcp --list-tools",
        "agent_session": '.dg-agent/bin/agent --task "..." --file path/to/file',
        "agent_bridge": ".dg-agent/bin/agent-bridge --server opencode-acp",
    }
    report: dict[str, Any] = {
        "status": status,
        "repo": str(repo),
        "client": args.client,
        "generated_at": generated_at,
        "live": args.live,
        "workspace": {
            "complete": workspace["complete"],
            "dir": workspace["dir"],
        },
        "client_smoke": smoke_action,
        "hub": hub,
        "client_config": client_config,
        "capabilities_latest": capabilities,
        "commands": commands,
        "outputs": {},
    }

    if not args.no_write:
        workspace_dir = repo / ".dg-agent"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        json_path = workspace_dir / "client-handoff.json"
        md_path = workspace_dir / "CLIENT_HANDOFF.md"
        report["outputs"] = {
            "json": {"path": str(json_path), "status": "written"},
            "markdown": {"path": str(md_path), "status": "written"},
        }
        md_text = client_handoff_markdown(report)
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(md_text, encoding="utf-8")
    else:
        report["outputs"] = {
            "json": {"status": "skipped", "reason": "--no-write"},
            "markdown": {"status": "skipped", "reason": "--no-write"},
        }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG client report: {status}")
        print(f"repo: {repo}")
        print(f"client: {args.client}")
        for name, output in report["outputs"].items():
            path = output.get("path", "")
            suffix = f" {path}" if path else ""
            print(f"- {name}: {output['status']}{suffix}")
        print(f"- client-smoke: {smoke_action.get('status')}")
        print(f"- mcp config: {client_config.get('status')} {client_config.get('path', '')}")
    return 0 if status == "success" else 1


def agent_bridge_command(repo: Path, server: str, host: str, port: int) -> tuple[list[str], dict[str, Any]]:
    if server == "opencode-acp":
        actual_port = port or 3295
        cmd = [
            str(DG_ROOT / "scripts" / "dg_agent.sh"),
            "opencode-acp",
            "--",
            "--cwd",
            str(repo),
            "--hostname",
            host,
            "--port",
            str(actual_port),
        ]
        return cmd, {
            "transport": "http",
            "url": f"http://{host}:{actual_port}",
            "profile": "opencode_acp",
            "cwd": str(repo),
        }
    if server == "goose-serve":
        actual_port = port or 3294
        cmd = [
            str(DG_ROOT / "scripts" / "dg_agent.sh"),
            "goose-serve",
            "--",
            "--host",
            host,
            "--port",
            str(actual_port),
        ]
        return cmd, {
            "transport": "http-websocket",
            "url": f"http://{host}:{actual_port}",
            "profile": "goose_serve",
            "cwd": str(repo),
        }
    if server == "goose-acp":
        cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), "goose-acp"]
        return cmd, {
            "transport": "stdio",
            "url": "",
            "profile": "goose_acp",
            "cwd": str(repo),
        }
    if server == "openhands-acp":
        cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), "openhands-acp"]
        return cmd, {
            "transport": "stdio",
            "url": "",
            "profile": "openhands_acp",
            "cwd": str(repo),
        }
    raise ValueError(f"unknown agent bridge server: {server}")


def run_agent_bridge(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    actions: list[dict[str, Any]] = []
    if args.no_init:
        actions.append({"step": "client-init", "status": "skipped", "reason": "--no-init"})
    else:
        init_argv = ["client-init", "--repo", str(repo), "--client", args.client]
        if args.force_init:
            init_argv.append("--force")
        if args.init_target:
            init_argv.extend(["--target", args.init_target])
        if args.no_rules:
            init_argv.append("--no-rules")
        if args.no_oss_stack:
            init_argv.append("--no-oss-stack")
        actions.append(run_json_subcommand("client-init", init_argv, timeout=180))

    if args.ensure_stack:
        up_argv = ["up", "--wait-timeout", str(args.wait_timeout)]
        if args.restart_stack:
            up_argv.append("--restart")
        actions.append(run_json_subcommand("up", up_argv, timeout=int(args.wait_timeout) + 30))

    cmd, connect = agent_bridge_command(repo, args.server, args.host, args.port)
    failed = [item for item in actions if item.get("status") in {"blocked", "failed"} or item.get("returncode", 0) != 0]
    status = "blocked" if failed else ("starting" if args.start else "ready")
    report = {
        "status": status,
        "repo": str(repo),
        "server": args.server,
        "client_init_client": args.client,
        "connect": connect,
        "command": cmd,
        "shell_command": f"cd {shlex.quote(str(repo))} && {shlex.join(cmd)}",
        "actions": actions,
        "start": args.start,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"DG agent bridge: {status}")
        print(f"repo: {repo}")
        print(f"server: {args.server}")
        if connect.get("url"):
            print(f"url: {connect['url']}")
        print("command:")
        print(report["shell_command"])
        for action in actions:
            print(f"- {action['step']}: {action['status']}")
    if failed:
        return 1
    if not args.start:
        return 0
    os.chdir(repo)
    return exec_cmd(cmd)


def gpu_snapshot() -> dict[str, Any]:
    proc = run_cmd(
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
        timeout=10,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout).strip()}
    apps = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 3:
            apps.append({"pid": parts[0], "process_name": parts[1], "used_memory": parts[2]})
    mem = run_cmd(["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"], timeout=10)
    memory = ""
    if mem.returncode == 0:
        memory = mem.stdout.strip()
    return {"ok": True, "compute_apps": apps, "memory": memory}


def workspace_state(repo: Path) -> dict[str, Any]:
    workspace = repo / ".dg-agent"
    expected = [
        "client-pack.json",
        "env.sh",
        "README.md",
        "aider.dg-fast.conf.yml",
        "aider.dg-model-settings.yml",
        "aider.dg-model-metadata.json",
        "continue.config.yaml",
        "opencode.dg.json",
        "opencode.dg-agent.json",
        "opencode.dg-mcp.json",
        "openhands.dg.toml",
        "openhands.env",
        "qwen-code.mcp.json",
        "autogen.dg.json",
        "smolagents.dg.json",
        "langgraph.dg.json",
        "crewai.dg.json",
        "open-interpreter.dg.json",
        "llamaindex.dg.json",
        "haystack.dg.json",
        "swe-agent.dg.yaml",
        "mini-swe-agent.dg.yaml",
        "mcp-server.json",
        "mcp-client-snippets.json",
        "claude-code.mcp.json",
        "claude-desktop-mcp.json",
        "cursor.mcp.json",
        "vscode.mcp.json",
        "agent-instructions.md",
        "AGENTS.dg.md",
        "CLAUDE.dg.md",
        "copilot-instructions.dg.md",
        "diffusiongemma.instructions.md",
        "cursor-rules.dg.mdc",
        "goose-mcp.dg.yaml",
        "litellm-local-model-registry.json",
        "AGENT_HUB.md",
        "agent-hub.json",
        "COMMANDS.md",
        "command-kit.json",
        "commands/dg-report.md",
        "commands/dg-smoke.md",
        "commands/dg-context.md",
        "commands/dg-plan-task.md",
        "commands/dg-agent.md",
        "commands/dg-verify.md",
        "commands/dg-mcp-handoff.md",
        "commands/dg-codex.md",
        "claude-skill/SKILL.md",
        "CODEX.md",
        "codex.config.toml",
        "codex.env",
        "IDE_CLIENTS.md",
        "ide-client-snippets.json",
        "openai-compatible.local.json",
        "openai.env",
        "kilo-code.config.json",
        "bin/run",
        "bin/agent",
        "bin/context",
        "bin/rag",
        "bin/repo-pack",
        "bin/repo-map",
        "bin/ast-grep",
        "bin/code-outline",
        "bin/client-init",
        "bin/client-smoke",
        "bin/client-report",
        "bin/agent-commands",
        "bin/codex-profile",
        "bin/agent-bridge",
        "bin/hub",
        "bin/plan",
        "bin/edit",
        "bin/task",
        "bin/verify",
        "bin/status",
        "bin/doctor",
        "bin/up",
        "bin/down",
        "bin/preflight",
        "bin/capabilities",
        "bin/sessions",
        "bin/supervisor",
        "bin/web",
        "bin/aider",
        "bin/opencode",
        "bin/opencode-agent",
        "bin/opencode-mcp",
        "bin/opencode-acp",
        "bin/goose",
        "bin/goose-mcp",
        "bin/goose-acp",
        "bin/goose-serve",
        "bin/openhands",
        "bin/openhands-acp",
        "bin/openhands-mcp",
        "bin/qwen-code",
        "bin/autogen",
        "bin/smolagents",
        "bin/langgraph",
        "bin/crewai",
        "bin/open-interpreter",
        "bin/llamaindex",
        "bin/haystack",
        "bin/swe-agent",
        "bin/mini-swe-agent",
        "bin/mini-swe-run",
        "bin/mini-swe-runs",
        "bin/mcp",
        "bin/mcp-http",
        "bin/serena-mcp",
        "bin/mcp-client-config",
        "bin/agent-rules",
    ]
    files = [{"path": str(workspace / name), "exists": (workspace / name).exists()} for name in expected]
    launchers = [
        workspace / "bin" / name
        for name in [
            "run",
            "agent",
            "autonomous",
            "context",
            "rag",
            "repo-pack",
            "repo-map",
            "ast-grep",
            "code-outline",
            "client-init",
            "client-smoke",
            "client-report",
            "agent-commands",
            "codex-profile",
            "agent-bridge",
            "hub",
            "plan",
            "edit",
            "task",
            "verify",
            "status",
            "doctor",
            "up",
            "down",
            "preflight",
            "capabilities",
            "sessions",
            "supervisor",
            "web",
            "aider",
            "opencode",
            "opencode-agent",
            "opencode-mcp",
            "opencode-acp",
            "goose",
            "goose-mcp",
            "goose-acp",
            "goose-serve",
            "openhands",
            "openhands-acp",
            "openhands-mcp",
            "qwen-code",
            "autogen",
            "smolagents",
            "langgraph",
            "crewai",
            "open-interpreter",
            "llamaindex",
            "haystack",
            "swe-agent",
            "mini-swe-agent",
            "mini-swe-run",
            "mini-swe-runs",
            "mcp",
            "mcp-http",
            "serena-mcp",
            "mcp-client-config",
            "agent-rules",
        ]
    ]
    executable = [{"path": str(path), "executable": os.access(path, os.X_OK)} for path in launchers]
    return {
        "dir": str(workspace),
        "exists": workspace.exists(),
        "complete": all(item["exists"] for item in files) and all(item["executable"] for item in executable),
        "files": files,
        "launchers": executable,
    }


def run_preflight(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        result = {"status": "blocked", "repo": str(repo), "issues": [f"repo does not exist: {repo}"]}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"preflight: blocked\nrepo does not exist: {repo}")
        return 2

    git_root = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=repo, timeout=10)
    git_status = run_cmd(["git", "status", "--short"], cwd=repo, timeout=10)
    workspace = workspace_state(repo)
    wrappers = wrapper_component_audit()
    backend_ok, backend = http_json("http://127.0.0.1:4100/healthz")
    proxy_ok, proxy = http_json("http://127.0.0.1:8090/healthz")
    litellm_ok, litellm = http_json("http://127.0.0.1:4100/v1/models")
    gpu = gpu_snapshot()

    issues: list[str] = []
    warnings: list[str] = []
    if git_root.returncode != 0:
        warnings.append("target path is not inside a git repository")
    if git_status.returncode == 0 and git_status.stdout.strip() and not args.allow_dirty:
        warnings.append("repo has uncommitted changes; pass --allow-dirty to silence this warning")
    if not workspace["complete"]:
        issues.append("repo-local .dg-agent workspace is missing or incomplete; run workspace-init")
    core_wrapper_ids = {"mcp"}
    missing_wrappers = [row["id"] for row in wrappers if not row["installed"]]
    missing_core_wrappers = [name for name in missing_wrappers if name in core_wrapper_ids]
    missing_optional_wrappers = [name for name in missing_wrappers if name not in core_wrapper_ids]
    if missing_core_wrappers:
        issues.append("missing required agent runtime: " + ", ".join(missing_core_wrappers))
    if missing_optional_wrappers:
        warnings.append("optional OSS wrappers are not installed: " + ", ".join(missing_optional_wrappers))
    if not proxy_ok:
        warnings.append("Aider-compatible proxy is not healthy on 8090")
    if not litellm_ok:
        warnings.append("LiteLLM gateway is not healthy on 4100")
    if not backend_ok:
        warnings.append("backend model is not loaded on 4100; live generation requires scripts/dg_agent.sh up")

    static_ready = not issues
    live_ready = static_ready and backend_ok and proxy_ok
    if live_ready:
        status = "live-ready"
    elif static_ready:
        status = "static-ready"
    else:
        status = "needs-setup"

    file_args = " ".join(f"--file {shlex.quote(item)}" for item in args.file)
    task_text = shlex.quote(args.task or "...")
    agent_cmd = f"{DG_ROOT}/scripts/dg_agent.sh agent --repo {shlex.quote(str(repo))} --task {task_text}"
    if file_args:
        agent_cmd += " " + file_args
    result = {
        "status": status,
        "repo": str(repo),
        "git": {
            "is_git_repo": git_root.returncode == 0,
            "root": git_root.stdout.strip() if git_root.returncode == 0 else "",
            "dirty": bool(git_status.stdout.strip()) if git_status.returncode == 0 else None,
            "status_short": git_status.stdout,
        },
        "workspace": workspace,
        "wrappers": wrappers,
        "wrapper_readiness": {
            "required": sorted(core_wrapper_ids),
            "missing_required": missing_core_wrappers,
            "missing_optional": missing_optional_wrappers,
        },
        "services": {
            "backend": {"ok": backend_ok, "detail": backend},
            "proxy": {"ok": proxy_ok, "detail": proxy},
            "litellm": {"ok": litellm_ok, "detail": litellm},
        },
        "gpu": gpu,
        "issues": issues,
        "warnings": warnings,
        "next": {
            "workspace_init": f"{DG_ROOT}/scripts/dg_agent.sh workspace-init --repo {shlex.quote(str(repo))}",
            "start_stack": f"{DG_ROOT}/scripts/dg_agent.sh up",
            "agent": agent_cmd,
            "repo_local_agent": ".dg-agent/bin/agent --task \"...\" --file path",
        },
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"DG agent preflight: {status}")
        print(f"repo: {repo}")
        print(f"workspace: {'ok' if workspace['complete'] else 'incomplete'} {workspace['dir']}")
        if missing_core_wrappers:
            print(f"wrappers: required missing {', '.join(missing_core_wrappers)}")
        elif missing_optional_wrappers:
            print(f"wrappers: core ok; optional missing {', '.join(missing_optional_wrappers)}")
        else:
            print("wrappers: core and optional tools installed")
        print(f"services: backend={backend_ok} proxy={proxy_ok} litellm={litellm_ok}")
        if gpu.get("ok"):
            print(f"gpu compute apps: {len(gpu.get('compute_apps', []))} memory={gpu.get('memory')}")
        if issues:
            print("issues:")
            for issue in issues:
                print(f"- {issue}")
        if warnings:
            print("warnings:")
            for warning in warnings:
                print(f"- {warning}")
        print("next:")
        print(f"- {result['next']['workspace_init']}")
        print(f"- {result['next']['start_stack']}")
        print(f"- {result['next']['agent']}")
    return 0 if static_ready else 1


def load_json_output(proc: subprocess.CompletedProcess[str]) -> Any:
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"parse_error": True, "stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}


def run_agent_orchestrator(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    actions: list[dict[str, Any]] = []
    if not repo.exists() or not repo.is_dir():
        result = {"status": "blocked", "repo": str(repo), "issues": [f"repo does not exist: {repo}"], "actions": actions}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"DG agent run: blocked\nrepo does not exist: {repo}")
        return 2

    if not args.no_init and not workspace_state(repo)["complete"]:
        cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), "workspace-init", "--repo", str(repo), "--json"]
        if args.force_init:
            cmd.append("--force")
        proc = run_cmd(cmd, timeout=60)
        data = load_json_output(proc)
        actions.append({"step": "workspace-init", "returncode": proc.returncode, "report": data})
        if proc.returncode != 0:
            result = {"status": "blocked", "repo": str(repo), "issues": ["workspace-init failed"], "actions": actions}
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("DG agent run: blocked")
                print("workspace-init failed; pass --force-init if .dg-agent files changed intentionally")
            return proc.returncode

    preflight_cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), "preflight", "--repo", str(repo), "--task", args.task, "--json"]
    for item in args.file:
        preflight_cmd.extend(["--file", item])
    if args.allow_dirty:
        preflight_cmd.append("--allow-dirty")
    preflight_proc = run_cmd(preflight_cmd, timeout=60)
    preflight = load_json_output(preflight_proc)
    actions.append({"step": "preflight", "returncode": preflight_proc.returncode, "report": preflight})

    if isinstance(preflight, dict) and preflight.get("status") == "needs-setup":
        result = {"status": "blocked", "repo": str(repo), "issues": preflight.get("issues", []), "actions": actions}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("DG agent run: blocked")
            for issue in result["issues"]:
                print(f"- {issue}")
        return 1

    live_ready = isinstance(preflight, dict) and preflight.get("status") == "live-ready"
    if not live_ready and args.start:
        up_cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), "up", "--json", "--wait-timeout", str(args.wait_timeout)]
        if args.restart:
            up_cmd.append("--restart")
        up_proc = run_cmd(up_cmd, timeout=int(args.wait_timeout) + 30)
        actions.append({"step": "up", "returncode": up_proc.returncode, "report": load_json_output(up_proc)})
        if up_proc.returncode != 0:
            result = {"status": "blocked", "repo": str(repo), "issues": ["failed to start backend/proxy/LiteLLM"], "actions": actions}
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("DG agent run: blocked")
                print("failed to start backend/proxy/LiteLLM")
            return up_proc.returncode
        preflight_proc = run_cmd(preflight_cmd, timeout=60)
        preflight = load_json_output(preflight_proc)
        actions.append({"step": "preflight-after-start", "returncode": preflight_proc.returncode, "report": preflight})
        live_ready = isinstance(preflight, dict) and preflight.get("status") == "live-ready"

    agent_cmd = [str(DG_ROOT / "scripts" / "dg_agent.sh"), "agent", "--repo", str(repo), "--task", args.task]
    for item in args.file:
        agent_cmd.extend(["--file", item])
    if args.out_dir:
        agent_cmd.extend(["--out-dir", args.out_dir])
    if args.test_cmd:
        agent_cmd.extend(["--test-cmd", args.test_cmd])
    if args.no_auto_test:
        agent_cmd.append("--no-auto-test")
    agent_cmd.extend(["--max-files", str(args.max_files)])
    agent_cmd.extend(["--max-snippet-chars", str(args.max_snippet_chars)])
    agent_cmd.extend(["--test-timeout", str(args.test_timeout)])
    agent_cmd.extend(["--aider-timeout", str(args.aider_timeout)])
    agent_cmd.extend(["--repair-attempts", str(args.repair_attempts)])
    agent_cmd.extend(["--wall-timeout", str(args.wall_timeout)])
    if args.no_rollback:
        agent_cmd.append("--no-rollback")
    if args.allow_dirty:
        agent_cmd.append("--allow-dirty")
    if args.no_deterministic_first:
        agent_cmd.append("--no-deterministic-first")

    if args.dry_run:
        result = {
            "status": "dry-run",
            "repo": str(repo),
            "live_ready": live_ready,
            "actions": actions,
            "would_run": agent_cmd,
            "requires_start": not live_ready,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("DG agent run: dry-run")
            print(f"repo: {repo}")
            print(f"live_ready: {live_ready}")
            print("would run:")
            print(" ".join(shlex.quote(part) for part in agent_cmd))
            if not live_ready:
                print("backend is not live; pass --start to load the model before executing")
        return 0

    if not live_ready:
        result = {
            "status": "needs-start",
            "repo": str(repo),
            "issues": ["backend/proxy not live; pass --start to load the model before executing"],
            "actions": actions,
            "would_run": agent_cmd,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("DG agent run: needs-start")
            print("backend/proxy not live; pass --start to load the model before executing")
        return 1

    if args.json:
        print(json.dumps({"status": "executing", "repo": str(repo), "actions": actions, "command": agent_cmd}, ensure_ascii=False, indent=2))
    return exec_cmd(agent_cmd)


def stack_watchdog_script() -> Path:
    return DG_ROOT / "scripts" / "run_stack_watchdog.sh"


def fallback_service_status(timeout: float) -> dict[str, Any]:
    services = {
        "backend": "http://127.0.0.1:4100/healthz",
        "proxy": "http://127.0.0.1:8090/healthz",
        "litellm": "http://127.0.0.1:4100/v1/models",
    }
    result: dict[str, Any] = {"status": "fallback", "watchdog": str(stack_watchdog_script()), "services": {}}
    for name, url in services.items():
        http_ok, payload = http_json(url, timeout=max(1, int(timeout)))
        semantic_ok = http_ok
        if isinstance(payload, dict) and "ok" in payload:
            semantic_ok = bool(payload.get("ok"))
        if name == "litellm" and isinstance(payload, dict):
            semantic_ok = http_ok and bool(payload.get("data"))
        result["services"][name] = {"ok": semantic_ok, "http_ok": http_ok, "url": url, "detail": payload}
    result["ok"] = all(item["ok"] for item in result["services"].values())
    return result


def print_fallback_service_status(result: dict[str, Any]) -> None:
    print("DG stack status fallback")
    print(f"watchdog: missing ({result['watchdog']})")
    for name, item in result["services"].items():
        mark = "ok" if item["ok"] else "bad"
        print(f"{name}: {mark} {item['url']}")


def ensure_stack() -> int:
    script = stack_watchdog_script()
    if not script.exists():
        result = fallback_service_status(3)
        print_fallback_service_status(result)
        print("cannot ensure stack: run_stack_watchdog.sh is missing in this checkout")
        return 1
    return exec_cmd([str(script), "ensure"])


def run_stack_status(args: argparse.Namespace) -> int:
    script = stack_watchdog_script()
    if not script.exists():
        result = fallback_service_status(args.timeout)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_fallback_service_status(result)
        return 0 if result["ok"] else 1
    cmd = [str(script), "status"]
    if args.json:
        cmd.append("--json")
    cmd.extend(["--timeout", str(args.timeout)])
    return exec_cmd(cmd)


def run_stack_up(args: argparse.Namespace) -> int:
    script = stack_watchdog_script()
    if not script.exists():
        result = fallback_service_status(3)
        if args.json:
            result["error"] = "run_stack_watchdog.sh is missing in this checkout; use the WSL Windows start wrappers or restore scripts/run_stack_watchdog.sh"
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_fallback_service_status(result)
            print("cannot start stack: run_stack_watchdog.sh is missing in this checkout")
        return 1
    cmd = [str(script), "ensure"]
    if args.json:
        cmd.append("--json")
    if args.restart:
        cmd.append("--restart")
    cmd.extend(["--wait-timeout", str(args.wait_timeout)])
    return exec_cmd(cmd)


def run_stack_down(args: argparse.Namespace) -> int:
    script = stack_watchdog_script()
    if not script.exists():
        print("cannot stop stack: run_stack_watchdog.sh is missing in this checkout")
        return 1
    services = args.services or ["all"]
    return exec_cmd([str(script), "stop", *services])


def run_capabilities_command(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.live:
        script_args.append("--live")
    if args.json:
        script_args.append("--json")
    if args.out:
        script_args.extend(["--out", str(Path(args.out).resolve())])
    if args.no_save:
        script_args.append("--no-save")
    if args.latest:
        script_args.append("--latest")
    if args.path_only:
        script_args.append("--path-only")
    script_args.extend(["--timeout", str(args.timeout)])
    try:
        cmd = agent_python_command(DG_ROOT / "scripts" / "dg_agent_capabilities.py", script_args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return exec_cmd(cmd)


def run_smokes(args: argparse.Namespace) -> int:
    suites = args.suite or [
        "context",
        "auto-test",
        "verify",
        "session",
        "sessions",
        "session-artifacts",
        "agent",
        "autonomous",
        "capabilities",
        "proxy-adapter",
        "supervisor",
        "wrappers",
        "bootstrap",
        "client-pack",
        "workspace-init",
        "client-init",
        "client-smoke",
        "client-report",
        "agent-commands",
        "codex-profile",
        "ide-clients",
        "agent-bridge",
        "external-agents",
        "mini-swe-runner",
        "autogen",
        "smolagents",
        "langgraph",
        "crewai",
        "open-interpreter",
        "llamaindex",
        "haystack",
        "repo-map",
        "preflight",
        "run",
        "edit",
        "task",
        "agentapi",
        "goose",
        "goose-mcp",
        "goose-acp",
        "openhands-acp",
        "openhands-mcp",
        "qwen-code",
        "litellm",
        "gateway-clients",
        "openai-sdk",
        "mcp",
        "mcp-http",
        "serena-mcp",
        "ast-grep",
        "code-outline",
        "watchdog",
        "stack-control",
        "opencode-provider",
        "opencode-agent",
        "opencode-run",
    ]
    scripts = {
        "context": "smoke_dg_agent_context_plan.sh",
        "auto-test": "smoke_dg_agent_auto_test.sh",
        "verify": "smoke_dg_agent_verify.sh",
        "session": "smoke_dg_agent_session.sh",
        "sessions": "smoke_dg_agent_sessions.sh",
        "session-artifacts": "smoke_dg_agent_session_artifacts.sh",
        "agent": "smoke_dg_agent_agent.sh",
        "autonomous": "smoke_persistent_supervisor.sh",
        "capabilities": "smoke_dg_agent_capabilities.sh",
        "proxy-adapter": "smoke_aider_proxy_adapter.sh",
        "supervisor": "smoke_supervisor_agent.sh",
        "wrappers": "smoke_dg_agent_wrappers.sh",
        "bootstrap": "smoke_dg_agent_bootstrap.sh",
        "client-pack": "smoke_dg_agent_client_pack.sh",
        "workspace-init": "smoke_dg_agent_workspace_init.sh",
        "client-init": "smoke_client_init.sh",
        "client-smoke": "smoke_client_smoke.sh",
        "client-report": "smoke_client_report.sh",
        "agent-commands": "smoke_agent_commands.sh",
        "codex-profile": "smoke_codex_profile.sh",
        "ide-clients": "smoke_ide_client_profiles.sh",
        "agent-bridge": "smoke_agent_bridge.sh",
        "external-agents": "smoke_external_agent_profiles.sh",
        "mini-swe-runner": "smoke_mini_swe_runner.sh",
        "autogen": "smoke_autogen_local.sh",
        "smolagents": "smoke_smolagents_local.sh",
        "langgraph": "smoke_langgraph_local.sh",
        "crewai": "smoke_crewai_local.sh",
        "open-interpreter": "smoke_open_interpreter_local.sh",
        "llamaindex": "smoke_llamaindex_local.sh",
        "haystack": "smoke_haystack_local.sh",
        "repo-map": "smoke_repo_map.sh",
        "preflight": "smoke_dg_agent_preflight.sh",
        "run": "smoke_dg_agent_run.sh",
        "edit": "smoke_dg_agent_edit.sh",
        "task": "smoke_task_runner.sh",
        "agentapi": "smoke_agentapi_aider.sh",
        "goose": "smoke_goose_local.sh",
        "goose-mcp": "smoke_goose_mcp_local.sh",
        "goose-acp": "smoke_goose_acp_local.sh",
        "openhands-acp": "smoke_openhands_acp_local.sh",
        "openhands-mcp": "smoke_openhands_mcp_local.sh",
        "qwen-code": "smoke_qwen_code_local.sh",
        "litellm": "smoke_litellm_gateway.sh",
        "gateway-clients": "smoke_gateway_clients.sh",
        "openai-sdk": "smoke_openai_sdk_gateway.sh",
        "openai-tool-loop": "smoke_openai_tool_loop.sh",
        "mcp": "smoke_mcp_server.sh",
        "mcp-http": "smoke_mcp_http_server.sh",
        "serena-mcp": "smoke_serena_mcp.sh",
        "ast-grep": "smoke_ast_grep.sh",
        "code-outline": "smoke_code_outline.sh",
        "watchdog": "smoke_stack_watchdog.sh",
        "stack-control": "smoke_stack_control.sh",
        "opencode-provider": "smoke_opencode_local.sh",
        "opencode-agent": "smoke_opencode_agent_local.sh",
        "opencode-run": "smoke_opencode_run_fallback.sh",
        "opencode-mcp": "smoke_opencode_mcp_local.sh",
        "opencode-acp": "smoke_opencode_acp_local.sh",
    }
    failed = False
    for suite in suites:
        script = scripts.get(suite)
        if not script:
            print(f"unknown smoke suite: {suite}", file=sys.stderr)
            return 2
        print(f"\n=== smoke: {suite} ===")
        proc = run_cmd([str(DG_ROOT / "scripts" / script)], timeout=args.timeout)
        print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        if proc.returncode != 0:
            failed = True
            if not args.keep_going:
                return proc.returncode
    return 1 if failed else 0


def run_edit(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    step: dict[str, Any] = {
        "name": "edit",
        "task": args.task,
        "max_files": args.max_files,
        "aider_timeout": args.aider_timeout,
        "repair_attempts": args.repair_attempts,
    }
    if args.file:
        step["files"] = args.file
        step["max_files"] = max(args.max_files, len(args.file))
    test_cmd = args.test_cmd
    if not test_cmd and args.auto_test:
        test_cmd = detect_test_cmd(repo, args.file)
        if test_cmd:
            print(f"Auto test command: {test_cmd}", flush=True)
    if test_cmd:
        step["test_cmd"] = test_cmd
    if args.no_deterministic_first:
        step["no_deterministic_first"] = True

    plan = {
        "stop_on_failure": True,
        "defaults": {
            "max_files": args.max_files,
            "aider_timeout": args.aider_timeout,
            "repair_attempts": args.repair_attempts,
            "test_timeout": args.test_timeout,
        },
        "steps": [step],
    }

    report = Path(args.report).resolve() if args.report else Path(tempfile.mktemp(prefix="dg-edit-report.", suffix=".json"))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json", prefix="dg-edit-plan.") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2)
        plan_path = Path(handle.name)

    cmd = [
        str(DG_ROOT / "scripts" / "run_task_runner.sh"),
        "--repo",
        str(repo),
        "--plan",
        str(plan_path),
        "--report",
        str(report),
    ]
    if args.rollback_on_failure:
        cmd.append("--rollback-on-failure")
    if args.allow_dirty:
        cmd.append("--allow-dirty")
    if args.dry_run:
        cmd.append("--dry-run")

    print(f"Generated temporary plan: {plan_path}", flush=True)
    print(f"Aggregate report: {report}", flush=True)
    return exec_cmd(cmd)


def ranked_context(repo: Path, task: str, forced_files: list[str], max_files: int, max_snippet_chars: int) -> dict[str, Any]:
    from dg_supervisor_agent import extract_terms, list_files, score_files, snippet_for

    ignored_parts = {
        ".git",
        ".venv",
        ".venv-aider",
        ".venv-litellm",
        ".tools",
        "__pycache__",
        "archives",
        "bench-results",
        "models",
        "runlogs",
        "snapshots",
    }

    def eligible(path: Path) -> bool:
        if any(part in ignored_parts for part in path.parts):
            return False
        if path.suffix.lower() in {".pyc", ".log", ".csv"}:
            return False
        try:
            return not (path.suffix.lower() == ".html" and (repo / path).stat().st_size > 100_000)
        except OSError:
            return False

    all_files = [path for path in list_files(repo) if eligible(path)]
    ranked = score_files(repo, all_files, task)
    selected: list[Path] = []
    for item in forced_files:
        rel = Path(item)
        if rel not in selected:
            selected.append(rel)
    for cand in ranked:
        if len(selected) >= max_files:
            break
        if cand.path not in selected:
            selected.append(cand.path)

    by_path = {cand.path: cand for cand in ranked}
    files: list[dict[str, Any]] = []
    for rel in selected:
        cand = by_path.get(rel)
        lines = cand.lines if cand else set()
        reasons = cand.reasons[:8] if cand else ["forced file"]
        files.append(
            {
                "path": rel.as_posix(),
                "score": cand.score if cand else 0,
                "lines": sorted(lines),
                "reasons": reasons,
                "snippet": snippet_for(repo, rel, lines, max_chars=max_snippet_chars),
            }
        )

    return {
        "repo": str(repo),
        "task": task,
        "terms": extract_terms(task),
        "selected_files": [item["path"] for item in files],
        "files": files,
        "ranked": [
            {
                "path": cand.path.as_posix(),
                "score": cand.score,
                "lines": sorted(cand.lines),
                "reasons": cand.reasons[:8],
            }
            for cand in ranked[:20]
        ],
    }


def context_markdown(data: dict[str, Any]) -> str:
    lines: list[str] = [
        "# DG Context Pack",
        "",
        f"Repo: `{data['repo']}`",
        f"Task: {data['task']}",
        "",
        "## Selected Files",
    ]
    for file_data in data["files"]:
        reasons = "; ".join(file_data["reasons"][:4])
        lines.append(f"- `{file_data['path']}` score={file_data['score']} {reasons}")
    lines.extend(["", "## Snippets"])
    for file_data in data["files"]:
        lines.extend(["", f"### {file_data['path']}", "", "```text", file_data["snippet"].rstrip(), "```"])
    return "\n".join(lines).rstrip() + "\n"


def run_context(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    data = ranked_context(repo, args.task, args.file, args.max_files, args.max_snippet_chars)
    output = json.dumps(data, ensure_ascii=False, indent=2) if args.json else context_markdown(data)
    if args.out:
        path = Path(args.out).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(path)
    else:
        print(output, end="")
    return 0


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo).resolve()
    data = ranked_context(repo, args.task, args.file, args.max_files, args.max_snippet_chars)
    files = args.file or data["selected_files"][: args.max_files]
    step: dict[str, Any] = {
        "name": args.name,
        "task": args.task,
        "files": files,
        "max_files": max(args.max_files, len(files)),
        "aider_timeout": args.aider_timeout,
        "repair_attempts": args.repair_attempts,
    }
    test_cmd = args.test_cmd
    if not test_cmd and args.auto_test:
        test_cmd = detect_test_cmd(repo, files)
    if test_cmd:
        step["test_cmd"] = test_cmd
        step.setdefault("metadata", {})["test_source"] = "auto" if args.auto_test and not args.test_cmd else "user"
    if args.no_deterministic_first:
        step["no_deterministic_first"] = True
    return {
        "stop_on_failure": True,
        "defaults": {
            "max_files": args.max_files,
            "aider_timeout": args.aider_timeout,
            "repair_attempts": args.repair_attempts,
            "test_timeout": args.test_timeout,
        },
        "metadata": {
            "generated_by": "dg_agent plan",
            "repo": str(repo),
            "selected_files": data["selected_files"],
            "ranked": data["ranked"][:10],
        },
        "steps": [step],
    }


def detect_test_cmd(repo: Path, files: list[str]) -> str:
    rels = [Path(item) for item in files if item]
    suffixes = {rel.suffix.lower() for rel in rels}

    if rels and suffixes <= {".py"}:
        return "python3 -m py_compile " + " ".join(shlex.quote(rel.as_posix()) for rel in rels)
    if rels and suffixes <= {".sh"}:
        return "bash -n " + " ".join(shlex.quote(rel.as_posix()) for rel in rels)
    if len(rels) == 1 and rels[0].suffix.lower() == ".json":
        return "python3 -m json.tool " + shlex.quote(rels[0].as_posix()) + " >/dev/null"

    if (repo / "go.mod").exists():
        return "go test ./..."
    if (repo / "Cargo.toml").exists():
        return "cargo test"
    if (repo / "package.json").exists():
        try:
            package = json.loads((repo / "package.json").read_text(encoding="utf-8"))
            scripts = package.get("scripts") if isinstance(package, dict) else {}
            if isinstance(scripts, dict) and "test" in scripts:
                return "npm test -- --runInBand"
        except Exception:
            return ""
    if (repo / "pyproject.toml").exists() or (repo / "pytest.ini").exists() or (repo / "tests").exists():
        return "python3 -m pytest -q"
    return ""


def run_verify(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    command = args.test_cmd or detect_test_cmd(repo, args.file)
    if not command:
        print("No verification command could be inferred. Pass --test-cmd or --file hints.", file=sys.stderr)
        return 2

    started = time.time()
    proc = subprocess.run(
        command,
        cwd=str(repo),
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout,
        check=False,
        executable="/bin/bash",
    )
    elapsed = time.time() - started
    output = (proc.stdout + "\n" + proc.stderr).strip()
    report = {
        "repo": str(repo),
        "command": command,
        "returncode": proc.returncode,
        "status": "success" if proc.returncode == 0 else "failed",
        "elapsed_sec": round(elapsed, 3),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "output_tail": output[-4000:],
        "files": args.file,
        "source": "user" if args.test_cmd else "auto",
    }
    if args.report:
        path = Path(args.report).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Verification command: {command}")
        print(f"Status: {report['status']} rc={proc.returncode} elapsed={report['elapsed_sec']}s")
        if output:
            print(output[-4000:])
        if args.report:
            print(f"Report: {Path(args.report).resolve()}")
    return proc.returncode


def git_capture(repo: Path, args: list[str], timeout: int = 60) -> str:
    proc = run_cmd(["git", *args], cwd=repo, timeout=timeout)
    return proc.stdout if proc.returncode == 0 else (proc.stdout + proc.stderr)


def run_session(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    session_root = Path(args.out_dir).resolve() if args.out_dir else DEFAULT_SESSION_ROOT
    stamp = time.strftime("%Y%m%d-%H%M%S")
    slug = "".join(ch if ch.isalnum() else "-" for ch in args.task.lower())[:48].strip("-") or "session"
    session_dir = session_root / f"{stamp}-{slug}"
    session_dir.mkdir(parents=True, exist_ok=False)

    forced_files = args.file or []
    context_data = ranked_context(repo, args.task, forced_files, args.max_files, args.max_snippet_chars)
    (session_dir / "context.json").write_text(json.dumps(context_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (session_dir / "context.md").write_text(context_markdown(context_data), encoding="utf-8")

    class PlanArgs:
        pass

    plan_args = PlanArgs()
    plan_args.repo = str(repo)
    plan_args.task = args.task
    plan_args.file = forced_files
    plan_args.max_files = args.max_files
    plan_args.max_snippet_chars = args.max_snippet_chars
    plan_args.name = "session-edit"
    plan_args.test_cmd = args.test_cmd
    plan_args.auto_test = args.auto_test
    plan_args.test_timeout = args.test_timeout
    plan_args.aider_timeout = args.aider_timeout
    plan_args.repair_attempts = args.repair_attempts
    plan_args.no_deterministic_first = args.no_deterministic_first

    plan = build_plan(plan_args)  # type: ignore[arg-type]
    plan_path = session_dir / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    before_status = git_capture(repo, ["status", "--short"])
    before_diff = git_capture(repo, ["diff", "--binary", "--", "."])
    (session_dir / "before.status.txt").write_text(before_status, encoding="utf-8")
    (session_dir / "before.diff").write_text(before_diff, encoding="utf-8")

    task_report = session_dir / "task-report.json"
    task_cmd = [
        str(DG_ROOT / "scripts" / "run_task_runner.sh"),
        "--repo",
        str(repo),
        "--plan",
        str(plan_path),
        "--report",
        str(task_report),
    ]
    if args.rollback_on_failure:
        task_cmd.append("--rollback-on-failure")
    if args.allow_dirty:
        task_cmd.append("--allow-dirty")
    if args.dry_run:
        task_cmd.append("--dry-run")

    print(f"Session dir: {session_dir}", flush=True)
    print(f"Context: {session_dir / 'context.md'}", flush=True)
    print(f"Plan: {plan_path}", flush=True)
    task_started = time.time()
    try:
        task_proc = run_cmd(task_cmd, timeout=args.wall_timeout)
    except subprocess.TimeoutExpired as exc:
        task_proc = subprocess.CompletedProcess(
            task_cmd,
            124,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=f"session task timed out after {exc.timeout}s",
        )
    task_elapsed = time.time() - task_started
    (session_dir / "task.stdout.log").write_text(task_proc.stdout, encoding="utf-8")
    (session_dir / "task.stderr.log").write_text(task_proc.stderr, encoding="utf-8")
    if task_proc.stdout:
        print(task_proc.stdout[-6000:], end="")
    if task_proc.stderr:
        print(task_proc.stderr[-4000:], end="", file=sys.stderr)

    verify_report = session_dir / "verify.json"
    verify_rc: int | None = None
    test_cmd = ""
    if plan["steps"] and isinstance(plan["steps"][0], dict):
        test_cmd = str(plan["steps"][0].get("test_cmd") or "")
    if args.verify_after and test_cmd and task_proc.returncode == 0 and not args.dry_run:
        verify_args = argparse.Namespace(
            repo=str(repo),
            file=forced_files or plan["steps"][0].get("files", []),
            test_cmd=test_cmd,
            timeout=args.test_timeout,
            report=str(verify_report),
            json=False,
        )
        verify_rc = run_verify(verify_args)

    after_status = git_capture(repo, ["status", "--short"])
    after_diff = git_capture(repo, ["diff", "--binary", "--", "."])
    (session_dir / "after.status.txt").write_text(after_status, encoding="utf-8")
    (session_dir / "final.diff").write_text(after_diff, encoding="utf-8")

    session_report = {
        "repo": str(repo),
        "task": args.task,
        "session_dir": str(session_dir),
        "task_returncode": task_proc.returncode,
        "verify_returncode": verify_rc,
        "status": "success" if task_proc.returncode == 0 and (verify_rc in (None, 0)) else "failed",
        "task_elapsed_sec": round(task_elapsed, 3),
        "artifacts": {
            "context_md": str(session_dir / "context.md"),
            "context_json": str(session_dir / "context.json"),
            "plan": str(plan_path),
            "task_report": str(task_report),
            "verify_report": str(verify_report) if verify_report.exists() else "",
            "final_diff": str(session_dir / "final.diff"),
            "before_status": str(session_dir / "before.status.txt"),
            "after_status": str(session_dir / "after.status.txt"),
            "before_diff": str(session_dir / "before.diff"),
            "task_stdout": str(session_dir / "task.stdout.log"),
            "task_stderr": str(session_dir / "task.stderr.log"),
            "session_json": str(session_dir / "session.json"),
        },
    }
    (session_dir / "session.json").write_text(json.dumps(session_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Session status: {session_report['status']}")
    print(f"Session report: {session_dir / 'session.json'}")
    return task_proc.returncode if task_proc.returncode != 0 else (verify_rc or 0)


def infer_agent_mode(task: str) -> str:
    lowered = task.lower()
    if any(marker in lowered for marker in AGENT_EDIT_MARKERS):
        return "edit"
    if any(marker in lowered for marker in AGENT_READ_MARKERS):
        return "read"
    words = {item.lower() for item in re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", task)}
    if words & AGENT_EDIT_KEYWORDS:
        return "edit"
    if words & AGENT_READ_KEYWORDS:
        return "read"
    return "read"


def agent_run_dir(args: argparse.Namespace, selected_mode: str) -> Path:
    if args.out_dir:
        root = Path(args.out_dir).resolve()
        if root.suffix:
            root = root.parent
    else:
        root = DEFAULT_AGENT_ROOT
    stamp = time.strftime("%Y%m%d-%H%M%S")
    slug = "".join(ch if ch.isalnum() else "-" for ch in args.task.lower())[:48].strip("-") or "agent"
    path = root / f"{stamp}-{selected_mode}-{slug}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def usable_agent_read_answer(value: Any) -> bool:
    text = str(value or "").strip()
    if len(text) < 24:
        return False
    return "<|channel>thought" not in text and "<|channel>analysis" not in text


def run_agent_read(args: argparse.Namespace, selected_mode: str) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    run_dir = agent_run_dir(args, selected_mode)
    transcript = run_dir / "tool-loop.json"
    canonical_report_path = run_dir / "agent.json"
    report_path = Path(args.report).resolve() if args.report else canonical_report_path
    python_bin = DG_ROOT / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = DG_ROOT / ".venv-litellm" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)

    cmd = [
        str(python_bin),
        str(DG_ROOT / "scripts" / "dg_openai_tool_loop.py"),
        "--repo",
        str(repo),
        "--task",
        args.task,
        "--base-url",
        args.base_url,
        "--model",
        args.model,
        "--tool-manifest-url",
        args.tool_manifest_url,
        "--tool-runtime-url",
        args.tool_runtime_url,
        "--max-steps",
        str(args.max_steps),
        "--max-tokens",
        str(args.max_tokens),
        "--temperature",
        str(args.temperature),
        "--timeout",
        str(args.timeout),
        "--read-only",
        "--json",
        "--out",
        str(transcript),
    ]
    for tool in args.tool:
        cmd.extend(["--tool", tool])
    for tool in args.exclude_tool:
        cmd.extend(["--exclude-tool", tool])
    if args.stop_after_tool:
        cmd.append("--stop-after-tool")
    if args.no_deterministic_first:
        cmd.append("--no-deterministic-first")

    started = time.time()
    proc = subprocess.run(cmd, cwd=str(DG_ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    elapsed = time.time() - started
    (run_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    report = {
        "repo": str(repo),
        "task": args.task,
        "mode": selected_mode,
        "route": "openai_tool_loop_read_only",
        "run_dir": str(run_dir),
        "returncode": proc.returncode,
        "status": "success" if proc.returncode == 0 else "failed",
        "elapsed_sec": round(elapsed, 3),
        "command": cmd,
        "artifacts": {
            "transcript": str(transcript),
            "stdout": str(run_dir / "stdout.log"),
            "stderr": str(run_dir / "stderr.log"),
            "agent_json": str(canonical_report_path),
            "requested_report": str(report_path) if report_path != canonical_report_path else "",
        },
    }
    if transcript.exists():
        try:
            transcript_data = json.loads(transcript.read_text(encoding="utf-8"))
            report["tool_names"] = transcript_data.get("tool_names")
            report["final_content"] = transcript_data.get("final_content")
            report["steps"] = transcript_data.get("steps")
            report["route"] = transcript_data.get("route", report["route"])
        except Exception as exc:
            report["transcript_error"] = str(exc)

    if report["status"] == "success" and not usable_agent_read_answer(report.get("final_content")):
        context = ranked_context(repo, args.task, args.file, args.max_files, args.max_snippet_chars)
        context_json = run_dir / "deterministic-context.json"
        context_md = run_dir / "deterministic-context.md"
        context_json.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        context_md.write_text(context_markdown(context) + "\n", encoding="utf-8")
        report["route"] = "deterministic_context_fallback"
        report["answer_mode"] = "retrieval_only"
        report["fallback_reason"] = "model did not produce a usable final answer or tool call"
        report["model_final_content"] = report.get("final_content", "")
        report["final_content"] = (
            "Reliable repository context (the model output was not used because it did not produce a usable final answer):\n\n"
            + context_markdown(context)
        )
        report["artifacts"].update(
            {
                "deterministic_context_json": str(context_json),
                "deterministic_context_markdown": str(context_md),
            }
        )

    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    canonical_report_path.write_text(report_text, encoding="utf-8")
    if report_path != canonical_report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Agent mode: {selected_mode}")
        print(f"Agent route: {report['route']}")
        print(f"Agent status: {report['status']} rc={proc.returncode}")
        if report.get("final_content"):
            print("\n" + str(report["final_content"]).strip())
        elif proc.stdout:
            print(proc.stdout[-4000:], end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr[-2000:], file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
        print(f"Agent report: {report_path}")
    return proc.returncode


def run_agent(args: argparse.Namespace) -> int:
    selected_mode = infer_agent_mode(args.task) if args.mode == "auto" else args.mode
    if selected_mode == "read":
        return run_agent_read(args, selected_mode)

    session_args = argparse.Namespace(
        repo=args.repo,
        task=args.task,
        file=args.file,
        out_dir=args.out_dir,
        test_cmd=args.test_cmd,
        auto_test=not args.no_auto_test,
        max_files=args.max_files,
        max_snippet_chars=args.max_snippet_chars,
        test_timeout=args.test_timeout,
        aider_timeout=args.aider_timeout,
        repair_attempts=args.repair_attempts,
        wall_timeout=args.wall_timeout,
        rollback_on_failure=not args.no_rollback,
        allow_dirty=args.allow_dirty,
        dry_run=args.dry_run,
        verify_after=True,
        no_deterministic_first=args.no_deterministic_first,
    )
    rc = run_session(session_args)
    if args.json:
        print(json.dumps({"mode": selected_mode, "route": "session", "returncode": rc}, ensure_ascii=False, indent=2))
    return rc


def session_reports(root: Path) -> list[dict[str, Any]]:
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
        "session_json": report.get("_session_json"),
        "task_returncode": report.get("task_returncode"),
        "verify_returncode": report.get("verify_returncode"),
        "task_elapsed_sec": report.get("task_elapsed_sec"),
        "final_diff_bytes": final_diff.stat().st_size if final_diff.exists() else 0,
    }


def print_session_summary(summary: dict[str, Any]) -> None:
    print(f"{summary.get('status')} task_rc={summary.get('task_returncode')} verify_rc={summary.get('verify_returncode')}")
    print(f"repo: {summary.get('repo')}")
    print(f"task: {summary.get('task')}")
    print(f"session: {summary.get('session_dir')}")
    print(f"diff bytes: {summary.get('final_diff_bytes')}")


def load_session_report(root: Path, reports: list[dict[str, Any]], session: str, latest: bool, default_latest: bool) -> dict[str, Any] | None:
    if latest or (default_latest and not session):
        return reports[0] if reports else None

    if not session:
        return None

    if session.isdigit():
        index = int(session) - 1
        if 0 <= index < len(reports):
            return reports[index]

    path = Path(session)
    if path.is_dir():
        path = path / "session.json"
    if not path.is_absolute():
        path = root / path
        if path.is_dir():
            path = path / "session.json"
    if not path.exists():
        return None

    report = json.loads(path.read_text(encoding="utf-8"))
    report["_session_json"] = str(path)
    return report


def available_session_artifacts() -> list[str]:
    return sorted(set(SESSION_ARTIFACT_FILENAMES) | set(SESSION_ARTIFACT_ALIASES))


def session_artifact_path(report: dict[str, Any], artifact: str) -> tuple[str, Path | None]:
    key = SESSION_ARTIFACT_ALIASES.get(artifact, artifact)
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}

    raw_path = str(artifacts.get(key) or "")
    if not raw_path and key == "session_json":
        raw_path = str(report.get("_session_json") or "")
    if not raw_path:
        session_dir = Path(str(report.get("session_dir") or ""))
        filename = SESSION_ARTIFACT_FILENAMES.get(key)
        if session_dir and filename:
            raw_path = str(session_dir / filename)
    if not raw_path:
        return key, None
    return key, Path(raw_path)


def print_session_artifact(report: dict[str, Any], artifact: str, path_only: bool) -> int:
    key, path = session_artifact_path(report, artifact)
    if path is None:
        print(f"Unknown session artifact: {artifact}", file=sys.stderr)
        print("Available artifacts: " + ", ".join(available_session_artifacts()), file=sys.stderr)
        return 2
    if not path.exists():
        print(f"Session artifact is missing: {key} -> {path}", file=sys.stderr)
        return 2
    if path_only:
        print(path)
        return 0
    print(path.read_text(encoding="utf-8", errors="replace"), end="")
    return 0


def run_sessions(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else DEFAULT_SESSION_ROOT
    reports = session_reports(root)
    if args.sessions_command == "list":
        summaries = [session_summary(item) for item in reports[: args.limit]]
        if args.json:
            print(json.dumps({"root": str(root), "sessions": summaries}, ensure_ascii=False, indent=2))
        else:
            if not summaries:
                print(f"No sessions found under {root}")
                return 0
            for idx, summary in enumerate(summaries, start=1):
                print(f"\n[{idx}]")
                print_session_summary(summary)
        return 0

    if args.sessions_command == "show":
        report = load_session_report(root, reports, args.session, args.latest, default_latest=False)
        if report is None:
            print("No session found.", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_session_summary(session_summary(report))
            artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
            if artifacts:
                print("\nArtifacts:")
                for name, path in artifacts.items():
                    if path:
                        print(f"  {name}: {path}")
        return 0

    if args.sessions_command == "diff":
        report = load_session_report(root, reports, args.session, args.latest, default_latest=True)
        if report is None:
            print("No session found.", file=sys.stderr)
            return 2
        return print_session_artifact(report, "final_diff", args.path_only)

    if args.sessions_command == "artifact":
        report = load_session_report(root, reports, args.session, args.latest, default_latest=True)
        if report is None:
            print("No session found.", file=sys.stderr)
            return 2
        return print_session_artifact(report, args.artifact, args.path_only)

    print(f"unknown sessions command: {args.sessions_command}", file=sys.stderr)
    return 2


def agent_run_reports(root: Path) -> list[dict[str, Any]]:
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


def print_agent_run_summary(summary: dict[str, Any]) -> None:
    print(f"{summary.get('status')} mode={summary.get('mode')} rc={summary.get('returncode')} route={summary.get('route')}")
    print(f"repo: {summary.get('repo')}")
    print(f"task: {summary.get('task')}")
    print(f"run: {summary.get('run_dir')}")
    print(f"steps: {summary.get('steps')} elapsed: {summary.get('elapsed_sec')}s")
    print(f"tools: {', '.join(str(item) for item in (summary.get('tool_names') or []))}")
    print(f"transcript bytes: {summary.get('transcript_bytes')}")


def load_agent_run_report(root: Path, reports: list[dict[str, Any]], run: str, latest: bool, default_latest: bool) -> dict[str, Any] | None:
    if latest or (default_latest and not run):
        return reports[0] if reports else None
    if not run:
        return None
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
        path = root / path
        if path.is_dir():
            path = path / "agent.json"
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    report["_agent_json"] = str(path)
    return report


def available_agent_run_artifacts() -> list[str]:
    return sorted(set(AGENT_RUN_ARTIFACT_FILENAMES) | set(AGENT_RUN_ARTIFACT_ALIASES))


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
        filename = AGENT_RUN_ARTIFACT_FILENAMES.get(key)
        if run_dir and filename:
            raw_path = str(run_dir / filename)
    if not raw_path:
        return key, None
    path = Path(raw_path)
    run_dir_text = str(report.get("run_dir") or "")
    if run_dir_text:
        run_dir = Path(run_dir_text).resolve()
        try:
            resolved = path.resolve()
        except Exception:
            return key, None
        if resolved != run_dir and run_dir not in resolved.parents:
            return key, None
    return key, path


def print_agent_run_artifact(report: dict[str, Any], artifact: str, path_only: bool) -> int:
    key, path = agent_run_artifact_path(report, artifact)
    if path is None:
        print(f"Unknown agent run artifact: {artifact}", file=sys.stderr)
        print("Available artifacts: " + ", ".join(available_agent_run_artifacts()), file=sys.stderr)
        return 2
    if not path.exists():
        print(f"Agent run artifact is missing: {key} -> {path}", file=sys.stderr)
        return 2
    if path_only:
        print(path)
        return 0
    print(path.read_text(encoding="utf-8", errors="replace"), end="")
    return 0


def run_agent_runs(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else DEFAULT_AGENT_ROOT
    reports = agent_run_reports(root)
    if args.agent_runs_command == "list":
        summaries = [agent_run_summary(item) for item in reports[: args.limit]]
        if args.json:
            print(json.dumps({"root": str(root), "runs": summaries}, ensure_ascii=False, indent=2))
        else:
            if not summaries:
                print(f"No agent runs found under {root}")
                return 0
            for idx, summary in enumerate(summaries, start=1):
                print(f"\n[{idx}]")
                print_agent_run_summary(summary)
        return 0

    if args.agent_runs_command == "show":
        report = load_agent_run_report(root, reports, args.run, args.latest, default_latest=False)
        if report is None:
            print("No agent run found.", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_agent_run_summary(agent_run_summary(report))
            artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
            if artifacts:
                print("\nArtifacts:")
                for name, path in artifacts.items():
                    if path:
                        print(f"  {name}: {path}")
        return 0

    if args.agent_runs_command == "artifact":
        report = load_agent_run_report(root, reports, args.run, args.latest, default_latest=True)
        if report is None:
            print("No agent run found.", file=sys.stderr)
            return 2
        return print_agent_run_artifact(report, args.artifact, args.path_only)

    print(f"unknown agent-runs command: {args.agent_runs_command}", file=sys.stderr)
    return 2


def mini_swe_reports(root: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if not root.exists():
        return reports
    for path in root.rglob("report.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_report_json"] = str(path)
            data["_mtime"] = path.stat().st_mtime
            reports.append(data)
        except Exception:
            continue
    reports.sort(key=lambda item: float(item.get("_mtime", 0)), reverse=True)
    return reports


def mini_swe_summary(report: dict[str, Any]) -> dict[str, Any]:
    trajectory = Path(str(report.get("trajectory") or ""))
    return {
        "status": report.get("status"),
        "task": report.get("task"),
        "repo": report.get("repo"),
        "run_dir": report.get("run_dir"),
        "report_json": report.get("_report_json"),
        "returncode": report.get("returncode"),
        "elapsed_sec": report.get("elapsed_sec"),
        "trajectory_exists": bool(report.get("trajectory_exists")) or trajectory.exists(),
        "trajectory_bytes": trajectory.stat().st_size if trajectory.exists() else int(report.get("trajectory_bytes") or 0),
    }


def print_mini_swe_summary(summary: dict[str, Any]) -> None:
    print(f"{summary.get('status')} rc={summary.get('returncode')} elapsed={summary.get('elapsed_sec')}")
    print(f"repo: {summary.get('repo')}")
    print(f"task: {summary.get('task')}")
    print(f"run: {summary.get('run_dir')}")
    print(f"trajectory bytes: {summary.get('trajectory_bytes')}")


def load_mini_swe_report(root: Path, reports: list[dict[str, Any]], run: str, latest: bool, default_latest: bool) -> dict[str, Any] | None:
    if latest or (default_latest and not run):
        return reports[0] if reports else None
    if not run:
        return None
    if run.isdigit():
        index = int(run) - 1
        if 0 <= index < len(reports):
            return reports[index]
    path = Path(run)
    if path.is_dir():
        path = path / "report.json"
    if not path.is_absolute():
        path = root / path
        if path.is_dir():
            path = path / "report.json"
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    report["_report_json"] = str(path)
    return report


def mini_swe_artifact_path(report: dict[str, Any], artifact: str) -> tuple[str, Path | None]:
    key = MINI_SWE_ARTIFACT_ALIASES.get(artifact, artifact)
    if key == "report":
        raw = str(report.get("_report_json") or "")
    elif key == "trajectory":
        raw = str(report.get("trajectory") or "")
    elif key == "command":
        raw = str(report.get("command_file") or "")
        if not raw:
            run_dir = Path(str(report.get("run_dir") or ""))
            raw = str(run_dir / "command.sh") if run_dir else ""
    else:
        raw = str(report.get(key) or "")
    if not raw:
        return key, None
    return key, Path(raw)


def print_mini_swe_artifact(report: dict[str, Any], artifact: str, path_only: bool) -> int:
    key, path = mini_swe_artifact_path(report, artifact)
    if path is None:
        print(f"Unknown mini-SWE artifact: {artifact}", file=sys.stderr)
        print("Available artifacts: " + ", ".join(sorted(MINI_SWE_ARTIFACT_ALIASES)), file=sys.stderr)
        return 2
    if not path.exists():
        print(f"Mini-SWE artifact is missing: {key} -> {path}", file=sys.stderr)
        return 2
    if path_only:
        print(path)
        return 0
    print(path.read_text(encoding="utf-8", errors="replace"), end="")
    return 0


def run_mini_swe_runs(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else DEFAULT_MINI_SWE_ROOT
    reports = mini_swe_reports(root)
    if args.mini_swe_runs_command == "list":
        summaries = [mini_swe_summary(item) for item in reports[: args.limit]]
        if args.json:
            print(json.dumps({"root": str(root), "runs": summaries}, ensure_ascii=False, indent=2))
        else:
            if not summaries:
                print(f"No mini-SWE runs found under {root}")
                return 0
            for idx, summary in enumerate(summaries, start=1):
                print(f"\n[{idx}]")
                print_mini_swe_summary(summary)
        return 0

    if args.mini_swe_runs_command == "show":
        report = load_mini_swe_report(root, reports, args.run, args.latest, default_latest=False)
        if report is None:
            print("No mini-SWE run found.", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_mini_swe_summary(mini_swe_summary(report))
            print("\nArtifacts:")
            for name in ["report", "trajectory", "stdout", "stderr", "command"]:
                _, path = mini_swe_artifact_path(report, name)
                if path:
                    print(f"  {name}: {path}")
        return 0

    if args.mini_swe_runs_command == "artifact":
        report = load_mini_swe_report(root, reports, args.run, args.latest, default_latest=True)
        if report is None:
            print("No mini-SWE run found.", file=sys.stderr)
            return 2
        return print_mini_swe_artifact(report, args.artifact, args.path_only)

    print(f"unknown mini-swe-runs command: {args.mini_swe_runs_command}", file=sys.stderr)
    return 2


def run_plan(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    plan = build_plan(args)
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.out:
        path = Path(args.out).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
        print(path)
    else:
        print(output)
    return 0


def run_task_command(args: argparse.Namespace) -> int:
    cmd = [
        str(DG_ROOT / "scripts" / "run_task_runner.sh"),
        "--repo",
        args.repo,
        "--plan",
        args.plan,
    ]
    if args.report:
        cmd.extend(["--report", args.report])
    if args.supervisor:
        cmd.extend(["--supervisor", args.supervisor])
    if args.step_report_dir:
        cmd.extend(["--step-report-dir", args.step_report_dir])
    if args.allow_dirty:
        cmd.append("--allow-dirty")
    if args.dry_run:
        cmd.append("--dry-run")
    if args.rollback_on_failure:
        cmd.append("--rollback-on-failure")
    if args.continue_on_failure:
        cmd.append("--continue-on-failure")
    return exec_cmd(cmd)


def run_rag_command(args: argparse.Namespace) -> int:
    python_bin = DG_ROOT / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)
    cmd = [
        str(python_bin),
        str(DG_ROOT / "scripts" / "rag_code_agent.py"),
        "--repo",
        args.repo,
        "--max-context-chars",
        str(args.max_context_chars),
        "--max-files",
        str(args.max_files),
        "--max-tokens",
        str(args.max_tokens),
        "--timeout",
        str(args.timeout),
    ]
    if args.base_url:
        cmd.extend(["--base-url", args.base_url])
    if args.model:
        cmd.extend(["--model", args.model])
    if args.print_context:
        cmd.append("--print-context")
    if args.debug:
        cmd.append("--debug")
    cmd.extend(["--task", args.task])
    return exec_cmd(cmd)


def run_openai_tool_loop_command(args: argparse.Namespace) -> int:
    python_bin = DG_ROOT / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = DG_ROOT / ".venv-litellm" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)
    cmd = [
        str(python_bin),
        str(DG_ROOT / "scripts" / "dg_openai_tool_loop.py"),
        "--task",
        args.task,
        "--base-url",
        args.base_url,
        "--model",
        args.model,
        "--tool-manifest-url",
        args.tool_manifest_url,
        "--tool-runtime-url",
        args.tool_runtime_url,
        "--max-steps",
        str(args.max_steps),
        "--max-tokens",
        str(args.max_tokens),
        "--temperature",
        str(args.temperature),
        "--timeout",
        str(args.timeout),
    ]
    if args.repo:
        cmd.extend(["--repo", args.repo])
    if args.system:
        cmd.extend(["--system", args.system])
    if args.stop_after_tool:
        cmd.append("--stop-after-tool")
    if args.include_execute_command:
        cmd.append("--include-execute-command")
    for tool in args.tool:
        cmd.extend(["--tool", tool])
    for tool in args.exclude_tool:
        cmd.extend(["--exclude-tool", tool])
    if args.read_only:
        cmd.append("--read-only")
    if args.json:
        cmd.append("--json")
    if args.out:
        cmd.extend(["--out", args.out])
    return exec_cmd(cmd)


def repomix_npx() -> Path | str:
    local_npx = DG_ROOT / ".tools" / "node" / "bin" / "npx"
    if local_npx.exists():
        return local_npx
    return shutil.which("npx") or "npx"


def repomix_env() -> dict[str, str]:
    env = os.environ.copy()
    node_bin = DG_ROOT / ".tools" / "node" / "bin"
    if node_bin.exists():
        env["PATH"] = str(node_bin) + os.pathsep + env.get("PATH", "")
    return env


def run_repo_pack_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    command = [
        str(repomix_npx()),
        "--yes",
        "repomix",
        str(repo),
        "--style",
        args.style,
        "--top-files-len",
        str(args.top_files_len),
    ]
    if args.stdout or not args.output:
        command.append("--stdout")
    else:
        command.extend(["--output", str(Path(args.output).resolve())])
    if args.compress:
        command.append("--compress")
    if args.include_diffs:
        command.append("--include-diffs")
    if args.output_show_line_numbers:
        command.append("--output-show-line-numbers")
    if args.remove_comments:
        command.append("--remove-comments")
    if args.remove_empty_lines:
        command.append("--remove-empty-lines")
    if args.no_files:
        command.append("--no-files")
    if args.no_security_check:
        command.append("--no-security-check")
    if args.token_budget > 0:
        command.extend(["--token-budget", str(args.token_budget)])
    if args.include:
        command.extend(["--include", ",".join(args.include)])
    if args.ignore:
        command.extend(["--ignore", ",".join(args.ignore)])

    proc = subprocess.run(command, cwd=str(repo), env=repomix_env(), check=False)
    return proc.returncode


def run_repo_map_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    aider_runner = DG_ROOT / "scripts" / "run_aider_local.sh"
    if not aider_runner.exists():
        print(f"Aider runner is missing: {aider_runner}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", env.get("AIDER_OPENAI_API_KEY", "dummy"))
    base_url = args.base_url or env.get("AIDER_OPENAI_API_BASE", "http://127.0.0.1:8090/v1")
    api_key = args.api_key or env.get("AIDER_OPENAI_API_KEY", "dummy")
    model = args.model or env.get("DG_AIDER_MODEL", "openai/diffusiongemma-26b-a4b-it-iq4xs-aider-local")
    preexisting_tag_caches = {path.resolve() for path in repo.glob(".aider.tags.cache.v*") if path.exists()}

    with tempfile.TemporaryDirectory(prefix="dg-aider-repo-map.") as tmp:
        tmp_path = Path(tmp)
        runner_path = str(aider_runner)
        repo_path = str(repo)
        metadata_path = str(AIDER_MODEL_METADATA)
        settings_path = str(AIDER_MODEL_SETTINGS)
        history_path = str(tmp_path / "input.history")
        chat_history_path = str(tmp_path / "chat.history.md")
        llm_history_path = str(tmp_path / "llm.history.md")
        command_prefix: list[str] = []
        if os.name == "nt":
            wsl = shutil.which("wsl.exe") or shutil.which("wsl")
            if not wsl:
                print("WSL is unavailable for the installed Aider runtime", file=sys.stderr)
                return 2

            def to_wsl_path(path: str) -> str:
                proc = subprocess.run(
                    [wsl, "--exec", "wslpath", "-a", path],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                    check=False,
                )
                if proc.returncode != 0 or not proc.stdout.strip():
                    raise RuntimeError(proc.stderr.strip() or f"cannot convert path: {path}")
                return proc.stdout.strip()

            try:
                runner_path, repo_path, metadata_path, settings_path, history_path, chat_history_path, llm_history_path = [
                    to_wsl_path(path)
                    for path in [runner_path, repo_path, metadata_path, settings_path, history_path, chat_history_path, llm_history_path]
                ]
            except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                print(f"Cannot prepare WSL Aider command: {exc}", file=sys.stderr)
                return 2
            command_prefix = [wsl, "--exec", "bash"]
        command = [
            *command_prefix,
            runner_path,
            "--repo",
            repo_path,
            "--model",
            model,
            "--openai-api-base",
            base_url,
            "--openai-api-key",
            api_key,
            "--model-metadata-file",
            metadata_path,
            "--model-settings-file",
            settings_path,
            "--edit-format",
            "whole",
            "--map-tokens",
            str(args.map_tokens),
            "--map-refresh",
            "always",
            "--show-repo-map",
            "--yes-always",
            "--no-analytics",
            "--no-gitignore",
            "--no-auto-commits",
            "--no-dirty-commits",
            "--no-stream",
            "--no-check-update",
            "--no-show-release-notes",
            "--no-show-model-warnings",
            "--no-check-model-accepts-settings",
            "--input-history-file",
            history_path,
            "--chat-history-file",
            chat_history_path,
            "--llm-history-file",
            llm_history_path,
            "--exit",
        ]
        command.extend(args.paths)
        try:
            proc = subprocess.run(
                command,
                cwd=str(repo),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            if stdout:
                print(stdout, end="" if stdout.endswith("\n") else "\n")
            print(f"repo-map timed out after {args.timeout}s", file=sys.stderr)
            if stderr:
                print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
            return 124

    for cache_dir in repo.glob(".aider.tags.cache.v*"):
        try:
            resolved = cache_dir.resolve()
        except OSError:
            continue
        if resolved not in preexisting_tag_caches and cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)

    stdout = proc.stdout
    stderr = proc.stderr
    if args.map_only:
        marker = "Here are summaries of some files present in my git repository."
        idx = stdout.find(marker)
        if idx >= 0:
            stdout = stdout[idx:]
    if args.max_chars > 0 and len(stdout) > args.max_chars:
        stdout = stdout[: args.max_chars] + "\n[truncated]\n"
        stderr += f"\ndg_repo_map: truncated stdout by --max-chars={args.max_chars}\n"

    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
    return proc.returncode


def run_ast_grep_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    if not any([args.pattern, args.kind, args.selector]):
        print("ast-grep requires --pattern, --kind, or --selector", file=sys.stderr)
        return 2

    command = [str(repomix_npx()), "--yes", "-p", "@ast-grep/cli", "sg", "run"]
    if args.lang:
        command.extend(["--lang", args.lang])
    if args.pattern:
        command.extend(["--pattern", args.pattern])
    if args.kind:
        command.extend(["--kind", args.kind])
    if args.selector:
        command.extend(["--selector", args.selector])
    if args.strictness:
        command.extend(["--strictness", args.strictness])
    if args.context:
        command.extend(["--context", str(args.context)])
    for glob in args.glob:
        command.extend(["--globs", glob])
    command.extend(["--color", "never"])
    if args.files_with_matches:
        command.append("--files-with-matches")
    elif args.json:
        command.append("--json=compact")
    command.extend(args.paths or ["."])

    try:
        proc = subprocess.run(
            command,
            cwd=str(repo),
            env=repomix_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        print(f"ast-grep timed out after {args.timeout}s", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
        return 124

    stdout = proc.stdout
    stderr = proc.stderr
    if args.json and not args.files_with_matches and stdout.strip():
        try:
            matches = json.loads(stdout)
            if isinstance(matches, list) and len(matches) > args.max_matches:
                stdout = json.dumps(matches[: args.max_matches], ensure_ascii=False)
                stderr += f"\ndg_ast_grep: truncated {len(matches) - args.max_matches} matches by --max-matches\n"
        except Exception:
            pass
    if args.max_chars > 0 and len(stdout) > args.max_chars:
        stdout = stdout[: args.max_chars] + "\n[truncated]\n"
        stderr += f"\ndg_ast_grep: truncated stdout by --max-chars={args.max_chars}\n"

    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
    if proc.returncode == 1 and not proc.stderr.strip():
        return 0
    return proc.returncode


def run_code_outline_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    command = [str(repomix_npx()), "--yes", "-p", "@ast-grep/cli", "sg", "outline"]
    if args.lang:
        command.extend(["--lang", args.lang])
    if args.items:
        command.extend(["--items", args.items])
    if args.view:
        command.extend(["--view", args.view])
    if args.type:
        command.extend(["--type", args.type])
    if args.match:
        command.extend(["--match", args.match])
    if args.pub_members:
        command.append("--pub-members")
    for glob in args.glob:
        command.extend(["--globs", glob])
    command.extend(["--color", "never"])
    if args.json:
        command.append("--json=compact")
    command.extend(args.paths or ["."])

    try:
        proc = subprocess.run(
            command,
            cwd=str(repo),
            env=repomix_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        print(f"code-outline timed out after {args.timeout}s", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
        return 124

    stdout = proc.stdout
    stderr = proc.stderr
    if proc.returncode != 0 and (args.lang or "").lower() in {"python", "py"}:
        fallback_stdout, fallback_stderr = python_code_outline_fallback(args, repo)
        if fallback_stdout:
            stdout = fallback_stdout
            stderr = (stderr + "\n" if stderr else "") + fallback_stderr
            proc_returncode = 0
        else:
            proc_returncode = proc.returncode
    else:
        proc_returncode = proc.returncode
    if args.json and stdout.strip() and args.max_items > 0:
        try:
            entries = json.loads(stdout)
            if isinstance(entries, list):
                kept_entries: list[dict[str, Any]] = []
                total_items = 0
                kept_items = 0
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    items = entry.get("items")
                    if not isinstance(items, list):
                        kept_entries.append(entry)
                        continue
                    total_items += len(items)
                    remaining = args.max_items - kept_items
                    if remaining <= 0:
                        continue
                    clipped = dict(entry)
                    clipped["items"] = items[:remaining]
                    kept_items += len(clipped["items"])
                    if clipped["items"]:
                        kept_entries.append(clipped)
                if total_items > kept_items:
                    stdout = json.dumps(kept_entries, ensure_ascii=False)
                    stderr += f"\ndg_code_outline: truncated {total_items - kept_items} symbols by --max-items\n"
        except Exception:
            pass
    if args.max_chars > 0 and len(stdout) > args.max_chars:
        stdout = stdout[: args.max_chars] + "\n[truncated]\n"
        stderr += f"\ndg_code_outline: truncated stdout by --max-chars={args.max_chars}\n"

    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
    if proc_returncode == 1 and not proc.stderr.strip():
        return 0
    return proc_returncode


def python_code_outline_fallback(args: argparse.Namespace, repo: Path) -> tuple[str, str]:
    files = python_outline_files(repo, args.paths or ["."], args.glob)
    entries: list[dict[str, Any]] = []
    total_items = 0
    kept_items = 0
    for file in files:
        try:
            source = file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file))
        except SyntaxError as exc:
            rel = file.relative_to(repo).as_posix()
            entries.append({"path": rel, "items": [], "error": f"syntax error at line {exc.lineno}"})
            continue
        except OSError:
            continue

        rel = file.relative_to(repo).as_posix()
        items = python_outline_items(tree, args)
        total_items += len(items)
        if args.max_items > 0:
            remaining = args.max_items - kept_items
            if remaining <= 0:
                items = []
            else:
                items = items[:remaining]
                kept_items += len(items)
        if items:
            entries.append({"path": rel, "items": items})

    if args.json:
        stdout = json.dumps(entries, ensure_ascii=False)
    else:
        stdout = render_python_outline_text(entries)
    stderr = "dg_code_outline: upstream ast-grep outline failed; used Python AST fallback"
    if args.max_items > 0 and total_items > kept_items:
        stderr += f"\ndg_code_outline: truncated {total_items - kept_items} symbols by --max-items"
    if args.max_chars > 0 and len(stdout) > args.max_chars:
        stdout = stdout[: args.max_chars] + "\n[truncated]\n"
        stderr += f"\ndg_code_outline: truncated stdout by --max-chars={args.max_chars}"
    return stdout, stderr


def python_outline_files(repo: Path, paths: list[str], globs: list[str]) -> list[Path]:
    files: list[Path] = []
    ignored_dirs = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__"}
    for raw in paths:
        target = (repo / raw).resolve()
        try:
            target.relative_to(repo)
        except ValueError:
            continue
        if target.is_file():
            candidates = [target]
        elif target.is_dir():
            candidates = [
                path
                for path in target.rglob("*.py")
                if not any(part in ignored_dirs for part in path.relative_to(repo).parts)
            ]
        else:
            candidates = []
        for path in candidates:
            rel = path.relative_to(repo).as_posix()
            if globs and not any(fnmatch.fnmatch(rel, pattern) for pattern in globs):
                continue
            if path.suffix == ".py":
                files.append(path)
    return sorted(dict.fromkeys(files), key=lambda item: item.relative_to(repo).as_posix())


def python_outline_items(tree: ast.AST, args: argparse.Namespace) -> list[dict[str, Any]]:
    wanted_types = {item.strip() for item in (args.type or "").split(",") if item.strip()}
    matcher = re.compile(args.match) if args.match else None
    items: list[dict[str, Any]] = []
    for node in getattr(tree, "body", []):
        item = python_outline_node(node, include_members=True)
        if not item:
            continue
        if wanted_types and item.get("symbolType") not in wanted_types:
            continue
        haystack = f"{item.get('name', '')} {item.get('signature', '')}"
        if matcher and not matcher.search(haystack):
            continue
        items.append(item)
    return items


def python_outline_node(node: ast.AST, *, include_members: bool) -> dict[str, Any] | None:
    if isinstance(node, ast.ClassDef):
        item: dict[str, Any] = {
            "name": node.name,
            "symbolType": "class",
            "kind": "class",
            "line": node.lineno,
            "endLine": getattr(node, "end_lineno", node.lineno),
            "signature": f"class {node.name}",
        }
        if include_members:
            members = [
                member
                for child in node.body
                if (member := python_outline_node(child, include_members=False)) is not None
            ]
            if members:
                item["members"] = members
        return item
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return {
            "name": node.name,
            "symbolType": "function",
            "kind": "function",
            "line": node.lineno,
            "endLine": getattr(node, "end_lineno", node.lineno),
            "signature": f"{prefix} {node.name}{python_args_signature(node.args)}",
        }
    return None


def python_args_signature(args: ast.arguments) -> str:
    names: list[str] = []
    for arg in [*args.posonlyargs, *args.args]:
        names.append(arg.arg)
    if args.vararg:
        names.append("*" + args.vararg.arg)
    for arg in args.kwonlyargs:
        names.append(arg.arg)
    if args.kwarg:
        names.append("**" + args.kwarg.arg)
    return "(" + ", ".join(names) + ")"


def render_python_outline_text(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in entries:
        lines.append(str(entry.get("path") or ""))
        for item in entry.get("items", []):
            signature = item.get("signature") or item.get("name") or ""
            line = item.get("line")
            lines.append(f"  {signature}" + (f"  L{line}" if line else ""))
            for member in item.get("members", []):
                member_signature = member.get("signature") or member.get("name") or ""
                member_line = member.get("line")
                lines.append(f"    {member_signature}" + (f"  L{member_line}" if member_line else ""))
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified launcher for the local DiffusionGemma agent stack.")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check backend, proxy, Aider, AgentAPI and OpenCode readiness")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    sub.add_parser("ensure", help="Ensure backend, proxy and LiteLLM are healthy")

    wrappers = sub.add_parser("wrappers", help="Show ready-made OSS agent wrappers around the local model")
    wrappers.add_argument("--json", action="store_true")

    bootstrap = sub.add_parser("bootstrap", help="Audit or install local OSS agent wrappers")
    bootstrap.add_argument("--only", action="append", default=[], help="Component id or comma-list: aider, agentapi, opencode, goose, litellm, mcp, serena, openhands, qwen-code, autogen, smolagents, langgraph, crewai, open-interpreter, llamaindex, haystack, mini-swe-agent, swe-agent")
    bootstrap.add_argument("--external", action="store_true", help="Include optional OpenHands/Qwen/AutoGen/smolagents/LangGraph/CrewAI/Open Interpreter/LlamaIndex/Haystack/SWE-family CLI wrappers")
    bootstrap.add_argument("--install", action="store_true", help="Run existing install_*_local.sh scripts for missing wrappers")
    bootstrap.add_argument("--refresh", action="store_true", help="Run install scripts even when checks already exist")
    bootstrap.add_argument("--smoke-static", action="store_true", help="Run static wrapper checks that do not load the model backend")
    bootstrap.add_argument("--smoke-installed", action="store_true", help="Run component smokes; some require live proxy/backend")
    bootstrap.add_argument("--install-timeout", type=int, default=420)
    bootstrap.add_argument("--smoke-timeout", type=int, default=180)
    bootstrap.add_argument("--keep-going", action="store_true")
    bootstrap.add_argument("--json", action="store_true")

    client_pack = sub.add_parser("client-pack", help="Show or export client profiles for OSS agents and IDEs")
    client_pack.add_argument("--json", action="store_true")
    client_pack.add_argument("--env", action="store_true", help="Print shell env vars for OpenAI-compatible clients")
    client_pack.add_argument("--write", action="store_true", help="Write configs/client_profiles/agent-client-pack.json")

    workspace_init = sub.add_parser("workspace-init", help="Write repo-local .dg-agent profiles for local OSS agent clients")
    workspace_init.add_argument("--repo", required=True)
    workspace_init.add_argument("--force", action="store_true", help="Overwrite changed .dg-agent files")
    workspace_init.add_argument("--json", action="store_true")

    mcp_client_config = sub.add_parser("mcp-client-config", help="Install or print MCP client config for a repo/client")
    mcp_client_config.add_argument("--repo", default=".", help="Target repo for project-local clients")
    mcp_client_config.add_argument("--client", required=True, choices=["claude-code", "claude-desktop", "cursor", "vscode"])
    mcp_client_config.add_argument("--target", default="", help="Explicit config path; useful for Claude Desktop global config")
    mcp_client_config.add_argument("--force", action="store_true", help="Replace existing conflicting managed server entries")
    mcp_client_config.add_argument("--dry-run", action="store_true")
    mcp_client_config.add_argument("--with-repomix", action="store_true", help="Also install the optional native Repomix MCP server entry")
    mcp_client_config.add_argument("--with-serena", action="store_true", help="Also install the optional native Serena semantic/LSP MCP server entry")
    mcp_client_config.add_argument("--with-oss-stack", action="store_true", help="Install the recommended DG+Repomix+Serena MCP server bundle")
    mcp_client_config.add_argument("--print-template", action="store_true")
    mcp_client_config.add_argument("--json", action="store_true")

    agent_rules = sub.add_parser("agent-rules", help="Install DG/MCP instruction files for external agent clients")
    agent_rules.add_argument("--repo", default=".", help="Target repo")
    agent_rules.add_argument("--target", default="all", choices=["all", "agents", "claude", "copilot", "vscode", "cursor"])
    agent_rules.add_argument("--force", action="store_true", help="Overwrite generated dedicated rule files when they differ")
    agent_rules.add_argument("--dry-run", action="store_true")
    agent_rules.add_argument("--print-template", action="store_true")
    agent_rules.add_argument("--json", action="store_true")

    agent_commands = sub.add_parser("agent-commands", help="Install repo-local workflow command kit for external clients")
    agent_commands.add_argument("--repo", default=".", help="Target repo")
    agent_commands.add_argument("--target", default="all", choices=["all", "claude-skill"])
    agent_commands.add_argument("--force", action="store_true", help="Overwrite generated command files when they differ")
    agent_commands.add_argument("--dry-run", action="store_true")
    agent_commands.add_argument("--print-template", action="store_true")
    agent_commands.add_argument("--json", action="store_true")

    codex_profile = sub.add_parser("codex-profile", help="Install Codex CLI project config for the local DG model")
    codex_profile.add_argument("--repo", default=".", help="Target repo")
    codex_profile.add_argument("--target", default="all", choices=["all", "config"])
    codex_profile.add_argument("--force", action="store_true", help="Overwrite generated Codex config when it differs")
    codex_profile.add_argument("--dry-run", action="store_true")
    codex_profile.add_argument("--print-template", action="store_true")
    codex_profile.add_argument("--json", action="store_true")

    client_init = sub.add_parser("client-init", help="One-shot repo bootstrap for IDE/agent clients")
    client_init.add_argument("--repo", required=True, help="Target repo")
    client_init.add_argument("--client", required=True, choices=["claude-code", "claude-desktop", "cursor", "vscode"])
    client_init.add_argument("--target", default="", help="Explicit MCP config path; useful for Claude Desktop global config")
    client_init.add_argument("--force", action="store_true", help="Overwrite generated workspace/client files where supported")
    client_init.add_argument("--dry-run", action="store_true", help="Preview MCP/rules changes; workspace-init is reported as would_run")
    client_init.add_argument("--no-workspace", action="store_true", help="Skip .dg-agent workspace initialization")
    client_init.add_argument("--no-rules", action="store_true", help="Skip AGENTS/Claude/Copilot/VS Code/Cursor instruction files")
    client_init.add_argument("--rules-target", default="all", choices=["all", "agents", "claude", "copilot", "vscode", "cursor"])
    client_init.add_argument("--no-oss-stack", action="store_true", help="Do not install the default DG+Repomix+Serena MCP bundle")
    client_init.add_argument("--with-repomix", action="store_true", help="With --no-oss-stack, add native Repomix MCP")
    client_init.add_argument("--with-serena", action="store_true", help="With --no-oss-stack, add native Serena MCP")
    client_init.add_argument("--json", action="store_true")

    client_smoke = sub.add_parser("client-smoke", help="Validate target repo readiness for external IDE/agent clients")
    client_smoke.add_argument("--repo", required=True, help="Target repo")
    client_smoke.add_argument("--client", default="cursor", choices=["claude-code", "claude-desktop", "cursor", "vscode"])
    client_smoke.add_argument("--target", default="", help="Explicit MCP config path")
    client_smoke.add_argument("--force-init", action="store_true", help="Force generated files during preparatory client-init")
    client_smoke.add_argument("--no-init", action="store_true", help="Do not run client-init before checks")
    client_smoke.add_argument("--no-rules", action="store_true", help="Do not require agent instruction files")
    client_smoke.add_argument("--no-oss-stack", action="store_true", help="Only require the DG MCP server in client config")
    client_smoke.add_argument("--live", action="store_true", help="Also verify backend/proxy/LiteLLM health endpoints")
    client_smoke.add_argument("--json", action="store_true")

    client_report = sub.add_parser("client-report", help="Generate target-repo Markdown/JSON handoff for external clients")
    client_report.add_argument("--repo", required=True, help="Target repo")
    client_report.add_argument("--client", default="cursor", choices=["claude-code", "claude-desktop", "cursor", "vscode"])
    client_report.add_argument("--target", default="", help="Explicit MCP config path")
    client_report.add_argument("--force-init", action="store_true", help="Force generated files during preparatory client-smoke")
    client_report.add_argument("--no-init", action="store_true", help="Do not run client-init through client-smoke")
    client_report.add_argument("--no-rules", action="store_true", help="Do not require agent instruction files")
    client_report.add_argument("--no-oss-stack", action="store_true", help="Only require the DG MCP server in client config")
    client_report.add_argument("--live", action="store_true", help="Also verify backend/proxy/LiteLLM health endpoints")
    client_report.add_argument("--no-write", action="store_true", help="Print the report without writing .dg-agent handoff files")
    client_report.add_argument("--json", action="store_true")

    agent_bridge = sub.add_parser("agent-bridge", help="Prepare a repo and expose it through an OSS ACP agent server")
    agent_bridge.add_argument("--repo", required=True, help="Target repo")
    agent_bridge.add_argument("--server", default="opencode-acp", choices=["opencode-acp", "goose-serve", "goose-acp", "openhands-acp"])
    agent_bridge.add_argument("--host", default="127.0.0.1", help="Host for HTTP/WebSocket ACP servers")
    agent_bridge.add_argument("--port", type=int, default=0, help="Port; defaults to 3295 for OpenCode ACP or 3294 for Goose serve")
    agent_bridge.add_argument("--client", default="cursor", choices=["claude-code", "claude-desktop", "cursor", "vscode"], help="Client profile used for the preparatory client-init")
    agent_bridge.add_argument("--init-target", default="", help="Explicit MCP target path for the preparatory client-init")
    agent_bridge.add_argument("--force-init", action="store_true", help="Force generated workspace/client-init files")
    agent_bridge.add_argument("--no-init", action="store_true", help="Skip preparatory client-init")
    agent_bridge.add_argument("--no-rules", action="store_true", help="Skip instruction files during preparatory client-init")
    agent_bridge.add_argument("--no-oss-stack", action="store_true", help="Prepare only DG MCP instead of the DG+Repomix+Serena bundle")
    agent_bridge.add_argument("--ensure-stack", action="store_true", help="Ensure backend/proxy/LiteLLM are live before reporting or starting")
    agent_bridge.add_argument("--restart-stack", action="store_true", help="Restart stack when used with --ensure-stack")
    agent_bridge.add_argument("--wait-timeout", type=float, default=180.0)
    agent_bridge.add_argument("--start", action="store_true", help="Exec the selected ACP server after preparation")
    agent_bridge.add_argument("--json", action="store_true")

    preflight = sub.add_parser("preflight", help="Check a target repo before running the local DG agent")
    preflight.add_argument("--repo", required=True)
    preflight.add_argument("--task", default="")
    preflight.add_argument("--file", action="append", default=[])
    preflight.add_argument("--allow-dirty", action="store_true")
    preflight.add_argument("--json", action="store_true")

    run = sub.add_parser("run", help="Initialize, preflight, optionally start, and run the local DG agent")
    run.add_argument("--repo", required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--file", action="append", default=[])
    run.add_argument("--start", action="store_true", help="Start backend/proxy/LiteLLM before execution if needed")
    run.add_argument("--restart", action="store_true", help="Restart services when used with --start")
    run.add_argument("--wait-timeout", type=float, default=180.0)
    run.add_argument("--no-init", action="store_true", help="Do not create missing .dg-agent workspace files")
    run.add_argument("--force-init", action="store_true", help="Overwrite changed .dg-agent files during init")
    run.add_argument("--out-dir", default="")
    run.add_argument("--test-cmd", default="")
    run.add_argument("--no-auto-test", action="store_true")
    run.add_argument("--max-files", type=int, default=3)
    run.add_argument("--max-snippet-chars", type=int, default=1200)
    run.add_argument("--test-timeout", type=int, default=120)
    run.add_argument("--aider-timeout", type=int, default=420)
    run.add_argument("--repair-attempts", type=int, default=1)
    run.add_argument("--wall-timeout", type=int, default=900)
    run.add_argument("--no-rollback", action="store_true")
    run.add_argument("--allow-dirty", action="store_true")
    run.add_argument("--dry-run", action="store_true", help="Do setup/preflight, print the agent command, and do not execute")
    run.add_argument("--no-deterministic-first", action="store_true")
    run.add_argument("--json", action="store_true")

    stack_status = sub.add_parser("status", help="Short stack health check for backend, proxy and LiteLLM")
    stack_status.add_argument("--json", action="store_true")
    stack_status.add_argument("--timeout", type=float, default=3.0)

    stack_up = sub.add_parser("up", help="Ensure backend, proxy and LiteLLM are running")
    stack_up.add_argument("--json", action="store_true")
    stack_up.add_argument("--restart", action="store_true")
    stack_up.add_argument("--wait-timeout", type=float, default=180.0)

    stack_down = sub.add_parser("down", help="Stop backend, proxy and LiteLLM")
    stack_down.add_argument("services", nargs="*", default=["all"], help="backend, proxy, litellm, or all")

    capabilities = sub.add_parser("capabilities", help="Run capability probes for the local DG agent wrapper stack")
    capabilities.add_argument("--live", action="store_true", help="Include live model/proxy/Aider probes")
    capabilities.add_argument("--timeout", type=int, default=180)
    capabilities.add_argument("--json", action="store_true")
    capabilities.add_argument("--out", default="", help="Optional JSON report path")
    capabilities.add_argument("--no-save", action="store_true", help="Do not write runlogs/dg-agent-capabilities/latest.json")
    capabilities.add_argument("--latest", action="store_true", help="Show the last saved capability report instead of running probes")
    capabilities.add_argument("--path-only", action="store_true", help="With --latest, print only the report path")

    smoke = sub.add_parser("smoke", help="Run wrapper smoke tests")
    smoke.add_argument(
        "--suite",
        action="append",
        choices=[
            "context",
            "auto-test",
            "verify",
            "session",
            "sessions",
            "session-artifacts",
            "agent",
            "autonomous",
            "capabilities",
            "proxy-adapter",
            "supervisor",
            "wrappers",
            "bootstrap",
            "client-pack",
            "workspace-init",
            "client-init",
            "client-smoke",
            "client-report",
            "agent-commands",
            "codex-profile",
            "ide-clients",
            "agent-bridge",
            "external-agents",
            "mini-swe-runner",
            "autogen",
            "smolagents",
            "langgraph",
            "crewai",
            "open-interpreter",
            "llamaindex",
            "haystack",
            "repo-map",
            "preflight",
            "run",
            "edit",
            "task",
            "agentapi",
            "goose",
            "goose-mcp",
            "goose-acp",
            "litellm",
            "gateway-clients",
            "openai-sdk",
            "openai-tool-loop",
            "mcp",
            "mcp-http",
            "serena-mcp",
            "ast-grep",
            "code-outline",
            "watchdog",
            "stack-control",
            "opencode-provider",
            "opencode-agent",
            "opencode-run",
            "opencode-mcp",
            "opencode-acp",
            "openhands-acp",
            "openhands-mcp",
            "qwen-code",
        ],
    )
    smoke.add_argument("--timeout", type=int, default=180)
    smoke.add_argument("--keep-going", action="store_true")

    task = sub.add_parser("task", help="Run the reliable multi-step task runner")
    task.add_argument("--repo", required=True)
    task.add_argument("--plan", required=True)
    task.add_argument("--report", default="")
    task.add_argument("--supervisor", default="")
    task.add_argument("--step-report-dir", default="")
    task.add_argument("--allow-dirty", action="store_true")
    task.add_argument("--dry-run", action="store_true")
    task.add_argument("--rollback-on-failure", action="store_true")
    task.add_argument("--continue-on-failure", action="store_true")

    context = sub.add_parser("context", help="Build a small rg-based repo context pack")
    context.add_argument("--repo", required=True)
    context.add_argument("--task", required=True)
    context.add_argument("--file", action="append", default=[], help="Force a file into the context pack")
    context.add_argument("--max-files", type=int, default=3)
    context.add_argument("--max-snippet-chars", type=int, default=1200)
    context.add_argument("--json", action="store_true")
    context.add_argument("--out", default="")

    rag = sub.add_parser("rag", help="Run the rg-based read-only RAG wrapper over a repository")
    rag.add_argument("--repo", required=True)
    rag.add_argument("--task", required=True)
    rag.add_argument("--base-url", default="")
    rag.add_argument("--model", default="")
    rag.add_argument("--max-context-chars", type=int, default=650)
    rag.add_argument("--max-files", type=int, default=3)
    rag.add_argument("--max-tokens", type=int, default=128)
    rag.add_argument("--timeout", type=int, default=300)
    rag.add_argument("--print-context", action="store_true", help="Print retrieved context and do not call the model")
    rag.add_argument("--debug", action="store_true", help="Include retrieval terms and ranked files in the context")

    tool_loop = sub.add_parser("tool-loop", help="Run a small OpenAI-compatible DG tool-call loop")
    tool_loop.add_argument("--task", required=True)
    tool_loop.add_argument("--repo", default="")
    tool_loop.add_argument("--base-url", default="http://127.0.0.1:4100/v1")
    tool_loop.add_argument("--model", default="diffusiongemma-local")
    tool_loop.add_argument("--tool-manifest-url", default="http://127.0.0.1:8090/v1/agent/tool_manifest")
    tool_loop.add_argument("--tool-runtime-url", default="http://127.0.0.1:8090/v1/agent/tool")
    tool_loop.add_argument("--system", default="")
    tool_loop.add_argument("--max-steps", type=int, default=2)
    tool_loop.add_argument("--max-tokens", type=int, default=256)
    tool_loop.add_argument("--temperature", type=float, default=0.0)
    tool_loop.add_argument("--timeout", type=int, default=120)
    tool_loop.add_argument("--stop-after-tool", action="store_true")
    tool_loop.add_argument("--include-execute-command", action="store_true")
    tool_loop.add_argument("--tool", action="append", default=[])
    tool_loop.add_argument("--exclude-tool", action="append", default=[])
    tool_loop.add_argument("--read-only", action="store_true")
    tool_loop.add_argument("--json", action="store_true")
    tool_loop.add_argument("--out", default="")

    repo_pack = sub.add_parser("repo-pack", help="Pack a repository with Repomix for AI consumption")
    repo_pack.add_argument("--repo", required=True)
    repo_pack.add_argument("--style", default="markdown", choices=["xml", "markdown", "json", "plain"])
    repo_pack.add_argument("--output", default="", help="Output file path. Defaults to stdout when omitted.")
    repo_pack.add_argument("--stdout", action="store_true", help="Write packed output to stdout")
    repo_pack.add_argument("--include", action="append", default=[], help="Comma-compatible include glob; repeatable")
    repo_pack.add_argument("--ignore", action="append", default=[], help="Comma-compatible ignore glob; repeatable")
    repo_pack.add_argument("--compress", action="store_true", help="Use Repomix Tree-sitter compression")
    repo_pack.add_argument("--include-diffs", action="store_true")
    repo_pack.add_argument("--output-show-line-numbers", action="store_true")
    repo_pack.add_argument("--remove-comments", action="store_true")
    repo_pack.add_argument("--remove-empty-lines", action="store_true")
    repo_pack.add_argument("--no-files", action="store_true", help="Generate metadata only without file contents")
    repo_pack.add_argument("--no-security-check", action="store_true")
    repo_pack.add_argument("--token-budget", type=int, default=0)
    repo_pack.add_argument("--top-files-len", type=int, default=5)

    repo_map = sub.add_parser("repo-map", help="Print upstream Aider repo-map with bounded output")
    repo_map.add_argument("--repo", required=True)
    repo_map.add_argument("--map-tokens", type=int, default=512)
    repo_map.add_argument("--max-chars", type=int, default=20000)
    repo_map.add_argument("--timeout", type=int, default=180)
    repo_map.add_argument("--map-only", action="store_true", help="Strip Aider startup text and print only the map section")
    repo_map.add_argument("--base-url", default="")
    repo_map.add_argument("--api-key", default="")
    repo_map.add_argument("--model", default="")
    repo_map.add_argument("paths", nargs="*", help="Optional repo-relative files to add to Aider context while building the map")

    ast_grep = sub.add_parser("ast-grep", help="Run upstream ast-grep structural search over a repository")
    ast_grep.add_argument("--repo", required=True)
    ast_grep.add_argument("-p", "--pattern", default="", help="AST pattern, for example: 'return $X'")
    ast_grep.add_argument("-k", "--kind", default="", help="Tree-sitter node kind or ESQuery-style kind selector")
    ast_grep.add_argument("--selector", default="", help="Sub-syntax node kind to extract from the pattern")
    ast_grep.add_argument(
        "--strictness",
        default="",
        choices=["", "cst", "smart", "ast", "relaxed", "signature", "template"],
        help="ast-grep pattern strictness",
    )
    ast_grep.add_argument("-l", "--lang", default="", help="Pattern language, for example python, ts, rust, go")
    ast_grep.add_argument("-C", "--context", type=int, default=0, help="Show context lines around matches")
    ast_grep.add_argument("--glob", action="append", default=[], help="ast-grep include/exclude glob; repeatable")
    ast_grep.add_argument("--json", action="store_true", help="Emit compact JSON matches")
    ast_grep.add_argument("--files-with-matches", action="store_true", help="Only print files with at least one match")
    ast_grep.add_argument("--max-matches", type=int, default=80, help="Limit JSON match count")
    ast_grep.add_argument("--max-chars", type=int, default=20000, help="Limit stdout characters")
    ast_grep.add_argument("--timeout", type=int, default=120)
    ast_grep.add_argument("paths", nargs="*", help="Optional paths inside --repo; defaults to .")

    code_outline = sub.add_parser("code-outline", help="Run upstream ast-grep outline to summarize repository symbols")
    code_outline.add_argument("--repo", required=True)
    code_outline.add_argument("-l", "--lang", default="", help="Input language, for example python, ts, rust, go")
    code_outline.add_argument(
        "--items",
        default="auto",
        choices=["auto", "structure", "exports", "imports", "all"],
        help="Top-level outline item set",
    )
    code_outline.add_argument(
        "--view",
        default="auto",
        choices=["auto", "names", "signatures", "digest", "expanded"],
        help="Text presentation view",
    )
    code_outline.add_argument("--type", default="", help="Comma-separated symbol types to keep, e.g. class,function")
    code_outline.add_argument("--match", default="", help="Regex matched against top-level item names/signatures")
    code_outline.add_argument("--pub-members", action="store_true", help="Show only public members in member views")
    code_outline.add_argument("--glob", action="append", default=[], help="ast-grep include/exclude glob; repeatable")
    code_outline.add_argument("--json", action="store_true", help="Emit compact JSON outline")
    code_outline.add_argument("--max-items", type=int, default=200, help="Limit JSON top-level symbol count")
    code_outline.add_argument("--max-chars", type=int, default=20000, help="Limit stdout characters")
    code_outline.add_argument("--timeout", type=int, default=120)
    code_outline.add_argument("paths", nargs="*", help="Optional paths inside --repo; defaults to .")

    plan = sub.add_parser("plan", help="Generate a task-runner JSON plan from a natural-language task")
    plan.add_argument("--repo", required=True)
    plan.add_argument("--task", required=True)
    plan.add_argument("--file", action="append", default=[], help="Editable file hint, repeatable")
    plan.add_argument("--out", default="")
    plan.add_argument("--name", default="edit")
    plan.add_argument("--test-cmd", default="")
    plan.add_argument("--auto-test", action="store_true", help="Infer a safe verification command when --test-cmd is omitted")
    plan.add_argument("--max-files", type=int, default=1)
    plan.add_argument("--max-snippet-chars", type=int, default=1200)
    plan.add_argument("--test-timeout", type=int, default=120)
    plan.add_argument("--aider-timeout", type=int, default=420)
    plan.add_argument("--repair-attempts", type=int, default=1)
    plan.add_argument("--no-deterministic-first", action="store_true")

    verify = sub.add_parser("verify", help="Run a user or inferred verification command")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--file", action="append", default=[], help="File hint for auto-test inference")
    verify.add_argument("--test-cmd", default="")
    verify.add_argument("--timeout", type=int, default=120)
    verify.add_argument("--report", default="")
    verify.add_argument("--json", action="store_true")

    session = sub.add_parser("session", help="Run context->plan->task->verify and preserve all artifacts")
    session.add_argument("--repo", required=True)
    session.add_argument("--task", required=True)
    session.add_argument("--file", action="append", default=[])
    session.add_argument("--out-dir", default="")
    session.add_argument("--test-cmd", default="")
    session.add_argument("--auto-test", action="store_true")
    session.add_argument("--max-files", type=int, default=1)
    session.add_argument("--max-snippet-chars", type=int, default=1200)
    session.add_argument("--test-timeout", type=int, default=120)
    session.add_argument("--aider-timeout", type=int, default=420)
    session.add_argument("--repair-attempts", type=int, default=1)
    session.add_argument("--wall-timeout", type=int, default=900)
    session.add_argument("--rollback-on-failure", action="store_true")
    session.add_argument("--allow-dirty", action="store_true")
    session.add_argument("--dry-run", action="store_true")
    session.add_argument("--verify-after", action=argparse.BooleanOptionalAction, default=True)
    session.add_argument("--no-deterministic-first", action="store_true")

    agent = sub.add_parser("agent", help="Run the recommended artifacted local coding-agent mode")
    agent.add_argument("--repo", required=True, help="Target git repository")
    agent.add_argument("--task", required=True, help="Natural-language coding task")
    agent.add_argument("--mode", choices=["auto", "read", "edit"], default="auto", help="auto chooses read-only tool-loop for inspection tasks and session for edits")
    agent.add_argument("--file", action="append", default=[], help="Editable file hint, repeatable")
    agent.add_argument("--out-dir", default="")
    agent.add_argument("--report", default="", help="High-level agent JSON report path, mainly for read mode")
    agent.add_argument("--test-cmd", default="", help="Verification command to run from the target repo")
    agent.add_argument("--no-auto-test", action="store_true", help="Disable conservative verification inference")
    agent.add_argument("--max-files", type=int, default=3)
    agent.add_argument("--max-snippet-chars", type=int, default=1200)
    agent.add_argument("--test-timeout", type=int, default=120)
    agent.add_argument("--aider-timeout", type=int, default=420)
    agent.add_argument("--repair-attempts", type=int, default=1)
    agent.add_argument("--wall-timeout", type=int, default=900)
    agent.add_argument("--no-rollback", action="store_true", help="Keep failed edits instead of rolling back")
    agent.add_argument("--allow-dirty", action="store_true")
    agent.add_argument("--dry-run", action="store_true")
    agent.add_argument("--no-deterministic-first", action="store_true")
    agent.add_argument("--base-url", default="http://127.0.0.1:4100/v1")
    agent.add_argument("--model", default="diffusiongemma-local")
    agent.add_argument("--tool-manifest-url", default="http://127.0.0.1:8090/v1/agent/tool_manifest")
    agent.add_argument("--tool-runtime-url", default="http://127.0.0.1:8090/v1/agent/tool")
    agent.add_argument("--max-steps", type=int, default=2)
    agent.add_argument("--max-tokens", type=int, default=256)
    agent.add_argument("--temperature", type=float, default=0.0)
    agent.add_argument("--timeout", type=int, default=120)
    agent.add_argument("--tool", action="append", default=[])
    agent.add_argument("--exclude-tool", action="append", default=[])
    agent.add_argument("--stop-after-tool", action="store_true")
    agent.add_argument("--json", action="store_true")

    autonomous = sub.add_parser("autonomous", help="Run the checkpointed persistent supervisor over Haystack retrieval and DG sessions")
    autonomous.add_argument("args", nargs=argparse.REMAINDER)

    sessions = sub.add_parser("sessions", help="List or inspect artifacted DG agent sessions")
    sessions_sub = sessions.add_subparsers(dest="sessions_command", required=True)
    sessions_list = sessions_sub.add_parser("list", help="List recent sessions")
    sessions_list.add_argument("--root", default="")
    sessions_list.add_argument("--limit", type=int, default=20)
    sessions_list.add_argument("--json", action="store_true")
    sessions_show = sessions_sub.add_parser("show", help="Show one session")
    sessions_show.add_argument("session", nargs="?", default="")
    sessions_show.add_argument("--root", default="")
    sessions_show.add_argument("--latest", action="store_true")
    sessions_show.add_argument("--json", action="store_true")
    sessions_diff = sessions_sub.add_parser("diff", help="Print a session final.diff")
    sessions_diff.add_argument("session", nargs="?", default="", help="Session dir, session.json, relative session path, or 1-based list index")
    sessions_diff.add_argument("--root", default="")
    sessions_diff.add_argument("--latest", action="store_true")
    sessions_diff.add_argument("--path-only", action="store_true")
    sessions_artifact = sessions_sub.add_parser("artifact", help="Print a preserved session artifact")
    sessions_artifact.add_argument("artifact", choices=available_session_artifacts())
    sessions_artifact.add_argument("session", nargs="?", default="", help="Session dir, session.json, relative session path, or 1-based list index")
    sessions_artifact.add_argument("--root", default="")
    sessions_artifact.add_argument("--latest", action="store_true")
    sessions_artifact.add_argument("--path-only", action="store_true")

    agent_runs = sub.add_parser("agent-runs", help="List or inspect high-level dg_agent run artifacts")
    agent_runs_sub = agent_runs.add_subparsers(dest="agent_runs_command", required=True)
    agent_runs_list = agent_runs_sub.add_parser("list", help="List recent high-level dg_agent runs")
    agent_runs_list.add_argument("--root", default="")
    agent_runs_list.add_argument("--limit", type=int, default=20)
    agent_runs_list.add_argument("--json", action="store_true")
    agent_runs_show = agent_runs_sub.add_parser("show", help="Show one high-level dg_agent run")
    agent_runs_show.add_argument("run", nargs="?", default="", help="Run dir, agent.json, relative run path, run id, or 1-based list index")
    agent_runs_show.add_argument("--root", default="")
    agent_runs_show.add_argument("--latest", action="store_true")
    agent_runs_show.add_argument("--json", action="store_true")
    agent_runs_artifact = agent_runs_sub.add_parser("artifact", help="Print a preserved high-level dg_agent run artifact")
    agent_runs_artifact.add_argument("artifact", choices=available_agent_run_artifacts())
    agent_runs_artifact.add_argument("run", nargs="?", default="", help="Run dir, agent.json, relative run path, run id, or 1-based list index")
    agent_runs_artifact.add_argument("--root", default="")
    agent_runs_artifact.add_argument("--latest", action="store_true")
    agent_runs_artifact.add_argument("--path-only", action="store_true")

    mini_swe_runs = sub.add_parser("mini-swe-runs", help="List or inspect artifacted mini-SWE runs")
    mini_swe_runs_sub = mini_swe_runs.add_subparsers(dest="mini_swe_runs_command", required=True)
    mini_swe_runs_list = mini_swe_runs_sub.add_parser("list", help="List recent mini-SWE runs")
    mini_swe_runs_list.add_argument("--root", default="")
    mini_swe_runs_list.add_argument("--limit", type=int, default=20)
    mini_swe_runs_list.add_argument("--json", action="store_true")
    mini_swe_runs_show = mini_swe_runs_sub.add_parser("show", help="Show one mini-SWE run")
    mini_swe_runs_show.add_argument("run", nargs="?", default="")
    mini_swe_runs_show.add_argument("--root", default="")
    mini_swe_runs_show.add_argument("--latest", action="store_true")
    mini_swe_runs_show.add_argument("--json", action="store_true")
    mini_swe_runs_artifact = mini_swe_runs_sub.add_parser("artifact", help="Print a preserved mini-SWE run artifact")
    mini_swe_runs_artifact.add_argument("artifact", choices=sorted(MINI_SWE_ARTIFACT_ALIASES))
    mini_swe_runs_artifact.add_argument("run", nargs="?", default="")
    mini_swe_runs_artifact.add_argument("--root", default="")
    mini_swe_runs_artifact.add_argument("--latest", action="store_true")
    mini_swe_runs_artifact.add_argument("--path-only", action="store_true")

    edit = sub.add_parser("edit", help="Run a one-step natural-language edit through the task runner")
    edit.add_argument("--repo", required=True, help="Target git repository")
    edit.add_argument("--task", required=True, help="Natural-language edit task")
    edit.add_argument("--file", action="append", default=[], help="Editable file hint, repeatable")
    edit.add_argument("--test-cmd", default="", help="Verification command to run from the target repo")
    edit.add_argument("--auto-test", action="store_true", help="Infer a safe verification command when --test-cmd is omitted")
    edit.add_argument("--report", default="", help="Aggregate JSON report path")
    edit.add_argument("--max-files", type=int, default=1)
    edit.add_argument("--test-timeout", type=int, default=120)
    edit.add_argument("--aider-timeout", type=int, default=420)
    edit.add_argument("--repair-attempts", type=int, default=1)
    edit.add_argument("--rollback-on-failure", action="store_true")
    edit.add_argument("--allow-dirty", action="store_true")
    edit.add_argument("--dry-run", action="store_true")
    edit.add_argument("--no-deterministic-first", action="store_true")

    supervisor = sub.add_parser("supervisor", help="Run the single-step supervisor")
    supervisor.add_argument("args", nargs=argparse.REMAINDER)

    web = sub.add_parser("web", help="Run AgentAPI over Aider")
    web.add_argument("args", nargs=argparse.REMAINDER)

    opencode = sub.add_parser("opencode", help="Run OpenCode with the local provider profile")
    opencode.add_argument("args", nargs=argparse.REMAINDER)

    opencode_agent = sub.add_parser("opencode-agent", help="Run compact OpenCode through the verified DG read/edit delegate")
    opencode_agent.add_argument("args", nargs=argparse.REMAINDER)

    opencode_mcp = sub.add_parser("opencode-mcp", help="Run OpenCode with local DG MCP and Repomix MCP servers")
    opencode_mcp.add_argument("args", nargs=argparse.REMAINDER)

    opencode_acp = sub.add_parser("opencode-acp", help="Run OpenCode ACP server with local DG MCP and Repomix MCP servers")
    opencode_acp.add_argument("args", nargs=argparse.REMAINDER)

    goose = sub.add_parser("goose", help="Run Goose with the local OpenAI-compatible provider profile")
    goose.add_argument("args", nargs=argparse.REMAINDER)

    goose_mcp = sub.add_parser("goose-mcp", help="Run Goose with the local DG MCP extension profile")
    goose_mcp.add_argument("args", nargs=argparse.REMAINDER)

    goose_acp = sub.add_parser("goose-acp", help="Run Goose ACP stdio server with local DG MCP tools")
    goose_acp.add_argument("args", nargs=argparse.REMAINDER)

    goose_serve = sub.add_parser("goose-serve", help="Run Goose ACP HTTP/WebSocket server with local DG MCP tools")
    goose_serve.add_argument("args", nargs=argparse.REMAINDER)

    openhands = sub.add_parser("openhands", help="Run OpenHands with the local LiteLLM Proxy profile")
    openhands.add_argument("args", nargs=argparse.REMAINDER)

    openhands_acp = sub.add_parser("openhands-acp", help="Run OpenHands ACP stdio server with the local LiteLLM Proxy profile")
    openhands_acp.add_argument("args", nargs=argparse.REMAINDER)

    openhands_mcp = sub.add_parser("openhands-mcp", help="Configure OpenHands MCP servers for a repo")
    openhands_mcp.add_argument("args", nargs=argparse.REMAINDER)

    qwen_code = sub.add_parser("qwen-code", help="Run Qwen Code with the local LiteLLM/OpenAI-compatible profile")
    qwen_code.add_argument("args", nargs=argparse.REMAINDER)

    autogen = sub.add_parser("autogen", help="Run AutoGen AgentChat with the local OpenAI-compatible profile")
    autogen.add_argument("args", nargs=argparse.REMAINDER)

    smolagents = sub.add_parser("smolagents", help="Run Hugging Face smolagents CodeAgent with the local OpenAI-compatible profile")
    smolagents.add_argument("args", nargs=argparse.REMAINDER)

    langgraph = sub.add_parser("langgraph", help="Run LangGraph/LangChain agent with the local OpenAI-compatible profile")
    langgraph.add_argument("args", nargs=argparse.REMAINDER)

    crewai = sub.add_parser("crewai", help="Run CrewAI with the local OpenAI-compatible profile")
    crewai.add_argument("args", nargs=argparse.REMAINDER)

    open_interpreter = sub.add_parser("open-interpreter", help="Run Open Interpreter with the local OpenAI-compatible profile")
    open_interpreter.add_argument("args", nargs=argparse.REMAINDER)

    llamaindex = sub.add_parser("llamaindex", help="Run LlamaIndex with the local OpenAI-compatible profile")
    llamaindex.add_argument("args", nargs=argparse.REMAINDER)

    haystack = sub.add_parser("haystack", help="Run Haystack BM25 RAG with the local OpenAI-compatible profile")
    haystack.add_argument("args", nargs=argparse.REMAINDER)

    swe_agent = sub.add_parser("swe-agent", help="Run classic SWE-agent with the local LiteLLM profile")
    swe_agent.add_argument("args", nargs=argparse.REMAINDER)

    mini_swe_agent = sub.add_parser("mini-swe-agent", help="Run mini-swe-agent with the local LiteLLM profile")
    mini_swe_agent.add_argument("args", nargs=argparse.REMAINDER)

    mini_swe_run = sub.add_parser("mini-swe-run", help="Run mini-swe-agent with preserved logs and a JSON report")
    mini_swe_run.add_argument("--repo", required=True)
    mini_swe_run.add_argument("--task", required=True)
    mini_swe_run.add_argument("--out-dir", default="")
    mini_swe_run.add_argument("--report", default="")
    mini_swe_run.add_argument("--output", default="", help="Trajectory JSON path")
    mini_swe_run.add_argument("--config", default="")
    mini_swe_run.add_argument("--model-registry", default="")
    mini_swe_run.add_argument("--binary", default="")
    mini_swe_run.add_argument("--timeout", type=int, default=420)
    mini_swe_run.add_argument("--cost-limit", type=float, default=0.01)
    mini_swe_run.add_argument("--yolo", action="store_true")
    mini_swe_run.add_argument("--exit-immediately", action="store_true")
    mini_swe_run.add_argument("--extra-config", action="append", default=[])
    mini_swe_run.add_argument("--dry-run", action="store_true")
    mini_swe_run.add_argument("--json", action="store_true")

    mcp = sub.add_parser("mcp", help="Run local MCP stdio server exposing DG agent tools")
    mcp.add_argument("--list-tools", action="store_true")
    mcp.add_argument("--stdio", action="store_true")
    mcp.add_argument("--help-local", action="store_true")
    mcp.add_argument("--legacy", action="store_true", help="Use dependency-free JSON-RPC fallback server")
    mcp.add_argument("args", nargs=argparse.REMAINDER)

    mcp_http = sub.add_parser("mcp-http", help="Run local MCP streamable HTTP server exposing DG agent tools")
    mcp_http.add_argument("args", nargs=argparse.REMAINDER)

    serena_mcp = sub.add_parser("serena-mcp", help="Run upstream Serena semantic/LSP MCP server")
    serena_mcp.add_argument("args", nargs=argparse.REMAINDER)

    litellm = sub.add_parser("litellm", help="Run LiteLLM gateway for OpenAI-compatible clients")
    litellm.add_argument("args", nargs=argparse.REMAINDER)

    watchdog = sub.add_parser("watchdog", help="Run stack watchdog commands")
    watchdog.add_argument("args", nargs=argparse.REMAINDER)

    args, unknown = parser.parse_known_args()
    passthrough_commands = {
        "supervisor",
        "web",
        "opencode",
        "opencode-agent",
        "opencode-mcp",
        "opencode-acp",
        "goose",
        "goose-mcp",
        "goose-acp",
        "goose-serve",
        "openhands",
        "openhands-acp",
        "openhands-mcp",
        "qwen-code",
        "autogen",
        "smolagents",
        "langgraph",
        "crewai",
        "open-interpreter",
        "llamaindex",
        "haystack",
        "autonomous",
        "swe-agent",
        "mini-swe-agent",
        "mcp-http",
        "serena-mcp",
        "litellm",
        "watchdog",
    }
    if unknown:
        if args.command in passthrough_commands:
            existing = getattr(args, "args", [])
            setattr(args, "args", [*existing, *unknown])
        else:
            parser.error("unrecognized arguments: " + " ".join(unknown))
    return args


def strip_separator(args: list[str]) -> list[str]:
    return args[1:] if args and args[0] == "--" else args


def main() -> int:
    args = parse_args()
    if args.command == "doctor":
        report = component_report()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_text_report(report)
        return 0
    if args.command == "ensure":
        return ensure_stack()
    if args.command == "wrappers":
        data = wrapper_matrix()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_wrappers_report(data)
        return 0
    if args.command == "bootstrap":
        return run_wrapper_bootstrap(args)
    if args.command == "client-pack":
        return run_client_pack(args)
    if args.command == "workspace-init":
        return run_workspace_init(args)
    if args.command == "mcp-client-config":
        return run_mcp_client_config(args)
    if args.command == "agent-rules":
        return run_agent_rules(args)
    if args.command == "agent-commands":
        return run_agent_commands(args)
    if args.command == "codex-profile":
        return run_codex_profile(args)
    if args.command == "client-init":
        return run_client_init(args)
    if args.command == "client-smoke":
        return run_client_smoke(args)
    if args.command == "client-report":
        return run_client_report(args)
    if args.command == "agent-bridge":
        return run_agent_bridge(args)
    if args.command == "preflight":
        return run_preflight(args)
    if args.command == "run":
        return run_agent_orchestrator(args)
    if args.command == "status":
        return run_stack_status(args)
    if args.command == "up":
        return run_stack_up(args)
    if args.command == "down":
        return run_stack_down(args)
    if args.command == "capabilities":
        return run_capabilities_command(args)
    if args.command == "smoke":
        return run_smokes(args)
    if args.command == "context":
        return run_context(args)
    if args.command == "rag":
        return run_rag_command(args)
    if args.command == "tool-loop":
        return run_openai_tool_loop_command(args)
    if args.command == "repo-pack":
        return run_repo_pack_command(args)
    if args.command == "repo-map":
        return run_repo_map_command(args)
    if args.command == "ast-grep":
        return run_ast_grep_command(args)
    if args.command == "code-outline":
        return run_code_outline_command(args)
    if args.command == "plan":
        return run_plan(args)
    if args.command == "verify":
        return run_verify(args)
    if args.command == "session":
        return run_session(args)
    if args.command == "agent":
        return run_agent(args)
    if args.command == "autonomous":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_persistent_supervisor.sh"), *strip_separator(args.args)])
    if args.command == "sessions":
        return run_sessions(args)
    if args.command == "agent-runs":
        return run_agent_runs(args)
    if args.command == "mini-swe-runs":
        return run_mini_swe_runs(args)
    if args.command == "edit":
        return run_edit(args)
    if args.command == "task":
        return run_task_command(args)
    if args.command == "supervisor":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_supervisor_agent.sh"), *strip_separator(args.args)])
    if args.command == "web":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_agentapi_aider.sh"), *strip_separator(args.args)])
    if args.command in {"opencode", "opencode-agent", "opencode-mcp", "opencode-acp"}:
        windows_launcher = DG_ROOT / "scripts" / (
            "run_opencode_agent_windows.ps1" if args.command == "opencode-agent" else "run_opencode_windows.ps1"
        )
        powershell = powershell_executable()
        if windows_launcher.exists() and powershell:
            opencode_args = strip_separator(args.args)
            if args.command == "opencode-mcp":
                opencode_args.insert(0, "mcp")
            elif args.command == "opencode-acp":
                opencode_args.insert(0, "acp")
            runner_args: list[str] = []
            current_dir = caller_working_directory()
            if os.name == "nt":
                runner_args.extend(["-WorkingDirectory", str(current_dir)])
            elif str(current_dir).startswith("/mnt/"):
                runner_args.extend(["-WorkingDirectory", wsl_path_to_windows(current_dir)])
            if "--help" in opencode_args or "-h" in opencode_args:
                # Static help must work even for a WSL-only temporary directory.
                runner_args.append("-NoMcp")
            return exec_cmd(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    wsl_path_to_windows(windows_launcher),
                    *runner_args,
                    *opencode_args,
                ]
            )
    if args.command == "opencode":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_opencode_local.sh"), *strip_separator(args.args)])
    if args.command == "opencode-agent":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_opencode_agent_local.sh"), *strip_separator(args.args)])
    if args.command == "opencode-mcp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_opencode_mcp_local.sh"), *strip_separator(args.args)])
    if args.command == "opencode-acp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_opencode_acp_local.sh"), *strip_separator(args.args)])
    if args.command == "goose":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_goose_local.sh"), *strip_separator(args.args)])
    if args.command == "goose-mcp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_goose_mcp_local.sh"), *strip_separator(args.args)])
    if args.command == "goose-acp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_goose_mcp_local.sh"), "--acp", *strip_separator(args.args)])
    if args.command == "goose-serve":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_goose_mcp_local.sh"), "--serve", *strip_separator(args.args)])
    if args.command == "openhands":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_openhands_local.sh"), *strip_separator(args.args)])
    if args.command == "openhands-acp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_openhands_acp_local.sh"), *strip_separator(args.args)])
    if args.command == "openhands-mcp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_openhands_mcp_setup.sh"), *strip_separator(args.args)])
    if args.command == "qwen-code":
        return exec_cmd(qwen_code_command(strip_separator(args.args)))
    if args.command == "autogen":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_autogen_local.sh"), *strip_separator(args.args)])
    if args.command == "smolagents":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_smolagents_local.sh"), *strip_separator(args.args)])
    if args.command == "langgraph":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_langgraph_local.sh"), *strip_separator(args.args)])
    if args.command == "crewai":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_crewai_local.sh"), *strip_separator(args.args)])
    if args.command == "open-interpreter":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_open_interpreter_local.sh"), *strip_separator(args.args)])
    if args.command == "llamaindex":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_llamaindex_local.sh"), *strip_separator(args.args)])
    if args.command == "haystack":
        haystack_args = strip_separator(args.args)
        if os.name == "nt" and shutil.which("wsl.exe"):
            wsl_args: list[str] = []
            path_flags = {"--repo", "--config", "--index-dir"}
            index = 0
            while index < len(haystack_args):
                value = haystack_args[index]
                wsl_args.append(value)
                if value in path_flags and index + 1 < len(haystack_args):
                    index += 1
                    wsl_args.append(windows_path_to_wsl(Path(haystack_args[index]).resolve()))
                index += 1
            return exec_cmd(["wsl.exe", "--exec", windows_path_to_wsl(DG_ROOT / "scripts" / "run_haystack_local.sh"), *wsl_args])
        return exec_cmd([str(DG_ROOT / "scripts" / "run_haystack_local.sh"), *haystack_args])
    if args.command == "swe-agent":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_swe_agent_local.sh"), *strip_separator(args.args)])
    if args.command == "mini-swe-agent":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_mini_swe_agent_local.sh"), *strip_separator(args.args)])
    if args.command == "mini-swe-run":
        cmd = [
            str(DG_ROOT / ".venv" / "bin" / "python"),
            str(DG_ROOT / "scripts" / "dg_mini_swe_runner.py"),
            "--repo",
            args.repo,
            "--task",
            args.task,
            "--timeout",
            str(args.timeout),
            "--cost-limit",
            str(args.cost_limit),
        ]
        for name in ["out_dir", "report", "output", "config", "model_registry", "binary"]:
            value = getattr(args, name)
            if value:
                cmd.extend(["--" + name.replace("_", "-"), value])
        for item in args.extra_config:
            cmd.extend(["--extra-config", item])
        if args.yolo:
            cmd.append("--yolo")
        if args.exit_immediately:
            cmd.append("--exit-immediately")
        if args.dry_run:
            cmd.append("--dry-run")
        if args.json:
            cmd.append("--json")
        return exec_cmd(cmd)
    if args.command == "mcp":
        mcp_args = strip_separator(args.args)
        if args.list_tools:
            mcp_args.append("--list-tools")
        if args.stdio:
            mcp_args.append("--stdio")
        if args.help_local:
            mcp_args.append("--help-local")
        if args.legacy:
            mcp_args.insert(0, "--legacy")
        return exec_cmd([str(DG_ROOT / "scripts" / "run_mcp_server.sh"), *mcp_args])
    if args.command == "mcp-http":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_mcp_http_server.sh"), *strip_separator(args.args)])
    if args.command == "serena-mcp":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_serena_mcp.sh"), *strip_separator(args.args)])
    if args.command == "litellm":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_litellm_gateway.sh"), *strip_separator(args.args)])
    if args.command == "watchdog":
        return exec_cmd([str(DG_ROOT / "scripts" / "run_stack_watchdog.sh"), *strip_separator(args.args)])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
