#!/usr/bin/env python3
"""Build and validate the effective canonical repository registry.

The effective registry is the canonical registry plus staged registry admission
fragments. This gives admissions a checked integration surface without requiring
large full-file rewrites of registry/canonical-repos.yaml through connector APIs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "registry" / "canonical-repos.yaml"
ADMISSIONS = ROOT / "registry" / "admissions"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_canonical() -> dict[str, Any]:
    data = load_yaml(CANONICAL)
    if not isinstance(data, dict):
        raise AssertionError("canonical registry root must be a mapping")
    repos = data.get("repositories")
    if not isinstance(repos, list):
        raise AssertionError("canonical registry must contain repositories list")
    return data


def normalized_admission(admission: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": admission["id"],
        "name": admission["name"],
        "url": admission["url"],
        "role": admission["role"],
        "status": admission["status"],
        "description": admission["description"],
        "primary_language": admission["primary_language"],
        "tags": admission["tags"],
    }


def load_admissions() -> list[dict[str, Any]]:
    if not ADMISSIONS.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(ADMISSIONS.glob("*.yaml")):
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise AssertionError(f"{path}: admission root must be a mapping")
        out.append(normalized_admission(data))
    return out


def build_effective_registry() -> dict[str, Any]:
    canonical = load_canonical()
    repos = list(canonical.get("repositories", []))
    by_id = {repo.get("id"): repo for repo in repos if isinstance(repo, dict)}
    for admission in load_admissions():
        rid = admission["id"]
        if rid in by_id:
            raise AssertionError(f"admission duplicates canonical repository id: {rid}")
        repos.append(admission)
        by_id[rid] = admission
    effective = dict(canonical)
    effective["repositories"] = repos
    effective["effective_admissions_count"] = len(load_admissions())
    return effective


def validate_effective(effective: dict[str, Any]) -> None:
    repos = effective.get("repositories", [])
    ids: set[str] = set()
    urls: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            raise AssertionError("repository entry must be a mapping")
        rid = repo.get("id")
        url = repo.get("url")
        if not rid:
            raise AssertionError("repository entry missing id")
        if rid in ids:
            raise AssertionError(f"duplicate repository id: {rid}")
        ids.add(str(rid))
        if url:
            if url in urls:
                raise AssertionError(f"duplicate repository url: {url}")
            urls.add(str(url))
    if "tritfabric" not in ids:
        raise AssertionError("effective registry missing tritfabric admission")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=None)
    args = parser.parse_args()

    effective = build_effective_registry()
    validate_effective(effective)
    text = yaml.safe_dump(effective, sort_keys=False)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(text, encoding="utf-8")
        print(f"effective registry: wrote {args.write}")
    else:
        print("effective registry: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
