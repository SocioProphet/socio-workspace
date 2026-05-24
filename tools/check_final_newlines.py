#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKED = [
    "Makefile",
    "registry/spine-v0.txt",
    "manifest/active-spine.repos.toml",
    "governance/CANONICAL_SOURCES.yaml",
    "catalog/boundaries.yaml",
    "docs/TOPOLOGY.md",
    "docs/governance/active-spine-audit-2026-05-23.md",
    "docs/governance/runner-overlay-integration-note-2026-05-23.md",
    "docs/governance/active-spine-validation-stack-2026-05-23.md",
    "docs/governance/neurosymbolic-repo-graph-reasoner.md",
    "registry/neurosymbolic-repo-graph-reasoner/active-spine.repo-graph.findings.schema.json",
    "registry/neurosymbolic-repo-graph-reasoner/diagnostic.stale-pin.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/generated.active-spine.repo-graph.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/graph-lift.manifest.json",
    "registry/neurosymbolic-repo-graph-reasoner/invalid.missing-boundary.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/invalid.policy-denied-shacl-pass.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/neurosymbolic-repo-graph.shacl.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/neurosymbolic-repo-graph.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/valid.active-spine-inference.ttl",
    "registry/neurosymbolic-repo-graph-reasoner/fixtures/invalid.missing-finding-kind.repo-graph.findings.json",
    "registry/neurosymbolic-repo-graph-reasoner/fixtures/valid.active-spine.repo-graph.findings.json",
    "registry/neurosymbolic-repo-graph-reasoner/valid.active-spine-inference.json",
    "registry/neurosymbolic-repo-graph-reasoner/invalid.missing-boundary.json",
    "registry/neurosymbolic-repo-graph-reasoner/invalid.policy-denied-shacl-pass.json",
    "registry/neurosymbolic-repo-graph-reasoner/diagnostic.stale-pin.json",
    "tools/check_spine_v0.py",
    "tools/check_active_spine_overlay.py",
    "tools/check_active_spine_sources.py",
    "tools/check_spine_canonical_sources_drift.py",
    "tools/check_topology_doc_active_spine.py",
    "tools/check_active_spine_boundaries.py",
    "tools/check_active_spine_validation_stack_doc.py",
    "tools/check_neurosymbolic_repo_graph_reasoner_doc.py",
    "tools/check_neurosymbolic_repo_graph_fixtures.py",
    "tools/check_neurosymbolic_repo_graph_ttl_fixtures.py",
    "tools/check_neurosymbolic_repo_graph_vocabulary.py",
    "tools/check_neurosymbolic_repo_graph_shacl_contract.py",
    "tools/check_active_spine_repo_graph_lift.py",
    "tools/check_active_spine_repo_graph_snapshot.py",
    "tools/check_active_spine_repo_graph_evaluator.py",
    "tools/check_active_spine_repo_graph_findings_schema.py",
    "tools/evaluate_active_spine_repo_graph.py",
    "tools/generate_active_spine_repo_graph.py",
    "tools/check_runner_overlay_discovery.py",
    "tools/check_runner_overlay_merge_order.py",
    "tools/runner/manifest_layers.py",
]


def main() -> int:
    failed = False
    for rel in CHECKED:
        path = ROOT / rel
        if not path.exists():
            print(f"ERR: missing checked file: {rel}", file=sys.stderr)
            failed = True
            continue
        data = path.read_bytes()
        if not data:
            print(f"ERR: empty file: {rel}", file=sys.stderr)
            failed = True
            continue
        if not data.endswith(b"\n"):
            print(f"ERR: missing trailing newline: {rel}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print("OK: checked files end with trailing newlines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
