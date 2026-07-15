#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "autogen.dg.json"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def model_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": os.environ.get("AUTOGEN_MODEL") or config["model"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "base_url": os.environ.get("OPENAI_BASE_URL") or config["base_url"],
        "model_info": config["model_info"],
        "max_tokens": int(os.environ.get("AUTOGEN_MAX_TOKENS") or config.get("max_tokens") or 256),
        "temperature": float(os.environ.get("AUTOGEN_TEMPERATURE") or config.get("temperature") or 0.0),
    }


async def run_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    client = OpenAIChatCompletionClient(**model_kwargs(config))
    system_message = (
        "You are running through the local DiffusionGemma AutoGen profile. "
        "Keep answers short, ask for explicit file snippets before broad edits, "
        "and prefer DG MCP/session tools when available."
    )
    agent = AssistantAgent("dg_autogen", model_client=client, system_message=system_message)
    try:
        result = await agent.run(task=args.task)
    finally:
        await client.close()

    if args.json:
        print(json.dumps({"status": "success", "messages": [str(item) for item in result.messages]}, ensure_ascii=False, indent=2))
    else:
        last = result.messages[-1] if result.messages else ""
        print(getattr(last, "content", str(last)))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AutoGen AgentChat with the local DiffusionGemma profile.")
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
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        print("autogen import ok")
        print(AssistantAgent.__name__)
        print(OpenAIChatCompletionClient.__name__)
        print(config["model_client"])
        return 0

    if args.dry_run:
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "model_client": config["model_client"],
            "model_kwargs": model_kwargs(config),
            "command": f"scripts/dg_agent.sh autogen -- --repo {repo} --task '...'",
        }
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in data.items()))
        return 0

    if not args.task:
        print("--task is required unless --dry-run or --smoke-import is used", flush=True)
        return 2

    os.chdir(repo)
    return asyncio.run(run_task(args, config))


if __name__ == "__main__":
    raise SystemExit(main())
