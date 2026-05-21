#!/usr/bin/env python3
"""Validate HELL-ER protocol schemas and synthetic fixtures.

This checker is intentionally dependency-free. It does not replace full JSON
Schema validation; it enforces the first HELL-ER conformance invariants so the
protocol directory can participate in Sociosphere workspace checks without
introducing a new dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HELLER_DIR = ROOT / "protocol" / "identity-is-prime" / "hell-er"
SCHEMA_DIR = HELLER_DIR / "schemas"
FIXTURE_DIR = HELLER_DIR / "fixtures"
EXPECTED_DIR = HELLER_DIR / "expected"

REQUIRED_SCHEMAS = {
    "prime-atom.v1.schema.json",
    "contradiction-object.v1.schema.json",
    "release-pack.v1.schema.json",
}

REQUIRED_FIXTURES = {
    "release_pack.internal_operational.synthetic.valid.json",
}

REQUIRED_EXPECTED = {
    "release_pack.internal_operational.synthetic.valid.result.json",
}

RELEASE_CLASSES = {
    "self_view_unredacted",
    "internal_operational",
    "partner_federated",
    "external_redacted",
    "public_synthetic",
}

SUBJECT_STATES = {
    "unresolved",
    "candidate",
    "context_resolved",
    "validated_core",
    "verified_subject",
    "enrolled",
    "contested",
    "revoked",
    "expired",
}

REDaction_STATES = {"not_redacted", "redacted", "withheld", "synthetic", "derived_only"}
SUMMARY_STATES = {"full", "summary_only", "existence_only", "withheld", "not_applicable"}


def fail(path: Path, message: str) -> None:
    raise SystemExit(f"{path}: {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(path, f"invalid JSON: {exc}")
    if not isinstance(data, dict):
        fail(path, "top-level JSON value must be an object")
    return data


def require_str(obj: dict[str, Any], key: str, path: Path) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        fail(path, f"{key} must be a non-empty string")
    return value


def require_bool(obj: dict[str, Any], key: str, path: Path) -> bool:
    value = obj.get(key)
    if not isinstance(value, bool):
        fail(path, f"{key} must be a boolean")
    return value


def require_int(obj: dict[str, Any], key: str, path: Path) -> int:
    value = obj.get(key)
    if not isinstance(value, int):
        fail(path, f"{key} must be an integer")
    return value


def require_obj(obj: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        fail(path, f"{key} must be an object")
    return value


def require_list(obj: dict[str, Any], key: str, path: Path, *, min_items: int = 0) -> list[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        fail(path, f"{key} must be a list")
    if len(value) < min_items:
        fail(path, f"{key} must have at least {min_items} entries")
    return value


def validate_schema_file(path: Path, expected_const: str) -> None:
    schema = load_json(path)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail(path, "$schema must be JSON Schema 2020-12")
    require_str(schema, "$id", path)
    require_str(schema, "title", path)
    if schema.get("type") != "object":
        fail(path, "schema type must be object")
    required = require_list(schema, "required", path, min_items=1)
    properties = require_obj(schema, "properties", path)
    if "schema_version" not in required:
        fail(path, "required must include schema_version")
    schema_version = require_obj(properties, "schema_version", path)
    if schema_version.get("const") != expected_const:
        fail(path, f"schema_version.const must be {expected_const!r}")


def validate_schemas() -> None:
    missing = sorted(name for name in REQUIRED_SCHEMAS if not (SCHEMA_DIR / name).exists())
    if missing:
        raise SystemExit(f"missing required HELL-ER schemas: {missing}")
    validate_schema_file(SCHEMA_DIR / "prime-atom.v1.schema.json", "hell-er.prime-atom.v1")
    validate_schema_file(SCHEMA_DIR / "contradiction-object.v1.schema.json", "hell-er.contradiction-object.v1")
    validate_schema_file(SCHEMA_DIR / "release-pack.v1.schema.json", "hell-er.release-pack.v1")


def validate_audience(path: Path, pack: dict[str, Any]) -> None:
    audience = require_obj(pack, "audience", path)
    require_str(audience, "audience_type", path)
    require_str(audience, "audience_ref", path)
    require_str(audience, "purpose", path)


def validate_context(path: Path, pack: dict[str, Any]) -> None:
    context = require_obj(pack, "context", path)
    require_str(context, "context_ref", path)
    require_str(context, "context_type", path)
    require_str(context, "served_population", path)
    require_str(context, "policy_regime", path)


def validate_hazard_profile(path: Path, pack: dict[str, Any]) -> None:
    hazard = require_obj(pack, "hazard_profile", path)
    require_list(hazard, "hazard_classes", path, min_items=1)
    if require_bool(hazard, "minimum_necessary", path) is not True:
        fail(path, "hazard_profile.minimum_necessary must be true for the synthetic valid fixture")
    require_str(hazard, "release_risk", path)
    require_list(hazard, "abuse_modes", path, min_items=1)


def validate_subject_graph_summary(path: Path, pack: dict[str, Any]) -> None:
    summary = require_obj(pack, "subject_graph_summary", path)
    subject_state = require_str(summary, "subject_state", path)
    if subject_state not in SUBJECT_STATES:
        fail(path, f"subject_graph_summary.subject_state must be one of {sorted(SUBJECT_STATES)}")
    require_str(summary, "graph_snapshot_ref", path)
    if require_int(summary, "node_count", path) < 0:
        fail(path, "node_count must be non-negative")
    if require_int(summary, "edge_count", path) < 0:
        fail(path, "edge_count must be non-negative")


def validate_atom_ledger(path: Path, pack: dict[str, Any]) -> None:
    ledger = require_list(pack, "prime_atom_ledger", path, min_items=1)
    released_count = 0
    withheld_count = 0
    for entry in ledger:
        if not isinstance(entry, dict):
            fail(path, "prime_atom_ledger entries must be objects")
        require_str(entry, "atom_ref", path)
        if require_bool(entry, "released", path):
            released_count += 1
        state = require_str(entry, "redaction_state", path)
        if state not in REDaction_STATES:
            fail(path, f"redaction_state must be one of {sorted(REDaction_STATES)}")
        if state in {"withheld", "redacted"}:
            withheld_count += 1
        require_list(entry, "policy_tags", path, min_items=1)
    if released_count == 0:
        fail(path, "synthetic valid release pack must release at least one atom")
    if withheld_count == 0:
        fail(path, "synthetic valid release pack must demonstrate withholding/redaction")


def validate_contradiction_ledger(path: Path, pack: dict[str, Any]) -> None:
    ledger = require_list(pack, "contradiction_ledger", path)
    if not ledger:
        fail(path, "synthetic valid release pack must retain at least one contradiction pointer")
    for entry in ledger:
        if not isinstance(entry, dict):
            fail(path, "contradiction_ledger entries must be objects")
        require_str(entry, "contradiction_ref", path)
        require_bool(entry, "released", path)
        state = require_str(entry, "summary_state", path)
        if state not in SUMMARY_STATES:
            fail(path, f"summary_state must be one of {sorted(SUMMARY_STATES)}")


def validate_assurance_vector(path: Path, pack: dict[str, Any]) -> None:
    assurance = require_obj(pack, "assurance_vector", path)
    if require_str(assurance, "identity_state", path) != "context_resolved":
        fail(path, "synthetic valid fixture must be context_resolved")
    require_str(assurance, "evidence_state", path)
    require_str(assurance, "authenticator_state", path)
    if require_str(assurance, "civil_identity_state", path) != "not_proofed":
        fail(path, "synthetic valid fixture must not claim civil identity proof")
    require_str(assurance, "federation_state", path)


def validate_release_policy(path: Path, pack: dict[str, Any]) -> None:
    policy = require_obj(pack, "release_policy", path)
    require_str(policy, "policy_ref", path)
    require_list(policy, "allowed_actions", path, min_items=1)
    denied = require_list(policy, "denied_actions", path, min_items=1)
    require_bool(policy, "review_required", path)
    if "export_bulk_applicant_data" not in denied:
        fail(path, "synthetic valid release pack must deny bulk export")


def validate_lifecycle(path: Path, pack: dict[str, Any]) -> None:
    lifecycle = require_obj(pack, "lifecycle", path)
    require_str(lifecycle, "state", path)
    require_str(lifecycle, "retention_policy_ref", path)


def validate_machine_annex(path: Path, pack: dict[str, Any]) -> None:
    annex = require_obj(pack, "machine_annex", path)
    require_str(annex, "annex_ref", path)
    require_str(annex, "annex_hash", path)
    require_str(annex, "format", path)


def validate_release_pack(path: Path) -> None:
    pack = load_json(path)
    if pack.get("schema_version") != "hell-er.release-pack.v1":
        fail(path, "schema_version must be hell-er.release-pack.v1")
    require_str(pack, "release_pack_id", path)
    release_class = require_str(pack, "release_class", path)
    if release_class not in RELEASE_CLASSES:
        fail(path, f"release_class must be one of {sorted(RELEASE_CLASSES)}")
    validate_audience(path, pack)
    validate_context(path, pack)
    validate_hazard_profile(path, pack)
    validate_subject_graph_summary(path, pack)
    validate_atom_ledger(path, pack)
    validate_contradiction_ledger(path, pack)
    validate_assurance_vector(path, pack)
    validate_release_policy(path, pack)
    validate_lifecycle(path, pack)
    require_list(pack, "redress_queue", path)
    validate_machine_annex(path, pack)
    require_str(pack, "created_at", path)


def validate_expected(path: Path) -> None:
    expected = load_json(path)
    fixture_ref = require_str(expected, "fixture", path)
    if not fixture_ref.endswith("release_pack.internal_operational.synthetic.valid.json"):
        fail(path, "expected fixture pointer must reference the synthetic release pack")
    if require_str(expected, "expected_result", path) != "VERIFIED":
        fail(path, "synthetic expected result must be VERIFIED")
    for key in (
        "schema_version",
        "policy_version",
        "resolver_version",
        "release_template_version",
        "hazard_classifier_version",
    ):
        require_str(expected, key, path)
    requirements = require_obj(expected, "result_requirements", path)
    for key in (
        "context_resolved_access",
        "civil_identity_not_proofed",
        "stale_affiliation_contradiction_retained",
        "minimum_necessary",
        "bulk_export_denied",
        "release_pack_has_machine_annex",
    ):
        if requirements.get(key) is not True:
            fail(path, f"result_requirements.{key} must be true")


def main() -> None:
    validate_schemas()

    missing_fixtures = sorted(name for name in REQUIRED_FIXTURES if not (FIXTURE_DIR / name).exists())
    if missing_fixtures:
        raise SystemExit(f"missing required HELL-ER fixtures: {missing_fixtures}")
    for name in sorted(REQUIRED_FIXTURES):
        validate_release_pack(FIXTURE_DIR / name)

    missing_expected = sorted(name for name in REQUIRED_EXPECTED if not (EXPECTED_DIR / name).exists())
    if missing_expected:
        raise SystemExit(f"missing required HELL-ER expected results: {missing_expected}")
    for name in sorted(REQUIRED_EXPECTED):
        validate_expected(EXPECTED_DIR / name)

    print("OK: HELL-ER conformance fixtures validated")


if __name__ == "__main__":
    main()
