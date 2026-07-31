#!/usr/bin/env python3
"""Validate the Cross-Repo Proof Ledger v0 seed.

This validator is intentionally stdlib-only so it can run in CI before we decide
whether to promote the proof ledger into the main Makefile validation path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "registry" / "cross-repo-proof-ledger.v0.json"

ALLOWED_STATUSES = {"planned", "seeded", "validated", "consumed", "blocked"}
REQUIRED_NODE_IDS = {
    "sourceos-contract-canon",
    "storage-standards",
    "knowledge-standards",
    "sourceos-local-substrate",
    "agentplane-execution-evidence",
    "policy-fabric-gates",
    "prophet-platform-parity",
    "sociosphere-ledger",
    "socioprophet-proof-ui",
}
REQUIRED_EDGE_IDS = {
    "contract-to-substrate",
    "substrate-to-agentplane",
    "agentplane-to-policy",
    "policy-to-platform",
    "platform-to-ledger",
    "ledger-to-ui",
}
FORBIDDEN_CLAIM_WORDS = {"production-ready", "production_ready", "prod-ready"}


def fail(message: str) -> None:
    print(f"ERR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_ledger() -> dict:
    require(LEDGER_PATH.exists(), f"missing ledger file: {LEDGER_PATH}")
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")


def validate_metadata(ledger: dict) -> None:
    require(ledger.get("apiVersion") == "socioprophet.org/proof-ledger/v0", "unexpected apiVersion")
    require(ledger.get("kind") == "CrossRepoProofLedger", "unexpected kind")
    metadata = ledger.get("metadata")
    require(isinstance(metadata, dict), "metadata must be an object")
    require(metadata.get("ownerRepo") == "SocioProphet/sociosphere", "ownerRepo must be SocioProphet/sociosphere")
    claim_boundary = metadata.get("claimBoundary", "")
    require("not production readiness" in claim_boundary.lower(), "claimBoundary must explicitly deny production readiness")


def validate_status(value: str, context: str) -> None:
    require(value in ALLOWED_STATUSES, f"{context} has invalid status {value!r}")


def validate_nodes(ledger: dict) -> set[str]:
    nodes = ledger.get("nodes")
    require(isinstance(nodes, list) and nodes, "nodes must be a non-empty list")
    seen = set()
    for node in nodes:
        require(isinstance(node, dict), "each node must be an object")
        node_id = node.get("id")
        require(isinstance(node_id, str) and node_id, "node id is required")
        require(node_id not in seen, f"duplicate node id: {node_id}")
        seen.add(node_id)
        require(isinstance(node.get("repo"), str) and "/" in node["repo"], f"node {node_id} repo must be owner/name")
        validate_status(node.get("status"), f"node {node_id}")
        evidence_refs = node.get("evidenceRefs")
        require(isinstance(evidence_refs, list) and evidence_refs, f"node {node_id} must have evidenceRefs")
    missing = REQUIRED_NODE_IDS - seen
    require(not missing, f"missing required node ids: {sorted(missing)}")
    return seen


def validate_edges(ledger: dict, node_ids: set[str]) -> None:
    edges = ledger.get("edges")
    require(isinstance(edges, list) and edges, "edges must be a non-empty list")
    seen = set()
    for edge in edges:
        require(isinstance(edge, dict), "each edge must be an object")
        edge_id = edge.get("id")
        require(isinstance(edge_id, str) and edge_id, "edge id is required")
        require(edge_id not in seen, f"duplicate edge id: {edge_id}")
        seen.add(edge_id)
        require(edge.get("from") in node_ids, f"edge {edge_id} references unknown from node")
        require(edge.get("to") in node_ids, f"edge {edge_id} references unknown to node")
        require(isinstance(edge.get("sourceRepo"), str) and "/" in edge["sourceRepo"], f"edge {edge_id} sourceRepo must be owner/name")
        require(isinstance(edge.get("targetRepo"), str) and "/" in edge["targetRepo"], f"edge {edge_id} targetRepo must be owner/name")
        validate_status(edge.get("status"), f"edge {edge_id}")
        require(isinstance(edge.get("mutationPosture"), str) and edge["mutationPosture"], f"edge {edge_id} must declare mutationPosture")
        require(isinstance(edge.get("evidenceRefs"), list) and edge["evidenceRefs"], f"edge {edge_id} must have evidenceRefs")
    missing = REQUIRED_EDGE_IDS - seen
    require(not missing, f"missing required edge ids: {sorted(missing)}")


def validate_commands(ledger: dict) -> None:
    commands = ledger.get("canonicalCommandRefs")
    require(isinstance(commands, list) and commands, "canonicalCommandRefs must be non-empty")
    fogstack = next((command for command in commands if command.get("id") == "fogstack-parity-readiness"), None)
    require(fogstack is not None, "missing fogstack-parity-readiness command ref")
    require(fogstack.get("repo") == "SocioProphet/prophet-platform", "fogstack command must live in prophet-platform")
    require(fogstack.get("command") == "make fogstack-parity-readiness", "unexpected fogstack parity command")
    require(fogstack.get("mutationPosture") == "non-mutating", "fogstack parity command must be non-mutating")
    validate_status(fogstack.get("status"), "fogstack parity command")


def validate_deferred_gaps(ledger: dict) -> None:
    gaps = ledger.get("deferredGaps")
    require(isinstance(gaps, list) and gaps, "deferredGaps must be non-empty")
    for gap in gaps:
        require(isinstance(gap.get("id"), str) and gap["id"], "gap id is required")
        require(isinstance(gap.get("repo"), str) and "/" in gap["repo"], f"gap {gap.get('id')} repo must be owner/name")
        validate_status(gap.get("status"), f"gap {gap.get('id')}")
        require(isinstance(gap.get("description"), str) and len(gap["description"]) >= 20, f"gap {gap.get('id')} needs concrete description")


def validate_no_production_overclaim(ledger: dict) -> None:
    encoded = json.dumps(ledger, sort_keys=True).lower()
    for word in FORBIDDEN_CLAIM_WORDS:
        require(word not in encoded, f"forbidden production-readiness overclaim found: {word}")


def main() -> int:
    ledger = load_ledger()
    validate_metadata(ledger)
    validate_commands(ledger)
    node_ids = validate_nodes(ledger)
    validate_edges(ledger, node_ids)
    validate_deferred_gaps(ledger)
    validate_no_production_overclaim(ledger)
    print(f"OK: validated {LEDGER_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
