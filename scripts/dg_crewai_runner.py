#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "crewai.dg.json"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_crewai() -> tuple[Any, Any, Any, Any]:
    from crewai import Agent, Crew, LLM, Task

    return Agent, Task, Crew, LLM


def llm_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": os.environ.get("CREWAI_MODEL") or config["model"],
        "base_url": os.environ.get("OPENAI_BASE_URL") or config["base_url"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "temperature": float(os.environ.get("CREWAI_TEMPERATURE") or config.get("temperature") or 0.0),
        "max_tokens": int(os.environ.get("CREWAI_MAX_TOKENS") or config.get("max_tokens") or 256),
    }


def run_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    Agent, Task, Crew, LLM = import_crewai()
    llm = LLM(**llm_kwargs(config))
    agent = Agent(
        role="Local Repository Assistant",
        goal="Answer small, bounded repository questions with concise output.",
        backstory="You use a small-context local DiffusionGemma profile. Ask for exact files before broad edits.",
        llm=llm,
        verbose=bool(config.get("verbose", False)),
        allow_delegation=False,
    )
    task = Task(
        description=args.task,
        expected_output="A concise answer. If code changes are needed, recommend using dg_agent.sh agent/session/task.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=bool(config.get("verbose", False)))
    result = crew.kickoff()
    if args.json:
        print(json.dumps({"status": "success", "result": str(result)}, ensure_ascii=False, indent=2))
    else:
        print(result)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CrewAI with the local DiffusionGemma profile.")
    parser.add_argument("--repo", default=".", help="Target repo, used as working directory")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--task", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-import", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)

    if args.smoke_import:
        Agent, Task, Crew, LLM = import_crewai()
        print("crewai import ok")
        print(Agent.__name__)
        print(Task.__name__)
        print(Crew.__name__)
        print(LLM.__name__)
        return 0

    if args.dry_run:
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "classes": config["classes"],
            "llm_kwargs": llm_kwargs(config),
            "command": f"scripts/dg_agent.sh crewai -- --repo {repo} --task '...'",
        }
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in data.items()))
        return 0

    if not args.task:
        print("--task is required unless --dry-run or --smoke-import is used", flush=True)
        return 2

    os.chdir(repo)
    return run_task(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
