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
    "SocioProphet/sociosphere",
    "SocioProphet/model-governance-ledger",
}
REQUIRED_BLOCKS = {
    "production_ready",
    "remote_execution",
    "autonomous_remediation",
    "customer_facing_claim",
}
ALLOWED_READINESS_STATES = {
    "fixture_validated",
    "runtime_receipt_fixture_validated",
}
ALLOWED_REGISTRY_DECISIONS = {
    "register_fixture_validated",
    "register_runtime_receipt_fixture_validated",
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
    if record.get("readiness_state") not in ALLOWED_READINESS_STATES:
        errors.append("readiness_state must be fixture_validated or runtime_receipt_fixture_validated")
    if record.get("production_ready") is not False:
        errors.append("production_ready must remain false")

    repos = set(record.get("source_repos", []))
    missing_repos = sorted(REQUIRED_REPOS - repos)
    if missing_repos:
        errors.append(f"missing source_repos: {missing_repos}")

    validation_refs = record.get("validation_refs", [])
    for expected in (
        "prophet-core-contracts:make validate",
        "prophet-platform:python3 tools/validate_workspace_prophet_membrane_e2e.py",
        "prophet-platform:python3 tools/validate_workspace_prophet_claim_projection.py",
        "prophet-platform:python3 tools/validate_workspace_prophet_runtime_receipts.py",
        "sherlock-search:python3 scripts/validate_workspace_prophet_search_packet.py",
        "sociosphere:python3 tools/validate_workspace_prophet_readiness.py",
        "model-governance-ledger:python3 tools/validate_workspace_prophet_ledger_entry.py",
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
        "action-receipt-workspace-operation-prophet-v0.json",
        "claim-projection-workspace-operation-prophet-v0.json",
        "runtime-receipts.generated.json",
        "search-packet.example.json",
        "workspace-prophet-readiness.yaml",
        "ledger-entry.fixture_validated.json",
    ):
        if not any(fragment in ref for ref in evidence_refs):
            errors.append(f"missing evidence ref containing: {fragment}")

    blocked = set(record.get("blocked_from", []))
    missing_blocks = sorted(REQUIRED_BLOCKS - blocked)
    if missing_blocks:
        errors.append(f"missing blocked_from entries: {missing_blocks}")

    decision = record.get("registry_decision", {})
    if decision.get("decision") not in ALLOWED_REGISTRY_DECISIONS:
        errors.append("registry_decision.decision must be an allowed fixture-readiness decision")

    metadata = record.get("metadata", {})
    if record.get("readiness_state") == "runtime_receipt_fixture_validated":
        if metadata.get("runtime_receipts_generated") is not True:
            errors.append("runtime_receipt_fixture_validated requires metadata.runtime_receipts_generated=true")
        if not metadata.get("ledger_entry_id"):
            errors.append("runtime_receipt_fixture_validated requires metadata.ledger_entry_id")

    if errors:
        print("ERR: Workspace PROPHET readiness validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print("OK: Workspace PROPHET readiness fixture passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
