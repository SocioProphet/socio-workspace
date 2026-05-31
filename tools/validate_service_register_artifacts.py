#!/usr/bin/env python3
"""Warn-only validator for SocioSphere service-register control-set artifacts.

This script checks that the expected service-register artifact locations exist and
that core CSV headers remain recognizable. Strict semantic checks live in the
specialized validators wired into the service-register workflow.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"

EXPECTED = [
    "service-architecture-register.v1.0.csv",
    "canonical-repo-estate.v1.0.csv",
    "canonical-repo-estate.mirror.v1.0.json",
    "workspace-inventory-source.v0.1.json",
    "workspace-inventory-sync-report.generated.csv",
    "service-dependency-edges.v0.1.csv",
    "critical-contract-path-stubs.v0.1.csv",
    "critical-path-blocking-report.generated.csv",
    "critical-path-blocking-report.v0.2.csv",
    "repo-reconciliation-report.v0.1.csv",
    "fabric-atlas-model-carry-reconciliation.v0.1.csv",
    "fabric-atlas-model-carry-propagation-plan.v0.1.csv",
    "service-register-drift-report.generated.csv",
    "sociosphere-service-register-ingestion-manifest.v1.0.json",
    "service-register-gate-policy.v0.1.json",
]

SERVICE_REQUIRED = [
    "service_id",
    "service_name",
    "stack_tier",
    "owning_repo",
    "supporting_repos",
    "contract_family",
    "contract_repo",
    "contract_paths",
    "runtime_authority",
    "evidence_emitted",
    "depends_on",
    "consumed_by",
    "governance_boundary",
    "product_status",
    "local_first_posture",
    "notes",
]

EDGE_REQUIRED = [
    "edge_id",
    "from_service_id",
    "to_service_id",
    "edge_kind",
    "dependency_mode",
    "cycle_policy",
    "required_for_bootstrap",
    "required_for_product_hardening",
    "evidence_required",
    "notes",
]

RECONCILIATION_REQUIRED = [
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

PROPAGATION_REQUIRED = [
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def warn(message: str) -> None:
    print(f"WARN: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def validate_csv_headers(filename: str, required: list[str]) -> None:
    path = ARTIFACT_ROOT / filename
    if not path.exists():
        warn(f"missing {filename}; strict validators may cover this in later workflow steps")
        return
    rows = read_csv(path)
    if not rows:
        warn(f"{filename} has no data rows")
        return
    missing = [name for name in required if name not in rows[0]]
    if missing:
        warn(f"{filename} missing columns: {missing}")
    else:
        ok(f"{filename} columns present; rows={len(rows)}")


def main() -> int:
    print(f"SocioSphere service-register control-set validation: {ARTIFACT_ROOT}")
    if not ARTIFACT_ROOT.exists():
        warn("architecture/service-register directory is missing")
        return 0

    for filename in EXPECTED:
        if (ARTIFACT_ROOT / filename).exists():
            ok(f"found {filename}")
        else:
            warn(f"missing {filename}")

    validate_csv_headers("service-architecture-register.v1.0.csv", SERVICE_REQUIRED)
    validate_csv_headers("service-dependency-edges.v0.1.csv", EDGE_REQUIRED)
    validate_csv_headers("fabric-atlas-model-carry-reconciliation.v0.1.csv", RECONCILIATION_REQUIRED)
    validate_csv_headers("fabric-atlas-model-carry-propagation-plan.v0.1.csv", PROPAGATION_REQUIRED)

    manifest_path = ARTIFACT_ROOT / "sociosphere-service-register-ingestion-manifest.v1.0.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            warn(f"manifest is invalid JSON: {exc}")
        else:
            ok(f"manifest artifact_id={manifest.get('artifact_id', '<missing>')}")
    else:
        warn("manifest missing")

    print("control-set validator is warn-only by design; specialized validators enforce strict gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
