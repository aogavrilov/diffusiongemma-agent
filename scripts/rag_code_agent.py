#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:4100/v1"
DEFAULT_MODEL = "diffusiongemma-26b-a4b-it-iq4xs-agent-fast-local"

EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".cache",
    ".codex_tmp",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tools",
    ".wheelhouse",
    "__pycache__",
    "models",
    "mnt",
    "runlogs",
    "scratch",
    "temp",
    "tmp",
    "target",
    "out",
    "coverage",
}

TEXT_EXTS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".cu",
    ".cuh",
    ".h",
    ".hpp",
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".cs",
    ".sh",
    ".ps1",
    ".bat",
    ".cmake",
    ".txt",
    ".sql",
    ".html",
    ".css",
    ".scss",
}


@dataclass
class FileScore:
    score: int = 0
    lines: set[int] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)


def run(args: list[str], cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def rg_available(cwd: Path) -> bool:
    proc = run(["rg", "--version"], cwd, timeout=5)
    return proc.returncode == 0


def rg_exclude_args() -> list[str]:
    args: list[str] = []
    for name in sorted(EXCLUDE_DIRS):
        args.extend(["-g", f"!{name}/**"])
    return args


def list_files(repo: Path) -> list[Path]:
    if rg_available(repo):
        proc = run(
            [
                "rg",
                "--files",
                "--hidden",
                *rg_exclude_args(),
            ],
            repo,
            timeout=30,
        )
        if proc.returncode == 0:
            return [Path(p) for p in proc.stdout.splitlines() if is_interesting_path(Path(p))]

    files: list[Path] = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        base = Path(root)
        for name in names:
            rel = (base / name).relative_to(repo)
            if is_interesting_path(rel):
                files.append(rel)
    return files


def is_interesting_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return False
    if path.suffix.lower() in TEXT_EXTS:
        return True
    return path.name in {
        "Dockerfile",
        "Makefile",
        "CMakeLists.txt",
        "requirements.txt",
        "package.json",
        "pyproject.toml",
        ".env.example",
    }


def extract_terms(task: str) -> list[str]:
    raw = re.findall(r"[A-Za-zА-Яа-яЁё0-9_./:+#-]{3,}", task)
    stop = {
        "and",
        "the",
        "for",
        "with",
        "from",
        "where",
        "what",
        "which",
        "file",
        "files",
        "configured",
        "configuration",
        "service",
        "как",
        "что",
        "это",
        "для",
        "или",
        "его",
        "она",
        "они",
        "можно",
        "нужно",
        "сделай",
        "почему",
    }
    terms: list[str] = []
    for item in raw:
        term = item.strip(".,:;()[]{}<>\"'`").lower()
        if len(term) < 3 or term in stop:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:10]


def explicit_file_hints(task: str, files: list[Path]) -> dict[Path, str]:
    hints: dict[Path, str] = {}
    tokens = re.findall(r"[\w./\\-]+\.[A-Za-z0-9_]+", task)
    normalized = [t.replace("\\", "/").strip("./") for t in tokens]
    for rel in files:
        rel_s = rel.as_posix()
        for token in normalized:
            if rel_s.endswith(token) or rel.name == token:
                hints[rel] = f"explicit file hint: {token}"
    return hints


def score_files(repo: Path, files: list[Path], task: str) -> dict[Path, FileScore]:
    terms = extract_terms(task)
    scores: dict[Path, FileScore] = defaultdict(FileScore)

    for rel, reason in explicit_file_hints(task, files).items():
        scores[rel].score += 50
        scores[rel].reasons.append(reason)

    for rel in files:
        lower_path = rel.as_posix().lower()
        for term in terms:
            if term in lower_path:
                scores[rel].score += 5
                scores[rel].reasons.append(f"path contains '{term}'")

    if rg_available(repo):
        for term in terms:
            if len(term) > 40:
                continue
            proc = run(["rg", "--vimgrep", "-i", "-S", "-m", "8", *rg_exclude_args(), "--", term, "."], repo, timeout=20)
            if proc.returncode not in (0, 1):
                continue
            for row in proc.stdout.splitlines()[:300]:
                parts = row.split(":", 3)
                if len(parts) < 4:
                    continue
                rel = Path(parts[0])
                if not is_interesting_path(rel):
                    continue
                try:
                    line_no = int(parts[1])
                except ValueError:
                    continue
                scores[rel].score += 10
                scores[rel].lines.add(line_no)
                scores[rel].reasons.append(f"content matches '{term}'")

    if terms and not any(score.lines for score in scores.values()):
        scan_files_for_terms(repo, files, terms, scores)

    return scores


