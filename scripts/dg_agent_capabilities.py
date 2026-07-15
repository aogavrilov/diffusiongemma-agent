#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DG_AGENT = DG_ROOT / "scripts" / "dg_agent.sh"
TRACE_PATH = DG_ROOT / "runlogs" / "aider_proxy.trace.jsonl"
DEFAULT_REPORT_ROOT = DG_ROOT / "runlogs" / "dg-agent-capabilities"
CORE_WORKSPACE_LAUNCHER_HELP_CHECKS = {
    "run": ["--help"],
    "agent": ["--help"],
    "context": ["--help"],
    "rag": ["--help"],
    "repo-pack": ["--help"],
    "repo-map": ["--help"],
    "ast-grep": ["--help"],
    "code-outline": ["--help"],
    "client-init": ["--help"],
    "client-smoke": ["--help"],
    "client-report": ["--help"],
    "agent-commands": ["--help"],
    "codex-profile": ["--help"],
    "agent-bridge": ["--help"],
    "hub": ["--json"],
    "plan": ["--help"],
    "edit": ["--help"],
    "task": ["--help"],
    "verify": ["--help"],
    "status": ["--help"],
    "doctor": ["--help"],
    "preflight": ["--help"],
    "capabilities": ["--help"],
    "sessions": ["--help"],
    "supervisor": ["--help"],
    "aider": ["--help"],
    "opencode": ["--help"],
    "opencode-mcp": ["--help"],
    "opencode-acp": ["--help"],
    "mini-swe-run": ["--help"],
    "mini-swe-runs": ["--help"],
    "mcp": ["--list-tools"],
    "mcp-http": ["--help-local"],
    "mcp-client-config": ["--help"],
    "agent-rules": ["--help"],
}


