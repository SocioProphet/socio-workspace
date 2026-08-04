"""Crystal Atlas adapter — emit self-heal decisions into the estate's shared graph.

Crystal Atlas (`prophet-platform/contracts/crystal-atlas`) is the estate's contract-intelligence
graph substrate; its `graph-upsert-request.v0` (nodes / edges / claims / evidence) is the write
interface to the graph the graph-brain MLN reasons over and Sherlock searches. This maps a
self-heal decision onto that contract, so a decision becomes a first-class, Sherlock-citable
claim backed by evidence — the same vocabulary as the rest of the reasoning spine.

  subject (`system`)  -> graph-node.v0
  decision receipt    -> claim.v0    (predicate = self_heal.<action>, evidence_refs = the signals)
  each detector beacon -> evidence.v0 (source_ref/observed_at/extractor_ref, receipt_ref = the
                                       decision's content hash)

The schemas are VENDORED + pinned in `third_party/crystal-atlas-schemas/` and a conformance test
validates this output against them. The actual POST to the live graph endpoint is deploy-time
(endpoint + credentials); the honest produce side here writes upserts to a durable queue a
credentialed job drains — the same pattern as the propose_pr / proposal-opener split.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from automation.durable_queue import DurableQueue, state_dir
from automation.envelope import ulid
from automation.responder import evidence_verdict

DEFAULT_TENANT = "sociosphere"
INTERNAL = "internal_private"  # self-heal decisions are internal graph facts

# beacon kind_class -> a graph-node.v0 node_kind (from that schema's enum).
_NODE_KIND = {"build_failure": "workflow_run"}  # a CI run; everything else is a data/config artifact
_DEFAULT_NODE_KIND = "dataset"

_VERDICT_CONFIDENCE = {"sealed": 0.95, "probable": 0.75, "weak": 0.45, "quarantine": 0.6, "refuse": 0.2}
_EVIDENCE_CONFIDENCE = {"sealed": 0.9, "probable": 0.6, "weak": 0.3}


def _rfc3339(value: Optional[str] = None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evidence_node(beacon: dict, tenant_id: str, receipt_ref: str, ingested_at: str) -> dict:
    ev = beacon.get("evidence") or {}
    extractor = ev.get("detector")
    return {
        "evidence_id": beacon.get("message_id") or ulid(),
        "tenant_id": tenant_id,
        "source_ref": beacon.get("evidence_ref") or f"selfheal://detector/{extractor or 'unknown'}",
        "observed_at": _rfc3339(beacon.get("observed_at")),
        "ingested_at": ingested_at,
        "extractor_ref": extractor or "selfheal",
        "confidence": _EVIDENCE_CONFIDENCE.get(evidence_verdict(beacon), 0.1),
        "distribution_class": INTERNAL,
        "receipt_ref": receipt_ref,
    }


def to_graph_upsert(receipt: dict, beacons: List[dict], *, tenant_id: str = DEFAULT_TENANT) -> dict:
    """Map a self-heal decision + its signals to a Crystal Atlas graph-upsert-request.v0."""
    system = (beacons[0].get("system") if beacons else None) or receipt.get("beacon_kind") or "unknown"
    kind = beacons[0].get("kind_class") if beacons else receipt.get("beacon_kind")
    now = _rfc3339()
    created = _rfc3339(receipt.get("decided_at"))
    node_id = f"selfheal:node:{system}"
    receipt_ref = receipt.get("content_sha256") or (receipt.get("message_id") or ulid())

    node = {
        "node_id": node_id,
        "tenant_id": tenant_id,
        "node_kind": _NODE_KIND.get(str(kind), _DEFAULT_NODE_KIND),
        "display_name": str(system),
        "attributes": {"kind_class": kind, "epistemic_level": receipt.get("epistemic_level")},
        "distribution_class": INTERNAL,
        "created_at": created,
        "updated_at": created,
    }

    evidence = [_evidence_node(b, tenant_id, receipt_ref, now) for b in beacons]
    claim = {
        "claim_id": receipt.get("message_id") or ulid(),
        "tenant_id": tenant_id,
        "subject_ref": node_id,
        "predicate": f"self_heal.{receipt.get('action', 'unknown')}",
        "value": {
            "verdict": receipt.get("verdict"),
            "epistemic_level": receipt.get("epistemic_level"),
            "reason": receipt.get("reason"),
        },
        "confidence": _VERDICT_CONFIDENCE.get(str(receipt.get("verdict")), 0.1),
        "evidence_refs": [e["evidence_id"] for e in evidence],
        "distribution_class": INTERNAL,
        "created_at": created,
    }

    return {"tenant_id": tenant_id, "nodes": [node], "edges": [], "claims": [claim], "evidence": evidence}


def emit_graph_upsert(receipt: dict, beacons: List[dict], *,
                      tenant_id: str = DEFAULT_TENANT, sink: Optional[DurableQueue] = None) -> dict:
    """Produce a graph-upsert and record it durably for a credentialed job to POST upstream."""
    upsert = to_graph_upsert(receipt, beacons, tenant_id=tenant_id)
    (sink if sink is not None else DurableQueue(state_dir() / "graph-upserts")).put(upsert)
    return upsert
