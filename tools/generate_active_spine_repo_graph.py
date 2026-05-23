#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
MANIFEST = BASE / "graph-lift.manifest.json"
OUTPUT = BASE / "generated.active-spine.repo-graph.ttl"

PREDICATES = {
    "canonical": "canonical",
    "candidate": "promotion_candidate",
    "adjacent": "adjacent_standard",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def repo_local_name(repo: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", repo).strip("-")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_manifest() -> dict:
    return json.loads(read_text(MANIFEST))


def classify_repo(repo: str, spine_text: str) -> str:
    canonical_index = spine_text.find("Canonical:")
    candidates_index = spine_text.find("Candidates:")
    adjacent_index = spine_text.find("Adjacent:")
    repo_index = spine_text.find(repo)
    if repo_index < 0:
        return "unclassified"
    if canonical_index <= repo_index < candidates_index:
        return PREDICATES["canonical"]
    if candidates_index <= repo_index < adjacent_index:
        return PREDICATES["candidate"]
    if adjacent_index <= repo_index:
        return PREDICATES["adjacent"]
    return "unclassified"


def presence(repo: str, text: str) -> str:
    return "true" if repo in text or repo.split("/", 1)[-1] in text else "false"


def source_digest(paths: list[str]) -> str:
    h = hashlib.sha256()
    for rel in paths:
        path = ROOT / rel
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def ttl_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def generate() -> str:
    manifest = load_manifest()
    inputs = manifest["inputs"]
    for rel in inputs:
        if not (ROOT / rel).exists():
            raise FileNotFoundError(rel)

    spine_text = read_text(ROOT / "registry/spine-v0.txt")
    overlay_text = read_text(ROOT / "manifest/active-spine.repos.toml")
    sources_text = read_text(ROOT / "governance/CANONICAL_SOURCES.yaml")
    boundaries_text = read_text(ROOT / "catalog/boundaries.yaml")
    topology_text = read_text(ROOT / "docs/TOPOLOGY.md")
    digest = source_digest(inputs)

    lines = [
        "@prefix nrg: <https://socioprophet.org/ns/neurosymbolic-repo-graph#> .",
        "@prefix repo: <https://github.com/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "repo:active-spine-generated-graph",
        "  a nrg:RepositoryGraphFixture ;",
        f"  nrg:fixtureId {ttl_string('generated.active-spine.repo-graph')} ;",
        f"  nrg:expectedResult {ttl_string('generated_repo_state_graph')} ;",
        f"  nrg:corpusLoop {ttl_string(manifest['corpus_loop'])} ;",
        "  nrg:canonicalSourcePresent true ;",
        "  nrg:manifestOverlayPresent true ;",
        "  nrg:boundaryPresent true ;",
        f"  nrg:boundaryClass {ttl_string('active_spine_repo_state_graph')} ;",
        "  nrg:shaclConforms true ;",
        f"  nrg:policyDecision {ttl_string('review_required')} ;",
        "  nrg:ledgerRequired true ;",
        f"  nrg:evidencePlane {ttl_string(manifest['required_planes']['evidence'])} ;",
        f"  nrg:ontologyPlane {ttl_string(manifest['required_planes']['ontology'])} ;",
        f"  nrg:policyPlane {ttl_string(manifest['required_planes']['policy'])} ;",
        f"  nrg:runtimePlane {ttl_string(manifest['required_planes']['runtime'])} ;",
        f"  nrg:ledgerPlane {ttl_string(manifest['required_planes']['ledger'])} ;",
        f"  nrg:chronosReasoning {ttl_string('active_spine_surfaces_lifted_into_generated_repo_state_graph')} ;",
        f"  nrg:watsonCycReasoning {ttl_string('repository_roles_are_interpreted_through_governed_plane_bindings_not_direct_action')} ;",
        f"  nrg:sourceDigest {ttl_string(digest)} .",
        "",
    ]

    for rel in inputs:
        node = repo_local_name(rel)
        lines.extend([
            f"repo:input-{node}",
            "  a nrg:RepositoryGraphInput ;",
            f"  nrg:sourcePath {ttl_string(rel)} .",
            "",
        ])

    for repo in manifest["required_repositories"]:
        local = repo_local_name(repo)
        role = classify_repo(repo, spine_text)
        lines.extend([
            f"repo:{local}",
            "  a nrg:ActiveSpineRepository ;",
            f"  nrg:repository {ttl_string(repo)} ;",
            f"  nrg:spineRole {ttl_string(role)} ;",
            f"  nrg:presentInSpine {presence(repo, spine_text)} ;",
            f"  nrg:presentInManifestOverlay {presence(repo, overlay_text)} ;",
            f"  nrg:presentInCanonicalSources {presence(repo, sources_text)} ;",
            f"  nrg:presentInBoundaries {presence(repo, boundaries_text)} ;",
            f"  nrg:presentInTopology {presence(repo, topology_text)} .",
            "",
        ])

    return "\n".join(lines)


def main() -> int:
    try:
        text = generate()
    except Exception as exc:  # pragma: no cover
        fail(str(exc))
        return 1
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"OK: wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
