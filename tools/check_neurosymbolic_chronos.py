#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "registry" / "corpus-loop-v0"
VALID = FIXTURES / "valid.asu-nsr-chronos.json"
INVALIDS = [
    FIXTURES / "invalid.soft-score-as-authority.json",
    FIXTURES / "invalid.ungrounded-symbol-promotion.json",
    FIXTURES / "invalid.label-leakage-carrier.json",
]

REQUIRED_METHOD_FAMILIES = {
    "NSR-FOUNDATION-LOGIC",
    "NSR-TAXONOMY",
    "NSR-SOFT-CONSTRAINT",
    "NSR-TRUTH-BOUND",
    "NSR-SYMBOLIC-ADJUDICATION",
    "NSR-DIFFERENTIABLE-CONSTRAINT-LEARNING",
    "NSR-RULE-LEARNING",
    "NSR-ONTOLOGY-INFERENCE",
    "NSR-SYMBOLIC-POLICY",
}

REQUIRED_AUTHORITIES = {
    "integrationPlane": "SocioProphet/sociosphere",
    "schemaAuthority": "SourceOS-Linux/sourceos-spec",
    "semanticVocabularyDraft": "SocioProphet/ontogenesis",
    "evidenceReplayAuthority": "SocioProphet/agentplane",
    "policyAdmissionAuthority": "SocioProphet/policy-fabric",
    "modelGovernanceAuthority": "SocioProphet/model-governance-ledger",
    "routingAuthority": "SocioProphet/model-router",
}

FAILURE_MODE_BY_FILE = {
    "invalid.soft-score-as-authority.json": "soft_score_as_truth",
    "invalid.ungrounded-symbol-promotion.json": "ungrounded_symbol_promotion",
    "invalid.label-leakage-carrier.json": "label_leakage_grounding_failure",
}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be object")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def dotted(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise SystemExit(f"missing field: {path}")
        current = current[part]
    return current


def validate_valid_fixture(data: dict[str, Any]) -> None:
    require(data.get("kind") == "ChronosCarrierRegistration", "valid fixture wrong kind")
    require(data.get("schemaVersion") == "0.1.0", "valid fixture wrong schemaVersion")
    require(dotted(data, "carrier.status") == "candidate", "valid carrier must remain candidate")
    require(
        dotted(data, "carrier.claimStatus") == "derived-integration-summary",
        "valid carrier claimStatus must be derived-integration-summary",
    )
    require(
        dotted(data, "carrier.validationState") == "human-reviewed-corpus-map",
        "valid carrier validationState mismatch",
    )
    families = set(dotted(data, "carrier.methodFamilies"))
    require(families == REQUIRED_METHOD_FAMILIES, "valid carrier method family set drifted")
    declaration = dotted(data, "carrier.nonAuthorityDeclaration")
    require(isinstance(declaration, str) and "does not promote" in declaration, "valid fixture missing non-authority declaration")
    authorities = dotted(data, "authority")
    for key, expected in REQUIRED_AUTHORITIES.items():
        require(authorities.get(key) == expected, f"authority mismatch for {key}")
    lifecycle = dotted(data, "replay.expectedLifecycle")
    require("governance_decision" in lifecycle, "valid fixture must include governance_decision lifecycle step")
    require("receipt_or_rejection" in lifecycle, "valid fixture must include receipt_or_rejection lifecycle step")


def assert_invalid_rejected(path: Path, data: dict[str, Any]) -> None:
    expected_failure_mode = FAILURE_MODE_BY_FILE[path.name]
    failure = data.get("expectedValidationFailure")
    require(isinstance(failure, dict), f"{path.name}: missing expectedValidationFailure")
    require(failure.get("failureMode") == expected_failure_mode, f"{path.name}: failure mode drift")

    carrier = data.get("carrier", {})
    authority = data.get("authority", {})
    require(isinstance(carrier, dict), f"{path.name}: carrier must be object")
    require(isinstance(authority, dict), f"{path.name}: authority must be object")

    if path.name == "invalid.soft-score-as-authority.json":
        require(carrier.get("status") == "admitted", "soft-score fixture must try invalid admission")
        require(carrier.get("validationState") == "soft-score-only", "soft-score fixture must expose soft-score-only validation")
        require(authority.get("policyAdmissionAuthority") == "self-authorized-by-score", "soft-score fixture must expose self-authorization")

    if path.name == "invalid.ungrounded-symbol-promotion.json":
        require(not data.get("source", {}).get("evidenceRefs"), "ungrounded symbol fixture must lack evidence refs")
        require(carrier.get("groundingStatus") == "unknown", "ungrounded symbol fixture must expose unknown grounding")
        require(authority.get("schemaAuthority") == "bypassed", "ungrounded symbol fixture must bypass schema authority")

    if path.name == "invalid.label-leakage-carrier.json":
        require(carrier.get("leakageAssessment") == "missing", "label-leakage fixture must lack leakage assessment")
        require(carrier.get("transductionAssessment") == "missing", "label-leakage fixture must lack transduction assessment")
        require(authority.get("evidenceReplayAuthority") == "missing", "label-leakage fixture must lack evidence replay authority")


def main() -> int:
    validate_valid_fixture(load(VALID))
    for path in INVALIDS:
        assert_invalid_rejected(path, load(path))
    print("OK: neuro-symbolic CHRONOS carrier fixtures validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
