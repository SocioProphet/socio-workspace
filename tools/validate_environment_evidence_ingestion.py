#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = [
    ROOT / "tests" / "fixtures" / "environment" / "evidence-ingestion.observed.valid.json",
    ROOT / "tests" / "fixtures" / "environment" / "evidence-ingestion.failed.valid.json",
]
INVALID_FIXTURES = [
    ROOT / "tests" / "fixtures" / "environment" / "evidence-ingestion.observed.missing-evidence.invalid.json",
]
VALID_STATES = {"environment_requested", "environment_observed", "environment_failed"}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object: {path}")
    return data


def validate(data: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    before = data.get("environment_state_before")
    after = data.get("environment_state_after")
    agentplane = data.get("agentplane_refs", {})
    evidence_refs = agentplane.get("evidence_refs", [])
    receipt_refs = agentplane.get("receipt_refs", [])
    failure_codes = agentplane.get("failure_codes", [])
    state_write = data.get("state_write", {})

    if data.get("schema_version") != "1.0":
        problems.append("schema_version must be 1.0")
    if not str(data.get("ingestion_id", "")).startswith("sociosphere:environment-evidence-ingestion:"):
        problems.append("ingestion_id shape is invalid")
    if not str(data.get("workspace_ref", "")).startswith("workspace://"):
        problems.append("workspace_ref must start with workspace://")
    if not str(data.get("environment_profile_id", "")).startswith("environment-sandbox:profile:"):
        problems.append("environment_profile_id shape is invalid")
    if before not in VALID_STATES:
        problems.append(f"invalid environment_state_before: {before}")
    if after not in VALID_STATES:
        problems.append(f"invalid environment_state_after: {after}")
    if before != "environment_requested":
        problems.append("ingestion must start from environment_requested in this tranche")
    if after not in {"environment_observed", "environment_failed"}:
        problems.append("ingestion must end in observed or failed")

    pp = data.get("prophet_platform_refs", {})
    if not str(pp.get("request_id", "")).startswith("environment:validate-change-v2-request:"):
        problems.append("prophet_platform_refs.request_id must reference validate_change v2")
    if after == "environment_observed" and not str(pp.get("response_id", "")).startswith("environment:validate-change-v2-response:observed:"):
        problems.append("observed ingestion must reference observed response")
    if after == "environment_failed" and not str(pp.get("response_id", "")).startswith("environment:validate-change-v2-response:failed:"):
        problems.append("failed ingestion must reference failed response")
    if not str(pp.get("run_link_id", "")).startswith("environment:validate-change-v2-agentplane-link:"):
        problems.append("run_link_id shape is invalid")

    if not str(agentplane.get("sandbox_run_ref", "")).startswith("agentplane:sandbox-run:"):
        problems.append("sandbox_run_ref must reference AgentPlane sandbox run")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        problems.append("evidence_refs must be a non-empty list")
    if not isinstance(receipt_refs, list) or not receipt_refs:
        problems.append("receipt_refs must be a non-empty list")
    if any(not str(ref).startswith("evidence://") for ref in evidence_refs):
        problems.append("all evidence refs must use evidence://")
    if any(not str(ref).startswith("receipt://") for ref in receipt_refs):
        problems.append("all receipt refs must use receipt://")

    if after == "environment_observed" and failure_codes:
        problems.append("observed ingestion must not carry failure_codes")
    if after == "environment_failed" and "synthetic_validation_failed" not in failure_codes:
        problems.append("failed ingestion must carry synthetic_validation_failed")

    if state_write.get("allowed") is not True:
        problems.append("state_write.allowed must be true for valid ingestion")
    if state_write.get("state_authority") != "Sociosphere":
        problems.append("state authority must be Sociosphere")
    if state_write.get("execution_authority") != "AgentPlane":
        problems.append("execution authority must be AgentPlane")
    if state_write.get("product_surface") != "Prophet Platform":
        problems.append("product surface must be Prophet Platform")

    non_claims = data.get("non_claims", [])
    if not isinstance(non_claims, list) or not non_claims:
        problems.append("non_claims must be a non-empty list")
    return problems


def main() -> int:
    failed = False
    results: dict[str, Any] = {"valid": {}, "invalid": {}}

    for path in VALID_FIXTURES:
        problems = validate(load(path))
        results["valid"][str(path.relative_to(ROOT))] = problems
        failed = failed or bool(problems)

    for path in INVALID_FIXTURES:
        problems = validate(load(path))
        if not problems:
            problems = ["expected invalid fixture to fail validation"]
            failed = True
        results["invalid"][str(path.relative_to(ROOT))] = problems

    report = {
        "validator": "sociosphere.environment-evidence-ingestion.synthetic.v1",
        "passed": not failed,
        "results": results,
        "non_claims": [
            "Validator checks Sociosphere state-ingestion semantics only.",
            "Validator does not execute infrastructure.",
            "Validator does not certify runtime parity."
        ]
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    print(("PASS" if not failed else "FAIL") + ": environment evidence ingestion fixtures")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
