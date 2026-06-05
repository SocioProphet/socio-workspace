#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "workspace-prophet" / "readiness.fixture_validated.json"

REQUIRED_REPOS = {
    "SocioProphet/prophet-core-contracts",
    "SocioProphet/prophet-platform",
    "SocioProphet/sherlock-search",
}
REQUIRED_BLOCKS = {
    "production_ready",
    "remote_execution",
    "autonomous_remediation",
    "customer_facing_claim",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    try:
        record = load_json(FIXTURE)
    except Exception as exc:
        print(f"ERR: failed to load readiness fixture: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    if record.get("schema_version") != "0.1.0":
        errors.append("schema_version must be 0.1.0")
    if record.get("capability_id") != "workspace_operation_prophet_membrane_v0":
        errors.append("unexpected capability_id")
    if record.get("readiness_state") != "fixture_validated":
        errors.append("readiness_state must be fixture_validated")
    if record.get("production_ready") is not False:
        errors.append("production_ready must remain false")

    repos = set(record.get("source_repos", []))
    missing_repos = sorted(REQUIRED_REPOS - repos)
    if missing_repos:
        errors.append(f"missing source_repos: {missing_repos}")

    validation_refs = record.get("validation_refs", [])
    for expected in (
        "prophet-core-contracts:make validate",
        "prophet-platform:make validate-workspace-prophet-membrane-e2e",
        "sherlock-search:make validate-workspace-prophet-evidence-index",
    ):
        if expected not in validation_refs:
            errors.append(f"missing validation ref: {expected}")

    evidence_refs = record.get("evidence_refs", [])
    for fragment in (
        "scoped-capability.schema.json",
        "action-receipt.schema.json",
        "claim-record.schema.json",
        "evidence-thread.schema.json",
        "workspace-operation-prophet-membrane-v0.json",
        "evidence-index.example.json",
    ):
        if not any(fragment in ref for ref in evidence_refs):
            errors.append(f"missing evidence ref containing: {fragment}")

    blocked = set(record.get("blocked_from", []))
    missing_blocks = sorted(REQUIRED_BLOCKS - blocked)
    if missing_blocks:
        errors.append(f"missing blocked_from entries: {missing_blocks}")

    decision = record.get("registry_decision", {})
    if decision.get("decision") != "register_fixture_validated":
        errors.append("registry_decision.decision must be register_fixture_validated")

    if errors:
        print("ERR: Workspace PROPHET readiness validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print("OK: Workspace PROPHET readiness fixture passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
