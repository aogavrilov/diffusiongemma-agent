#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


DG_ROOT = Path(__file__).resolve().parents[1]
AIDER_RUNNER = DG_ROOT / "scripts" / "run_aider_local.sh"

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
    "__pycache__",
    "target",
    "out",
    "coverage",
    ".aider.dg-local",
}

TEXT_EXTS = {
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
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".cu",
    ".cuh",
    ".h",
    ".hpp",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".txt",
}

KNOWN_FILENAMES = {
    "Dockerfile",
    "Makefile",
    "CMakeLists.txt",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    ".env.example",
}


@dataclass
class Candidate:
    path: Path
    score: int = 0
    lines: set[int] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)


def run_cmd(args: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
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
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        executable="/bin/bash",
    )


def is_git_repo(repo: Path) -> bool:
    return run_cmd(["git", "rev-parse", "--is-inside-work-tree"], repo, timeout=10).stdout.strip() == "true"


def is_interesting(path: Path) -> bool:
    if set(path.parts) & EXCLUDE_DIRS:
        return False
    return path.suffix.lower() in TEXT_EXTS or path.name in KNOWN_FILENAMES


def list_files(repo: Path) -> list[Path]:
    proc = run_cmd(
        [
            "rg",
            "--files",
            "--hidden",
            "-g",
            "!.git",
            "-g",
            "!node_modules",
            "-g",
            "!build",
            "-g",
            "!dist",
            "-g",
            "!.venv",
            "-g",
            "!.aider.dg-local",
            "-g",
            "!__pycache__",
        ],
        repo,
        timeout=30,
    )
    if proc.returncode == 0:
        return [Path(row) for row in proc.stdout.splitlines() if is_interesting(Path(row))]

    found: list[Path] = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [name for name in dirs if name not in EXCLUDE_DIRS]
        base = Path(root)
        for name in names:
            rel = (base / name).relative_to(repo)
            if is_interesting(rel):
                found.append(rel)
    return sorted(found)


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
        "make",
        "change",
        "update",
        "add",
        "remove",
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
        "измени",
        "добавь",
        "файл",
    }
    terms: list[str] = []
    for item in raw:
        term = item.strip(".,:;()[]{}<>\"'`").lower()
        if len(term) < 3 or term in stop:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:16]


def explicit_file_hints(task: str, files: list[Path]) -> dict[Path, str]:
    hints: dict[Path, str] = {}
    tokens = re.findall(r"[\w./\\-]+\.[A-Za-z0-9_]+", task)
    normalized = [token.replace("\\", "/").strip("./") for token in tokens]
    for rel in files:
        rel_s = rel.as_posix()
        for token in normalized:
            if rel_s.endswith(token) or rel.name == token:
                hints[rel] = f"explicit file hint: {token}"
    return hints


def protected_file_hints(task: str, files: list[Path]) -> dict[Path, str]:
    """Find explicit files the task says must not be modified."""
    protected: dict[Path, str] = {}
    negative_prefix = re.compile(
        r"(?:\bdo\s+not|\bdon't|\bnever|\bavoid)\s+"
        r"(?:modify|edit|change|touch|update)\s+$|"
        r"(?:\bне\s+(?:меняй|изменяй|трогай|редактируй))\s+$",
        flags=re.I,
    )
    for match in re.finditer(r"[\w./\\-]+\.[A-Za-z0-9_]+", task):
        token = match.group(0).replace("\\", "/").strip("./")
        prefix = task[max(0, match.start() - 96) : match.start()]
        if not negative_prefix.search(prefix):
            continue
        for rel in files:
            if rel.as_posix().endswith(token) or rel.name == token:
                protected[rel] = f"explicit no-edit constraint: {token}"
    return protected


