#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "generate_active_spine_repo_graph.py"
OUTPUT = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner" / "active-spine.repo-graph.findings.json"

REQUIRED_FINDINGS = {
    "promotion-ready",
    "missing-surface",
    "stale-pin",
    "policy-review-required",
    "blocked-non-actionable",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_active_spine_repo_graph", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load repo graph generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_repo_blocks(graph: str) -> list[dict[str, str]]:
    blocks = []
    for match in re.finditer(r"repo:([^\n]+)\n  a nrg:ActiveSpineRepository ;\n(?P<body>.*?)(?:\n\n|\Z)", graph, re.DOTALL):
        body = match.group("body")
        record = {"node": match.group(1)}
        for key in [
            "repository",
            "spineRole",
            "presentInSpine",
            "presentInManifestOverlay",
            "presentInCanonicalSources",
            "presentInBoundaries",
            "presentInTopology",
        ]:
            value_match = re.search(rf"nrg:{key} (?P<value>[^;\.]+)", body)
            if value_match:
                value = value_match.group("value").strip().strip('"')
                record[key] = value
        blocks.append(record)
    return blocks


def finding(kind: str, repo: str, severity: str, reason: str, actionable: bool) -> dict:
    return {
        "kind": kind,
        "repository": repo,
        "severity": severity,
        "reason": reason,
        "actionable": actionable,
    }


def evaluate() -> dict:
    generator = load_generator()
    graph = generator.generate()
    repos = parse_repo_blocks(graph)
    findings = []

    for repo in repos:
        name = repo.get("repository", "unknown")
        role = repo.get("spineRole", "unclassified")
        surfaces = {
            "spine": repo.get("presentInSpine") == "true",
            "manifest_overlay": repo.get("presentInManifestOverlay") == "true",
            "canonical_sources": repo.get("presentInCanonicalSources") == "true",
            "boundaries": repo.get("presentInBoundaries") == "true",
            "topology": repo.get("presentInTopology") == "true",
        }
        missing = [surface for surface, present in surfaces.items() if not present]

        if role == "promotion_candidate" and not missing:
            findings.append(finding(
                "promotion-ready",
                name,
                "info",
                "promotion candidate has spine, manifest overlay, canonical-source, boundary, and topology coverage",
                True,
            ))
        if missing:
            findings.append(finding(
                "missing-surface",
                name,
                "warn",
                "missing governance surfaces: " + ",".join(missing),
                True,
            ))
        if role == "canonical" and not surfaces["manifest_overlay"]:
            findings.append(finding(
                "policy-review-required",
                name,
                "info",
                "canonical repository is tracked by spine but not by the committed active-spine overlay",
                True,
            ))
        if role == "adjacent_standard":
            findings.append(finding(
                "blocked-non-actionable",
                name,
                "info",
                "adjacent SourceOS lane is represented for governance visibility but is not a SocioProphet mutation target",
                False,
            ))

    findings.append(finding(
        "stale-pin",
        "watson-cyc-semantic-web-chronos-v1",
        "review",
        "corpus-loop plane pins are intentionally fixed and require explicit review before refresh",
        True,
    ))

    return {
        "schema_version": "0.1",
        "kind": "active_spine_repo_graph_findings",
        "corpus_loop": "watson-cyc-semantic-web-chronos-v1",
        "generated_from": "registry/neurosymbolic-repo-graph-reasoner/graph-lift.manifest.json",
        "finding_kinds": sorted({item["kind"] for item in findings}),
        "findings": findings,
    }


def main() -> int:
    result = evaluate()
    kinds = set(result["finding_kinds"])
    missing = REQUIRED_FINDINGS - kinds
    if missing:
        fail(f"missing required finding kinds: {sorted(missing)}")
        return 1
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: wrote {OUTPUT.relative_to(ROOT)} with {len(result['findings'])} findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
