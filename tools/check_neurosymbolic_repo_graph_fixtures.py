#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"

REQUIRED_FILES = {
    "valid.active-spine-inference.json": "governed_candidate",
    "invalid.missing-boundary.json": "block_governed_action",
    "invalid.policy-denied-shacl-pass.json": "block_governed_action",
    "diagnostic.stale-pin.json": "diagnostic_finding_only",
}

REQUIRED_PLANES = {
    "evidence": "SocioProphet/sherlock-search",
    "ontology": "SocioProphet/ontogenesis",
    "policy": "SocioProphet/policy-fabric",
    "runtime": "SocioProphet/agentplane",
    "ledger": "SocioProphet/model-governance-ledger",
}

REQUIRED_REASONING = {
    "valid.active-spine-inference.json": {
        "chronos": "all_required_governance_surfaces_present",
        "watson_cyc": "runtime_product_may_consume_standards_when_boundary_and_policy_are_present",
    },
    "invalid.missing-boundary.json": {
        "chronos": "promotion_candidate_blocked_by_missing_boundary",
        "watson_cyc": "proof_runtime_requires_boundary_before_action",
    },
    "invalid.policy-denied-shacl-pass.json": {
        "chronos": "shacl_passed_but_policy_denied_current_transition",
        "watson_cyc": "shape_conformance_is_not_action_authorization",
    },
    "diagnostic.stale-pin.json": {
        "chronos": "stale_pin_emits_diagnostic_not_automatic_action",
        "watson_cyc": "freshness_gap_requires_review_before_execution",
    },
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def main() -> int:
    failed = False

    for filename, expected_result in REQUIRED_FILES.items():
        path = FIXTURE_DIR / filename
        if not path.exists():
            fail(f"missing fixture: {filename}")
            failed = True
            continue

        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("corpus_loop") != "watson-cyc-semantic-web-chronos-v1":
            fail(f"{filename}: wrong corpus_loop")
            failed = True
        if fixture.get("expected_result") != expected_result:
            fail(f"{filename}: wrong expected_result")
            failed = True

        planes = fixture.get("planes", {})
        for plane, repo in REQUIRED_PLANES.items():
            if planes.get(plane) != repo:
                fail(f"{filename}: missing plane {plane} -> {repo}")
                failed = True

        reasoning = fixture.get("reasoning", {})
        for key, value in REQUIRED_REASONING[filename].items():
            if reasoning.get(key) != value:
                fail(f"{filename}: missing reasoning {key} -> {value}")
                failed = True

        graph_state = fixture.get("graph_state", {})
        if filename.startswith("valid.") and graph_state.get("policy_decision") != "allow":
            fail(f"{filename}: valid fixture must have allow policy decision")
            failed = True
        if filename.startswith("invalid.") and graph_state.get("policy_decision") != "deny":
            fail(f"{filename}: invalid fixture must have deny policy decision")
            failed = True
        if filename.startswith("diagnostic.") and graph_state.get("policy_decision") != "review_required":
            fail(f"{filename}: diagnostic fixture must require review")
            failed = True

    if failed:
        return 1

    print("OK: neurosymbolic repo graph fixtures cover governed, blocked, and diagnostic cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
