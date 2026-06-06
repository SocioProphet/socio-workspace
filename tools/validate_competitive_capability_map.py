#!/usr/bin/env python3
"""Validate the regulated AI competitive capability map.

The repository stores the map as YAML for review readability. This validator uses
PyYAML rather than a partial parser so list/object semantics remain exact.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - CI setup failure only
    print("competitive-capability-map: ERROR: PyYAML is required", file=sys.stderr)
    raise SystemExit(2) from exc

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "registry" / "competitive-capability-map-v0.yaml"

REQUIRED_TOP_LEVEL = {
    "version",
    "status",
    "date",
    "owner",
    "subject",
    "purpose",
    "sources",
    "capabilities",
    "parity_plus_requirements",
    "next_schema_backlog",
    "limitations",
}
REQUIRED_SOURCE_FIELDS = {"id", "name", "url", "pattern"}
REQUIRED_CAPABILITY_FIELDS = {
    "id",
    "source_patterns",
    "observed_capability",
    "governed_analogue",
    "required_objects",
    "governance_delta",
}
REQUIRED_BASE_OBJECTS = {
    "InstitutionalAction",
    "ProcedureTemplate",
    "EvidenceBundle",
    "ExecutionReceipt",
}
REQUIRED_BACKLOG_OBJECTS = {
    "GovernanceBench",
    "WorkflowBench",
    "DomainBench",
    "ReplayBench",
    "ConnectorContract",
    "CapabilityGrant",
    "AppActionPolicy",
    "SecurityProfile",
    "ExtractionReceipt",
    "GraphSnapshot",
    "ComplianceLogEvent",
    "RetentionPolicy",
}
REQUIRED_PARITY_REQUIREMENTS = {
    "explicit_actor_role_authority_policy_capability",
    "evidence_bundle_with_provenance_digest_authority_class",
    "human_in_command_synthesis_recommendation_approval_execution_split",
    "execution_receipt_with_artifacts_graph_snapshot_replay_posture",
    "connector_actions_classified_by_read_write_action_risk",
    "benchmarks_with_rubric_lineage_failure_classes_thresholds",
    "runtime_claims_require_schema_fixture_validator_graph_query_admission",
}


def fail(message: str) -> int:
    print(f"competitive-capability-map: ERROR: {message}", file=sys.stderr)
    return 1


def as_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a list")
    return value


def as_dict(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{field} must be a mapping")
    return value


def main() -> int:
    try:
        data = as_dict(yaml.safe_load(MAP_PATH.read_text(encoding="utf-8")), "map")
    except FileNotFoundError:
        return fail(f"missing {MAP_PATH.relative_to(ROOT)}")
    except yaml.YAMLError as exc:
        return fail(f"invalid YAML: {exc}")
    except TypeError as exc:
        return fail(str(exc))

    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing:
        return fail("missing top-level fields: " + ", ".join(sorted(missing)))

    try:
        sources = [as_dict(item, "source") for item in as_list(data["sources"], "sources")]
        capabilities = [as_dict(item, "capability") for item in as_list(data["capabilities"], "capabilities")]
        parity = set(as_list(data["parity_plus_requirements"], "parity_plus_requirements"))
        backlog = set(as_list(data["next_schema_backlog"], "next_schema_backlog"))
        limitations = as_list(data["limitations"], "limitations")
    except TypeError as exc:
        return fail(str(exc))

    if not sources:
        return fail("sources must not be empty")
    if not capabilities:
        return fail("capabilities must not be empty")
    if not limitations:
        return fail("limitations must not be empty")

    source_ids: set[str] = set()
    for source in sources:
        missing_source = REQUIRED_SOURCE_FIELDS - set(source)
        if missing_source:
            return fail(f"source missing fields: {', '.join(sorted(missing_source))}")
        source_id = str(source["id"])
        if source_id in source_ids:
            return fail(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        url = str(source["url"])
        if not (url.startswith("https://") or url.startswith("http://")):
            return fail(f"source {source_id} has non-URL url: {url}")

    capability_ids: set[str] = set()
    mentioned_objects: set[str] = set()
    for capability in capabilities:
        missing_capability = REQUIRED_CAPABILITY_FIELDS - set(capability)
        if missing_capability:
            return fail(f"capability missing fields: {', '.join(sorted(missing_capability))}")
        capability_id = str(capability["id"])
        if capability_id in capability_ids:
            return fail(f"duplicate capability id: {capability_id}")
        capability_ids.add(capability_id)

        try:
            source_patterns = {str(item) for item in as_list(capability["source_patterns"], f"{capability_id}.source_patterns")}
            required_objects = {str(item) for item in as_list(capability["required_objects"], f"{capability_id}.required_objects")}
        except TypeError as exc:
            return fail(str(exc))

        if not source_patterns:
            return fail(f"{capability_id} source_patterns must not be empty")
        unknown_sources = source_patterns - source_ids
        if unknown_sources:
            return fail(f"{capability_id} references unknown sources: {', '.join(sorted(unknown_sources))}")
        if not required_objects:
            return fail(f"{capability_id} required_objects must not be empty")
        mentioned_objects.update(required_objects)

        for text_field in ["observed_capability", "governed_analogue", "governance_delta"]:
            if not str(capability[text_field]).strip():
                return fail(f"{capability_id} {text_field} must not be empty")

    missing_parity = REQUIRED_PARITY_REQUIREMENTS - parity
    if missing_parity:
        return fail("missing parity requirements: " + ", ".join(sorted(missing_parity)))

    missing_backlog = REQUIRED_BACKLOG_OBJECTS - backlog
    if missing_backlog:
        return fail("missing backlog objects: " + ", ".join(sorted(missing_backlog)))

    missing_base_objects = REQUIRED_BASE_OBJECTS - mentioned_objects
    if missing_base_objects:
        return fail("base governance objects not referenced by capabilities: " + ", ".join(sorted(missing_base_objects)))

    print(
        "competitive-capability-map: OK "
        f"({len(sources)} sources, {len(capabilities)} capabilities, {len(backlog)} backlog objects)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
