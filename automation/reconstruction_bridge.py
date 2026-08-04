"""Reconstruction → Crystal Atlas bridge.

Turns three-space reconstruction output (``topic-record.v0`` + ``reconstruction-manifest.v0``, as
produced by the standalone `three-space-reconstruction` engine) into a Crystal Atlas
`graph-upsert-request.v0`, so a reconstructed corpus becomes a first-class, Sherlock-citable set of
claims backed by evidence — the retrieval-side counterpart to `crystal_atlas.py` (which does the
same for self-heal decisions).

  corpus (manifest)          -> graph-node.v0   (node_kind = dataset)
  each GROUNDED topic-record -> claim.v0        (predicate = reconstruction.topic; label+reasoning+mass)
  each representative snippet -> evidence.v0    (source_ref = doc_id, receipt_ref = corpus_sha256)

Deliberately plain-dict in / plain-dict out: no scikit-learn dependency here, so the sovereign
automation image stays light. The engine runs elsewhere; this only maps its records onto the
contract and records the upsert to the SAME durable queue `post_graph_upserts` already drains.

HONEST DEFAULT: only ``grounded=true`` topic-records become claims. A topic that is still just a
term-list (no reasoning / no evidence) is not a trustworthy claim and is skipped — never emitted as
if it were grounded.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from automation.crystal_atlas import INTERNAL, _rfc3339
from automation.durable_queue import DurableQueue, state_dir
from automation.envelope import ulid

DEFAULT_TENANT = "sociosphere"
EXTRACTOR = "three-space-reconstruction"


def _clamp(x, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return lo


def to_graph_upsert(records: List[dict], manifest: dict, *,
                    tenant_id: str = DEFAULT_TENANT) -> Tuple[dict, int]:
    """Map grounded topic-records + manifest to a graph-upsert-request.v0.

    Returns ``(upsert, skipped)`` where ``skipped`` counts ungrounded records left out.
    """
    corpus_id = manifest.get("corpus_id") or "corpus"
    receipt_ref = manifest.get("corpus_sha256") or ulid()
    now = _rfc3339()
    cov = manifest.get("coverage") or {}
    created = _rfc3339(cov.get("ts_max") or cov.get("ts_min"))
    node_id = f"reconstruction:node:{corpus_id}"

    node = {
        "node_id": node_id,
        "tenant_id": tenant_id,
        "node_kind": "dataset",
        "display_name": str(corpus_id),
        "attributes": {
            "document_count": cov.get("document_count"),
            "declared_gaps": cov.get("declared_gaps"),
            "spaces": sorted((manifest.get("spaces") or {}).keys()),
        },
        "distribution_class": INTERNAL,
        "created_at": created,
        "updated_at": now,
    }

    claims: List[dict] = []
    evidence: List[dict] = []
    skipped = 0
    for rec in records:
        if not rec.get("grounded"):
            skipped += 1
            continue
        ev_ids: List[str] = []
        for item in rec.get("representative_evidence") or []:
            eid = f"{rec['topic_id']}:{item.get('doc_id')}"
            evidence.append({
                "evidence_id": eid,
                "tenant_id": tenant_id,
                "source_ref": str(item.get("doc_id") or "unknown"),
                "observed_at": _rfc3339(cov.get("ts_min")),
                "ingested_at": now,
                "extractor_ref": EXTRACTOR,
                "confidence": _clamp(item.get("score", 0.0)),
                "distribution_class": INTERNAL,
                "receipt_ref": receipt_ref,
            })
            ev_ids.append(eid)
        claims.append({
            "claim_id": f"{corpus_id}:{rec['topic_id']}",
            "tenant_id": tenant_id,
            "subject_ref": node_id,
            "predicate": "reconstruction.topic",
            "value": {
                "topic_id": rec.get("topic_id"),
                "label": rec.get("label"),
                "reasoning": rec.get("reasoning"),
                "top_terms": rec.get("top_terms"),
                "mass": rec.get("mass"),
            },
            "confidence": _clamp(rec.get("mass", 0.0)),
            "evidence_refs": ev_ids,
            "distribution_class": INTERNAL,
            "created_at": created,
        })

    upsert = {"tenant_id": tenant_id, "nodes": [node], "edges": [], "claims": claims, "evidence": evidence}
    return upsert, skipped


def emit_reconstruction(records: List[dict], manifest: dict, *,
                        tenant_id: str = DEFAULT_TENANT,
                        sink: Optional[DurableQueue] = None) -> Tuple[dict, int]:
    """Produce the upsert and record it to the shared graph-upserts queue for the poster to drain."""
    upsert, skipped = to_graph_upsert(records, manifest, tenant_id=tenant_id)
    if upsert["claims"]:  # nothing grounded → nothing to say; don't emit an empty, claimless upsert
        (sink if sink is not None else DurableQueue(state_dir() / "graph-upserts")).put(upsert)
    return upsert, skipped
