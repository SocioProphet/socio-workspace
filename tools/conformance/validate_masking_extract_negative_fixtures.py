#!/usr/bin/env python3
"""Validate masking / tokenization / GrASP-extraction NEGATIVE conformance fixtures.

The positive validator (validate_regis_extract_masking_fixtures.py) proves that
well-formed masking-decision / tokenization-profile / grasp-pattern fixtures are
ACCEPTED. That alone does not prove the contracts have teeth: a schema that
accepts everything would pass it too.

This validator proves the other direction — that under-masked / ungoverned /
uninterpretable input is REJECTED — for the four privacy invariants the
Masking/Tokenization & GrASP design (docs/architecture/masking-tokenization-and-grasp-extraction.md)
calls load-bearing:

  1. CROSS_DOMAIN_LINKABLE_TOKEN      — tokens MUST NOT be cross-domain-linkable
                                        (tokenization-profile.cross_domain_linkable const false;
                                        the crypto realization of scope-realm sovereignty /
                                        no side-channel leakage between datasets).
  2. ONE_WAY_SCHEME_DECLARED_REVERSIBLE — an irreversible scheme (one_way_hash / hmac_pseudonym /
                                        redact / suppress / generalize) declared reversibility=reversible
                                        is under-masked; the schema forces reversibility=one_way.
  3. REIDENTIFY_WITHOUT_REASON        — a re_identify decision with no reason_for_action violates the
                                        mandatory reason-for-action gate on governed re-identification.
  4. EMPTY_FEATURE_SETS               — a GrASP pattern with zero feature-set positions is
                                        uninterpretable/unmatchable (feature_sets minItems 1).

Like its siblings this file is dependency-free for the structural checks. When
`jsonschema` is importable it additionally asserts that a full draft 2020-12
validation REJECTS each negative fixture and ACCEPTS each valid counterpart —
the accepted/rejected teeth in one place.

Exit code 0 = all checks pass; non-zero on first failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
IP = ROOT / "protocol" / "identity-is-prime"

ONE_WAY_SCHEMES = {"one_way_hash", "hmac_pseudonym", "redact", "suppress", "generalize"}


def _cross_domain_linkable(d: dict[str, Any]) -> bool:
    return d.get("cross_domain_linkable") is True


def _one_way_declared_reversible(d: dict[str, Any]) -> bool:
    return d.get("scheme") in ONE_WAY_SCHEMES and d.get("reversibility") == "reversible"


def _reidentify_without_reason(d: dict[str, Any]) -> bool:
    if d.get("requested_op") != "re_identify":
        return False
    reid = d.get("re_identification")
    if not isinstance(reid, dict):
        return True
    return not reid.get("reason_for_action")


def _classifications(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for tr in d.get("applied_transforms") or []:
        c = tr.get("classification") if isinstance(tr, dict) else None
        if isinstance(c, dict):
            out.append(c)
    return out


def _inadmissible_classification_allowed(d: dict[str, Any]) -> bool:
    """A glut resolved in the requester's favour.

    INADMISSIBLE means two fingerprint layers disagree about what this field IS, and one of
    the readings may well be "personal data". Serving it lets the contradiction settle itself
    in favour of whoever asked — the one resolution nobody chose.
    """
    if d.get("verdict") != "allow":
        return False
    return any(c.get("stance") == "INADMISSIBLE" for c in _classifications(d))


def _zero_failopen_unattested(d: dict[str, Any]) -> bool:
    """Data whose classification is unknown, served with nobody on the record for it.

    fail-open on ZERO is a legitimate choice for a public reference table and a breach for a
    customer-master column. That is exactly why it is attested rather than defaulted.
    """
    return any(c.get("stance") == "ZERO" and c.get("zero_disposition") == "fail-open"
               and not c.get("zero_attestation_ref") for c in _classifications(d))


def _empty_feature_sets(d: dict[str, Any]) -> bool:
    return d.get("feature_sets") == []


# invariant name -> (schema relpath, structural predicate proving the invariant is violated)
INVARIANTS: dict[str, tuple[str, Callable[[dict[str, Any]], bool]]] = {
    "CROSS_DOMAIN_LINKABLE_TOKEN": (
        "masking/schemas/tokenization-profile.v1.schema.json",
        _cross_domain_linkable,
    ),
    "ONE_WAY_SCHEME_DECLARED_REVERSIBLE": (
        "masking/schemas/tokenization-profile.v1.schema.json",
        _one_way_declared_reversible,
    ),
    "REIDENTIFY_WITHOUT_REASON": (
        "masking/schemas/masking-decision.v1.schema.json",
        _reidentify_without_reason,
    ),
    "INADMISSIBLE_CLASSIFICATION_ALLOWED": (
        "masking/schemas/masking-decision.v1.schema.json",
        _inadmissible_classification_allowed,
    ),
    "ZERO_CLASSIFICATION_FAIL_OPEN_UNATTESTED": (
        "masking/schemas/masking-decision.v1.schema.json",
        _zero_failopen_unattested,
    ),
    "EMPTY_FEATURE_SETS": (
        "extract/schemas/grasp-pattern.v1.schema.json",
        _empty_feature_sets,
    ),
}

# negative fixture relpath -> invariant it must trip (and the schema must reject it)
NEGATIVE_FIXTURES: dict[str, str] = {
    "masking/fixtures/negative/tokenization_profile.cross_domain_linkable.invalid.json": "CROSS_DOMAIN_LINKABLE_TOKEN",
    "masking/fixtures/negative/tokenization_profile.under_masked_hmac.invalid.json": "ONE_WAY_SCHEME_DECLARED_REVERSIBLE",
    "masking/fixtures/negative/masking_decision.reidentify_without_reason.invalid.json": "REIDENTIFY_WITHOUT_REASON",
    "masking/fixtures/negative/masking_decision.inadmissible_classification_allowed.invalid.json": "INADMISSIBLE_CLASSIFICATION_ALLOWED",
    "masking/fixtures/negative/masking_decision.zero_failopen_unattested.invalid.json": "ZERO_CLASSIFICATION_FAIL_OPEN_UNATTESTED",
    "extract/fixtures/negative/grasp_pattern.empty_feature_sets.invalid.json": "EMPTY_FEATURE_SETS",
}

# valid fixtures that MUST be accepted (and must trip no invariant for their schema)
VALID_FIXTURES: dict[str, str] = {
    "masking/fixtures/tokenization_profile.chameleon_patient_mrn.valid.json": "masking/schemas/tokenization-profile.v1.schema.json",
    "masking/fixtures/masking_decision.reidentify_with_reason.valid.json": "masking/schemas/masking-decision.v1.schema.json",
    "masking/fixtures/masking_decision.health_adtech_deny.valid.json": "masking/schemas/masking-decision.v1.schema.json",
    "masking/fixtures/masking_decision.classified_governed.valid.json": "masking/schemas/masking-decision.v1.schema.json",
    "extract/fixtures/grasp_pattern.compliance_sentence.valid.json": "extract/schemas/grasp-pattern.v1.schema.json",
}


def fail(path: Path, message: str) -> None:
    raise SystemExit(f"{path.relative_to(ROOT)}: {message}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing required fixture: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(path, f"invalid JSON: {exc}")
    if not isinstance(data, dict):
        fail(path, "top-level JSON value must be an object")
    return data


def make_deep_validator():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return None

    cache: dict[str, Any] = {}

    def validator(schema_rel: str):
        if schema_rel not in cache:
            schema = json.loads((IP / schema_rel).read_text(encoding="utf-8"))
            cache[schema_rel] = Draft202012Validator(schema)
        return cache[schema_rel]

    return validator


def main() -> int:
    validator = make_deep_validator()

    # 1. negatives — must trip the named invariant AND be rejected by the schema.
    for rel, invariant in sorted(NEGATIVE_FIXTURES.items()):
        path = IP / rel
        data = load_json(path)
        schema_rel, predicate = INVARIANTS[invariant]
        if not predicate(data):
            fail(path, f"fixture does not demonstrate {invariant}; it is not a genuine violation")
        if validator is not None:
            errors = list(validator(schema_rel).iter_errors(data))
            if not errors:
                fail(path, f"schema ACCEPTED an under-masked/invalid fixture — {invariant} has no teeth")

    # 2. valids — must trip no invariant for their schema AND be accepted by the schema.
    for rel, schema_rel in sorted(VALID_FIXTURES.items()):
        path = IP / rel
        data = load_json(path)
        for invariant, (inv_schema_rel, predicate) in INVARIANTS.items():
            if inv_schema_rel == schema_rel and predicate(data):
                fail(path, f"valid fixture unexpectedly trips {invariant}")
        if validator is not None:
            errors = list(validator(schema_rel).iter_errors(data))
            if errors:
                joined = "; ".join(f"{e.message} at {list(e.path)}" for e in errors)
                fail(path, f"schema REJECTED a valid fixture: {joined}")

    mode = "deep jsonschema (accept+reject)" if validator else "structural only (install jsonschema for deep)"
    print(
        f"OK: masking/extract negative conformance — "
        f"{len(NEGATIVE_FIXTURES)} rejected, {len(VALID_FIXTURES)} accepted [{mode}]"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
