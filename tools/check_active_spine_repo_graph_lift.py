#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
MANIFEST = BASE / "graph-lift.manifest.json"
GENERATOR = ROOT / "tools" / "generate_active_spine_repo_graph.py"

REQUIRED_GRAPH_TERMS = {
    "nrg:RepositoryGraphFixture",
    "nrg:ActiveSpineRepository",
    "nrg:RepositoryGraphInput",
    "nrg:sourceDigest",
    "nrg:repository",
    "nrg:spineRole",
    "nrg:presentInSpine",
    "nrg:presentInManifestOverlay",
    "nrg:presentInCanonicalSources",
    "nrg:presentInBoundaries",
    "nrg:presentInTopology",
}

EXPECTED_ROLES = {
    "SocioProphet/sociosphere": "canonical",
    "SocioProphet/prophet-platform": "canonical",
    "SocioProphet/TriTRPC": "canonical",
    "SocioProphet/socioprophet-standards-storage": "canonical",
    "SocioProphet/socioprophet-standards-knowledge": "canonical",
    "SocioProphet/prophet-platform-standards": "promotion_candidate",
    "SocioProphet/socioprophet-agent-standards": "promotion_candidate",
    "SocioProphet/prophet-workspace": "promotion_candidate",
    "SocioProphet/hellgraph": "promotion_candidate",
    "SourceOS-Linux/sourceos-spec": "adjacent_standard",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_active_spine_repo_graph", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_triple(text: str, repo: str, predicate: str, value: str) -> bool:
    local = re.sub(r"[^A-Za-z0-9]", "-", repo).strip("-")
    block_match = re.search(rf"repo:{re.escape(local)}\n(?P<body>.*?)(?:\n\n|\Z)", text, re.DOTALL)
    if not block_match:
        return False
    return f"nrg:{predicate} {json.dumps(value)}" in block_match.group("body")


def main() -> int:
    failed = False
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for key in ["manifest_id", "corpus_loop", "output", "inputs", "required_repositories", "required_planes", "non_goals"]:
        if key not in manifest:
            fail(f"manifest missing {key}")
            failed = True

    for rel in manifest.get("inputs", []):
        if not (ROOT / rel).exists():
            fail(f"manifest input does not exist: {rel}")
            failed = True

    if manifest.get("corpus_loop") != "watson-cyc-semantic-web-chronos-v1":
        fail("manifest is not pinned to watson-cyc-semantic-web-chronos-v1")
        failed = True

    for non_goal in ["do_not_execute_repo_mutations", "do_not_replace_policy_fabric", "do_not_treat_shacl_as_action_authorization"]:
        if non_goal not in manifest.get("non_goals", []):
            fail(f"manifest missing non-goal {non_goal}")
            failed = True

    try:
        generator = load_generator()
        graph = generator.generate()
    except Exception as exc:  # pragma: no cover
        fail(f"generator failed: {exc}")
        return 1

    for term in REQUIRED_GRAPH_TERMS:
        if term not in graph:
            fail(f"generated graph missing term {term}")
            failed = True

    for repo, role in EXPECTED_ROLES.items():
        if repo not in manifest.get("required_repositories", []):
            fail(f"manifest missing repo {repo}")
            failed = True
        if not has_triple(graph, repo, "repository", repo):
            fail(f"graph missing repository triple for {repo}")
            failed = True
        if not has_triple(graph, repo, "spineRole", role):
            fail(f"graph missing expected spine role for {repo}: {role}")
            failed = True
        if not has_triple(graph, repo, "presentInSpine", "true") and 'nrg:presentInSpine true' not in graph:
            fail(f"graph missing spine presence for {repo}")
            failed = True

    for plane, repo in manifest.get("required_planes", {}).items():
        if repo not in graph:
            fail(f"generated graph missing plane binding {plane}: {repo}")
            failed = True

    digest_match = re.search(r'nrg:sourceDigest "([0-9a-f]{64})"', graph)
    if not digest_match:
        fail("generated graph missing stable sha256 source digest")
        failed = True

    graph2 = generator.generate()
    if graph != graph2:
        fail("generator is not deterministic across repeated calls")
        failed = True

    if failed:
        return 1

    print("OK: active spine repo graph lift is deterministic and governance-bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
