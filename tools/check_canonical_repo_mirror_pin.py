#!/usr/bin/env python3
"""Validate the pinned local mirror of workspace-inventory's canonical repo estate."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "architecture" / "service-register" / "canonical-repo-estate.mirror.v1.0.json"


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def main() -> int:
    if not MANIFEST.exists():
        return fail(f"missing mirror manifest: {MANIFEST.relative_to(ROOT)}")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"invalid mirror manifest JSON: {exc}")

    local_path = manifest.get("local_artifact_path")
    if not isinstance(local_path, str) or not local_path:
        return fail("mirror manifest missing local_artifact_path")

    artifact = ROOT / local_path
    if not artifact.exists():
        return fail(f"missing local mirror artifact: {local_path}")

    expected_sha = manifest.get("expected_git_blob_sha")
    if not isinstance(expected_sha, str) or len(expected_sha) != 40:
        return fail(f"invalid expected_git_blob_sha: {expected_sha!r}")

    data = artifact.read_bytes()
    actual_sha = git_blob_sha(data)
    if actual_sha != expected_sha:
        return fail(f"mirror Git blob SHA {actual_sha} != expected {expected_sha}")

    expected_columns = manifest.get("expected_columns")
    if not isinstance(expected_columns, list) or not all(isinstance(item, str) for item in expected_columns):
        return fail("mirror manifest expected_columns must be a list of strings")

    with artifact.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_columns:
            return fail(f"mirror columns {reader.fieldnames!r} != expected {expected_columns!r}")
        rows = list(reader)

    expected_rows = manifest.get("expected_row_count")
    if len(rows) != expected_rows:
        return fail(f"mirror row count {len(rows)} != expected {expected_rows}")

    repos: set[str] = set()
    for index, row in enumerate(rows, start=2):
        repo = row.get("repo_full_name", "").strip()
        if not repo or "/" not in repo:
            return fail(f"row {index} invalid repo_full_name: {repo!r}")
        if repo in repos:
            return fail(f"duplicate repo_full_name: {repo}")
        repos.add(repo)

    print(f"OK: canonical repo estate mirror pin valid ({len(rows)} repos, git blob {actual_sha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