def score_files(repo: Path, files: list[Path], task: str) -> list[Candidate]:
    terms = extract_terms(task)
    by_path: dict[Path, Candidate] = {rel: Candidate(path=rel) for rel in files}

    for rel, reason in explicit_file_hints(task, files).items():
        by_path[rel].score += 80
        by_path[rel].reasons.append(reason)

    for rel, reason in protected_file_hints(task, files).items():
        # A named no-edit file must never win a bounded edit slot merely
        # because it also appears as an explicit path in the prompt.
        by_path[rel].score -= 10_000
        by_path[rel].reasons.append(reason)

    for rel in files:
        lower_path = rel.as_posix().lower()
        for term in terms:
            if term in lower_path:
                by_path[rel].score += 8
                by_path[rel].reasons.append(f"path contains '{term}'")

    for term in terms:
        proc = run_cmd(["rg", "--vimgrep", "-i", "-S", "-m", "12", "--", term, "."], repo, timeout=25)
        if proc.returncode not in (0, 1):
            continue
        for row in proc.stdout.splitlines()[:500]:
            parts = row.split(":", 3)
            if len(parts) < 4:
                continue
            rel = Path(parts[0])
            if rel not in by_path:
                continue
            try:
                line_no = int(parts[1])
            except ValueError:
                continue
            cand = by_path[rel]
            cand.score += 12
            cand.lines.add(line_no)
            cand.reasons.append(f"content matches '{term}'")

    ranked = [cand for cand in by_path.values() if cand.score > 0]
    ranked.sort(key=lambda item: (-item.score, item.path.as_posix()))
    return ranked


def snippet_for(repo: Path, rel: Path, lines: set[int], radius: int = 4, max_chars: int = 1200) -> str:
    path = repo / rel
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if not rows:
        return ""
    if not lines:
        start, end = 1, min(len(rows), 30)
    else:
        start = max(1, min(lines) - radius)
        end = min(len(rows), max(lines) + radius)
    out: list[str] = []
    for idx in range(start, end + 1):
        out.append(f"{idx:4}: {rows[idx - 1]}")
    text = "\n".join(out)
    return text[:max_chars]


def git_status(repo: Path) -> str:
    proc = run_cmd(["git", "status", "--short"], repo, timeout=20)
    return proc.stdout.strip()


def git_diff(repo: Path) -> str:
    proc = run_cmd(["git", "diff", "--", "."], repo, timeout=30)
    return proc.stdout


def read_text(repo: Path, rel: Path) -> str:
    return (repo / rel).read_text(encoding="utf-8", errors="replace")


def write_text(repo: Path, rel: Path, text: str) -> None:
    (repo / rel).write_text(text, encoding="utf-8")


