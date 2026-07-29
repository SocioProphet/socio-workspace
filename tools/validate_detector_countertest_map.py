#!/usr/bin/env python3
"""Validate standards/epistemic-governance/detector-countertest-map.yaml.

The ruleset became a union in 1.4.0: shipped detectors that exist in code today
sit alongside proposed detectors that are specified but not yet implemented.
That is the honest shape, but only if the union is machine-checkable — otherwise
"shipped" is a claim like any other. This validator enforces:

  1. Every detector carries `maturity` in the closed set {shipped, proposed}.
  2. `succeeded_by`, when present, points at a detector id that exists here.
     A shipped detector saying it will be replaced by an id nobody has declared
     is worse than saying nothing.
  3. Every `required_counter_tests` id is declared under
     `counter_test_availability` as either `runnable` or `proposed`.
     A CTEST used but nowhere declared is an undeclared control.
  4. `runnable` and `proposed` CTEST sets are disjoint (a runner cannot be both
     available and not available).
  5. No shipped-detector id collides with a proposed-detector id — that is what
     the maturity ladder is for.
  6. `principles.counter_tests_required_for_warn_or_block` remains true — this
     ruleset only makes sense under that principle; flipping it silently would
     erase the whole point.

Exit 0 clean, 1 on any violation, 2 when the file cannot be read or parsed
(a validator that cannot run must not read as one that passed).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULESET = ROOT / "standards" / "epistemic-governance" / "detector-countertest-map.yaml"

VALID_MATURITY = {"shipped", "proposed"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"ok: {msg}")


def main() -> int:
    if not RULESET.exists():
        print(f"ERR: missing ruleset: {RULESET}", file=sys.stderr)
        return 2
    try:
        doc = yaml.safe_load(RULESET.read_text())
    except yaml.YAMLError as exc:
        print(f"ERR: {RULESET} is not valid YAML: {exc}", file=sys.stderr)
        return 2
    if not isinstance(doc, dict):
        print(f"ERR: {RULESET} must parse to a mapping", file=sys.stderr)
        return 2

    principles = doc.get("principles") or {}
    if principles.get("counter_tests_required_for_warn_or_block") is not True:
        fail("principles.counter_tests_required_for_warn_or_block must remain true — "
             "this ruleset only makes sense under it")

    proposed_dets = list(doc.get("detectors") or [])
    shipped_dets = list(doc.get("shipped_detectors") or [])
    tech_dets = list(doc.get("technical_claim_detectors") or [])

    all_ids: dict[str, str] = {}   # id -> source list name, for collision check
    ok_by_maturity = {"shipped": 0, "proposed": 0}

    def check_detector_list(name: str, entries: list, default_maturity: str | None) -> None:
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                fail(f"{name}[{i}] is not a mapping"); continue
            rid = entry.get("rule_id")
            if not isinstance(rid, str) or not rid:
                fail(f"{name}[{i}] is missing rule_id"); continue

            maturity = entry.get("maturity", default_maturity)
            if maturity not in VALID_MATURITY:
                fail(f"{rid} has maturity {maturity!r}; must be one of {sorted(VALID_MATURITY)}")
                continue
            ok_by_maturity[maturity] += 1

            if rid in all_ids:
                fail(f"{rid} declared in both {all_ids[rid]} and {name}")
                continue
            all_ids[rid] = name

    check_detector_list("detectors", proposed_dets, default_maturity=None)
    check_detector_list("shipped_detectors", shipped_dets, default_maturity="shipped")
    check_detector_list("technical_claim_detectors", tech_dets, default_maturity="proposed")

    # succeeded_by must point at a declared id
    for entries in (shipped_dets, proposed_dets, tech_dets):
        for entry in entries:
            if not isinstance(entry, dict): continue
            succ = entry.get("succeeded_by")
            if succ is None: continue
            if succ not in all_ids:
                fail(f"{entry.get('rule_id')} succeeded_by {succ!r} which is not declared in this ruleset")

    # counter_test_availability disjointness + coverage
    avail = doc.get("counter_test_availability") or {}
    runnable = set(avail.get("runnable") or [])
    proposed_ct = set(avail.get("proposed") or [])
    if not runnable and not proposed_ct:
        fail("counter_test_availability missing runnable/proposed lists")
    overlap = runnable & proposed_ct
    if overlap:
        fail(f"counter-tests appear in BOTH runnable and proposed: {sorted(overlap)}")

    declared_ct = runnable | proposed_ct
    used_ct: set[str] = set()
    for entries in (shipped_dets, proposed_dets, tech_dets):
        for entry in entries:
            if not isinstance(entry, dict): continue
            for cid in entry.get("required_counter_tests") or []:
                used_ct.add(cid)
                if cid not in declared_ct:
                    # TTEST ids are a separate namespace, allowed and not required to appear here
                    if cid.startswith("TTEST."):
                        continue
                    fail(f"{entry.get('rule_id')} requires undeclared counter-test {cid}")

    unused = declared_ct - used_ct
    if unused:
        # Not fatal — a runner may exist ahead of a detector that needs it — but surface it.
        ok(f"{len(unused)} declared counter-test(s) currently unused by any detector: {sorted(unused)}")

    if not failures:
        ok(f"ruleset union holds: {ok_by_maturity['shipped']} shipped, {ok_by_maturity['proposed']} proposed; "
           f"{len(runnable)} runnable CTESTs, {len(proposed_ct)} proposed")

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nOK: detector-countertest-map — shipped and proposed distinguishable, "
          "counter-tests declared, succeeded_by ladder resolves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
