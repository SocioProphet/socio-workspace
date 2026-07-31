#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "registry" / "corpus-loop-v0"
VALID_ASU_NSR = FIXTURES / "valid.asu-nsr-chronos.json"
VALID_SR = FIXTURES / "valid.symbolic-regression-insertion-map.json"
INVALIDS = [
    FIXTURES / "invalid.soft-score-as-authority.json",
    FIXTURES / "invalid.ungrounded-symbol-promotion.json",
    FIXTURES / "invalid.label-leakage-carrier.json",
    FIXTURES / "invalid.visual-embedding-as-evidence.json",
    FIXTURES / "invalid.transduction-certificate-missing.json",
    FIXTURES / "invalid.equation-as-authority.json",
    FIXTURES / "invalid.telemetry-model-as-policy.json",
    FIXTURES / "invalid.notebook-equation-as-ontology.json",
    FIXTURES / "invalid.kairos-schema-promoted-as-canonical-ontology.json",
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

REQUIRED_SR_METHOD_FAMILIES = {
    "SR-GP-EVOLUTIONARY",
    "SR-SPARSE-REGRESSION",
    "SR-TRANSFORMER-PRETRAINING",
    "SR-MCTS-DECODING",
    "SR-CROSS-MODAL-PRETRAINING",
    "SR-LLM-EVOLUTIONARY",
    "SR-PROGRAM-SEARCH",
    "SR-KAN-BASED",
    "SR-PHYSICS-CONSTRAINED",
    "SR-BENCHMARKING",
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
    "invalid.visual-embedding-as-evidence.json": "visual_embedding_as_evidence",
    "invalid.transduction-certificate-missing.json": "transduction_certificate_missing",
    "invalid.equation-as-authority.json": "equation_as_authority",
    "invalid.telemetry-model-as-policy.json": "telemetry_model_as_policy",
    "invalid.notebook-equation-as-ontology.json": "notebook_equation_as_ontology",
    "invalid.kairos-schema-promoted-as-canonical-ontology.json": "kairos_schema_as_canonical_ontology",
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


def validate_valid_nsr_fixture(data: dict[str, Any]) -> None:
    require(data.get("kind") == "ChronosCarrierRegistration", "valid NSR fixture wrong kind")
    require(data.get("schemaVersion") == "0.1.0", "valid NSR fixture wrong schemaVersion")
    require(dotted(data, "carrier.status") == "candidate", "valid NSR carrier must remain candidate")
    require(
        dotted(data, "carrier.claimStatus") == "derived-integration-summary",
        "valid NSR carrier claimStatus must be derived-integration-summary",
    )
    require(
        dotted(data, "carrier.validationState") == "human-reviewed-corpus-map",
        "valid NSR carrier validationState mismatch",
    )
    families = set(dotted(data, "carrier.methodFamilies"))
    require(families == REQUIRED_METHOD_FAMILIES, "valid NSR carrier method family set drifted")
    declaration = dotted(data, "carrier.nonAuthorityDeclaration")
    require(isinstance(declaration, str) and "does not promote" in declaration, "valid NSR fixture missing non-authority declaration")
    authorities = dotted(data, "authority")
    for key, expected in REQUIRED_AUTHORITIES.items():
        require(authorities.get(key) == expected, f"authority mismatch for {key}")
    lifecycle = dotted(data, "replay.expectedLifecycle")
    require("governance_decision" in lifecycle, "valid NSR fixture must include governance_decision lifecycle step")
    require("receipt_or_rejection" in lifecycle, "valid NSR fixture must include receipt_or_rejection lifecycle step")


def validate_valid_sr_fixture(data: dict[str, Any]) -> None:
    require(data.get("kind") == "ChronosCarrierRegistration", "valid SR fixture wrong kind")
    require(data.get("schemaVersion") == "0.1.0", "valid SR fixture wrong schemaVersion")
    require(dotted(data, "carrier.status") == "candidate", "valid SR carrier must remain candidate")
    require(
        dotted(data, "carrier.validationState") == "human-reviewed-field-map",
        "valid SR carrier validationState mismatch",
    )
    families = set(dotted(data, "carrier.methodFamilies"))
    require(families == REQUIRED_SR_METHOD_FAMILIES, "valid SR carrier method family set drifted")
    insertion_points = set(dotted(data, "carrier.insertionPoints"))
    required_insertion_points = {
        "SocioProphet/memory-mesh",
        "SocioProphet/prophet-platform",
        "notebook-layer",
        "SocioProphet/ontogenesis",
        "SocioProphet/webprotege",
        "SocioProphet/agentplane",
        "SocioProphet/alexandrian-academy",
        "quantum-hamiltonian-learning-lane",
    }
    require(required_insertion_points <= insertion_points, "valid SR fixture missing insertion point")
    declaration = dotted(data, "carrier.nonAuthorityDeclaration")
    require(isinstance(declaration, str) and "does not promote equations" in declaration, "valid SR fixture missing equation non-authority declaration")
    authorities = dotted(data, "authority")
    for key, expected in REQUIRED_AUTHORITIES.items():
        require(authorities.get(key) == expected, f"SR authority mismatch for {key}")
    require(authorities.get("educationCanonAuthority") == "SocioProphet/alexandrian-academy", "SR education authority mismatch")
    lifecycle = dotted(data, "replay.expectedLifecycle")
    require("equation_candidate" in lifecycle, "valid SR fixture must include equation_candidate lifecycle step")
    require("semantic_review_request" in lifecycle, "valid SR fixture must include semantic_review_request lifecycle step")
    require("receipt_or_rejection" in lifecycle, "valid SR fixture must include receipt_or_rejection lifecycle step")


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

    if path.name == "invalid.visual-embedding-as-evidence.json":
        require(carrier.get("visualizationType") == "t-SNE", "visual embedding fixture must expose t-SNE visualization")
        require(carrier.get("validationState") == "visual-inspection-only", "visual embedding fixture must expose visual-only validation")
        require(authority.get("semanticVocabularyDraft") == "bypassed", "visual embedding fixture must bypass semantic vocabulary authority")
        require(authority.get("evidenceReplayAuthority") == "missing", "visual embedding fixture must lack evidence replay authority")

    if path.name == "invalid.transduction-certificate-missing.json":
        require(carrier.get("transductionAssessment") == "missing", "transduction fixture must lack transduction assessment")
        require(carrier.get("maskedOutputEvaluation") == "missing", "transduction fixture must lack masked output evaluation")
        require(carrier.get("heldOutGroundingValidation") == "missing", "transduction fixture must lack held-out grounding validation")
        require(authority.get("evidenceReplayAuthority") == "missing", "transduction fixture must lack evidence replay authority")

    if path.name == "invalid.equation-as-authority.json":
        require(carrier.get("status") == "admitted", "equation fixture must try invalid admission")
        require(carrier.get("claimStatus") == "law", "equation fixture must try law claim")
        require(carrier.get("validationState") == "fit-metric-only", "equation fixture must expose fit-metric-only validation")
        require(authority.get("semanticVocabularyDraft") == "bypassed", "equation fixture must bypass semantic vocabulary authority")

    if path.name == "invalid.telemetry-model-as-policy.json":
        require(carrier.get("claimStatus") == "policy", "telemetry fixture must try policy claim")
        require(carrier.get("validationState") == "telemetry-fit-only", "telemetry fixture must expose telemetry-fit-only validation")
        require(authority.get("policyAdmissionAuthority") == "bypassed", "telemetry fixture must bypass policy admission")
        require(authority.get("runtimeAuthority") == "bypassed", "telemetry fixture must bypass runtime authority")

    if path.name == "invalid.notebook-equation-as-ontology.json":
        require(carrier.get("claimStatus") == "ontology_assertion", "notebook fixture must try ontology assertion")
        require(carrier.get("validationState") == "notebook-output-only", "notebook fixture must expose notebook-output-only validation")
        require(carrier.get("webProtegeMutation") == "direct", "notebook fixture must try direct WebProtege mutation")
        require(authority.get("semanticVocabularyDraft") == "bypassed", "notebook fixture must bypass semantic vocabulary authority")

    if path.name == "invalid.kairos-schema-promoted-as-canonical-ontology.json":
        require(carrier.get("status") == "admitted", "KAIROS schema fixture must try invalid admission")
        require(carrier.get("claimStatus") == "canonical", "KAIROS schema fixture must try canonical claim")
        require(
            carrier.get("validationState") == "schema-match-confidence-only",
            "KAIROS schema fixture must expose schema-match-confidence-only validation",
        )
        require(carrier.get("groundingStatus") == "unknown", "KAIROS schema fixture must expose unknown grounding")
        require(authority.get("semanticVocabularyDraft") == "bypassed", "KAIROS schema fixture must bypass semantic vocabulary authority")


def main() -> int:
    validate_valid_nsr_fixture(load(VALID_ASU_NSR))
    validate_valid_sr_fixture(load(VALID_SR))
    for path in INVALIDS:
        assert_invalid_rejected(path, load(path))
    print("OK: neuro-symbolic and symbolic-regression CHRONOS carrier fixtures validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
