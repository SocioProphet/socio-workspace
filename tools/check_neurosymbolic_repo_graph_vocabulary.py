#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
VOCAB = FIXTURE_DIR / "neurosymbolic-repo-graph.ttl"

REQUIRED_CLASS = "RepositoryGraphFixture"
REQUIRED_PREDICATES = {
    "fixtureId",
    "expectedResult",
    "corpusLoop",
    "canonicalSourcePresent",
    "manifestOverlayPresent",
    "boundaryPresent",
    "boundaryClass",
    "shaclConforms",
    "policyDecision",
    "ledgerRequired",
    "pinnedCommitStale",
    "evidencePlane",
    "ontologyPlane",
    "policyPlane",
    "runtimePlane",
    "ledgerPlane",
    "chronosReasoning",
    "watsonCycReasoning",
}

REQUIRED_FIXTURE_PREDICATES = REQUIRED_PREDICATES - {"pinnedCommitStale"}

FIXTURES = [
    "valid.active-spine-inference.ttl",
    "invalid.missing-boundary.ttl",
    "invalid.policy-denied-shacl-pass.ttl",
    "diagnostic.stale-pin.ttl",
]


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def declared_terms(vocab_text: str) -> set[str]:
    return set(re.findall(r"^nrg:([A-Za-z][A-Za-z0-9]*)\s+a\s+(?:rdfs:Class|rdfs:Property)", vocab_text, re.MULTILINE))


def used_predicates(ttl_text: str) -> set[str]:
    terms = set(re.findall(r"\bnrg:([A-Za-z][A-Za-z0-9]*)\b", ttl_text))
    return terms - {REQUIRED_CLASS}


def main() -> int:
    failed = False
    vocab_text = VOCAB.read_text(encoding="utf-8")
    declared = declared_terms(vocab_text)

    if REQUIRED_CLASS not in declared:
        fail(f"vocabulary missing class {REQUIRED_CLASS}")
        failed = True

    missing_declared = REQUIRED_PREDICATES - declared
    if missing_declared:
        fail(f"vocabulary missing predicates: {sorted(missing_declared)}")
        failed = True

    for fixture_name in FIXTURES:
        path = FIXTURE_DIR / fixture_name
        if not path.exists():
            fail(f"missing fixture {fixture_name}")
            failed = True
            continue
        text = path.read_text(encoding="utf-8")
        if f"a nrg:{REQUIRED_CLASS}" not in text:
            fail(f"{fixture_name}: missing fixture class")
            failed = True
        used = used_predicates(text)
        undeclared = used - REQUIRED_PREDICATES
        if undeclared:
            fail(f"{fixture_name}: uses undeclared predicates {sorted(undeclared)}")
            failed = True
        missing = REQUIRED_FIXTURE_PREDICATES - used
        if missing:
            fail(f"{fixture_name}: missing required predicates {sorted(missing)}")
            failed = True
        if fixture_name == "diagnostic.stale-pin.ttl" and "pinnedCommitStale" not in used:
            fail("diagnostic.stale-pin.ttl: missing pinnedCommitStale")
            failed = True

    if failed:
        return 1

    print("OK: neurosymbolic repo graph vocabulary covers all TTL fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
