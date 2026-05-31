#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = [
    ROOT / "tests" / "fixtures" / "environment" / "runtime-evidence-ingestion.allocated.valid.json",
    ROOT / "tests" / "fixtures" / "environment" / "runtime-evidence-ingestion.failed.valid.json",
]
INVALID_FIXTURES = [
    ROOT / "tests" / "fixtures" / "environment" / "runtime-evidence-ingestion.invalid-certified-with-gaps.json",
]
VALID_AFTER_STATES = {"runtime_allocated", "runtime_failed"}


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
    state_write = data.get("state_write", {})
    parity = data.get("runtime_parity", {})
    evidence_refs = agentplane.get("evidence_refs", [])
    receipt_refs = agentplane.get("receipt_refs", [])
    failure_codes = agentplane.get("failure_codes", [])
    isolation = agentplane.get("isolation_refs", {})
    blocking_gaps = parity.get("blocking_gaps", [])

    if data.get("schema_version") != "1.0":
        problems.append("schema_version must be 1.0")
    if not str(data.get("ingestion_id", "")).startswith("sociosphere:runtime-evidence-ingestion:"):
        problems.append("ingestion_id must be sociosphere runtime evidence ingestion id")
    if not str(data.get("workspace_ref", "")).startswith("workspace://"):
        problems.append("workspace_ref must start with workspace://")
    if not str(data.get("environment_profile_id", "")).startswith("environment-sandbox:profile:"):
        problems.append("environment_profile_id must reference environment-sandbox profile")
    if before != "environment_observed":
        problems.append("environment_state_before must be environment_observed")
    if after not in VALID_AFTER_STATES:
        problems.append("environment_state_after must be runtime_allocated or runtime_failed")

    if not str(agentplane.get("runtime_run_ref", "")).startswith("agentplane:runtime-sandbox-run:"):
        problems.append("runtime_run_ref must reference AgentPlane runtime sandbox run")
    if not str(agentplane.get("environment_ref", "")).startswith("environment://"):
        problems.append("environment_ref must use environment://")
    if not str(agentplane.get("dependency_graph_ref", "")).startswith("dependency-graph://"):
        problems.append("dependency_graph_ref must use dependency-graph://")
    if not str(agentplane.get("routing_ref", "")).startswith("routing://"):
        problems.append("routing_ref must use routing://")
    if not isinstance(isolation, dict):
        problems.append("isolation_refs must be an object")
    else:
        for key in ("network", "async", "stateful"):
            if not str(isolation.get(key, "")).startswith("isolation://"):
                problems.append(f"isolation_refs.{key} must use isolation://")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        problems.append("evidence_refs must be a non-empty list")
    if not isinstance(receipt_refs, list) or not receipt_refs:
        problems.append("receipt_refs must be a non-empty list")
    if any(not str(ref).startswith("evidence://") for ref in evidence_refs):
        problems.append("all evidence refs must use evidence://")
    if any(not str(ref).startswith("receipt://") for ref in receipt_refs):
        problems.append("all receipt refs must use receipt://")
    if not isinstance(failure_codes, list):
        problems.append("failure_codes must be a list when present")
    if not str(agentplane.get("leak_check_ref", "")).startswith("leak-check://"):
        problems.append("leak_check_ref must use leak-check://")

    if state_write.get("allowed") is not True:
        problems.append("state_write.allowed must be true")
    if state_write.get("state_authority") != "Sociosphere":
        problems.append("state_authority must be Sociosphere")
    if state_write.get("execution_authority") != "AgentPlane":
        problems.append("execution_authority must be AgentPlane")
    if state_write.get("product_surface") != "Prophet Platform":
        problems.append("product_surface must be Prophet Platform")

    if parity.get("level") not in {"contract_only", "runtime_observed"}:
        problems.append("runtime_parity.level is invalid")
    if not isinstance(parity.get("certified"), bool):
        problems.append("runtime_parity.certified must be boolean")
    if not isinstance(blocking_gaps, list):
        problems.append("runtime_parity.blocking_gaps must be a list")
    if parity.get("certified") is True and blocking_gaps:
        problems.append("runtime parity cannot be certified while blocking gaps remain")

    if after == "runtime_allocated":
        if parity.get("level") != "runtime_observed":
            problems.append("runtime_allocated must have runtime_observed level")
        if parity.get("certified") is not False:
            problems.append("runtime_allocated is not parity-certified in this tranche")
        for gap in ("teardown_not_complete", "leak_check_not_complete"):
            if gap not in blocking_gaps:
                problems.append(f"runtime_allocated must preserve blocking gap {gap}")
        if failure_codes:
            problems.append("runtime_allocated must not include failure codes")
        if "allocated" not in str(agentplane.get("runtime_run_ref", "")):
            problems.append("runtime_allocated must reference allocated runtime run")
    if after == "runtime_failed":
        if parity.get("level") != "contract_only":
            problems.append("runtime_failed must have contract_only level")
        if parity.get("certified") is not False:
            problems.append("runtime_failed must not be parity-certified")
        for gap in ("runtime_allocation_failed", "teardown_failed", "leak_check_failed"):
            if gap not in blocking_gaps:
                problems.append(f"runtime_failed must preserve blocking gap {gap}")
        if "runtime_allocation_failed" not in failure_codes:
            problems.append("runtime_failed must preserve runtime_allocation_failed")
        if "failed" not in str(agentplane.get("runtime_run_ref", "")):
            problems.append("runtime_failed must reference failed runtime run")

    if not isinstance(data.get("non_claims"), list) or not data.get("non_claims"):
        problems.append("non_claims must be non-empty")
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
        "validator": "sociosphere.runtime-evidence-ingestion.validator.v1",
        "passed": not failed,
        "results": results,
        "non_claims": [
            "Validator checks runtime evidence-ingestion state only.",
            "Validator does not allocate infrastructure.",
            "Validator does not certify Signadot runtime parity."
        ]
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    print(("PASS" if not failed else "FAIL") + ": runtime evidence ingestion fixtures")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
