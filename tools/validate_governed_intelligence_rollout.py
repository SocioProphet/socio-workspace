#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "governed-intelligence-rollout.yaml"

REQUIRED_LOOP = [
    "Observe",
    "Anchor",
    "Normalize",
    "Propose",
    "Explain",
    "Verify",
    "Govern",
    "Act",
    "Receipt",
    "Learn",
]
REQUIRED_MEMBRANES = {
    "/architecture/governed-intelligence",
    "/chronos/evidence-loop",
    "/sherlock/evidence-answers",
    "/holmes/proof-claims",
    "/gaia/world-claims",
    "/agents/action-admission",
    "/policy/claim-action-admission",
    "/guardrails/evaluation-and-controls",
    "/ontogenesis/schema-contracts",
    "/ledger/governance-records",
}
REQUIRED_STATUSES = {
    "not_started",
    "schema_stubbed",
    "adapter_in_progress",
    "contract_tests_present",
    "vertical_slice_ready",
}
REQUIRED_REPOS = {
    "SocioProphet/sociosphere",
    "SocioProphet/sherlock-search",
    "SocioProphet/ontogenesis",
    "SocioProphet/policy-fabric",
    "SocioProphet/agentplane",
    "SocioProphet/model-governance-ledger",
    "SocioProphet/holmes",
    "SocioProphet/gaia-world-model",
    "SocioProphet/guardrail-fabric",
    "SocioProphet/slash-topics",
}
REQUIRED_OBJECTS = {
    "SourceQualityAnswerTrace",
    "CorpusEventSemantics",
    "GovernedPolicyDecision",
    "BoundedActionLoop",
    "GovernanceRecord",
    "CoordinationManifest",
    "ResolutionReport",
    "CustomerReadout",
    "ProofClaim",
    "WorldClaim",
    "GuardrailEvaluation",
    "SlashTopicProfile",
}
REQUIRED_CHRONOS_CARRIERS = {
    "SocioProphet/sherlock-search#58",
    "SocioProphet/ontogenesis#103",
    "SocioProphet/policy-fabric#85",
    "SocioProphet/agentplane#184",
    "SocioProphet/model-governance-ledger#20",
}


def fail(message: str) -> int:
    print(f"ERR: {message}", file=sys.stderr)
    return 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def as_list(value: Any, field: str) -> list[Any]:
    require(isinstance(value, list) and value, f"{field} must be non-empty list")
    return value


def main() -> int:
    if yaml is None:
        return fail("PyYAML is required")
    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        require(isinstance(data, dict), "registry must be mapping")
        require(data.get("kind") == "GovernedIntelligenceRolloutRegistration", "kind mismatch")
        require(data.get("version") == "0.2.0", "version mismatch")
        require(data.get("first_validated_vertical_slice") == "CHRONOS Evidence Loop", "missing CHRONOS vertical slice")
        require(data.get("canonical_platform_loop") == REQUIRED_LOOP, "canonical loop mismatch")

        membranes = {item["membrane"] for item in as_list(data.get("membranes"), "membranes") if isinstance(item, dict)}
        require(REQUIRED_MEMBRANES <= membranes, "required membranes missing")

        adoption = data.get("adoption_status_projection")
        require(isinstance(adoption, dict), "adoption_status_projection must be mapping")
        allowed = set(as_list(adoption.get("allowed_statuses"), "allowed_statuses"))
        require(allowed == REQUIRED_STATUSES, "status vocabulary mismatch")
        repos = as_list(adoption.get("repos"), "adoption repos")
        repo_map = {item["repo"]: item for item in repos if isinstance(item, dict) and "repo" in item}
        require(REQUIRED_REPOS <= set(repo_map), "required repos missing")
        require(repo_map["SocioProphet/sociosphere"].get("status") == "vertical_slice_ready", "SocioSphere must be vertical_slice_ready")
        for repo in [
            "SocioProphet/sherlock-search",
            "SocioProphet/ontogenesis",
            "SocioProphet/policy-fabric",
            "SocioProphet/agentplane",
            "SocioProphet/model-governance-ledger",
        ]:
            require(repo_map[repo].get("status") == "contract_tests_present", f"{repo} carrier status mismatch")

        objects = {item["object"] for item in as_list(data.get("canonical_object_matrix"), "canonical_object_matrix") if isinstance(item, dict)}
        require(REQUIRED_OBJECTS <= objects, "required objects missing")

        chronos = data.get("chronos_evidence_loop")
        require(isinstance(chronos, dict), "chronos_evidence_loop must be mapping")
        require(chronos.get("source_corpus") == "SocioProphet/sociosphere#334", "CHRONOS source corpus mismatch")
        carriers = {item["merged_ref"] for item in as_list(chronos.get("carriers"), "chronos carriers") if isinstance(item, dict)}
        require(carriers == REQUIRED_CHRONOS_CARRIERS, "CHRONOS carrier refs mismatch")
        require(chronos.get("validation_target") == "make corpus-loop-check", "CHRONOS validation target mismatch")

        non_goals = "\n".join(as_list(data.get("non_goals"), "non_goals")).lower()
        for term in ["runtime execution", "external effects", "production storage", "corpus normalization", "patent or license"]:
            require(term in non_goals, f"missing non-goal term: {term}")
    except Exception as exc:
        return fail(str(exc))
    print("OK: governed intelligence rollout registry validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
