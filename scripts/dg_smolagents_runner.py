#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "smolagents.dg.json"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_smolagents() -> tuple[Any, Any]:
    from smolagents import CodeAgent

    try:
        from smolagents import OpenAIModel as ModelClass
    except ImportError:
        from smolagents import OpenAIServerModel as ModelClass
    return CodeAgent, ModelClass


def model_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    data = {
        "model_id": os.environ.get("SMOLAGENTS_MODEL") or config["model_id"],
        "api_base": os.environ.get("OPENAI_BASE_URL") or config["api_base"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "max_tokens": int(os.environ.get("SMOLAGENTS_MAX_TOKENS") or config.get("max_tokens") or 256),
        "temperature": float(os.environ.get("SMOLAGENTS_TEMPERATURE") or config.get("temperature") or 0.0),
    }
    if "flatten_messages_as_text" in config:
        data["flatten_messages_as_text"] = bool(config["flatten_messages_as_text"])
    return data


def run_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    CodeAgent, ModelClass = import_smolagents()
    model = ModelClass(**model_kwargs(config))
    agent = CodeAgent(
        tools=[],
        model=model,
        max_steps=int(os.environ.get("SMOLAGENTS_MAX_STEPS") or config.get("max_steps") or 2),
        verbosity_level=1,
    )
    result = agent.run(args.task)
    if args.json:
        print(json.dumps({"status": "success", "result": str(result)}, ensure_ascii=False, indent=2))
    else:
        print(result)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hugging Face smolagents CodeAgent with the local DiffusionGemma profile.")
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
        CodeAgent, ModelClass = import_smolagents()
        print("smolagents import ok")
        print(CodeAgent.__name__)
        print(ModelClass.__name__)
        print(config["model_class"])
        return 0

    if args.dry_run:
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "agent": config["agent"],
            "model_class": config["model_class"],
            "model_kwargs": model_kwargs(config),
            "max_steps": int(os.environ.get("SMOLAGENTS_MAX_STEPS") or config.get("max_steps") or 2),
            "command": f"scripts/dg_agent.sh smolagents -- --repo {repo} --task '...'",
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
