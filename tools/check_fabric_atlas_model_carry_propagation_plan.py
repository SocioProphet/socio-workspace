#!/usr/bin/env python3
"""Validate the Fabric / Atlas / Model Carry propagation plan."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "fabric-atlas-model-carry-propagation-plan.v0.1.csv"
RECONCILIATION = ROOT / "architecture" / "service-register" / "fabric-atlas-model-carry-reconciliation.v0.1.csv"

REQUIRED_COLUMNS = [
    "propagation_id",
    "source_artifact",
    "decision_scope",
    "from_authority",
    "to_consumer",
    "service_surface",
    "propagation_mode",
    "target_artifact",
    "next_action",
    "status",
    "notes",
]

ALLOWED_STATUS = {"planned", "active", "blocked", "complete"}
REQUIRED_PROPAGATIONS = {f"FAMC-PROP-{index:03d}" for index in range(1, 14)}
ALLOWED_SOURCE_ARTIFACT = "fabric-atlas-model-carry-reconciliation.v0.1.csv"
ALLOWED_TARGET_SUFFIXES = (".csv", ".json")


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def is_repo_name(value: str) -> bool:
    parts = value.split("/")
    return len(parts) == 2 and all(parts) and not any(part.strip() != part for part in parts)


def main() -> int:
    if not ARTIFACT.exists():
        return fail(f"missing artifact: {ARTIFACT.relative_to(ROOT)}")
    if not RECONCILIATION.exists():
        return fail(f"missing source reconciliation artifact: {RECONCILIATION.relative_to(ROOT)}")

    with ARTIFACT.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            return fail(f"unexpected columns: {reader.fieldnames!r}")
        rows = list(reader)

    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        prop_id = row["propagation_id"].strip()
        if prop_id in seen:
            return fail(f"duplicate propagation_id: {prop_id}")
        seen.add(prop_id)

        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

        if row["source_artifact"] != ALLOWED_SOURCE_ARTIFACT:
            return fail(f"row {index} invalid source_artifact={row['source_artifact']!r}")
        if row["status"] not in ALLOWED_STATUS:
            return fail(f"row {index} invalid status={row['status']!r}; allowed={sorted(ALLOWED_STATUS)}")
        if not is_repo_name(row["from_authority"]):
            return fail(f"row {index} invalid from_authority={row['from_authority']!r}")
        if not is_repo_name(row["to_consumer"]):
            return fail(f"row {index} invalid to_consumer={row['to_consumer']!r}")
        if not row["target_artifact"].endswith(ALLOWED_TARGET_SUFFIXES):
            return fail(f"row {index} invalid target_artifact={row['target_artifact']!r}")
        if not row["service_surface"].startswith("svc."):
            return fail(f"row {index} service_surface must start with svc.: {row['service_surface']!r}")

    missing = sorted(REQUIRED_PROPAGATIONS - seen)
    if missing:
        return fail(f"missing required propagation rows: {missing}")

    print(f"OK: Fabric / Atlas / Model Carry propagation plan valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