def ensure_git_exclude(repo: Path, patterns: list[str]) -> None:
    git_path = run_cmd(["git", "rev-parse", "--git-path", "info/exclude"], repo, timeout=10)
    if git_path.returncode != 0 or not git_path.stdout.strip():
        return
    exclude_path = Path(git_path.stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = (repo / exclude_path).resolve()
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text(encoding="utf-8", errors="replace") if exclude_path.exists() else ""
    existing_patterns = {line.strip() for line in existing.splitlines()}
    missing = [pattern for pattern in patterns if pattern not in existing_patterns]
    if not missing:
        return
    suffix = "" if not existing or existing.endswith("\n") else "\n"
    addition = "# DG local agent transient files\n" + "\n".join(missing) + "\n"
    exclude_path.write_text(existing + suffix + addition, encoding="utf-8")


def derive_python_return_fix(task: str, repo: Path, rel: Path) -> tuple[str, str] | None:
    if rel.suffix.lower() != ".py":
        return None
    match = re.search(
        r"([A-Za-z_][A-Za-z0-9_]*)\(\s*['\"]([^'\"]+)['\"]\s*\)\s+returns\s+exactly\s+(.+?)(?=\s+Keep\b|\.?\s*$|\n)",
        task,
        flags=re.I | re.S,
    )
    if not match:
        return None
    func, sample_value, expected = match.groups()
    expected = expected.strip().strip("`'\"")
    text = read_text(repo, rel)
    def_match = re.search(rf"(?m)^\ufeff?def\s+{re.escape(func)}\(([^)]*)\):", text)
    if not def_match:
        return None
    params = [part.strip().split("=")[0].strip() for part in def_match.group(1).split(",") if part.strip()]
    if len(params) != 1:
        return None
    param = params[0]
    template = expected.replace(sample_value, "{" + param + "}")
    if "{" + param + "}" not in template:
        return None
    return func, f'return f"{template}"'


def derive_python_expression_return_fix(task: str, repo: Path, rel: Path) -> tuple[str, str] | None:
    """Handle a narrowly-scoped ``returns X instead of Y`` Python request."""
    if rel.suffix.lower() != ".py":
        return None
    match = re.search(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\(\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s*\)"
        r"\s+returns?\s+(.+?)\s+instead\s+of\s+(.+?)(?:\.\s|\.$|\n|$)",
        task,
        flags=re.I | re.S,
    )
    if not match:
        return None

    func, params_text, wanted, current = match.groups()
    params = [value.strip() for value in params_text.split(",")]
    wanted = wanted.strip().strip("`'\"")
    current = current.strip().strip("`'\"")
    # This fallback is deliberately limited to arithmetic expressions over the
    # named function parameters. Anything richer belongs to an OSS edit engine.
    allowed = re.compile(r"[A-Za-z0-9_ \t()+\-*/%<>=!&|~.,]+$")
    if not wanted or not current or not allowed.fullmatch(wanted) or not allowed.fullmatch(current):
        return None
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", wanted))
    if not identifiers.issubset(set(params)):
        return None

    text = read_text(repo, rel)
    def_match = re.search(rf"(?m)^\ufeff?def\s+{re.escape(func)}\(([^)]*)\):", text)
    if not def_match:
        return None
    source_params = [part.strip().split("=")[0].strip() for part in def_match.group(1).split(",") if part.strip()]
    if source_params != params:
        return None
    source_returns = re.findall(r"(?m)^\s*return\s+([^\r\n]+)$", text)
    if len(source_returns) != 1:
        return None
    normalized = lambda value: re.sub(r"\s+", "", value)
    if normalized(source_returns[0]) != normalized(current):
        return None
    return func, f"return {wanted}"


def derive_python_direct_expression_return_fix(task: str, repo: Path, rel: Path) -> tuple[str, str] | None:
    """Handle ``change file so function returns expression`` without guessing."""
    if rel.suffix.lower() != ".py":
        return None
    match = re.search(
        r"\b(?:so|that)\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\(\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)?\s*\))?"
        r"\s+returns?\s+(.+?)(?=\.\s*(?:do\s+not|keep|$)|\s+(?:do\s+not|keep)\b|$)",
        task,
        flags=re.I | re.S,
    )
    if not match:
        return None

    func, declared_params, wanted = match.groups()
    wanted = wanted.strip().strip("`'\"")
    allowed = re.compile(r"[A-Za-z0-9_ \t()+\-*/%<>=!&|~.,]+$")
    if not wanted or not allowed.fullmatch(wanted):
        return None

    text = read_text(repo, rel)
    def_match = re.search(rf"(?m)^\ufeff?def\s+{re.escape(func)}\(([^)]*)\):", text)
    if not def_match:
        return None
    source_params = [part.strip().split("=")[0].strip() for part in def_match.group(1).split(",") if part.strip()]
    if declared_params:
        requested_params = [value.strip() for value in declared_params.split(",")]
        if requested_params != source_params:
            return None
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", wanted))
    if not identifiers.issubset(set(source_params)):
        return None
    if len(re.findall(r"(?m)^\s*return\s+[^\r\n]+$", text)) != 1:
        return None
    return func, f"return {wanted}"


def derive_python_binary_operation_return_fix(task: str, repo: Path, rel: Path) -> tuple[str, str] | None:
    """Map an explicit two-argument arithmetic phrase to one Python return."""
    if rel.suffix.lower() != ".py":
        return None

    match = re.search(
        r"\b(?:so|that)\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\(\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)?\s*\))?"
        r"\s+returns?\s+(?:the\s+)?(sum|difference|product|quotient)\s+of\s+"
        r"(?:its|the)\s+(?:two\s+)?arguments?",
        task,
        flags=re.I | re.S,
    )
    if not match:
        return None

    func, declared_params, operation = match.groups()
    text = read_text(repo, rel)
    def_match = re.search(rf"(?m)^\ufeff?def\s+{re.escape(func)}\(([^)]*)\):", text)
    if not def_match:
        return None
    source_params = [part.strip().split("=")[0].strip() for part in def_match.group(1).split(",") if part.strip()]
    if len(source_params) != 2:
        return None
    if declared_params:
        requested_params = [value.strip() for value in declared_params.split(",")]
        if requested_params != source_params:
            return None
    if len(re.findall(r"(?m)^\s*return\s+[^\r\n]+$", text)) != 1:
        return None

    operator = {
        "sum": "+",
        "difference": "-",
        "product": "*",
        "quotient": "/",
    }[operation.lower()]
    return func, f"return {source_params[0]} {operator} {source_params[1]}"


def python_string(value: str) -> str:
    return repr(value)


def numeric_literal(value: str) -> str:
    value = value.strip()
    try:
        parsed = float(value)
    except ValueError:
        return value
    if parsed.is_integer():
        return str(int(parsed))
    return value


def comparison_operator(phrase: str) -> str | None:
    normalized = re.sub(r"\s+", " ", phrase.strip().lower())
    return {
        ">=": ">=",
        "greater than or equal to": ">=",
        "greater or equal to": ">=",
        "at least": ">=",
        ">": ">",
        "greater than": ">",
        "<=": "<=",
        "less than or equal to": "<=",
        "less or equal to": "<=",
        "at most": "<=",
        "<": "<",
        "less than": "<",
        "==": "==",
        "equal to": "==",
        "equals": "==",
    }.get(normalized)


def derive_python_threshold_return_fix(task: str, repo: Path, rel: Path) -> tuple[str, str] | None:
    if rel.suffix.lower() != ".py":
        return None

    func_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", task)
    behavior_match = re.search(
        r"return\s+['\"]([^'\"]+)['\"]\s+when\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
        r"(?:is\s+)?(greater than or equal to|greater or equal to|at least|>=|greater than|>|"
        r"less than or equal to|less or equal to|at most|<=|less than|<|equal to|equals|==)\s+"
        r"(-?\d+(?:\.\d+)?)\s*,?\s+otherwise\s+return\s+['\"]([^'\"]+)['\"]",
        task,
        flags=re.I | re.S,
    )
    if not func_match or not behavior_match:
        return None

    func, declared_param = func_match.groups()
    true_value, condition_param, op_phrase, threshold, false_value = behavior_match.groups()
    if declared_param != condition_param:
        return None

    text = read_text(repo, rel)
    def_match = re.search(rf"(?m)^\ufeff?def\s+{re.escape(func)}\(([^)]*)\):", text)
    if not def_match:
        return None
    params = [part.strip().split("=")[0].strip() for part in def_match.group(1).split(",") if part.strip()]
    if params != [declared_param]:
        return None

    op = comparison_operator(op_phrase)
    if not op:
        return None
    hint = (
        f"return {python_string(true_value)} "
        f"if {declared_param} {op} {numeric_literal(threshold)} "
        f"else {python_string(false_value)}"
    )
    return func, hint


def derive_python_return_hint(task: str, repo: Path, rel: Path) -> str | None:
    explicit = derive_explicit_return_hint(task, repo, rel)
    if explicit:
        return explicit
    fix = (
        derive_python_return_fix(task, repo, rel)
        or derive_python_direct_expression_return_fix(task, repo, rel)
        or derive_python_binary_operation_return_fix(task, repo, rel)
        or derive_python_threshold_return_fix(task, repo, rel)
    )
    return fix[1] if fix else None


def derive_explicit_return_hint(task: str, repo: Path, rel: Path) -> str | None:
    if rel.suffix.lower() != ".py":
        return None
    match = re.search(r"(?is)Derived exact code constraint:\s*(return\s+[^\r\n]+)", task)
    if not match:
        return None
    hint = match.group(1).strip()
    text = read_text(repo, rel)
    if len(re.findall(r"(?m)^\s*return\b", text)) != 1:
        return None
    return hint


def unquote_task_literal(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"', "`"}:
        return value[1:-1]
    return value


def derive_exact_replace_fix(task: str, repo: Path, rel: Path) -> tuple[str, str] | None:
    patterns = [
        r"(?:replace|change)\s+(['\"`][^'\"`]+['\"`])\s+(?:with|to)\s+(['\"`][^'\"`]+['\"`])",
        r"(?:replace|change)\s+the\s+text\s+(['\"`][^'\"`]+['\"`])\s+(?:with|to)\s+(['\"`][^'\"`]+['\"`])",
        r"(?:rename)\s+(['\"`][^'\"`]+['\"`])\s+(?:to)\s+(['\"`][^'\"`]+['\"`])",
    ]
    for pattern in patterns:
        match = re.search(pattern, task, flags=re.I | re.S)
        if not match:
            continue
        old, new = (unquote_task_literal(match.group(1)), unquote_task_literal(match.group(2)))
        if not old or old == new:
            continue
        text = read_text(repo, rel)
        if text.count(old) != 1:
            continue
        return old, new
    return None


def apply_python_return_hint(repo: Path, rel: Path, hint: str) -> bool:
    if rel.suffix.lower() != ".py":
        return False
    text = read_text(repo, rel)
    pattern = re.compile(r"(?m)^(\s*)return\b[^\r\n]*$")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        return False
    match = matches[0]
    replacement = f"{match.group(1)}{hint}"
    updated = text[: match.start()] + replacement + text[match.end() :]
    if updated == text:
        return False
    write_text(repo, rel, updated)
    return True


def apply_exact_replace_fix(repo: Path, rel: Path, old: str, new: str) -> bool:
    text = read_text(repo, rel)
    if text.count(old) != 1:
        return False
    updated = text.replace(old, new, 1)
    if updated == text:
        return False
    write_text(repo, rel, updated)
    return True


def apply_python_function_return_fix(repo: Path, rel: Path, func: str, hint: str) -> bool:
    text = read_text(repo, rel)
    lines = text.splitlines(keepends=True)
    def_idx = None
    def_indent = ""
    for idx, line in enumerate(lines):
        match = re.match(rf"^\ufeff?(\s*)def\s+{re.escape(func)}\([^)]*\):", line)
        if match:
            def_idx = idx
            def_indent = match.group(1)
            break
    if def_idx is None:
        return False

    end_idx = len(lines)
    for idx in range(def_idx + 1, len(lines)):
        line = lines[idx]
        if line.strip() and not line.startswith(def_indent + " ") and not line.startswith(def_indent + "\t"):
            end_idx = idx
            break

    newline = "\n"
    def_line = lines[def_idx].rstrip("\r\n")
    fixed = [def_line + newline, def_indent + "    " + hint + newline]
    updated = "".join(lines[:def_idx] + fixed + lines[end_idx:])
    if updated == text:
        return False
    write_text(repo, rel, updated)
    return True


def deterministic_repair(repo: Path, selected: list[Path], task: str) -> list[str]:
    applied: list[str] = []
    for rel in selected:
        explicit_hint = derive_explicit_return_hint(task, repo, rel)
        if explicit_hint and apply_python_return_hint(repo, rel, explicit_hint):
            applied.append(f"{rel}: applied explicit return hint `{explicit_hint}`")
            continue

        fix = (
            derive_python_return_fix(task, repo, rel)
            or derive_python_direct_expression_return_fix(task, repo, rel)
            or derive_python_binary_operation_return_fix(task, repo, rel)
            or derive_python_expression_return_fix(task, repo, rel)
            or derive_python_threshold_return_fix(task, repo, rel)
        )
        if fix:
            func, hint = fix
            if apply_python_function_return_fix(repo, rel, func, hint) or apply_python_return_hint(repo, rel, hint):
                applied.append(f"{rel}: applied derived return hint `{hint}`")
                continue

        replace_fix = derive_exact_replace_fix(task, repo, rel)
        if replace_fix:
            old, new = replace_fix
            if apply_exact_replace_fix(repo, rel, old, new):
                applied.append(f"{rel}: replaced exact text `{old}` -> `{new}`")
    return applied


def run_aider(repo: Path, files: list[Path], message: str, timeout: int) -> subprocess.CompletedProcess[str]:
    args = [str(AIDER_RUNNER), "--repo", str(repo), "--yes-always"]
    args.extend(rel.as_posix() for rel in files)
    args.extend(["--message", message])
    try:
        return run_cmd(args, DG_ROOT, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args,
            124,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=f"Aider timed out after {timeout}s",
        )


def verify_syntax(repo: Path, files: list[Path]) -> tuple[bool, str]:
    messages: list[str] = []
    ok = True
    for rel in files:
        suffix = rel.suffix.lower()
        if suffix == ".py":
            # Compile in memory so validation never leaves __pycache__ in the
            # user's repository.
            proc = run_cmd(
                [
                    sys.executable,
                    "-c",
                    "import sys, tokenize; path = sys.argv[1]; "
                    "source = tokenize.open(path).read(); compile(source, path, 'exec')",
                    rel.as_posix(),
                ],
                repo,
                timeout=30,
            )
        elif suffix == ".json":
            proc = run_cmd([sys.executable, "-m", "json.tool", rel.as_posix()], repo, timeout=30)
        elif suffix == ".sh":
            proc = run_cmd(["bash", "-n", rel.as_posix()], repo, timeout=30)
        else:
            continue
        if proc.returncode != 0:
            ok = False
            messages.append(f"{rel}: {proc.stderr or proc.stdout}")
    return ok, "\n".join(messages).strip()


def run_tests(repo: Path, command: str | None, timeout: int) -> tuple[bool, str]:
    if not command:
        return True, ""
    proc = shell_cmd(command, repo, timeout=timeout)
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, output[-4000:]


def build_message(task: str, repo: Path, candidates: list[Candidate], selected: list[Path], repair: str | None = None) -> str:
    context_parts: list[str] = []
    candidate_by_path = {cand.path: cand for cand in candidates}
    for rel in selected:
        cand = candidate_by_path.get(rel, Candidate(path=rel))
        snip = snippet_for(repo, rel, cand.lines)
        reason = "; ".join(cand.reasons[:3])
        context_parts.append(f"Selected file context for {rel}:\n{snip}\nReasons: {reason}")

    selected_text = ", ".join(path.as_posix() for path in selected)
    hints = [hint for rel in selected if (hint := derive_python_return_hint(task, repo, rel))]
    base = (
        f"{task}\n\n"
        f"Allowed files to edit: {selected_text}\n"
        "Make the smallest correct change. Preserve existing style. "
        "Do not mention or edit any file outside the allowed list.\n\n"
        + "\n\n---\n\n".join(context_parts)
    )
    if hints:
        base += "\n\nDerived exact code constraint:\n" + "\n".join(hints)
    if repair:
        base += (
            "\n\nPrevious attempt failed verification. Fix only the allowed files.\n"
            f"Verification output:\n{repair[-2500:]}"
        )
    return base


def write_report(path: Path | None, data: dict[str, object]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supervisor around rg + Aider + local DiffusionGemma proxy.")
    parser.add_argument("--repo", required=True, type=Path, help="Target git repository")
    parser.add_argument("--task", required=True, help="Task to perform")
    parser.add_argument("--file", action="append", default=[], help="Force an editable file, repeatable")
    parser.add_argument("--max-files", type=int, default=1, help="Maximum files to pass to Aider")
    parser.add_argument("--test-cmd", default="", help="Optional test command to run after edits")
    parser.add_argument("--test-timeout", type=int, default=120)
    parser.add_argument("--aider-timeout", type=int, default=420)
    parser.add_argument("--repair-attempts", type=int, default=1)
    parser.add_argument(
        "--no-deterministic-first",
        action="store_true",
        help="Do not apply deterministic exact-constraint fixes before calling Aider",
    )
    parser.add_argument("--allow-dirty", action="store_true", help="Allow starting with an already dirty repo")
    parser.add_argument("--dry-run", action="store_true", help="Only show selected files and prompt")
    parser.add_argument("--report", type=Path, default=None, help="Write JSON run report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    if not repo.exists():
        print(f"repo does not exist: {repo}", file=sys.stderr)
        return 2
    if not is_git_repo(repo):
        print(f"repo is not a git repository: {repo}", file=sys.stderr)
        return 2
    ensure_git_exclude(repo, [".aider.dg-local/", ".dg-agent/"])
    status_before = git_status(repo)
    if status_before and not args.allow_dirty:
        print("Refusing to start with a dirty repo. Use --allow-dirty if this is intentional.", file=sys.stderr)
        print(status_before, file=sys.stderr)
        return 3

    all_files = list_files(repo)
    ranked = score_files(repo, all_files, args.task)
    forced = [Path(item) for item in args.file]
    selected: list[Path] = []
    for rel in forced:
        if rel not in selected:
            selected.append(rel)
    for cand in ranked:
        if len(selected) >= args.max_files:
            break
        if cand.path not in selected:
            selected.append(cand.path)

    if not selected:
        print("No relevant files found. Add --file path/to/file.", file=sys.stderr)
        return 4

    prompt = build_message(args.task, repo, ranked, selected)
    report: dict[str, object] = {
        "repo": str(repo),
        "task": args.task,
        "selected_files": [path.as_posix() for path in selected],
        "ranked": [
            {
                "path": cand.path.as_posix(),
                "score": cand.score,
                "lines": sorted(cand.lines),
                "reasons": cand.reasons[:6],
            }
            for cand in ranked[:10]
        ],
        "started_at": time.time(),
    }

    print("Selected files:")
    for rel in selected:
        print(f"  {rel}")
    if ranked:
        print("\nTop candidates:")
        for cand in ranked[: min(5, len(ranked))]:
            reasons = "; ".join(cand.reasons[:3])
            print(f"  {cand.path} score={cand.score} {reasons}")

    if args.dry_run:
        print("\nPrompt preview:\n")
        print(prompt[:4000])
        write_report(args.report, {**report, "dry_run": True})
        return 0

    if not args.no_deterministic_first:
        deterministic = deterministic_repair(repo, selected, args.task)
        if deterministic:
            syntax_ok, syntax_output = verify_syntax(repo, selected)
            tests_ok, test_output = run_tests(repo, args.test_cmd or None, args.test_timeout)
            diff = git_diff(repo)
            if diff.strip() and syntax_ok and tests_ok:
                report.update(
                    {
                        "status": "success",
                        "strategy": "deterministic-first",
                        "deterministic_repair": deterministic,
                        "diff": diff,
                        "finished_at": time.time(),
                    }
                )
                write_report(args.report, report)
                print("\nSupervisor succeeded with deterministic-first repair. Diff:\n")
                print(diff)
                return 0
            print("\nDeterministic-first did not pass; falling back to Aider.")
            if syntax_output:
                print(syntax_output[-2000:])
            if test_output:
                print(test_output[-2000:])

    if not AIDER_RUNNER.exists():
        report.update(
            {
                "status": "failed",
                "reason": f"Aider runner missing: {AIDER_RUNNER}",
                "finished_at": time.time(),
                "diff": git_diff(repo),
            }
        )
        write_report(args.report, report)
        print(report["reason"], file=sys.stderr)
        return 2

    attempt_outputs: list[dict[str, object]] = []
    verification_error = ""
    for attempt in range(args.repair_attempts + 1):
        message = prompt if attempt == 0 else build_message(args.task, repo, ranked, selected, repair=verification_error)
        print(f"\nAider attempt {attempt + 1}/{args.repair_attempts + 1}...")
        proc = run_aider(repo, selected, message, timeout=args.aider_timeout)
        combined = (proc.stdout + "\n" + proc.stderr).strip()
        print(combined[-5000:])
        attempt_outputs.append({"attempt": attempt + 1, "returncode": proc.returncode, "output_tail": combined[-4000:]})

        syntax_ok, syntax_output = verify_syntax(repo, selected)
        tests_ok, test_output = run_tests(repo, args.test_cmd or None, args.test_timeout)
        diff = git_diff(repo)
        changed = bool(diff.strip())

        deterministic = []
        if not syntax_ok or not tests_ok:
            deterministic = deterministic_repair(repo, selected, args.task)
            if deterministic:
                syntax_ok, syntax_output = verify_syntax(repo, selected)
                tests_ok, test_output = run_tests(repo, args.test_cmd or None, args.test_timeout)
                diff = git_diff(repo)
                changed = bool(diff.strip())

        attempt_outputs[-1].update(
            {
                "syntax_ok": syntax_ok,
                "syntax_output": syntax_output,
                "tests_ok": tests_ok,
                "test_output_tail": test_output[-2000:],
                "changed": changed,
                "deterministic_repair": deterministic,
            }
        )

        if changed and syntax_ok and tests_ok and (proc.returncode == 0 or deterministic):
            report.update(
                {
                    "status": "success",
                    "strategy": "aider-with-deterministic-repair" if deterministic else "aider",
                    "attempts": attempt_outputs,
                    "diff": diff,
                    "finished_at": time.time(),
                }
            )
            write_report(args.report, report)
            print("\nSupervisor succeeded. Diff:\n")
            print(diff)
            return 0

        verification_error = "\n".join(
            part
            for part in [
                f"aider_returncode={proc.returncode}",
                "no git diff was produced" if not changed else "",
                syntax_output if not syntax_ok else "",
                test_output if not tests_ok else "",
            ]
            if part
        )
        if attempt < args.repair_attempts:
            print("\nVerification failed; trying repair.")
            print(verification_error[-2500:])

    report.update({"status": "failed", "attempts": attempt_outputs, "finished_at": time.time(), "diff": git_diff(repo)})
    write_report(args.report, report)
    print("\nSupervisor failed.")
    if verification_error:
        print(verification_error[-4000:])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