def run_cmd(args: list[str], cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or DG_ROOT),
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def shell_cmd(command: str, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        executable="/bin/bash",
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def tail(text: str, limit: int = 3000) -> str:
    return text[-limit:] if len(text) > limit else text


def http_ok(url: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        return bool(data.get("ok")) if isinstance(data, dict) else True
    except Exception:
        return False


def init_repo(prefix: str, files: dict[str, str]) -> Path:
    repo = Path(tempfile.mkdtemp(prefix=prefix))
    run_cmd(["git", "init", "-q"], cwd=repo, timeout=20)
    run_cmd(["git", "config", "user.email", "local-capabilities@example.invalid"], cwd=repo, timeout=20)
    run_cmd(["git", "config", "user.name", "Local Capabilities"], cwd=repo, timeout=20)
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    run_cmd(["git", "add", "."], cwd=repo, timeout=20)
    run_cmd(["git", "commit", "-qm", "initial"], cwd=repo, timeout=20)
    return repo


def scenario_result(name: str, started: float, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "elapsed_sec": round(time.time() - started, 3),
        **extra,
    }


def report_timestamp(ts: float) -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(ts))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_report(report: dict[str, Any], out: str, save_default: bool) -> dict[str, str]:
    saved: dict[str, str] = {}
    if save_default:
        root = DEFAULT_REPORT_ROOT
        started = float(report.get("started_at") or time.time())
        suffix = "live" if report.get("live") else "static"
        timestamped = root / f"{report_timestamp(started)}-{suffix}.json"
        latest = root / "latest.json"
        saved["timestamped"] = str(timestamped)
        saved["latest"] = str(latest)
    if out:
        saved["out"] = str(Path(out).resolve())

    if saved:
        report["report_paths"] = saved
        if "timestamped" in saved:
            write_json(Path(saved["timestamped"]), report)
        if "latest" in saved:
            write_json(Path(saved["latest"]), report)
        if "out" in saved:
            write_json(Path(saved["out"]), report)
    return saved


def load_latest_report() -> tuple[Path | None, dict[str, Any] | None]:
    latest = DEFAULT_REPORT_ROOT / "latest.json"
    if not latest.exists():
        reports = sorted(DEFAULT_REPORT_ROOT.glob("*.json")) if DEFAULT_REPORT_ROOT.exists() else []
        reports = [path for path in reports if path.name != "latest.json"]
        if not reports:
            return None, None
        latest = reports[-1]
    try:
        return latest, json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return latest, None


def scenario_workspace_run_dry(timeout: int) -> dict[str, Any]:
    started = time.time()
    repo = init_repo(
        "/tmp/dg-cap-workspace.",
        {"hello.py": 'def greet(name):\n    return f"hello {name}"\n'},
    )
    proc = run_cmd(
        [
            str(DG_AGENT),
            "run",
            "--repo",
            str(repo),
            "--task",
            "Fix hello.py so greet('Ada') returns exactly hello, Ada!",
            "--file",
            "hello.py",
            "--dry-run",
            "--json",
        ],
        timeout=timeout,
    )
    data: dict[str, Any]
    try:
        data = json.loads(proc.stdout)
    except Exception:
        data = {"parse_error": True}
    status_proc = run_cmd(["git", "status", "--short", "--untracked-files=all"], cwd=repo, timeout=20)
    status_text = status_proc.stdout.strip()
    launchers_ok = os.access(repo / ".dg-agent" / "bin" / "run", os.X_OK)
    ok = (
        proc.returncode == 0
        and data.get("status") == "dry-run"
        and launchers_ok
        and ".dg-agent" not in status_text
    )
    return scenario_result(
        "workspace-run-dry",
        started,
        "passed" if ok else "failed",
        repo=str(repo),
        returncode=proc.returncode,
        dry_status=data.get("status"),
        launchers_ok=launchers_ok,
        git_status=status_text,
        stdout_tail="" if ok else tail(proc.stdout),
        stderr_tail="" if ok else tail(proc.stderr),
    )


def scenario_workspace_launchers_static(timeout: int) -> dict[str, Any]:
    started = time.time()
    repo = init_repo(
        "/tmp/dg-cap-launchers.",
        {"hello.py": 'def greet(name):\n    return f"hello {name}"\n'},
    )
    init_proc = run_cmd(
        [str(DG_AGENT), "workspace-init", "--repo", str(repo), "--json"],
        timeout=min(timeout, 60),
    )
    init_report: dict[str, Any]
    try:
        init_report = json.loads(init_proc.stdout)
    except Exception:
        init_report = {"parse_error": True}

    per_launcher_timeout = max(10, min(timeout, 45))
    launcher_results: list[dict[str, Any]] = []
    for name, argv in CORE_WORKSPACE_LAUNCHER_HELP_CHECKS.items():
        path = repo / ".dg-agent" / "bin" / name
        exists = path.exists()
        executable = os.access(path, os.X_OK)
        if not exists or not executable:
            launcher_results.append(
                {
                    "name": name,
                    "exists": exists,
                    "executable": executable,
                    "status": "failed",
                    "reason": "missing or not executable",
                }
            )
            continue
        try:
            proc = run_cmd([str(path), *argv], cwd=repo, timeout=per_launcher_timeout)
            combined = proc.stdout + proc.stderr
            launcher_results.append(
                {
                    "name": name,
                    "exists": exists,
                    "executable": executable,
                    "status": "passed" if proc.returncode == 0 and bool(combined.strip()) else "failed",
                    "returncode": proc.returncode,
                    "stdout_bytes": len(proc.stdout),
                    "stderr_bytes": len(proc.stderr),
                    "output_tail": "" if proc.returncode == 0 and combined.strip() else tail(combined),
                }
            )
        except subprocess.TimeoutExpired as exc:
            launcher_results.append(
                {
                    "name": name,
                    "exists": exists,
                    "executable": executable,
                    "status": "failed",
                    "reason": f"timeout after {exc.timeout}s",
                }
            )

    status_proc = run_cmd(["git", "status", "--short", "--untracked-files=all"], cwd=repo, timeout=20)
    status_text = status_proc.stdout.strip()
    failed_launchers = [item["name"] for item in launcher_results if item["status"] != "passed"]
    ok = (
        init_proc.returncode == 0
        and init_report.get("status") == "success"
        and not failed_launchers
        and ".dg-agent" not in status_text
    )
    return scenario_result(
        "workspace-launchers-static",
        started,
        "passed" if ok else "failed",
        repo=str(repo),
        returncode=init_proc.returncode,
        workspace_init_status=init_report.get("status"),
        launchers_checked=len(launcher_results),
        failed_launchers=failed_launchers,
        git_status=status_text,
        launcher_results=launcher_results if not ok else [],
        stdout_tail="" if ok else tail(init_proc.stdout),
        stderr_tail="" if ok else tail(init_proc.stderr),
    )


def scenario_oss_wrapper_audit_static(timeout: int) -> dict[str, Any]:
    started = time.time()
    proc = run_cmd(
        [
            str(DG_AGENT),
            "bootstrap",
            "--json",
            "--smoke-static",
            "--smoke-timeout",
            str(min(timeout, 120)),
        ],
        timeout=min(timeout, 120) + 30,
    )
    data: dict[str, Any]
    try:
        data = json.loads(proc.stdout)
    except Exception:
        data = {"parse_error": True}
    after = data.get("after") if isinstance(data.get("after"), list) else []
    smoke_results = data.get("smoke_results") if isinstance(data.get("smoke_results"), list) else []
    required = {"aider", "opencode", "mcp"}
    missing = [str(item.get("id")) for item in after if item.get("id") in required and not item.get("installed")]
    optional_missing = [str(item.get("id")) for item in after if item.get("id") not in required and not item.get("installed")]
    failed_smokes = [str(item.get("suite")) for item in smoke_results if item.get("status") != "success"]
    ok = proc.returncode == 0 and not missing and not failed_smokes and bool(smoke_results)
    return scenario_result(
        "oss-wrapper-audit-static",
        started,
        "passed" if ok else "failed",
        returncode=proc.returncode,
        installed=[str(item.get("id")) for item in after if item.get("installed")],
        missing=missing,
        optional_missing=optional_missing,
        smoke_results=[{"suite": item.get("suite"), "status": item.get("status")} for item in smoke_results],
        failed_smokes=failed_smokes,
        stdout_tail="" if ok else tail(proc.stdout),
        stderr_tail="" if ok else tail(proc.stderr),
    )


def scenario_external_agent_profiles_static(timeout: int) -> dict[str, Any]:
    started = time.time()
    smoke = run_cmd(
        [str(DG_AGENT), "smoke", "--suite", "qwen-code", "--timeout", str(min(timeout, 120))],
        timeout=min(timeout, 120) + 30,
    )
    audit = run_cmd([str(DG_AGENT), "bootstrap", "--only", "qwen-code", "--json"], timeout=60)
    qwen_installed = False
    qwen_binary = ""
    try:
        data = json.loads(audit.stdout)
        rows = data.get("after") if isinstance(data.get("after"), list) else []
        for row in rows:
            if row.get("id") == "qwen-code":
                qwen_installed = bool(row.get("installed"))
                checks = row.get("checks") if isinstance(row.get("checks"), list) else []
                for check in checks:
                    if check.get("exists") and "qwen" in str(check.get("path") or "").lower():
                        qwen_binary = str(check.get("path") or "")
                        break
    except Exception:
        pass
    ok = smoke.returncode == 0 and audit.returncode == 0 and qwen_installed
    return scenario_result(
        "external-agent-profiles-static",
        started,
        "passed" if ok else "failed",
        returncode=smoke.returncode,
        audit_returncode=audit.returncode,
        qwen_code_installed=qwen_installed,
        qwen_code_binary=qwen_binary,
        stdout_tail="" if ok else tail(smoke.stdout),
        stderr_tail="" if ok else tail(smoke.stderr),
        audit_tail="" if ok else tail(audit.stdout + audit.stderr),
    )


def scenario_proxy_adapter_static(timeout: int) -> dict[str, Any]:
    started = time.time()
    proc = run_cmd([str(DG_AGENT), "smoke", "--suite", "proxy-adapter", "--timeout", str(timeout)], timeout=timeout + 15)
    return scenario_result(
        "proxy-adapter-static",
        started,
        "passed" if proc.returncode == 0 else "failed",
        returncode=proc.returncode,
        stdout_tail="" if proc.returncode == 0 else tail(proc.stdout),
        stderr_tail="" if proc.returncode == 0 else tail(proc.stderr),
    )


def scenario_supervisor_exact_replace(timeout: int) -> dict[str, Any]:
    started = time.time()
    repo = init_repo(
        "/tmp/dg-cap-replace.",
        {"message.py": 'WELCOME = "hello beta"\n\ndef welcome():\n    return WELCOME\n'},
    )
    test_cmd = "python3 -c 'from message import welcome; assert welcome() == \"hello stable\"'"
    report_path = repo / "replace-report.json"
    proc = run_cmd(
        [
            str(DG_AGENT),
            "supervisor",
            "--",
            "--repo",
            str(repo),
            "--task",
            "In message.py, replace 'hello beta' with 'hello stable'. Keep everything else unchanged.",
            "--file",
            "message.py",
            "--test-cmd",
            test_cmd,
            "--aider-timeout",
            str(timeout),
            "--repair-attempts",
            "0",
            "--report",
            str(report_path),
        ],
        timeout=timeout + 30,
    )
    verify = shell_cmd(test_cmd, repo, timeout=30)
    strategy = ""
    status = ""
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            strategy = str(report.get("strategy") or "")
            status = str(report.get("status") or "")
        except Exception as exc:
            status = f"report-error: {exc}"
    text = (repo / "message.py").read_text(encoding="utf-8", errors="replace")
    ok = (
        proc.returncode == 0
        and verify.returncode == 0
        and status == "success"
        and strategy == "deterministic-first"
        and 'WELCOME = "hello stable"' in text
    )
    return scenario_result(
        "supervisor-exact-replace",
        started,
        "passed" if ok else "failed",
        repo=str(repo),
        returncode=proc.returncode,
        verify_returncode=verify.returncode,
        report_status=status,
        strategy=strategy,
        stdout_tail="" if ok else tail(proc.stdout),
        stderr_tail="" if ok else tail(proc.stderr),
        verify_output_tail="" if ok else tail(verify.stdout + verify.stderr),
    )


def read_trace_since(started_at: float, kinds: set[str]) -> list[dict[str, Any]]:
    if not TRACE_PATH.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in TRACE_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except Exception:
            continue
        if float(event.get("ts") or 0.0) < started_at:
            continue
        if str(event.get("kind")) in kinds:
            events.append(event)
    return events


def session_from_stdout(stdout: str) -> Path | None:
    match = re.search(r"(?m)^Session dir:\s*(.+)$", stdout)
    if not match:
        return None
    path = Path(match.group(1).strip())
    return path if path.exists() else None


def step_strategy(session_dir: Path) -> tuple[str, str]:
    task_report = json.loads((session_dir / "task-report.json").read_text(encoding="utf-8"))
    step_path = Path(task_report["steps"][0]["step_report"])
    step_report = json.loads(step_path.read_text(encoding="utf-8"))
    return str(step_report.get("status") or ""), str(step_report.get("strategy") or "")


def scenario_live_proxy_repair(timeout: int) -> dict[str, Any]:
    started = time.time()
    services_ok = {
        "backend": http_ok("http://127.0.0.1:4100/healthz"),
        "proxy": http_ok("http://127.0.0.1:8090/healthz"),
    }
    if not all(services_ok.values()):
        return scenario_result("live-proxy-repair", started, "skipped", reason="backend/proxy not live", services=services_ok)

    repo = init_repo(
        "/tmp/dg-cap-live.",
        {"score.py": 'def label_score(score):\n    return "TODO"\n'},
    )
    test_cmd = "python3 -c 'from score import label_score; assert label_score(90) == \"high\"; assert label_score(89) == \"normal\"'"
    proc = run_cmd(
        [
            str(DG_AGENT),
            "run",
            "--repo",
            str(repo),
            "--task",
            "Edit score.py. Implement label_score(score): return 'high' when score is greater than or equal to 90, otherwise return 'normal'. Keep the same function name.",
            "--file",
            "score.py",
            "--test-cmd",
            test_cmd,
            "--repair-attempts",
            "0",
            "--aider-timeout",
            str(timeout),
            "--wall-timeout",
            str(timeout + 60),
            "--max-files",
            "1",
        ],
        timeout=timeout + 90,
    )
    verify = shell_cmd(test_cmd, repo, timeout=30)
    session_dir = session_from_stdout(proc.stdout)
    step_status = ""
    strategy = ""
    if session_dir:
        try:
            step_status, strategy = step_strategy(session_dir)
        except Exception as exc:
            step_status = f"report-error: {exc}"
    repair_events = read_trace_since(started, {"proxy_exact_repair"})
    score_text = (repo / "score.py").read_text(encoding="utf-8", errors="replace")
    strategy_ok = strategy == "deterministic-first" or (
        strategy in {"aider", "aider-with-deterministic-repair"} and bool(repair_events)
    )
    ok = (
        proc.returncode == 0
        and verify.returncode == 0
        and strategy_ok
        and "return 'high' if score >= 90 else 'normal'" in score_text
    )
    return scenario_result(
        "live-proxy-repair",
        started,
        "passed" if ok else "failed",
        repo=str(repo),
        services=services_ok,
        returncode=proc.returncode,
        verify_returncode=verify.returncode,
        session_dir=str(session_dir) if session_dir else "",
        step_status=step_status,
        strategy=strategy,
        proxy_exact_repair_events=len(repair_events),
        score_py=score_text,
        stdout_tail="" if ok else tail(proc.stdout),
        stderr_tail="" if ok else tail(proc.stderr),
        verify_output_tail="" if ok else tail(verify.stdout + verify.stderr),
    )


def run_capabilities(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    scenarios = [
        scenario_workspace_run_dry(args.timeout),
        scenario_workspace_launchers_static(args.timeout),
        scenario_oss_wrapper_audit_static(args.timeout),
        scenario_external_agent_profiles_static(args.timeout),
        scenario_proxy_adapter_static(min(args.timeout, 120)),
        scenario_supervisor_exact_replace(min(args.timeout, 120)),
    ]
    if args.live:
        scenarios.append(scenario_live_proxy_repair(args.timeout))
    passed = sum(1 for item in scenarios if item["status"] == "passed")
    failed = [item["name"] for item in scenarios if item["status"] == "failed"]
    skipped = [item["name"] for item in scenarios if item["status"] == "skipped"]
    return {
        "status": "success" if not failed else "failed",
        "live": args.live,
        "started_at": started,
        "elapsed_sec": round(time.time() - started, 3),
        "summary": {"passed": passed, "failed": failed, "skipped": skipped},
        "scenarios": scenarios,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"DG agent capabilities: {report['status']}")
    print(f"live: {report['live']} elapsed={report['elapsed_sec']}s")
    paths = report.get("report_paths")
    if isinstance(paths, dict) and paths.get("latest"):
        print(f"latest: {paths['latest']}")
    for item in report["scenarios"]:
        print(f"- {item['name']}: {item['status']} ({item['elapsed_sec']}s)")
        if item.get("strategy"):
            print(f"  strategy: {item['strategy']}")
        if item.get("proxy_exact_repair_events") is not None:
            print(f"  proxy_exact_repair_events: {item['proxy_exact_repair_events']}")
        if item.get("launchers_checked") is not None:
            print(f"  launchers_checked: {item['launchers_checked']}")
        if item.get("installed") is not None:
            print(f"  installed: {', '.join(item['installed'])}")
        if item.get("mini_swe_agent_installed") is not None:
            print(f"  mini_swe_agent_installed: {item['mini_swe_agent_installed']}")
        if item.get("session_dir"):
            print(f"  session: {item['session_dir']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run capability probes for the local DG agent wrapper stack.")
    parser.add_argument("--live", action="store_true", help="Include live model/proxy/Aider capability probes")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default="", help="Optional JSON report path")
    parser.add_argument("--no-save", action="store_true", help="Do not write runlogs/dg-agent-capabilities/latest.json")
    parser.add_argument("--latest", action="store_true", help="Show the last saved capability report instead of running probes")
    parser.add_argument("--path-only", action="store_true", help="With --latest, print only the report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.latest:
        path, report = load_latest_report()
        if path is None:
            print("No saved capability report found.", file=sys.stderr)
            return 2
        if args.path_only:
            print(path)
            return 0 if report is not None else 1
        if report is None:
            print(f"Saved capability report is not valid JSON: {path}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_report(report)
        return 0 if report.get("status") == "success" else 1

    report = run_capabilities(args)
    save_report(report, args.out, not args.no_save)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
