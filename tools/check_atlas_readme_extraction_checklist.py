#!/usr/bin/env python3
"""Validate the Atlas README extraction checklist."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "atlas-readme-extraction-checklist.v0.1.csv"

REQUIRED_COLUMNS = [
    "extraction_id",
    "source_repo",
    "source_evidence",
    "concept",
    "canonical_target",
    "extraction_status",
    "next_action",
    "notes",
]

REQUIRED_IDS = {f"ATLAS-EXTRACT-{index:03d}" for index in range(1, 11)}
REQUIRED_REPOS = {
    "SocioProphet/atlas_master_bundle_complete",
    "SocioProphet/atlas_master_bundle_autopilot_fullorchestration",
    "SocioProphet/atlas_os_service_full",
}
ALLOWED_STATUS = {"pending", "extracted", "covered-elsewhere", "not-needed", "blocked"}
ALLOWED_TARGETS = {
    "SocioProphet/tritfabric",
    "SocioProphet/prophet-platform-fabric-mlops-ts-suite",
    "SocioProphet/ontogenesis",
    "SocioProphet/agentplane",
}
EXPECTED_STATUS = {
    "ATLAS-EXTRACT-001": "extracted",
    "ATLAS-EXTRACT-002": "extracted",
    "ATLAS-EXTRACT-003": "extracted",
    "ATLAS-EXTRACT-004": "extracted",
    "ATLAS-EXTRACT-005": "blocked",
    "ATLAS-EXTRACT-006": "extracted",
    "ATLAS-EXTRACT-007": "extracted",
    "ATLAS-EXTRACT-008": "extracted",
    "ATLAS-EXTRACT-009": "extracted",
    "ATLAS-EXTRACT-010": "extracted",
}


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def is_repo(value: str) -> bool:
    parts = value.split("/")
    return len(parts) == 2 and all(parts)


def main() -> int:
    if not ARTIFACT.exists():
        return fail(f"missing artifact: {ARTIFACT.relative_to(ROOT)}")

    with ARTIFACT.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            return fail(f"unexpected columns: {reader.fieldnames!r}")
        rows = list(reader)

    seen: set[str] = set()
    repos_seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        extraction_id = row["extraction_id"].strip()
        if extraction_id in seen:
            return fail(f"duplicate extraction_id={extraction_id}")
        seen.add(extraction_id)
        source_repo = row["source_repo"].strip()
        repos_seen.add(source_repo)
        if extraction_id not in REQUIRED_IDS:
            return fail(f"row {index} unexpected extraction_id={extraction_id!r}")
        if source_repo not in REQUIRED_REPOS:
            return fail(f"row {index} unexpected source_repo={source_repo!r}")
        if not is_repo(row["canonical_target"]):
            return fail(f"row {index} invalid canonical_target={row['canonical_target']!r}")
        if row["canonical_target"] not in ALLOWED_TARGETS:
            return fail(f"row {index} unexpected canonical_target={row['canonical_target']!r}")
        if row["extraction_status"] not in ALLOWED_STATUS:
            return fail(f"row {index} invalid extraction_status={row['extraction_status']!r}")
        if row["extraction_status"] != EXPECTED_STATUS[extraction_id]:
            return fail(
                f"row {index} extraction_status must be {EXPECTED_STATUS[extraction_id]!r}; "
                "update EXPECTED_STATUS when extraction state changes"
            )
        if "README" not in row["source_evidence"]:
            return fail(f"row {index} source_evidence must cite README-derived evidence")
        if row["extraction_status"] == "extracted" and "Preserved in" not in row["next_action"]:
            return fail(f"row {index} extracted rows must cite preservation target in next_action")
        if row["extraction_status"] == "blocked" and "branch-protected" not in row["next_action"]:
            return fail(f"row {index} blocked rows must cite branch-protection reason in next_action")
        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

    missing_ids = sorted(REQUIRED_IDS - seen)
    if missing_ids:
        return fail(f"missing required extraction rows: {missing_ids}")
    missing_repos = sorted(REQUIRED_REPOS - repos_seen)
    if missing_repos:
        return fail(f"missing Atlas source repos: {missing_repos}")
    if len(rows) != len(REQUIRED_IDS):
        return fail(f"expected exactly {len(REQUIRED_IDS)} rows, found {len(rows)}")

    print(f"OK: Atlas README extraction checklist valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