def scan_files_for_terms(repo: Path, files: list[Path], terms: list[str], scores: dict[Path, FileScore]) -> None:
    for rel in files:
        abs_path = repo / rel
        try:
            if abs_path.stat().st_size > 512_000:
                continue
            lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        lower_path = rel.as_posix().lower()
        for idx, line in enumerate(lines, start=1):
            lower_line = line.lower()
            matched = [term for term in terms if term in lower_line or term in lower_path]
            if not matched:
                continue
            scores[rel].score += 8 * len(matched)
            scores[rel].lines.add(idx)
            scores[rel].reasons.append("python scan matched " + ", ".join(matched[:3]))
            if len(scores[rel].lines) >= 8:
                break


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def snippet_for_file(repo: Path, rel: Path, matched_lines: set[int], max_chars: int) -> str:
    abs_path = repo / rel
    lines = read_lines(abs_path)
    if not lines:
        return ""

    ranges: list[tuple[int, int]] = []
    if matched_lines:
        for line_no in sorted(matched_lines)[:4]:
            start = max(1, line_no - 5)
            end = min(len(lines), line_no + 5)
            ranges.append((start, end))
    else:
        ranges.append((1, min(len(lines), 80)))

    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1] + 2:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    out: list[str] = [f"### {rel.as_posix()}"]
    used = len(out[0]) + 1
    for start, end in merged:
        block = [f"@@ {start}-{end}"]
        for idx in range(start, end + 1):
            block.append(f"{idx:>5}: {lines[idx - 1]}")
        text = "\n".join(block)
        if used + len(text) + 1 > max_chars:
            compact = [f"@@ {start}-{end}"]
            for idx in range(start, end + 1):
                line = lines[idx - 1]
                row_prefix = f"{idx:>5}: "
                remaining = max_chars - used - len("\n".join(compact)) - len(row_prefix) - 4
                if remaining <= 24:
                    break
                compact.append(row_prefix + line[: max(24, min(220, remaining))])
                compact_text = "\n".join(compact)
                if used + len(compact_text) + 1 > max_chars:
                    compact.pop()
                    break
            if len(compact) > 1:
                out.append("\n".join(compact))
            break
        out.append(text)
        used += len(text) + 1
    return "\n".join(out) if len(out) > 1 else ""


def git_context(repo: Path, max_chars: int = 600) -> str:
    root_probe = run(["git", "rev-parse", "--show-toplevel"], repo, timeout=10)
    if root_probe.returncode != 0 or not root_probe.stdout.strip():
        return ""
    try:
        git_root = Path(root_probe.stdout.strip()).resolve()
    except OSError:
        return ""
    if git_root != repo.resolve():
        return ""
    chunks: list[str] = []
    for title, cmd in (
        ("git status --short", ["git", "status", "--short"]),
        ("git diff --stat", ["git", "diff", "--stat"]),
    ):
        proc = run(cmd, repo, timeout=10)
        if proc.returncode == 0 and proc.stdout.strip():
            lines = proc.stdout.strip().splitlines()
            if len(lines) > 20:
                lines = lines[:20] + [f"... truncated {len(proc.stdout.strip().splitlines()) - 20} lines"]
            chunks.append(f"### {title}\n" + "\n".join(lines))
    text = "\n\n".join(chunks)
    return text[:max_chars]


