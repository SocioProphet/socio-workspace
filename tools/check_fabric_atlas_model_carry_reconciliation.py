#!/usr/bin/env python3
"""Validate the Fabric / Atlas / Model Carry reconciliation matrix."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "architecture" / "service-register" / "fabric-atlas-model-carry-reconciliation.v0.1.csv"

REQUIRED_COLUMNS = [
    "repo_full_name",
    "observed_role",
    "prior_memory_role",
    "proposed_authority_role",
    "overlap_class",
    "canonical_owner_candidate",
    "supporting_services",
    "confidence",
    "next_action",
    "notes",
]

ALLOWED_CONFIDENCE = {"low", "medium", "medium-high", "high"}
REQUIRED_ROWS = {
    "SocioProphet/tritfabric",
    "SocioProphet/atlas_master_bundle_complete",
    "SocioProphet/atlas_master_bundle_autopilot_fullorchestration",
    "SocioProphet/atlas_os_service_full",
    "SocioProphet/prophet-platform-fabric-mlops-ts-suite",
    "SocioProphet/semantic-serdes",
    "SocioProphet/ontogenesis",
    "SourceOS-Linux/sourceos-model-carry",
    "SourceOS-Linux/sourceos-spec",
    "SourceOS-Linux/agent-machine",
    "SocioProphet/agentplane",
    "SocioProphet/model-router",
    "SocioProphet/model-governance-ledger",
    "SocioProphet/policy-fabric",
    "SocioProphet/guardrail-fabric",
    "SociOS-Linux/embeddinglab",
    "SociOS-Linux/graphlab",
    "SociOS-Linux/nlplab",
    "SociOS-Linux/speechlab",
}


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def is_repo_name(value: str) -> bool:
    parts = value.split("/")
    return len(parts) == 2 and all(parts) and not any(part.strip() != part for part in parts)


def main() -> int:
    if not ARTIFACT.exists():
        return fail(f"missing artifact: {ARTIFACT.relative_to(ROOT)}")

    with ARTIFACT.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            return fail(f"unexpected columns: {reader.fieldnames!r}")
        rows = list(reader)

    if len(rows) < len(REQUIRED_ROWS):
        return fail(f"expected at least {len(REQUIRED_ROWS)} rows, found {len(rows)}")

    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        repo = row["repo_full_name"].strip()
        owner = row["canonical_owner_candidate"].strip()
        confidence = row["confidence"].strip()

        if not is_repo_name(repo):
            return fail(f"row {index} invalid repo_full_name: {repo!r}")
        if repo in seen:
            return fail(f"duplicate repo_full_name: {repo}")
        seen.add(repo)

        if not is_repo_name(owner):
            return fail(f"row {index} invalid canonical_owner_candidate: {owner!r}")
        if confidence not in ALLOWED_CONFIDENCE:
            return fail(f"row {index} invalid confidence {confidence!r}; allowed={sorted(ALLOWED_CONFIDENCE)}")

        for column in REQUIRED_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing required value for {column}")

        if ";" not in row["overlap_class"] and row["overlap_class"] not in {"ontology", "routing", "guardrail"}:
            return fail(f"row {index} overlap_class should contain at least one classified token: {row['overlap_class']!r}")

    missing = sorted(REQUIRED_ROWS - seen)
    if missing:
        return fail(f"missing required reconciliation rows: {missing}")

    if rows[0]["repo_full_name"] != "SocioProphet/tritfabric":
        return fail("first row must keep SocioProphet/tritfabric as the root reconciliation authority")

    print(f"OK: Fabric / Atlas / Model Carry reconciliation valid ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
