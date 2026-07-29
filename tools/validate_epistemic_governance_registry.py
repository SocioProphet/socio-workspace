#!/usr/bin/env python3
"""Validate registry/epistemic-governance.yaml.

This registry records two different things and they must never be conflated:

  * `canonical_namespaces`  — INTENT: who is assigned a surface.
  * `implementation_status` — VERIFIED DELIVERY: what a walk of that repo found.

A 2026-07-29 audit found the file readable as a delivery record while eight of
its nine named owner repos contained zero trace of the standard, and while the
repo that does implement the detectors was not named at all. This validator
makes that failure mode non-recurring by enforcing:

  1. every declared namespace carries an implementation_status entry;
  2. status comes from a closed vocabulary;
  3. `implemented` / `partial` carry at least one concrete evidence path;
  4. `unimplemented` claims NO evidence (an unimplemented surface with evidence
     is a contradiction — promote it or drop the evidence);
  5. every status entry carries a note, so a bare verdict is never the whole
     story;
  6. the verification stamp (verified_on / verified_by) is present, so a reader
     knows how old the delivery claim is.

Exit 0 on success, 1 on any violation. Stdlib + pyyaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "epistemic-governance.yaml"

VALID_STATUSES = {"implemented", "partial", "unimplemented"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"ok: {msg}")


def main() -> int:
    if not REGISTRY.exists():
        print(f"ERR: missing registry: {REGISTRY}", file=sys.stderr)
        return 2

    doc = yaml.safe_load(REGISTRY.read_text())

    declared = set(doc.get("canonical_namespaces", {}) or {})
    if not declared:
        fail("canonical_namespaces is empty or missing")
        return 1
    ok(f"{len(declared)} namespaces declared in canonical_namespaces")

    impl = doc.get("implementation_status")
    if not isinstance(impl, dict):
        fail("implementation_status block is missing — intent without a delivery record "
             "is exactly the failure this validator exists to prevent")
        return 1

    for stamp in ("verified_on", "verified_by"):
        if not impl.get(stamp):
            fail(f"implementation_status.{stamp} is missing — a delivery claim needs a provenance stamp")
    if impl.get("verified_on") and impl.get("verified_by"):
        ok(f"verification stamp present ({impl['verified_on']})")

    entries = impl.get("namespaces") or {}
    if not entries:
        fail("implementation_status.namespaces is empty")
        return 1

    # 1. coverage: every declared namespace has a status entry
    missing = sorted(declared - set(entries))
    if missing:
        for name in missing:
            fail(f"namespace '{name}' is declared but has no implementation_status entry")
    else:
        ok("every declared namespace has an implementation_status entry")

    # extra entries are allowed and expected: they record real implementations
    # that predate their own namespace declaration (e.g. the Noetica reasoner).
    extra = sorted(set(entries) - declared)
    if extra:
        ok(f"{len(extra)} status entr{'y' if len(extra) == 1 else 'ies'} beyond canonical_namespaces: "
           f"{', '.join(extra)} (real implementations recorded ahead of their declaration)")

    # 2-5. per-entry rules
    counts = {s: 0 for s in VALID_STATUSES}
    for name, entry in sorted(entries.items()):
        if not isinstance(entry, dict):
            fail(f"'{name}' status entry is not a mapping")
            continue

        status = entry.get("status")
        if status not in VALID_STATUSES:
            fail(f"'{name}' has status {status!r}; must be one of {sorted(VALID_STATUSES)}")
            continue
        counts[status] += 1

        evidence = entry.get("evidence")
        if evidence is None:
            fail(f"'{name}' has no evidence key (use an empty list for unimplemented)")
            continue
        if not isinstance(evidence, list):
            fail(f"'{name}' evidence must be a list")
            continue

        if status in {"implemented", "partial"} and not evidence:
            fail(f"'{name}' is {status} but lists no evidence — a delivery claim needs a path")
        if status == "unimplemented" and evidence:
            fail(f"'{name}' is unimplemented but lists evidence — promote it or drop the evidence")

        if not (entry.get("note") or "").strip():
            fail(f"'{name}' has no note — a bare status verdict hides why")

    if not failures:
        ok(f"per-entry rules hold: {counts['implemented']} implemented, "
           f"{counts['partial']} partial, {counts['unimplemented']} unimplemented")

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nOK: epistemic-governance registry — intent and verified delivery are distinguishable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
