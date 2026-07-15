from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi


def validate_staging(folder: Path, expected_tag: str) -> dict[str, Any]:
    manifest_path = folder / "manifest.json"
    index_path = folder / "runtime-index.json"
    if not folder.is_dir() or not manifest_path.is_file() or not index_path.is_file():
        raise ValueError(f"staged runtime is incomplete: {folder}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    files = manifest.get("files")
    if manifest.get("format") != 1 or not isinstance(files, list) or not files:
        raise ValueError("manifest.json has an unsupported format")
    if index.get("revision") != expected_tag:
        raise ValueError(f"runtime-index revision {index.get('revision')!r} does not match tag {expected_tag!r}")

    total_bytes = 0
    model_found = False
    for entry in files:
        relative = Path(str(entry.get("path", "")).replace("/", os.sep))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe manifest path: {relative}")
        target = folder / relative
        expected_size = int(entry.get("bytes", -1))
        if not target.is_file() or target.stat().st_size != expected_size:
            raise ValueError(f"missing or invalid staged file: {relative}")
        total_bytes += expected_size
        model_found = model_found or relative.name == manifest.get("model")
    if not model_found:
        raise ValueError(f"model is not represented in manifest: {manifest.get('model')}")
    return {"files": len(files), "bytes": total_bytes, "model": manifest.get("model"), "revision": expected_tag}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the staged DiffusionGemma runtime to a Hugging Face model repo")
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--folder", default="dist/hf-runtime-repo")
    parser.add_argument("--tag", default="v0.1.2-cu13-iq3")
    parser.add_argument("--package-tag", default="v0.1.2")
    parser.add_argument("--private", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN", ""), help=argparse.SUPPRESS)
    args = parser.parse_args()
    folder = Path(args.folder).resolve()
    try:
        summary = validate_staging(folder, args.tag)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.check_only:
        print(json.dumps(summary, indent=2))
        return 0
    if not args.token:
        parser.error("HF_TOKEN is missing")

    api = HfApi(token=args.token)
    api.create_repo(repo_id=args.repo_id, repo_type="model", private=args.private, exist_ok=True)
    api.upload_large_folder(
        repo_id=args.repo_id,
        repo_type="model",
        folder_path=folder,
        private=args.private,
        num_workers=max(1, args.workers),
    )
    revision = api.repo_info(repo_id=args.repo_id, repo_type="model").sha
    if not revision:
        raise RuntimeError("Hugging Face did not return the published revision")
    api.create_tag(repo_id=args.repo_id, repo_type="model", tag=args.tag, revision=revision, exist_ok=True)
    api.create_tag(repo_id=args.repo_id, repo_type="model", tag=args.package_tag, revision=revision, exist_ok=True)
    print(f"https://huggingface.co/{args.repo_id}/commit/{revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
