#!/usr/bin/env python3
"""Validate the Atlas retirement-readiness artifact."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "atlas-retirement-readiness.v0.1.csv"

REQUIRED_COLUMNS = [
    "readiness_id",
    "repo_full_name",
    "current_canonical_state",
    "extraction_state",
    "direct_tree_state",
    "retirement_readiness",
    "required_policy_decision",
    "recommended_count_after_retirement",
    "notes",
]

REQUIRED_ROWS = {
    "ATLAS-RETIRE-001": "SocioProphet/atlas_master_bundle_complete",
    "ATLAS-RETIRE-002": "SocioProphet/atlas_master_bundle_autopilot_fullorchestration",
    "ATLAS-RETIRE-003": "SocioProphet/atlas_os_service_full",
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
        readiness_id = row["readiness_id"].strip()
        if readiness_id in seen:
            return fail(f"duplicate readiness_id={readiness_id}")
        seen.add(readiness_id)
        if readiness_id not in REQUIRED_ROWS:
            return fail(f"row {index} unexpected readiness_id={readiness_id!r}")
        if row["repo_full_name"] != REQUIRED_ROWS[readiness_id]:
            return fail(f"row {index} repo_full_name mismatch: {row['repo_full_name']!r}")
        if row["current_canonical_state"] != "canonical-supporting":
            return fail(f"row {index} must remain canonical-supporting until count is formally reduced")
        if row["extraction_state"] != "extraction-discharged":
            return fail(f"row {index} extraction_state must be extraction-discharged")
        if row["direct_tree_state"] != "direct-tree-unavailable":
            return fail(f"row {index} direct_tree_state must be direct-tree-unavailable")
        if row["retirement_readiness"] != "ready-pending-policy":
            return fail(f"row {index} retirement_readiness must be ready-pending-policy")
        if "architecture-authority-may-retire" not in row["required_policy_decision"]:
            return fail(f"row {index} required_policy_decision must name architecture-authority-may-retire")
        try:
            recommended_count = int(row["recommended_count_after_retirement"])
        except ValueError:
            return fail(f"row {index} recommended_count_after_retirement must be integer")
        if recommended_count != 122:
            return fail(f"row {index} recommended_count_after_retirement must be 122")
        if "direct tree" not in row["notes"]:
            return fail(f"row {index} notes must mention direct tree limitation")
        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

    missing = sorted(set(REQUIRED_ROWS) - seen)
    if missing:
        return fail(f"missing Atlas readiness rows: {missing}")
    if len(rows) != len(REQUIRED_ROWS):
        return fail(f"expected exactly {len(REQUIRED_ROWS)} rows, found {len(rows)}")

    print(f"OK: Atlas retirement readiness valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
