#!/usr/bin/env python3
"""Validate the Lampstand contract registry artifact."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "lampstand-contract-registry.v0.1.csv"

REQUIRED_COLUMNS = [
    "contract_id",
    "service_id",
    "repo_full_name",
    "contract_family",
    "contract_path",
    "contract_role",
    "status",
    "validation_command",
    "notes",
]

REQUIRED_CONTRACTS = {
    "LAMPSTAND-CONTRACT-001": "lampstand.query",
    "LAMPSTAND-CONTRACT-002": "lampstand.index-publication",
    "LAMPSTAND-CONTRACT-003": "lampstand.mesh-publication-policy",
    "LAMPSTAND-CONTRACT-004": "lampstand.audit-receipt",
}
REQUIRED_SERVICE = "svc.substrate.lampstand-search"
REQUIRED_REPO = "SocioProphet/lampstand"


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
        contract_id = row["contract_id"].strip()
        if contract_id in seen:
            return fail(f"duplicate contract_id={contract_id}")
        seen.add(contract_id)
        if contract_id not in REQUIRED_CONTRACTS:
            return fail(f"row {index} unexpected contract_id={contract_id!r}")
        if row["contract_family"] != REQUIRED_CONTRACTS[contract_id]:
            return fail(f"row {index} unexpected contract_family={row['contract_family']!r}")
        if row["service_id"] != REQUIRED_SERVICE:
            return fail(f"row {index} unexpected service_id={row['service_id']!r}")
        if row["repo_full_name"] != REQUIRED_REPO:
            return fail(f"row {index} unexpected repo_full_name={row['repo_full_name']!r}")
        if row["status"] != "active":
            return fail(f"row {index} contract status must be active")
        if row["validation_command"] != "make validate":
            return fail(f"row {index} validation_command must be make validate")
        if not row["contract_path"].startswith("contracts/schemas/") or not row["contract_path"].endswith(".schema.json"):
            return fail(f"row {index} contract_path must point to a schema JSON file")
        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

    missing = sorted(set(REQUIRED_CONTRACTS) - seen)
    if missing:
        return fail(f"missing required Lampstand contracts: {missing}")
    if len(rows) != len(REQUIRED_CONTRACTS):
        return fail(f"expected exactly {len(REQUIRED_CONTRACTS)} rows, found {len(rows)}")

    print(f"OK: Lampstand contract registry valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
