#!/usr/bin/env python3
"""Report coverage of the live resolved workspace lock.

This is intentionally offline. It compares the declared workspace lock with the
live-resolved lock artifact and reports whether the resolved artifact covers the
full estate or only a slice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DECLARED_LOCK = ROOT / "manifest" / "workspace.lock.json"
RESOLVED_LOCK = ROOT / "manifest" / "workspace.resolved.lock.json"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be object")
    return data


def names(lock: dict[str, Any]) -> set[str]:
    repos = lock.get("repos")
    if not isinstance(repos, list):
        raise ValueError("lock repos must be list")
    result: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict) or not repo.get("name"):
            raise ValueError("repo entry missing name")
        name = str(repo["name"])
        if name in result:
            raise ValueError(f"duplicate repo name: {name}")
        result.add(name)
    return result


def status_counts(resolved: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for repo in resolved.get("repos", []):
        status = str(repo.get("resolution_status", "missing_status"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def build_report() -> dict[str, Any]:
    declared = load(DECLARED_LOCK)
    resolved = load(RESOLVED_LOCK)
    declared_names = names(declared)
    resolved_names = names(resolved)
    missing = sorted(declared_names - resolved_names)
    extra = sorted(resolved_names - declared_names)
    report_status = "full_estate" if not missing and not extra else "partial"
    return {
        "schema_version": "sociosphere.workspace-resolved-lock-coverage.v0",
        "source_declared_lock": "manifest/workspace.lock.json",
        "source_resolved_lock": "manifest/workspace.resolved.lock.json",
        "declared_repo_count": len(declared_names),
        "resolved_repo_count": len(resolved_names),
        "missing_from_resolved_count": len(missing),
        "extra_in_resolved_count": len(extra),
        "resolution_status_counts": status_counts(resolved),
        "report_status": report_status,
        "missing_from_resolved": missing,
        "extra_in_resolved": extra,
    }


def main() -> int:
    try:
        report = build_report()
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
