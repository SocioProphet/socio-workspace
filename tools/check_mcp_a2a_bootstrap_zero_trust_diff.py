#!/usr/bin/env python3
"""Validate the MCP/A2A bootstrap vs zero-trust diff artifact."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "mcp-a2a-bootstrap-zero-trust-diff.v0.1.csv"

REQUIRED_COLUMNS = [
    "repo_full_name",
    "repo_size",
    "observed_role",
    "confirmed_assets",
    "pr_title_evidence",
    "proposed_authority_role",
    "consolidation_status",
    "confidence",
    "next_action",
    "notes",
]

REQUIRED_ROWS = {
    "SocioProphet/mcp-a2a-zero-trust",
    "SocioProphet/sourceos-a2a-mcp-bootstrap",
    "PPS-carrier-verifier",
}
ALLOWED_CONFIDENCE = {"low", "medium", "medium-high", "high"}
ALLOWED_STATUS = {
    "retain-canonical",
    "migrate-or-supersede-before-archive",
    "must-preserve",
    "archive-ready",
    "archive-ready-after-tree-confirmation",
    "preserved-in-canonical",
    "blocked",
}
EXPECTED_ROLES = {
    "SocioProphet/mcp-a2a-zero-trust": "canonical-zero-trust-authority",
    "SocioProphet/sourceos-a2a-mcp-bootstrap": "transitional-bootstrap-helper",
    "PPS-carrier-verifier": "portable-verification-asset",
}


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def is_repo_or_asset(value: str) -> bool:
    if value == "PPS-carrier-verifier":
        return True
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
    for index, row in enumerate(rows, start=2):
        key = row["repo_full_name"].strip()
        if key in seen:
            return fail(f"duplicate row: {key}")
        seen.add(key)
        if key not in REQUIRED_ROWS:
            return fail(f"row {index} unexpected row key: {key!r}")
        if not is_repo_or_asset(key):
            return fail(f"row {index} invalid repo_full_name or asset key: {key!r}")
        try:
            size = int(row["repo_size"])
        except ValueError:
            return fail(f"row {index} repo_size is not an integer: {row['repo_size']!r}")
        if size < 0:
            return fail(f"row {index} repo_size must be non-negative")
        if row["confidence"] not in ALLOWED_CONFIDENCE:
            return fail(f"row {index} invalid confidence={row['confidence']!r}")
        if row["consolidation_status"] not in ALLOWED_STATUS:
            return fail(f"row {index} invalid consolidation_status={row['consolidation_status']!r}")
        if row["proposed_authority_role"] != EXPECTED_ROLES[key]:
            return fail(f"row {index} unexpected proposed_authority_role={row['proposed_authority_role']!r}")
        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

    missing = sorted(REQUIRED_ROWS - seen)
    if missing:
        return fail(f"missing required MCP/A2A diff rows: {missing}")

    by_key = {row["repo_full_name"]: row for row in rows}
    bootstrap = by_key["SocioProphet/sourceos-a2a-mcp-bootstrap"]
    verifier = by_key["PPS-carrier-verifier"]
    canonical = by_key["SocioProphet/mcp-a2a-zero-trust"]

    if bootstrap["consolidation_status"] != "archive-ready-after-tree-confirmation":
        return fail("bootstrap row must remain archive-ready-after-tree-confirmation after PPS verifier preservation")
    if verifier["consolidation_status"] != "preserved-in-canonical":
        return fail("PPS verifier row must remain preserved-in-canonical")
    if canonical["consolidation_status"] != "retain-canonical":
        return fail("zero-trust row must remain retain-canonical")
    for row in (canonical, verifier):
        if "BLAKE3" not in row["confirmed_assets"] or "Ed25519" not in row["confirmed_assets"]:
            return fail("canonical and verifier rows must preserve BLAKE3 and Ed25519 evidence")

    print(f"OK: MCP/A2A bootstrap zero-trust diff valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
