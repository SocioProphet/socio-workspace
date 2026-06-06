#!/usr/bin/env python3
"""Validate the regulated AI competitive capability map.

The validator is intentionally structural. It verifies that every capability cites known
sources, maps to required governance objects, and that the schema backlog covers all
non-core objects introduced by the map.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - CI setup failure only
    print("competitive-capability-map: ERROR: pyyaml is required", file=sys.stderr)
    raise SystemExit(2) from exc

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "registry" / "competitive-capability-map-v0.yaml"
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
CORE_OBJECTS = {
    "InstitutionalAction",
    "ProcedureTemplate",
    "EvidenceBundle",
    "ExecutionReceipt",
    "PolicyBasis",
    "AuthorityBoundary",
    "ApprovalEvent",
    "SourcePermission",
}
REQUIRED_PARITY_TERMS = {
    "explicit_actor_role_authority_policy_capability",
    "evidence_bundle_with_provenance_digest_authority_class",
    "human_in_command_synthesis_recommendation_approval_execution_split",
    "execution_receipt_with_artifacts_graph_snapshot_replay_posture",
    "runtime_claims_require_schema_fixture_validator_graph_query_admission",
}


def fail(message: str) -> int:
    print(f"competitive-capability-map: ERROR: {message}", file=sys.stderr)
    return 1


def load_map() -> dict:
    if not MAP.exists():
        raise FileNotFoundError(MAP)
    with MAP.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("top-level YAML value must be a mapping")
    return data


def main() -> int:
    try:
        data = load_map()
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return fail(str(exc))

    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing:
        return fail("missing top-level fields: " + ", ".join(sorted(missing)))

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return fail("sources must be a non-empty list")
    source_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            return fail("each source must be a mapping")
        for field in ("id", "name", "url", "pattern"):
            if not source.get(field):
                return fail(f"source missing {field}")
        sid = str(source["id"])
        if sid in source_ids:
            return fail(f"duplicate source id: {sid}")
        source_ids.add(sid)
        if not str(source["url"]).startswith("https://"):
            return fail(f"source url must be https: {sid}")

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return fail("capabilities must be a non-empty list")
    capability_ids: set[str] = set()
    introduced_objects: set[str] = set()
    for cap in capabilities:
        if not isinstance(cap, dict):
            return fail("each capability must be a mapping")
        for field in ("id", "source_patterns", "observed_capability", "governed_analogue", "required_objects", "governance_delta"):
            if field not in cap or cap[field] in (None, "", []):
                return fail(f"capability missing {field}")
        cid = str(cap["id"])
        if cid in capability_ids:
            return fail(f"duplicate capability id: {cid}")
        capability_ids.add(cid)
        source_patterns = cap["source_patterns"]
        if not isinstance(source_patterns, list) or not source_patterns:
            return fail(f"{cid} source_patterns must be a non-empty list")
        unknown_sources = set(map(str, source_patterns)) - source_ids
        if unknown_sources:
            return fail(f"{cid} references unknown sources: {', '.join(sorted(unknown_sources))}")
        required_objects = cap["required_objects"]
        if not isinstance(required_objects, list) or not required_objects:
            return fail(f"{cid} required_objects must be a non-empty list")
        introduced_objects.update(map(str, required_objects))

    parity = data.get("parity_plus_requirements")
    if not isinstance(parity, list) or not parity:
        return fail("parity_plus_requirements must be a non-empty list")
    missing_parity = REQUIRED_PARITY_TERMS - set(map(str, parity))
    if missing_parity:
        return fail("missing parity-plus requirements: " + ", ".join(sorted(missing_parity)))

    backlog = data.get("next_schema_backlog")
    if not isinstance(backlog, list) or not backlog:
        return fail("next_schema_backlog must be a non-empty list")
    backlog_set = set(map(str, backlog))
    uncovered = introduced_objects - CORE_OBJECTS - backlog_set
    if uncovered:
        return fail("required_objects not covered by core set or backlog: " + ", ".join(sorted(uncovered)))

    if not isinstance(data.get("limitations"), list) or not data["limitations"]:
        return fail("limitations must be a non-empty list")

    print(
        "competitive-capability-map: OK "
        f"({len(source_ids)} sources, {len(capability_ids)} capabilities, {len(backlog_set)} backlog objects)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
