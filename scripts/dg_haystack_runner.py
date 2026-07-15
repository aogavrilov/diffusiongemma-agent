#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


DG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DG_ROOT / "configs" / "client_profiles" / "haystack.dg.json"
SKIP_DIRS = {".git", ".dg-agent", ".venv", "node_modules", "__pycache__", "runlogs", ".tools"}
TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
INDEX_VERSION = 1
DEFAULT_INDEX_ROOT = DG_ROOT / "runlogs" / "dg-retrieval-index"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_haystack() -> tuple[Any, Any, Any, Any, Any, Any]:
    from haystack import Document
    from haystack.components.generators.chat import OpenAIChatGenerator
    from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
    from haystack.dataclasses import ChatMessage
    from haystack.document_stores.in_memory import InMemoryDocumentStore
    from haystack.utils import Secret

    return Document, InMemoryDocumentStore, InMemoryBM25Retriever, OpenAIChatGenerator, ChatMessage, Secret


def generator_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    generation_kwargs = dict(config.get("generation_kwargs") or {})
    generation_kwargs["max_tokens"] = int(os.environ.get("HAYSTACK_MAX_TOKENS") or config.get("max_tokens") or generation_kwargs.get("max_tokens") or 256)
    generation_kwargs["temperature"] = float(os.environ.get("HAYSTACK_TEMPERATURE") or config.get("temperature") or generation_kwargs.get("temperature") or 0.0)
    return {
        "model": os.environ.get("HAYSTACK_MODEL") or config["model"],
        "api_base_url": os.environ.get("OPENAI_BASE_URL") or config["api_base_url"],
        "api_key": os.environ.get("OPENAI_API_KEY") or config["api_key"],
        "generation_kwargs": generation_kwargs,
    }


def rg_files(repo: Path) -> list[str]:
    try:
        proc = subprocess.run(["rg", "--files"], cwd=repo, text=True, capture_output=True, timeout=20)
        if proc.returncode == 0 and proc.stdout.strip():
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    files: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path.relative_to(repo).as_posix())
    return files


def should_include(rel: str) -> bool:
    path = Path(rel)
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "Makefile", "README"}


