#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "open-interpreter.dg.json"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_open_interpreter() -> Any:
    from interpreter import interpreter

    return interpreter


def model_settings(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": os.environ.get("OPEN_INTERPRETER_MODEL") or config["model"],
        "api_base": os.environ.get("OPENAI_BASE_URL") or config["api_base"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "context_window": int(os.environ.get("OPEN_INTERPRETER_CONTEXT_WINDOW") or config.get("context_window") or 768),
        "max_tokens": int(os.environ.get("OPEN_INTERPRETER_MAX_TOKENS") or config.get("max_tokens") or 256),
        "temperature": float(os.environ.get("OPEN_INTERPRETER_TEMPERATURE") or config.get("temperature") or 0.0),
        "offline": bool(config.get("offline", True)),
        "auto_run": bool(config.get("auto_run", False)),
        "safe_mode": os.environ.get("OPEN_INTERPRETER_SAFE_MODE") or config.get("safe_mode") or "ask",
    }


def configure_interpreter(interpreter: Any, config: dict[str, Any]) -> dict[str, Any]:
    settings = model_settings(config)
    interpreter.offline = settings["offline"]
    interpreter.auto_run = settings["auto_run"]
    interpreter.safe_mode = settings["safe_mode"]
    interpreter.llm.model = settings["model"]
    interpreter.llm.api_base = settings["api_base"]
    interpreter.llm.api_key = settings["api_key"]
    interpreter.llm.context_window = settings["context_window"]
    interpreter.llm.max_tokens = settings["max_tokens"]
    interpreter.llm.temperature = settings["temperature"]
    return settings


def run_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    interpreter = import_open_interpreter()
    settings = configure_interpreter(interpreter, config)
    os.chdir(Path(args.repo).resolve())
    prompt = (
        "Use concise output. Prefer inspection and explanations. "
        "Do not make repository edits unless explicitly asked.\n\n"
        f"{args.task}"
    )
    result = interpreter.chat(prompt, display=not args.json)
    if args.json:
        print(json.dumps({"status": "success", "settings": settings, "result": result}, ensure_ascii=False, indent=2, default=str))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Open Interpreter with the local DiffusionGemma profile.")
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
        interpreter = import_open_interpreter()
        print("open-interpreter import ok")
        print(type(interpreter).__name__)
        return 0

    settings = model_settings(config)
    if args.dry_run:
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "module": config["module"],
            "agent": config["agent"],
            "settings": settings,
            "command": f"scripts/dg_agent.sh open-interpreter -- --repo {repo} --task '...'",
        }
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in data.items()))
        return 0

    if not args.task:
        print("--task is required unless --dry-run or --smoke-import is used", flush=True)
        return 2

    return run_task(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
