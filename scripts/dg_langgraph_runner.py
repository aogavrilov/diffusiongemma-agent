#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "langgraph.dg.json"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_langgraph() -> tuple[Any, Any, str]:
    from langchain_openai import ChatOpenAI

    try:
        from langchain.agents import create_agent
        return ChatOpenAI, create_agent, "langchain.agents.create_agent"
    except ImportError:
        from langgraph.prebuilt import create_react_agent
        return ChatOpenAI, create_react_agent, "langgraph.prebuilt.create_react_agent"


def model_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": os.environ.get("LANGGRAPH_MODEL") or config["model"],
        "base_url": os.environ.get("OPENAI_BASE_URL") or config["base_url"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "max_tokens": int(os.environ.get("LANGGRAPH_MAX_TOKENS") or config.get("max_tokens") or 256),
        "temperature": float(os.environ.get("LANGGRAPH_TEMPERATURE") or config.get("temperature") or 0.0),
    }


def build_agent(config: dict[str, Any]) -> tuple[Any, str]:
    ChatOpenAI, factory, factory_name = import_langgraph()
    model = ChatOpenAI(**model_kwargs(config))
    tools: list[Any] = []
    if factory_name == "langchain.agents.create_agent":
        return factory(model=model, tools=tools, system_prompt=config.get("system_prompt")), factory_name
    return factory(model, tools, prompt=config.get("system_prompt")), factory_name


def last_message_content(result: Any) -> str:
    if isinstance(result, dict):
        messages = result.get("messages") or []
        if messages:
            last = messages[-1]
            return str(getattr(last, "content", last.get("content") if isinstance(last, dict) else last))
    return str(result)


def run_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    agent, factory_name = build_agent(config)
    result = agent.invoke({"messages": [{"role": "user", "content": args.task}]})
    if args.json:
        print(json.dumps({"status": "success", "agent_factory": factory_name, "result": last_message_content(result)}, ensure_ascii=False, indent=2))
    else:
        print(last_message_content(result))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LangGraph/LangChain agent with the local DiffusionGemma profile.")
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
        ChatOpenAI, factory, factory_name = import_langgraph()
        print("langgraph import ok")
        print(ChatOpenAI.__name__)
        print(factory.__name__)
        print(factory_name)
        return 0

    if args.dry_run:
        _, _, factory_name = import_langgraph()
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "agent_factory": factory_name,
            "configured_agent_factory": config["agent_factory"],
            "fallback_agent_factory": config["fallback_agent_factory"],
            "model_class": config["model_class"],
            "model_kwargs": model_kwargs(config),
            "command": f"scripts/dg_agent.sh langgraph -- --repo {repo} --task '...'",
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
