#!/usr/bin/env python3
"""Validate standards/epistemic-governance/detector-id-map.yaml (+ bias-catalog.yaml).

The runtime emits detector ids (Noetica debate-detectors.ts, ruleset 0.1.0); the
standard declares canonical ids (detector-countertest-map.yaml, 1.5.0). The id
map is the governed bridge. It is only load-bearing if it is machine-checked —
otherwise "reconciled" is a claim like any other. This validator enforces:

  1. Every map entry has emitted_id / standard_id / family; emitted_id is unique.
  2. The map is a BIJECTION on (emitted_id <-> standard_id): no two emitted ids
     share a standard id and vice-versa. Reconciliation must round-trip.
  3. Every standard_id EXISTS in the ruleset, and is a SHIPPED-maturity detector
     (the id at the maturity actually run). A standard_id that is proposed-only
     would launder a not-yet-built detector as a runtime emission -> REJECTED.
  4. The set of emitted_ids EQUALS the set of shipped detectors in the ruleset,
     both ways: a shipped detector with no map entry fails (drift the map missed);
     a map entry for a non-shipped id fails (drift the map invented).
  5. succeeds_into, when non-null, EXISTS as a PROPOSED detector in the ruleset
     (the migration target must be real and must not already be shipped).
  6. bias-catalog.yaml: every detector_id exists in the ruleset and every
     required_counter_test is declared under counter_test_availability.

TEETH BOTH WAYS: --selftest constructs an in-memory drifted map and asserts the
checker REJECTS it, and a clean map and asserts it PASSES — so the rejection path
is exercised in CI without committing a broken file.

Exit 0 clean, 1 on any violation, 2 when a required file cannot be read/parsed
(a validator that cannot run must not read as one that passed). Stdlib + pyyaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EPIGOV = ROOT / "standards" / "epistemic-governance"
ID_MAP = EPIGOV / "detector-id-map.yaml"
RULESET = EPIGOV / "detector-countertest-map.yaml"
BIAS_CATALOG = EPIGOV / "bias-catalog.yaml"


def _load(path: Path) -> dict:
    """Read+parse a YAML mapping, or raise SystemExit(2) — 'could not run'."""
    if not path.exists():
        print(f"ERR: missing file: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERR: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except UnicodeDecodeError as exc:
        print(f"ERR: {path} is not valid UTF-8: {exc}", file=sys.stderr)
        raise SystemExit(2)
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print(f"ERR: {path} is not valid YAML: {exc}", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(doc, dict):
        print(f"ERR: {path} must parse to a mapping", file=sys.stderr)
        raise SystemExit(2)
    return doc


def ruleset_id_sets(ruleset: dict) -> tuple[set[str], set[str], set[str]]:
    """Return (all_ids, shipped_ids, proposed_ids) from a ruleset doc."""
    all_ids: set[str] = set()
    shipped: set[str] = set()
    proposed: set[str] = set()
    lists = [
        (ruleset.get("detectors") or [], None),
        (ruleset.get("shipped_detectors") or [], "shipped"),
        (ruleset.get("technical_claim_detectors") or [], "proposed"),
    ]
    for entries, default_maturity in lists:
        for e in entries:
            if not isinstance(e, dict):
                continue
            rid = e.get("rule_id")
            if not isinstance(rid, str) or not rid:
                continue
            all_ids.add(rid)
            maturity = e.get("maturity", default_maturity)
            if maturity == "shipped":
                shipped.add(rid)
            elif maturity == "proposed":
                proposed.add(rid)
    return all_ids, shipped, proposed


def declared_counter_tests(ruleset: dict) -> set[str]:
    avail = ruleset.get("counter_test_availability") or {}
    return set(avail.get("runnable") or []) | set(avail.get("proposed") or [])


def check_id_map(id_map_doc: dict, ruleset: dict) -> list[str]:
    """Pure checker over already-parsed docs. Returns a list of failure strings."""
    failures: list[str] = []
    all_ids, shipped_ids, proposed_ids = ruleset_id_sets(ruleset)

    entries = id_map_doc.get("detector_id_map")
    if not isinstance(entries, list) or not entries:
        return ["detector_id_map must be a non-empty list"]

    seen_emitted: dict[str, int] = {}
    seen_standard: dict[str, int] = {}
    mapped_emitted: set[str] = set()

    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            failures.append(f"detector_id_map[{i}] is not a mapping")
            continue
        emitted = e.get("emitted_id")
        standard = e.get("standard_id")
        family = e.get("family")
        if not emitted:
            failures.append(f"detector_id_map[{i}] missing emitted_id")
            continue
        if not standard:
            failures.append(f"{emitted}: missing standard_id")
            continue
        if family not in ("LOGFALL", "COGBIAS"):
            failures.append(f"{emitted}: family {family!r} must be LOGFALL or COGBIAS")

        # (1)+(2) uniqueness / bijection
        if emitted in seen_emitted:
            failures.append(f"{emitted}: duplicate emitted_id")
        seen_emitted[emitted] = i
        if standard in seen_standard:
            failures.append(f"{standard}: two emitted ids map to the same standard_id "
                            f"(not a bijection)")
        seen_standard[standard] = i
        mapped_emitted.add(emitted)

        # (3) standard_id must exist AND be shipped-maturity
        if standard not in all_ids:
            failures.append(f"{emitted}: standard_id {standard!r} does not exist in the "
                            f"ruleset (drift / unmapped id) -> REJECTED")
        elif standard not in shipped_ids:
            failures.append(f"{emitted}: standard_id {standard!r} is not shipped-maturity; "
                            f"emitting it would launder a not-yet-built detector")

        # (5) succeeds_into must be a real proposed detector
        succ = e.get("succeeds_into")
        if succ is not None:
            if succ not in all_ids:
                failures.append(f"{emitted}: succeeds_into {succ!r} does not exist in the ruleset")
            elif succ not in proposed_ids:
                failures.append(f"{emitted}: succeeds_into {succ!r} is not a proposed detector "
                                f"(a migration target must not already be shipped)")

    # (4) round-trip both ways vs the ruleset's shipped surface
    missing = shipped_ids - mapped_emitted
    if missing:
        failures.append(f"shipped detectors with no id-map entry (runtime allow-list "
                        f"incomplete): {sorted(missing)}")
    extra = mapped_emitted - shipped_ids
    if extra:
        failures.append(f"id-map entries for non-shipped ids (invented drift): {sorted(extra)}")

    return failures


def check_bias_catalog(bias_doc: dict, ruleset: dict) -> list[str]:
    failures: list[str] = []
    all_ids, _shipped, _proposed = ruleset_id_sets(ruleset)
    declared_ct = declared_counter_tests(ruleset)

    def check_entry(where: str, det_id, ct_id) -> None:
        if not det_id or det_id not in all_ids:
            failures.append(f"{where}: detector_id {det_id!r} not declared in the ruleset")
        if not ct_id or ct_id not in declared_ct:
            failures.append(f"{where}: required_counter_test {ct_id!r} not declared under "
                            f"counter_test_availability")

    biases = bias_doc.get("biases")
    if not isinstance(biases, list) or not biases:
        failures.append("bias-catalog: biases must be a non-empty list")
    else:
        for b in biases:
            if not isinstance(b, dict):
                failures.append("bias-catalog: a bias entry is not a mapping"); continue
            check_entry(f"bias {b.get('key')}", b.get("detector_id"), b.get("required_counter_test"))

    tooth = bias_doc.get("formal_validity_tooth")
    if isinstance(tooth, dict):
        check_entry("formal_validity_tooth", tooth.get("detector_id"),
                    tooth.get("required_counter_test"))
    return failures


def selftest() -> int:
    """Exercise the rejection path in-memory: teeth both ways."""
    ruleset = {
        "shipped_detectors": [{"rule_id": "LOGFALL.ADHOMINEM.V1", "maturity": "shipped"}],
        "detectors": [{"rule_id": "LOGFALL.ADHOM.V2", "maturity": "proposed"}],
        "counter_test_availability": {"runnable": [], "proposed": ["CTEST.X.V1"]},
    }
    clean = {"detector_id_map": [
        {"emitted_id": "LOGFALL.ADHOMINEM.V1", "standard_id": "LOGFALL.ADHOMINEM.V1",
         "family": "LOGFALL", "succeeds_into": "LOGFALL.ADHOM.V2"}]}
    if check_id_map(clean, ruleset):
        print("SELFTEST FAIL: clean map was rejected"); return 1

    # (a) drifted standard_id
    drift = {"detector_id_map": [
        {"emitted_id": "LOGFALL.ADHOMINEM.V1", "standard_id": "LOGFALL.NOTREAL.V9",
         "family": "LOGFALL"}]}
    if not check_id_map(drift, ruleset):
        print("SELFTEST FAIL: drifted standard_id was NOT rejected"); return 1

    # (b) laundering: standard_id points at a proposed (not shipped) id
    launder = {"detector_id_map": [
        {"emitted_id": "LOGFALL.ADHOMINEM.V1", "standard_id": "LOGFALL.ADHOM.V2",
         "family": "LOGFALL"}]}
    if not check_id_map(launder, ruleset):
        print("SELFTEST FAIL: V1->V2 laundering was NOT rejected"); return 1

    # (c) incomplete allow-list (a shipped detector left unmapped)
    ruleset2 = dict(ruleset)
    ruleset2["shipped_detectors"] = ruleset["shipped_detectors"] + [
        {"rule_id": "COGBIAS.CONFIRM.V1", "maturity": "shipped"}]
    if not check_id_map(clean, ruleset2):
        print("SELFTEST FAIL: incomplete allow-list was NOT rejected"); return 1

    print("ok: selftest — clean map passes; drift, laundering, and incomplete "
          "allow-list are all rejected (teeth both ways)")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()

    ruleset = _load(RULESET)
    id_map_doc = _load(ID_MAP)
    bias_doc = _load(BIAS_CATALOG)

    failures = check_id_map(id_map_doc, ruleset)
    failures += check_bias_catalog(bias_doc, ruleset)

    for f in failures:
        print(f"FAIL: {f}")
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1

    _all, shipped, _prop = ruleset_id_sets(ruleset)
    n = len(id_map_doc.get("detector_id_map") or [])
    print(f"ok: detector-id-map — {n} emitted ids reconciled to shipped standard ids "
          f"(bijection holds; {len(shipped)} shipped detectors all mapped)")
    print("ok: bias-catalog — every set-1 bias resolves to a governed detector id "
          "and a declared counter-test")
    print("\nOK: detector-id-map + bias-catalog reconcile against the ruleset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
