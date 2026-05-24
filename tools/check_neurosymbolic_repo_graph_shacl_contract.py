#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
VOCAB = FIXTURE_DIR / "neurosymbolic-repo-graph.ttl"
CONTRACT = FIXTURE_DIR / "neurosymbolic-repo-graph.shacl.ttl"
GRAPH_LIFT_CHECK = ROOT / "tools" / "check_active_spine_repo_graph_lift.py"
SNAPSHOT_CHECK = ROOT / "tools" / "check_active_spine_repo_graph_snapshot.py"
EVALUATOR_CHECK = ROOT / "tools" / "check_active_spine_repo_graph_evaluator.py"
FINDINGS_SCHEMA_CHECK = ROOT / "tools" / "check_active_spine_repo_graph_findings_schema.py"

REQUIRED_SHAPES = {
    "RepositoryGraphFixtureShape",
    "CorpusLoopPlaneBindingShape",
    "ActiveSpineRepositoryShape",
    "RepositoryGraphInputShape",
}

REQUIRED_CLASSES = {
    "RepositoryGraphFixture",
    "ActiveSpineRepository",
    "RepositoryGraphInput",
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
    "sourceDigest",
    "repository",
    "spineRole",
    "presentInSpine",
    "presentInManifestOverlay",
    "presentInCanonicalSources",
    "presentInBoundaries",
    "presentInTopology",
    "sourcePath",
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


def run_module(path: Path, module_name: str) -> int:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        fail(f"could not load {module_name}")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main())


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

    for klass in REQUIRED_CLASSES:
        if klass not in used:
            fail(f"contract missing target class {klass}")
            failed = True
        if klass not in declared:
            fail(f"vocabulary missing class {klass}")
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

    graph_lift_status = run_module(GRAPH_LIFT_CHECK, "check_active_spine_repo_graph_lift")
    if graph_lift_status != 0:
        return graph_lift_status

    snapshot_status = run_module(SNAPSHOT_CHECK, "check_active_spine_repo_graph_snapshot")
    if snapshot_status != 0:
        return snapshot_status

    evaluator_status = run_module(EVALUATOR_CHECK, "check_active_spine_repo_graph_evaluator")
    if evaluator_status != 0:
        return evaluator_status

    findings_schema_status = run_module(FINDINGS_SCHEMA_CHECK, "check_active_spine_repo_graph_findings_schema")
    if findings_schema_status != 0:
        return findings_schema_status

    print("OK: neurosymbolic repo graph SHACL contract is vocabulary-aligned, plane-bound, graph-lift checked, snapshot-drift checked, evaluator-checked, and findings-schema checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