def build_context(repo: Path, task: str, max_context_chars: int, max_files: int, debug: bool = False) -> str:
    files = list_files(repo)
    scores = score_files(repo, files, task)
    ranked = sorted(scores.items(), key=lambda item: (-item[1].score, item[0].as_posix()))[:max_files]
    overview = any(
        marker in task.lower()
        for marker in (
            "describe",
            "summarize",
            "overview",
            "what is in",
            "what is this",
            "опиши",
            "обзор",
            "что в",
            "что это",
            "проект",
        )
    )
    if overview:
        preferred_names = {"readme.md", "readme.rst", "pyproject.toml", "package.json", "cargo.toml", "main.py", "index.py"}
        text_suffixes = {".md", ".rst", ".txt", ".py", ".js", ".ts", ".json", ".toml", ".yaml", ".yml", ".tex"}
        # Overview requests need representative files even when their names do not
        # match the user's short question and therefore have no lexical score.
        preferred = [
            (rel, scores[rel])
            for rel in sorted(files, key=lambda path: (len(path.parts), path.as_posix().lower()))
            if rel.name.lower() in preferred_names
        ]
        top_level = [
            (rel, scores[rel])
            for rel in sorted(files, key=lambda path: path.as_posix().lower())
            if rel.parent == Path(".") and rel.suffix.lower() in text_suffixes
        ]
        ordered: list[tuple[Path, Any]] = []
        for item in preferred + top_level + ranked:
            if item[0] not in {path for path, _ in ordered}:
                ordered.append(item)
        ranked = ordered[:max_files]

    sections: list[str] = []
    if debug:
        debug_lines = [
            "### retrieval debug",
            "task: " + task,
            "terms: " + ", ".join(extract_terms(task)),
            f"files: {len(files)}",
            "ranked:",
        ]
        for rel, score in ranked[:10]:
            debug_lines.append(f"- {rel.as_posix()} score={score.score} lines={sorted(score.lines)[:5]}")
        sections.append("\n".join(debug_lines))

    file_map = "\n".join(p.as_posix() for p, _ in ranked[: min(20, len(ranked))])
    if file_map:
        sections.append("### selected file map\n" + file_map)

    remaining = max_context_chars - sum(len(s) + 2 for s in sections)
    for rel, score in ranked:
        if remaining <= 400:
            break
        chunk = snippet_for_file(repo, rel, score.lines, min(remaining, 1800))
        if not chunk:
            continue
        sections.append(chunk)
        remaining = max_context_chars - sum(len(s) + 2 for s in sections)

    git_info = git_context(repo)
    if git_info and sum(len(s) + 2 for s in sections) + len(git_info) + 2 <= max_context_chars:
        sections.append(git_info)

    if not sections:
        return "No relevant files were found by local retrieval."
    return "\n\n".join(sections)[:max_context_chars]


def post_chat(base_url: str, model: str, messages: list[dict[str, str]], max_tokens: int | None, timeout: int) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "n_blocks": 1,
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": "Bearer dummy"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    return body["choices"][0]["message"]["content"]


def build_prompt(task: str, context: str) -> list[dict[str, str]]:
    system = (
        "Local coding assistant. Use only provided repo context. Be concise. "
        "If changing code, output minimal diff or exact edits. Do not invent missing APIs."
    )
    user = (
        "Task:\n"
        f"{task.strip()}\n\n"
        "Repo context:\n"
        f"{context}\n\n"
        "Answer with exact files and the next action."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def main() -> int:
    parser = argparse.ArgumentParser(description="Tiny rg-based RAG wrapper for the local DiffusionGemma service.")
    parser.add_argument("task_parts", nargs="*", help="Question or coding task.")
    parser.add_argument("--task", dest="task_text", default=None, help="Question or coding task as a single option value.")
    parser.add_argument("--repo", default=".", help="Repository path to search.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-context-chars", type=int, default=650)
    parser.add_argument("--max-files", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=128, help="Completion max_tokens. Keep small for the MAXTOK=768 fast profile.")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--print-context", action="store_true", help="Print retrieved context and exit without calling the model.")
    parser.add_argument("--debug", action="store_true", help="Include retrieval terms and ranked files in printed context.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2

    task = args.task_text if args.task_text is not None else " ".join(args.task_parts)
    if not task.strip():
        print("task is empty", file=sys.stderr)
        return 2
    context = build_context(repo, task, args.max_context_chars, args.max_files, args.debug)
    if args.print_context:
        print(context)
        return 0

    messages = build_prompt(task, context)
    try:
        answer = post_chat(args.base_url, args.model, messages, args.max_tokens, args.timeout)
    except Exception as exc:
        print(f"model request failed: {exc}", file=sys.stderr)
        return 1
    print(answer.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
