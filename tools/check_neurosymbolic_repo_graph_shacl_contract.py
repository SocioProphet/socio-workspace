#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
VOCAB = FIXTURE_DIR / "neurosymbolic-repo-graph.ttl"
CONTRACT = FIXTURE_DIR / "neurosymbolic-repo-graph.shacl.ttl"

REQUIRED_SHAPES = {
    "RepositoryGraphFixtureShape",
    "CorpusLoopPlaneBindingShape",
}

REQUIRED_PATHS = {
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
    "evidencePlane",
    "ontologyPlane",
    "policyPlane",
    "runtimePlane",
    "ledgerPlane",
    "chronosReasoning",
    "watsonCycReasoning",
}

EXPECTED_BINDINGS = {
    "corpusLoop": "watson-cyc-semantic-web-chronos-v1",
    "evidencePlane": "SocioProphet/sherlock-search",
    "ontologyPlane": "SocioProphet/ontogenesis",
    "policyPlane": "SocioProphet/policy-fabric",
    "runtimePlane": "SocioProphet/agentplane",
    "ledgerPlane": "SocioProphet/model-governance-ledger",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def nrg_terms(text: str) -> set[str]:
    return set(re.findall(r"\bnrg:([A-Za-z][A-Za-z0-9]*)\b", text))


def declared_vocab_terms(text: str) -> set[str]:
    return set(re.findall(r"^nrg:([A-Za-z][A-Za-z0-9]*)\s+a\s+(?:rdfs:Class|rdfs:Property)", text, re.MULTILINE))


def main() -> int:
    failed = False
    vocab_text = VOCAB.read_text(encoding="utf-8")
    contract_text = CONTRACT.read_text(encoding="utf-8")
    declared = declared_vocab_terms(vocab_text)
    used = nrg_terms(contract_text)

    for shape in REQUIRED_SHAPES:
        if shape not in used:
            fail(f"contract missing shape {shape}")
            failed = True

    if "RepositoryGraphFixture" not in used:
        fail("contract missing target class RepositoryGraphFixture")
        failed = True

    for path in REQUIRED_PATHS:
        if f"sh:path nrg:{path}" not in contract_text:
            fail(f"contract missing sh:path nrg:{path}")
            failed = True
        if path not in declared:
            fail(f"vocabulary missing contract path {path}")
            failed = True

    undeclared = (used - REQUIRED_SHAPES) - declared
    if undeclared:
        fail(f"contract uses undeclared nrg terms: {sorted(undeclared)}")
        failed = True

    for path, value in EXPECTED_BINDINGS.items():
        if f"sh:path nrg:{path}" not in contract_text or f'sh:hasValue "{value}"' not in contract_text:
            fail(f"contract missing plane binding {path} -> {value}")
            failed = True

    if failed:
        return 1

    print("OK: neurosymbolic repo graph SHACL contract is vocabulary-aligned and plane-bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
