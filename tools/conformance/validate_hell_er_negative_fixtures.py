#!/usr/bin/env python3
"""Validate HELL-ER negative conformance fixtures.

The positive HELL-ER validator checks schema and valid release-pack structure.
This validator proves the first rejection cases: missing policy, query-negative
misuse, silent merge, and external unredacted direct-identifier release.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HELLER_DIR = ROOT / "protocol" / "identity-is-prime" / "hell-er"
FIXTURE_DIR = HELLER_DIR / "fixtures"
EXPECTED_DIR = HELLER_DIR / "expected"

NEGATIVE_FIXTURES = {
    "release_pack.missing_policy.invalid.json": "MISSING_RELEASE_POLICY",
    "release_pack.query_negative_as_absent.invalid.json": "QUERY_NEGATIVE_AS_FACT_ABSENT",
    "release_pack.silent_merge.invalid.json": "SILENT_MERGE_WITHOUT_AUDIT",
    "release_pack.external_unredacted_identifier.invalid.json": "EXTERNAL_UNREDACTED_DIRECT_IDENTIFIER",
}


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


def require_obj(obj: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        fail(path, f"{key} must be an object")
    return value


def validate_expected(path: Path, fixture_name: str, violation: str) -> None:
    expected_path = EXPECTED_DIR / fixture_name.replace(".json", ".result.json")
    if not expected_path.exists():
        fail(path, f"missing expected result {expected_path.relative_to(ROOT)}")
    expected = load_json(expected_path)
    if require_str(expected, "expected_result", expected_path) != "REFUTED":
        fail(expected_path, "expected_result must be REFUTED")
    if require_str(expected, "expected_violation", expected_path) != violation:
        fail(expected_path, f"expected_violation must be {violation}")
    fixture_ref = require_str(expected, "fixture", expected_path)
    if not fixture_ref.endswith(fixture_name):
        fail(expected_path, "fixture pointer must reference the matching invalid fixture")


def validate_common(path: Path, fixture: dict[str, Any], violation: str) -> dict[str, Any]:
    require_str(fixture, "fixture_id", path)
    require_str(fixture, "fixture_version", path)
    if require_str(fixture, "expected_result", path) != "REFUTED":
        fail(path, "expected_result must be REFUTED")
    if require_str(fixture, "expected_violation", path) != violation:
        fail(path, f"expected_violation must be {violation}")
    return require_obj(fixture, "candidate_release_pack", path)


def validate_missing_policy(path: Path, pack: dict[str, Any]) -> None:
    if "release_policy" in pack:
        fail(path, "MISSING_RELEASE_POLICY fixture must omit candidate_release_pack.release_policy")


def validate_query_negative_as_absent(path: Path, fixture: dict[str, Any]) -> None:
    qn = require_obj(fixture, "query_negative_handling", path)
    if qn.get("query_negative_interpreted_as_absent") is not True:
        fail(path, "fixture must demonstrate query_negative_interpreted_as_absent=true")
    if qn.get("correct_state") != "query_negative":
        fail(path, "correct_state must be query_negative")


def validate_silent_merge(path: Path, fixture: dict[str, Any]) -> None:
    merge = require_obj(fixture, "merge_decision", path)
    if merge.get("merge_performed") is not True:
        fail(path, "silent merge fixture must perform a merge")
    if merge.get("merge_audit_ref") is not None:
        fail(path, "silent merge fixture must omit merge_audit_ref")
    if merge.get("review_state") != "not_reviewed":
        fail(path, "silent merge fixture must be not_reviewed")


def validate_external_unredacted_identifier(path: Path, pack: dict[str, Any]) -> None:
    if pack.get("release_class") != "external_redacted":
        fail(path, "external identifier fixture must use external_redacted release_class")
    ledger = pack.get("prime_atom_ledger")
    if not isinstance(ledger, list):
        fail(path, "candidate_release_pack.prime_atom_ledger must be a list")
    offenders = []
    for entry in ledger:
        if not isinstance(entry, dict):
            fail(path, "prime_atom_ledger entries must be objects")
        if (
            entry.get("hazard_class") == "direct_identifier"
            and entry.get("released") is True
            and entry.get("redaction_state") == "not_redacted"
        ):
            offenders.append(entry.get("atom_ref", "<unknown>"))
    if not offenders:
        fail(path, "fixture must expose at least one unredacted direct identifier externally")


def validate_negative_fixture(name: str, violation: str) -> None:
    path = FIXTURE_DIR / name
    if not path.exists():
        raise SystemExit(f"missing required HELL-ER negative fixture: {path.relative_to(ROOT)}")
    fixture = load_json(path)
    pack = validate_common(path, fixture, violation)
    if violation == "MISSING_RELEASE_POLICY":
        validate_missing_policy(path, pack)
    elif violation == "QUERY_NEGATIVE_AS_FACT_ABSENT":
        validate_query_negative_as_absent(path, fixture)
    elif violation == "SILENT_MERGE_WITHOUT_AUDIT":
        validate_silent_merge(path, fixture)
    elif violation == "EXTERNAL_UNREDACTED_DIRECT_IDENTIFIER":
        validate_external_unredacted_identifier(path, pack)
    else:
        fail(path, f"no validator registered for {violation}")
    validate_expected(path, name, violation)


def main() -> None:
    for name, violation in sorted(NEGATIVE_FIXTURES.items()):
        validate_negative_fixture(name, violation)
    print("OK: HELL-ER negative fixtures validated")


if __name__ == "__main__":
    main()