def source_manifest(repo: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    max_files = int(config.get("max_files") or 120)
    manifest: list[dict[str, Any]] = []
    for rel in rg_files(repo):
        if len(manifest) >= max_files:
            break
        if not should_include(rel):
            continue
        target = (repo / rel).resolve()
        if repo not in target.parents and target != repo:
            continue
        try:
            stat = target.stat()
        except OSError:
            continue
        manifest.append({"path": rel, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return manifest


def source_documents(repo: Path, config: dict[str, Any], manifest: list[dict[str, Any]]) -> list[dict[str, str]]:
    max_file_chars = int(config.get("max_file_chars") or 4000)
    docs: list[dict[str, str]] = []
    for item in manifest:
        rel = str(item["path"])
        target = (repo / rel).resolve()
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        text = text.strip()
        if not text:
            continue
        if len(text) > max_file_chars:
            text = text[:max_file_chars] + "\n...[truncated]"
        docs.append({"path": rel, "content": text})
    return docs


def index_path(repo: Path, value: str) -> Path:
    if value:
        return Path(value).resolve()
    digest = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:16]
    return (DEFAULT_INDEX_ROOT / digest).resolve()


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    Path(temp_name).replace(path)


def load_or_build_index(repo: Path, config: dict[str, Any], directory: Path, rebuild: bool) -> tuple[list[dict[str, str]], dict[str, Any]]:
    manifest = source_manifest(repo, config)
    cache_file = directory / "documents.json"
    cached = None if rebuild else load_json(cache_file)
    cache_hit = bool(
        cached
        and cached.get("version") == INDEX_VERSION
        and cached.get("manifest") == manifest
        and isinstance(cached.get("documents"), list)
    )
    if cache_hit:
        documents = [item for item in cached["documents"] if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("content"), str)]
    else:
        documents = source_documents(repo, config, manifest)
        atomic_write_json(
            cache_file,
            {
                "version": INDEX_VERSION,
                "created_at": time.time(),
                "repo": str(repo),
                "manifest": manifest,
                "documents": documents,
            },
        )
    return documents, {
        "index_dir": str(directory),
        "index_file": str(cache_file),
        "cache_hit": cache_hit,
        "manifest_files": len(manifest),
        "indexed_documents": len(documents),
    }


def as_haystack_documents(documents: list[dict[str, str]]) -> list[Any]:
    Document, *_ = import_haystack()
    return [Document(content=f"File: {item['path']}\n\n{item['content']}", meta={"path": item["path"]}) for item in documents]


def retrieve_context(repo: Path, config: dict[str, Any], query: str, directory: Path, rebuild: bool) -> tuple[list[Any], dict[str, Any]]:
    _Document, InMemoryDocumentStore, InMemoryBM25Retriever, *_ = import_haystack()
    source_docs, index_stats = load_or_build_index(repo, config, directory, rebuild)
    docs = as_haystack_documents(source_docs)
    docstore = InMemoryDocumentStore()
    if docs:
        docstore.write_documents(docs)
    retriever = InMemoryBM25Retriever(document_store=docstore)
    top_k = int(config.get("top_k") or 4)
    retrieved = retriever.run(query=query, top_k=top_k).get("documents", [])
    stats = {
        **index_stats,
        "retrieved_documents": len(retrieved),
        "top_k": top_k,
        "paths": [doc.meta.get("path", "") for doc in retrieved],
    }
    return retrieved, stats


def build_messages(config: dict[str, Any], task: str, docs: list[Any]) -> list[Any]:
    *_prefix, ChatMessage, _Secret = import_haystack()
    max_prompt_chars = int(config.get("max_prompt_chars") or 14000)
    chunks: list[str] = []
    total = 0
    for doc in docs:
        content = str(doc.content)
        remaining = max_prompt_chars - total
        if remaining <= 0:
            break
        if len(content) > remaining:
            content = content[:remaining] + "\n...[truncated]"
        chunks.append(content)
        total += len(content)
    context = "\n\n---\n\n".join(chunks) if chunks else "No repository context retrieved."
    system = (
        "You are a bounded repository assistant running through Haystack RAG over "
        "a small-context local model. Answer from retrieved context only. For code "
        "edits, recommend dg_agent.sh agent/session/task instead of inventing broad patches."
    )
    user = f"Question:\n{task}\n\nRetrieved repository context:\n{context}"
    return [ChatMessage.from_system(system), ChatMessage.from_user(user)]


def run_task(args: argparse.Namespace, config: dict[str, Any]) -> int:
    repo = Path(args.repo).resolve()
    os.chdir(repo)
    docs, stats = retrieve_context(repo, config, args.task, index_path(repo, args.index_dir), args.rebuild_index)
    if args.retrieve_only:
        payload = {
            "status": "success",
            "retrieval": stats,
            "documents": [{"path": doc.meta.get("path", ""), "content": str(doc.content)} for doc in docs],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else "\n\n".join(item["content"] for item in payload["documents"]))
        return 0

    _Document, _Store, _Retriever, OpenAIChatGenerator, _ChatMessage, Secret = import_haystack()
    kwargs = generator_kwargs(config)
    api_key = kwargs.pop("api_key")
    generator = OpenAIChatGenerator(api_key=Secret.from_token(api_key), **kwargs)
    result = generator.run(messages=build_messages(config, args.task, docs))
    replies = result.get("replies", [])
    answer = replies[0].text if replies else ""
    payload = {"status": "success", "retrieval": stats, "result": answer}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(answer)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Haystack BM25 RAG with the local DiffusionGemma profile.")
    parser.add_argument("--repo", default=".", help="Target repo, used as working directory")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--task", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-import", action="store_true")
    parser.add_argument("--index-dir", default="", help="Persistent document-cache directory; defaults to runlogs/dg-retrieval-index/<repo-hash>")
    parser.add_argument("--rebuild-index", action="store_true", help="Discard the cached document set before retrieval")
    parser.add_argument("--retrieve-only", action="store_true", help="Return Haystack BM25 documents without asking the model to generate")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)

    if args.smoke_import:
        Document, InMemoryDocumentStore, InMemoryBM25Retriever, OpenAIChatGenerator, _ChatMessage, _Secret = import_haystack()
        print("haystack import ok")
        print(Document.__name__)
        print(InMemoryDocumentStore.__name__)
        print(InMemoryBM25Retriever.__name__)
        print(OpenAIChatGenerator.__name__)
        return 0

    if args.dry_run:
        data = {
            "repo": str(repo),
            "config": str(config_path),
            "document_store": config["document_store"],
            "retriever": config["retriever"],
            "generator": config["generator"],
            "generator_kwargs": generator_kwargs(config),
            "retrieval": {
                "top_k": int(config.get("top_k") or 4),
                "max_files": int(config.get("max_files") or 120),
                "max_file_chars": int(config.get("max_file_chars") or 4000),
                "index_dir": str(index_path(repo, args.index_dir)),
                "persistent_cache": True,
            },
            "command": f"scripts/dg_agent.sh haystack -- --repo {repo} --task '...'",
        }
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in data.items()))
        return 0

    if not args.task:
        print("--task is required unless --dry-run or --smoke-import is used", flush=True)
        return 2

    return run_task(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
