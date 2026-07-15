#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  DG_ROOT="$(cygpath -au "$DG_ROOT")"
fi
export DG_ROOT

if ! "$DG_ROOT/scripts/run_serena_mcp.sh" --check-installed >/tmp/dg-serena-check.txt 2>/tmp/dg-serena-check.err; then
  "$DG_ROOT/scripts/install_serena_local.sh" >/tmp/dg-serena-install.log
fi

"$DG_ROOT/scripts/run_serena_mcp.sh" --help-local >/tmp/dg-serena-mcp-help.txt
grep -F "Run upstream Serena as an MCP server" /tmp/dg-serena-mcp-help.txt >/dev/null
"$DG_ROOT/scripts/run_serena_mcp.sh" --version | grep -F "Serena" >/dev/null

PY_CMD="${DG_SERENA_SMOKE_PYTHON:-}"
if [[ -z "$PY_CMD" ]]; then
  if [[ -x "$DG_ROOT/.venv-serena/bin/python" ]]; then
    PY_CMD="$DG_ROOT/.venv-serena/bin/python"
  elif [[ -x "/root/diffusiongemma-agent/.venv-wsl/bin/python" ]]; then
    PY_CMD="/root/diffusiongemma-agent/.venv-wsl/bin/python"
  elif [[ -x "$DG_ROOT/.venv-wsl/bin/python" ]]; then
    PY_CMD="$DG_ROOT/.venv-wsl/bin/python"
  elif [[ -x "$DG_ROOT/.venv-serena/Scripts/python.exe" ]]; then
    PY_CMD="$DG_ROOT/.venv-serena/Scripts/python.exe"
  elif command -v python3 >/dev/null 2>&1; then
    PY_CMD="$(command -v python3)"
  else
    PY_CMD="$(command -v python)"
  fi
fi

timeout 150 "$PY_CMD" - "$DG_ROOT" <<'PY'
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

repo = Path(tempfile.mkdtemp(prefix="dg-serena-smoke."))
(repo / "hello.py").write_text(
    "def greet(name):\n"
    "    return f'hello {name}'\n\n"
    "class Greeter:\n"
    "    def run(self):\n"
    "        return greet('world')\n",
    encoding="utf-8",
)
subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

def as_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != "nt":
        return str(resolved)
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.relative_to(resolved.anchor).as_posix()
    return f"/mnt/{drive}/{rest}"


runner = Path(sys.argv[1]).resolve() / "scripts" / "run_serena_mcp.sh"
runner_args = ["--project", as_wsl_path(repo)]
if os.name == "nt":
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    command = [str(git_bash if git_bash.exists() else "bash"), runner.as_posix(), *runner_args]
else:
    command = [str(runner), *runner_args]

proc = subprocess.Popen(
    command,
    cwd=repo,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
)
stderr_queue: queue.Queue[str] = queue.Queue()
stderr_lines: list[str] = []


def read_stderr() -> None:
    assert proc.stderr is not None
    for item in iter(proc.stderr.readline, ""):
        stderr_lines.append(item)
        stderr_queue.put(item)


threading.Thread(target=read_stderr, daemon=True).start()


def send(payload: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    proc.stdin.flush()


def read_response(expected_id: int, timeout_s: float = 90.0) -> dict:
    assert proc.stdout is not None
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                stderr = "".join(stderr_lines)
                raise RuntimeError(f"Serena exited rc={proc.returncode}: {stderr[-2000:]}")
            time.sleep(0.05)
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == expected_id:
            if "error" in msg:
                raise RuntimeError(msg["error"])
            return msg
    stderr = "".join(stderr_lines)
    raise TimeoutError(f"timed out waiting for id={expected_id}; stderr={stderr[-2000:]}")


def wait_until_ready(timeout_s: float = 120.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            stderr = "".join(stderr_lines)
            raise RuntimeError(f"Serena exited rc={proc.returncode}: {stderr[-2000:]}")
        try:
            line = stderr_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if "MCP server lifetime setup complete" in line:
            return
    stderr = "".join(stderr_lines)
    raise TimeoutError(f"timed out waiting for Serena readiness; stderr={stderr[-2000:]}")


try:
    wait_until_ready()
    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dg-serena-smoke", "version": "0.1"},
            },
        }
    )
    read_response(1)
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools_msg = read_response(2)
    names = {tool["name"] for tool in tools_msg["result"]["tools"]}
    required = {
        "get_symbols_overview",
        "find_symbol",
        "find_referencing_symbols",
        "replace_symbol_body",
        "initial_instructions",
    }
    missing = sorted(required - names)
    assert not missing, {"missing": missing, "tools": sorted(names)}
    send(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_symbols_overview",
                "arguments": {"relative_path": "hello.py"},
            },
        }
    )
    symbols_msg = read_response(3, timeout_s=150.0)
    result = symbols_msg.get("result", {})
    result_text = json.dumps(result, ensure_ascii=False)
    assert not result.get("isError"), result_text
    assert "greet" in result_text and "Greeter" in result_text, result_text
    print(f"Serena MCP smoke passed with {len(names)} tools and live Pyright symbols.")
finally:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
PY
