#!/usr/bin/env python3
"""Validate workspace disposition metadata.

This validator is intentionally offline. It does not resolve network refs and it
must not mutate the workspace manifest. It only checks that disposition metadata
is well-formed and refers to declared workspace repos.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS_PATH = ROOT / "manifest" / "workspace.dispositions.json"
LOCK_PATH = ROOT / "manifest" / "workspace.lock.json"

ALLOWED_STATUSES = {
    "pin_drift_review_required",
    "ref_reconciliation_required",
    "alias_or_stale_pending_confirmation",
    "retain_candidate_canonical",
    "planned_or_stale_connector_stub_pending_confirmation",
    "planned_or_stale_adapter_pending_confirmation",
    "planned_or_stale_service_stub_pending_confirmation",
    "candidate_successor_pending_confirmation",
    "stale_or_merged_pending_confirmation",
    "stale_or_uncreated_pending_confirmation",
}

ALLOWED_ACTIONS = {
    "preserve_pin",
    "retain",
    "verify_ref_before_manifest_change",
    "hold_for_confirmation",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return data


def declared_names() -> set[str]:
    lock = load_json(LOCK_PATH)
    repos = lock.get("repos")
    if not isinstance(repos, list):
        raise ValueError("workspace lock repos must be a list")
    names: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            raise ValueError("workspace lock repo entries must be objects")
        name = repo.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("workspace lock repo entry missing non-empty name")
        if name in names:
            raise ValueError(f"duplicate workspace lock repo name: {name}")
        names.add(name)
    return names


def validate() -> dict[str, Any]:
    declared = declared_names()
    data = load_json(DISPOSITIONS_PATH)

    schema_version = data.get("schema_version")
    if schema_version != "sociosphere.workspace-dispositions.v0":
        raise ValueError(f"unexpected schema_version: {schema_version!r}")

    dispositions = data.get("dispositions")
    if not isinstance(dispositions, list):
        raise ValueError("dispositions must be a list")

    seen: set[str] = set()
    status_counts: dict[str, int] = {}
    for index, entry in enumerate(dispositions):
        if not isinstance(entry, dict):
            raise ValueError(f"disposition entry {index} must be an object")

        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"disposition entry {index} missing non-empty name")
        if name in seen:
            raise ValueError(f"duplicate disposition name: {name}")
        if name not in declared:
            raise ValueError(f"disposition name not present in workspace lock: {name}")
        seen.add(name)

        status = entry.get("status")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"{name}: unsupported status {status!r}")
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1

        action = entry.get("current_action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"{name}: unsupported current_action {action!r}")

        source_issue = entry.get("source_issue")
        if not isinstance(source_issue, int) or source_issue <= 0:
            raise ValueError(f"{name}: source_issue must be positive integer")

    return {
        "schema_version": "sociosphere.workspace-dispositions-validation.v0",
        "declared_repo_count": len(declared),
        "disposition_count": len(seen),
        "status_counts": dict(sorted(status_counts.items())),
        "validation_status": "valid",
    }


def main() -> int:
    try:
        report = validate()
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
