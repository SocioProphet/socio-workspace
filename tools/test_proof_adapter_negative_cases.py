#!/usr/bin/env python3
"""Negative tests for proof adapter validation.

These tests make sure proof adapters are load-bearing and fail closed. They do
not require pytest; CI can run this file directly.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

from validate_proof_apparatus import validate_adapter, validate_manifest


ROOT = Path(__file__).resolve().parents[1]
DUMMY_PATH = ROOT / "tmp" / "negative-proof-adapter.json"


VALID_ADAPTER: dict[str, Any] = {
    "adapter_version": "0.1",
    "repo": "SocioProphet/example-math-repo",
    "domain": "example-mathematical-physics-domain",
    "controller_protocol": "protocol/proof-apparatus-workspace/v0",
    "pfk_authority": {
        "authority_repo": "SocioProphet/Heller-Godel",
        "authority_path": "proof_fabric_kernel/",
        "pinned_commit": "988307215ad38ccb16514311222184a1b757752b",
        "consumed_schemas": [
            "PFK-SCHEMA-001",
            "PFK-SCHEMA-002",
            "PFK-SCHEMA-003",
            "PFK-SCHEMA-004",
        ],
        "consumer_maturity": "M1-pinned-schema-dependency",
        "local_schema_authority": False,
        "schema_validity_is_content_validity": False,
        "notes": ["PFK envelope validity is not theorem evidence."],
    },
    "claims": [
        {
            "claim_id": "EXAMPLE-CLAIM-001",
            "state": "draft",
            "severity": "E7",
            "substrate": "example substrate",
            "shell_level": "example shell",
            "projection": "example projection",
            "statement": "Example draft claim.",
            "boundary": ["This is a draft claim with explicit boundary."],
            "non_claim_refs": ["example.no-main-theorem-claim"],
            "owned_gates": ["claim-boundary", "fixture-check"],
            "obstruction_walls": ["certificate_wall"],
        }
    ],
    "gates": [
        {
            "gate_id": "claim-boundary",
            "kind": "claim_boundary_check",
            "status": "planned",
            "expected": "Boundary is explicit.",
        },
        {
            "gate_id": "fixture-check",
            "kind": "test",
            "status": "planned",
            "expected": "Fixture will be supplied later.",
        },
    ],
    "non_claims": [
        {
            "non_claim_id": "example.no-main-theorem-claim",
            "statement": "This adapter does not claim the main theorem.",
            "applies_to": ["EXAMPLE-CLAIM-001"],
        }
    ],
}

VALID_MANIFEST: dict[str, Any] = {
    "proof_workspace": {
        "controller_repo": "SocioProphet/sociosphere",
        "ledger_mode": "required",
        "attestation_required": True,
        "claim_schema": "standards/proof-apparatus/claim-ledger.schema.json",
        "policy": {
            "prose_only_promotion_allowed": False,
            "speculation_can_promote_to_theorem": False,
        },
        "evidence": {
            "severity_levels": ["E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7"],
            "failure_walls": [
                "certificate_wall",
                "counting_wall",
                "shell_map_preservation_wall",
                "quotient_wall",
                "preimage_wall",
                "continuum_reconstruction_wall",
                "integer_chern_wall",
                "height_bound_wall",
                "set_theoretic_wall",
                "combinatorial_extremal_wall",
            ],
        },
    },
    "repos": [
        {
            "name": "example-math-repo",
            "role": "mathematics-engine",
            "domain": "example-domain",
            "url": "https://github.com/SocioProphet/example-math-repo",
            "ref": "main",
            "local_path": "proof/example-math-repo",
            "owned_gates": ["claim-boundary"],
            "primary_walls": ["certificate_wall"],
        }
    ],
}


def clone_adapter() -> dict[str, Any]:
    return copy.deepcopy(VALID_ADAPTER)


def clone_manifest() -> dict[str, Any]:
    return copy.deepcopy(VALID_MANIFEST)


def expect_pass(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except SystemExit as exc:  # pragma: no cover - failure path
        raise AssertionError(f"expected pass but failed: {name}") from exc
    print(f"PASS expected-pass: {name}")


def expect_fail(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except SystemExit:
        print(f"PASS expected-fail: {name}")
        return
    raise AssertionError(f"expected failure but passed: {name}")


def validate_adapter_case(adapter: dict[str, Any]) -> None:
    validate_adapter(DUMMY_PATH, adapter)


def validate_manifest_case(manifest: dict[str, Any]) -> None:
    validate_manifest(manifest)


def main() -> int:
    expect_pass("valid minimal adapter", lambda: validate_adapter_case(clone_adapter()))
    expect_pass("valid generic mathematics-engine manifest role", lambda: validate_manifest_case(clone_manifest()))

    missing_claims = clone_adapter()
    del missing_claims["claims"]
    expect_fail("missing claims block", lambda: validate_adapter_case(missing_claims))

    undeclared_gate = clone_adapter()
    undeclared_gate["claims"][0]["owned_gates"].append("not-declared")
    expect_fail("claim references undeclared gate", lambda: validate_adapter_case(undeclared_gate))

    undeclared_non_claim = clone_adapter()
    undeclared_non_claim["claims"][0]["non_claim_refs"] = ["not-declared"]
    expect_fail("claim references undeclared non-claim", lambda: validate_adapter_case(undeclared_non_claim))

    no_non_claim_coverage = clone_adapter()
    no_non_claim_coverage["claims"][0]["non_claim_refs"] = []
    no_non_claim_coverage["non_claims"][0]["applies_to"] = []
    expect_fail("claim lacks non-claim coverage", lambda: validate_adapter_case(no_non_claim_coverage))

    invalid_wall = clone_adapter()
    invalid_wall["claims"][0]["obstruction_walls"] = ["not_a_wall"]
    expect_fail("invalid obstruction wall", lambda: validate_adapter_case(invalid_wall))

    self_promoted = clone_adapter()
    self_promoted["claims"][0]["state"] = "promoted"
    expect_fail("repo-local adapter self-promotion", lambda: validate_adapter_case(self_promoted))

    checked_without_passed_gate = clone_adapter()
    checked_without_passed_gate["claims"][0]["state"] = "checked"
    expect_fail("checked claim without passed gates", lambda: validate_adapter_case(checked_without_passed_gate))

    passed_gate_missing_digests = clone_adapter()
    passed_gate_missing_digests["gates"][0]["status"] = "pass"
    expect_fail("passed gate missing digests", lambda: validate_adapter_case(passed_gate_missing_digests))

    invalid_pfk_repo = clone_adapter()
    invalid_pfk_repo["pfk_authority"]["authority_repo"] = "SocioProphet/not-heller-godel"
    expect_fail("invalid PFK authority repo", lambda: validate_adapter_case(invalid_pfk_repo))

    floating_pfk_commit = clone_adapter()
    floating_pfk_commit["pfk_authority"]["pinned_commit"] = "main"
    expect_fail("PFK authority cannot float main", lambda: validate_adapter_case(floating_pfk_commit))

    unknown_pfk_schema = clone_adapter()
    unknown_pfk_schema["pfk_authority"]["consumed_schemas"] = ["PFK-SCHEMA-999"]
    expect_fail("unknown PFK schema identifier", lambda: validate_adapter_case(unknown_pfk_schema))

    duplicate_pfk_schema = clone_adapter()
    duplicate_pfk_schema["pfk_authority"]["consumed_schemas"] = ["PFK-SCHEMA-001", "PFK-SCHEMA-001"]
    expect_fail("duplicate PFK schema identifiers", lambda: validate_adapter_case(duplicate_pfk_schema))

    local_schema_authority = clone_adapter()
    local_schema_authority["pfk_authority"]["local_schema_authority"] = True
    expect_fail("local PFK schema authority forbidden", lambda: validate_adapter_case(local_schema_authority))

    schema_as_truth = clone_adapter()
    schema_as_truth["pfk_authority"]["schema_validity_is_content_validity"] = True
    expect_fail("schema validity cannot mean content validity", lambda: validate_adapter_case(schema_as_truth))

    invalid_manifest_role = clone_manifest()
    invalid_manifest_role["repos"][0]["role"] = "not-a-valid-role"
    expect_fail("manifest invalid research role", lambda: validate_manifest_case(invalid_manifest_role))

    print("proof adapter negative tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
