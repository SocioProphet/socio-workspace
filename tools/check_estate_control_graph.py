#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for check_estate_control_graph.py") from exc

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "registry" / "estate-control-graph.yaml"

REQUIRED_LANES = {
    "agentic-pr-control",
    "diff-hygiene-gate",
    "fogstack-deployment-parity",
    "identity-proof-ingress",
    "shir-semantic-hyperknowledge",
    "michael-machine-science",
    "lattice-gaia-runtime-governance",
    "open-office-runtime",
}

REQUIRED_EDGES = {
    ("agentic-pr-control", "diff-hygiene-gate", "invokes_before_review_and_merge"),
    ("diff-hygiene-gate", "all-agent-authored-prs", "blocks_polluted_or_unscoped_changes"),
    ("michael-machine-science", "identity-proof-ingress", "consumes_before_identity_sensitive_authority"),
    ("michael-machine-science", "shir-semantic-hyperknowledge", "respects_projection_and_promotion_boundaries"),
    ("michael-machine-science", "lattice-gaia-runtime-governance", "reuses_runtime_profile_and_evidence_style"),
    ("fogstack-deployment-parity", "identity-proof-ingress", "requires_identity_for_future_live_apply"),
    ("open-office-runtime", "diff-hygiene-gate", "must_preserve_closed_provider_quarantine"),
}


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not GRAPH_PATH.exists():
        return fail(f"missing {GRAPH_PATH}")

    data = yaml.safe_load(GRAPH_PATH.read_text())
    if not isinstance(data, dict):
        return fail("estate control graph must be a mapping")

    if data.get("kind") != "EstateControlGraph":
        return fail("kind must be EstateControlGraph")

    lanes = data.get("lanes")
    if not isinstance(lanes, list):
        return fail("lanes must be a list")

    lane_ids = {lane.get("id") for lane in lanes if isinstance(lane, dict)}
    missing_lanes = sorted(REQUIRED_LANES - lane_ids)
    if missing_lanes:
        return fail(f"missing required lanes: {missing_lanes}")

    for lane in lanes:
        if not isinstance(lane, dict):
            return fail("each lane must be a mapping")
        lane_id = lane.get("id")
        if not lane_id:
            return fail("lane missing id")
        if lane.get("required") is not True:
            return fail(f"lane {lane_id}: required must be true")
        anchors = lane.get("anchors")
        if not isinstance(anchors, list) or not anchors:
            return fail(f"lane {lane_id}: anchors must be a non-empty list")
        invariants = lane.get("required_invariants")
        if not isinstance(invariants, list) or not invariants:
            return fail(f"lane {lane_id}: required_invariants must be a non-empty list")

    edges = data.get("required_edges")
    if not isinstance(edges, list):
        return fail("required_edges must be a list")
    edge_tuples = {
        (edge.get("from"), edge.get("to"), edge.get("relation"))
        for edge in edges
        if isinstance(edge, dict)
    }
    missing_edges = sorted(REQUIRED_EDGES - edge_tuples)
    if missing_edges:
        return fail(f"missing required edges: {missing_edges}")

    print("OK: estate control graph present with required lanes and edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
