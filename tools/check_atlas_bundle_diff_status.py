#!/usr/bin/env python3
"""Validate the Atlas bundle diff-status artifact."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "atlas-bundle-diff-status.v0.1.csv"

REQUIRED_COLUMNS = [
    "repo_full_name",
    "repo_size",
    "last_observed_signal",
    "indexed_code_hits",
    "user_pr_history",
    "root_file_evidence",
    "current_status",
    "recommended_action",
    "confidence",
    "blocker",
    "notes",
]

REQUIRED_REPOS = {
    "SocioProphet/atlas_master_bundle_complete",
    "SocioProphet/atlas_master_bundle_autopilot_fullorchestration",
    "SocioProphet/atlas_os_service_full",
}
ALLOWED_CONFIDENCE = {"low", "medium", "medium-high", "high"}
ALLOWED_STATUS = {
    "reference-archive-candidate",
    "strong-archive-retire-candidate",
    "retain-reference",
    "extract-and-merge",
    "active-authority",
}


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def main() -> int:
    if not ARTIFACT.exists():
        return fail(f"missing artifact: {ARTIFACT.relative_to(ROOT)}")

    with ARTIFACT.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            return fail(f"unexpected columns: {reader.fieldnames!r}")
        rows = list(reader)

    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        repo = row["repo_full_name"].strip()
        if repo in seen:
            return fail(f"duplicate repo_full_name={repo}")
        seen.add(repo)
        if repo not in REQUIRED_REPOS:
            return fail(f"row {index} unexpected Atlas repo {repo!r}")
        try:
            size = int(row["repo_size"])
        except ValueError:
            return fail(f"row {index} repo_size is not an integer: {row['repo_size']!r}")
        if size < 0:
            return fail(f"row {index} repo_size must be non-negative")
        if row["current_status"] not in ALLOWED_STATUS:
            return fail(f"row {index} invalid current_status={row['current_status']!r}")
        if row["confidence"] not in ALLOWED_CONFIDENCE:
            return fail(f"row {index} invalid confidence={row['confidence']!r}")
        if row["indexed_code_hits"] != "none":
            return fail(f"row {index} indexed_code_hits must remain explicit; expected 'none'")
        if row["user_pr_history"] != "none":
            return fail(f"row {index} user_pr_history must remain explicit; expected 'none'")
        if "direct repository tree/file listing" not in row["blocker"]:
            return fail(f"row {index} blocker must name direct repository tree/file listing")
        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

    missing = sorted(REQUIRED_REPOS - seen)
    if missing:
        return fail(f"missing required Atlas rows: {missing}")
    if len(rows) != len(REQUIRED_REPOS):
        return fail(f"expected exactly {len(REQUIRED_REPOS)} rows, found {len(rows)}")

    print(f"OK: Atlas bundle diff status valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
