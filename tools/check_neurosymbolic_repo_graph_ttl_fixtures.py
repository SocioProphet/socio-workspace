#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"

CASES = [
    "valid.active-spine-inference",
    "invalid.missing-boundary",
    "invalid.policy-denied-shacl-pass",
    "diagnostic.stale-pin",
]

PLANE_MAP = {
    "evidence": "evidencePlane",
    "ontology": "ontologyPlane",
    "policy": "policyPlane",
    "runtime": "runtimePlane",
    "ledger": "ledgerPlane",
}

STATE_MAP = {
    "canonical_source_present": "canonicalSourcePresent",
    "manifest_overlay_present": "manifestOverlayPresent",
    "boundary_present": "boundaryPresent",
    "boundary_class": "boundaryClass",
    "shacl_conforms": "shaclConforms",
    "policy_decision": "policyDecision",
    "ledger_required": "ledgerRequired",
    "pinned_commit_stale": "pinnedCommitStale",
}

REASONING_MAP = {
    "chronos": "chronosReasoning",
    "watson_cyc": "watsonCycReasoning",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def ttl_value(text: str, predicate: str) -> object:
    # A quoted literal is read whole: "." is legal inside one, and every fixture id
    # is dotted ("valid.active-spine-inference"). Only an unquoted token may be
    # terminated by the statement "." or ";".
    pattern = rf'nrg:{re.escape(predicate)}\s+(?:"((?:[^"\\]|\\.)*)"|([^\s;.]*))\s*[;.](?:\s|$)'
    match = re.search(pattern, text)
    if not match:
        return None
    quoted, bare = match.group(1), match.group(2)
    if quoted is not None:
        return quoted
    if bare == "true":
        return True
    if bare == "false":
        return False
    return bare


def compare_value(case: str, field: str, json_value: object, ttl_field: str, text: str) -> bool:
    ttl = ttl_value(text, ttl_field)
    if json_value is None:
        json_value = ""
    if ttl != json_value:
        fail(f"{case}: {field} mismatch JSON={json_value!r} TTL={ttl!r}")
        return False
    return True


def main() -> int:
    failed = False

    for case in CASES:
        json_path = FIXTURE_DIR / f"{case}.json"
        ttl_path = FIXTURE_DIR / f"{case}.ttl"
        if not json_path.exists():
            fail(f"missing JSON fixture: {json_path.name}")
            failed = True
            continue
        if not ttl_path.exists():
            fail(f"missing TTL fixture: {ttl_path.name}")
            failed = True
            continue

        fixture = json.loads(json_path.read_text(encoding="utf-8"))
        ttl_text = ttl_path.read_text(encoding="utf-8")

        direct_fields = {
            "fixture_id": "fixtureId",
            "expected_result": "expectedResult",
            "corpus_loop": "corpusLoop",
        }
        for json_field, ttl_field in direct_fields.items():
            if not compare_value(case, json_field, fixture.get(json_field), ttl_field, ttl_text):
                failed = True

        for json_field, ttl_field in STATE_MAP.items():
            state = fixture.get("graph_state", {})
            if json_field not in state and json_field == "pinned_commit_stale":
                continue
            if not compare_value(case, json_field, state.get(json_field), ttl_field, ttl_text):
                failed = True

        for json_field, ttl_field in PLANE_MAP.items():
            planes = fixture.get("planes", {})
            if not compare_value(case, f"plane.{json_field}", planes.get(json_field), ttl_field, ttl_text):
                failed = True

        for json_field, ttl_field in REASONING_MAP.items():
            reasoning = fixture.get("reasoning", {})
            if not compare_value(case, f"reasoning.{json_field}", reasoning.get(json_field), ttl_field, ttl_text):
                failed = True

    if failed:
        return 1

    print("OK: neurosymbolic repo graph TTL fixtures agree with JSON fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
