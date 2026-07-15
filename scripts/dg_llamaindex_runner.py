#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "llamaindex.dg.json"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_llamaindex() -> tuple[Any, Any, Any, Any]:
    from llama_index.core.agent.workflow import AgentWorkflow
    from llama_index.core.agent.workflow import FunctionAgent
    from llama_index.core.agent.workflow import ReActAgent
    from llama_index.llms.openai_like import OpenAILike

    return OpenAILike, AgentWorkflow, FunctionAgent, ReActAgent


def llm_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": os.environ.get("LLAMAINDEX_MODEL") or config["model"],
        "api_base": os.environ.get("OPENAI_BASE_URL") or config["api_base"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "context_window": int(os.environ.get("LLAMAINDEX_CONTEXT_WINDOW") or config.get("context_window") or 768),
        "max_tokens": int(os.environ.get("LLAMAINDEX_MAX_TOKENS") or config.get("max_tokens") or 256),
        "temperature": float(os.environ.get("LLAMAINDEX_TEMPERATURE") or config.get("temperature") or 0.0),
        "is_chat_model": bool(config.get("is_chat_model", True)),
        "is_function_calling_model": bool(config.get("is_function_calling_model", False)),
    }


def resolve_repo_path(repo: Path, user_path: str) -> Path:
    target = (repo / user_path).resolve()
    if target != repo and repo not in target.parents:
        raise ValueError(f"path escapes repo: {user_path}")
    return target


def make_repo_tools(repo: Path, max_chars: int) -> list[Callable[..., str]]:
    def list_files(pattern: str = "", limit: int = 80) -> str:
        """List repository files, optionally filtered by an rg glob pattern."""
        limit = max(1, min(int(limit), 300))
        cmd = ["rg", "--files"]
        if pattern:
            cmd.extend(["-g", pattern])
        try:
            proc = subprocess.run(cmd, cwd=repo, text=True, capture_output=True, timeout=20)
            files = [line for line in proc.stdout.splitlines() if line.strip()]
        except (FileNotFoundError, subprocess.SubprocessError):
            files = []
            for path in repo.rglob("*"):
                if len(files) >= limit:
                    break
                if ".git" in path.parts or ".dg-agent" in path.parts:
                    continue
                if path.is_file():
                    rel = path.relative_to(repo).as_posix()
                    if not pattern or pattern.strip("*") in rel:
                        files.append(rel)
        return "\n".join(files[:limit])

    def read_file(path: str, max_read_chars: int = 4000) -> str:
        """Read a bounded UTF-8 text file from the repository."""
        max_read_chars = max(200, min(int(max_read_chars), max_chars))
        target = resolve_repo_path(repo, path)
        if not target.is_file():
            return f"not a file: {path}"
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_read_chars:
            return text[:max_read_chars] + "\n...[truncated]"
        return text

    def search_repo(query: str, limit: int = 40) -> str:
        """Search repository text with ripgrep and return bounded matches."""
        limit = max(1, min(int(limit), 200))
        try:
            proc = subprocess.run(
                ["rg", "-n", "--max-count", "5", "--", query],
                cwd=repo,
                text=True,
                capture_output=True,
                timeout=20,
            )
            lines = [line for line in proc.stdout.splitlines() if line.strip()]
        except (FileNotFoundError, subprocess.SubprocessError):
            lines = []
            for path in repo.rglob("*"):
                if len(lines) >= limit:
                    break
                if ".git" in path.parts or ".dg-agent" in path.parts or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for index, line in enumerate(text.splitlines(), start=1):
                    if query in line:
                        lines.append(f"{path.relative_to(repo).as_posix()}:{index}:{line}")
                        break
        return "\n".join(lines[:limit])

    return [list_files, read_file, search_repo]


def run_direct_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    OpenAILike, _AgentWorkflow, _FunctionAgent, _ReActAgent = import_llamaindex()
    llm = OpenAILike(**llm_kwargs(config))
    repo = Path(args.repo).resolve()
    os.chdir(repo)
    prompt = (
        "You are running through LlamaIndex over a small-context local model. "
        "Give concise output. For repository edits, recommend dg_agent.sh agent/session/task.\n\n"
        f"{args.task}"
    )
    response = llm.complete(prompt)
    if args.json:
        print(json.dumps({"status": "success", "result": str(response)}, ensure_ascii=False, indent=2))
    else:
        print(response)
    return 0


async def run_agent_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    OpenAILike, AgentWorkflow, _FunctionAgent, ReActAgent = import_llamaindex()
    llm = OpenAILike(**llm_kwargs(config))
    repo = Path(args.repo).resolve()
    os.chdir(repo)
    tools = make_repo_tools(repo, int(args.max_tool_chars))
    workflow = AgentWorkflow.from_tools_or_functions(
        tools,
        llm=llm,
        system_prompt=(
            "You are a bounded repository assistant running over a small-context "
            "local model. Use repo tools before answering questions about files. "
            "For edits, recommend dg_agent.sh agent/session/task instead of "
            "inventing patches from incomplete context."
        ),
        timeout=float(args.timeout),
        verbose=bool(args.verbose),
    )
    response = await workflow.run(args.task)
    payload = {
        "status": "success",
        "agent": ReActAgent.__name__ if not config.get("is_function_calling_model", False) else "FunctionAgent",
        "tools": [tool.__name__ for tool in tools],
        "result": str(response),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(response)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LlamaIndex with the local DiffusionGemma profile.")
    parser.add_argument("--repo", default=".", help="Target repo, used as working directory")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--task", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-import", action="store_true")
    parser.add_argument("--direct", action="store_true", help="Use direct llm.complete instead of the tool workflow")
    parser.add_argument("--timeout", type=float, default=120.0, help="Agent workflow timeout in seconds")
    parser.add_argument("--max-tool-chars", type=int, default=6000, help="Maximum characters returned by a repo tool")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose LlamaIndex workflow output")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)

    if args.smoke_import:
        OpenAILike, AgentWorkflow, FunctionAgent, ReActAgent = import_llamaindex()
        print("llamaindex import ok")
        print(OpenAILike.__name__)
        print(AgentWorkflow.__name__)
        print(FunctionAgent.__name__)
        print(ReActAgent.__name__)
        return 0

    if args.dry_run:
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "llm_class": config["llm_class"],
            "agent_workflow_class": config["agent_workflow_class"],
            "agent_class": config["agent_class"],
            "function_agent_class": config["function_agent_class"],
            "selected_agent_class": "ReActAgent" if not config.get("is_function_calling_model", False) else "FunctionAgent",
            "llm_kwargs": llm_kwargs(config),
            "tools": ["list_files", "read_file", "search_repo"],
            "command": f"scripts/dg_agent.sh llamaindex -- --repo {repo} --task '...'",
        }
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in data.items()))
        return 0

    if not args.task:
        print("--task is required unless --dry-run or --smoke-import is used", flush=True)
        return 2

    if args.direct:
        return run_direct_task(args, config)
    return asyncio.run(run_agent_task(args, config))


if __name__ == "__main__":
    raise SystemExit(main())
