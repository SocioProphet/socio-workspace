#!/usr/bin/env python3
"""Validate Workspace Context Fabric governance artifacts.

This file is intentionally watched by the Workspace Context Fabric governance
workflow. This branch touch exists to exercise the pull-request workflow path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "docs/governance/workspace-context-fabric-boundary-map.v0.1.json"
SOURCE_REVIEW = ROOT / "docs/governance/workspace-context-fabric-source-exposure-review.v0.1.md"

REQUIRED_REPOS = {
    "SocioProphet/prophet-workspace",
    "SocioProphet/prophet-platform",
    "SocioProphet/agentplane",
    "SocioProphet/memory-mesh",
    "SocioProphet/agent-registry",
    "SocioProphet/policy-fabric",
    "SocioProphet/mcp-a2a-zero-trust",
    "SocioProphet/socioprophet-agent-standards",
    "SocioProphet/sociosphere",
}

REQUIRED_EDGE_TARGETS = {
    "prophet-platform",
    "agentplane",
    "agent_registry",
    "memory_mesh",
    "policy-fabric",
    "mcp_a2a_zero_trust",
}


def main() -> int:
    try:
        boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
        source_review = SOURCE_REVIEW.read_text(encoding="utf-8")

        if boundary.get("schema_version") != "sociosphere.workspace-context-fabric-boundary-map.v0.1":
            raise AssertionError("unexpected boundary map schema_version")

        owner_repos = {entry["repo"] for entry in boundary["owning_repositories"]}
        missing_repos = REQUIRED_REPOS - owner_repos
        if missing_repos:
            raise AssertionError("missing owning repos: " + ", ".join(sorted(missing_repos)))

        edges = boundary["dependency_edges"]
        workspace_targets = {edge["to"] for edge in edges if edge.get("from") == "prophet_workspace"}
        missing_targets = REQUIRED_EDGE_TARGETS - workspace_targets
        if missing_targets:
            raise AssertionError("missing prophet_workspace dependency targets: " + ", ".join(sorted(missing_targets)))

        if not boundary.get("non_ownership_rules"):
            raise AssertionError("missing non_ownership_rules")

        required_review_terms = [
            "Provider projection",
            "Share grant",
            "Recall promotion",
            "External continuation",
            "manifest_declared_refs_only",
        ]
        for term in required_review_terms:
            if term not in source_review:
                raise AssertionError(f"source exposure review missing {term!r}")

    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2

    print("OK: Workspace Context Fabric governance artifacts validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
