"""Reconstruction records → a valid Crystal Atlas graph-upsert (real schema validation).

The bridge's output is validated against the SAME vendored, pinned graph-upsert-request.v0 the
self-heal adapter uses — so "a reconstructed topic IS a valid claim backed by evidence" is proven,
not asserted. Plus: only grounded topics become claims, and the emit path feeds the same queue the
poster drains.
"""

import json
from pathlib import Path

import pytest

from automation import reconstruction_bridge as rb
from automation.durable_queue import DurableQueue

referencing = pytest.importorskip("referencing")
jsonschema = pytest.importorskip("jsonschema")
from referencing import Registry, Resource  # noqa: E402

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "third_party" / "crystal-atlas-schemas"


def _validator():
    resources = [(p.name, Resource.from_contents(json.loads(p.read_text("utf-8"))))
                 for p in SCHEMA_DIR.glob("*.schema.json")]
    upsert_schema = json.loads((SCHEMA_DIR / "graph-upsert-request.v0.schema.json").read_text("utf-8"))
    return jsonschema.Draft202012Validator(upsert_schema, registry=Registry().with_resources(resources))


def _manifest():
    return {"corpus_id": "session-x", "corpus_sha256": "a" * 64,
            "coverage": {"ts_min": "2026-06-30T14:00:00Z", "ts_max": "2026-06-30T19:36:00Z",
                         "document_count": 256, "declared_gaps": ["post-19:36 not represented"]},
            "spaces": {"lda": {"k": 22, "seed": 42, "topics_hash": "sha256:" + "b" * 64}}}


def _grounded(topic_id="T06"):
    return {"topic_id": topic_id, "top_terms": ["know", "think", "point"], "mass": 0.0977,
            "label": "Open-ended methodology reasoning", "reasoning": "hedge words → meta-conversation",
            "representative_evidence": [{"doc_id": "doc-14-58", "snippet": "we can't yet derive...", "score": 0.83}],
            "grounded": True}


def _ungrounded(topic_id="T02"):
    r = _grounded(topic_id); r["grounded"] = False; r["reasoning"] = ""; r["representative_evidence"] = []
    return r


def test_grounded_topic_conforms_to_graph_upsert():
    upsert, skipped = rb.to_graph_upsert([_grounded()], _manifest())
    _validator().validate(upsert)                       # raises if not conformant
    assert skipped == 0
    claim = upsert["claims"][0]
    assert claim["predicate"] == "reconstruction.topic"
    assert claim["subject_ref"] == upsert["nodes"][0]["node_id"]
    assert claim["evidence_refs"] == [upsert["evidence"][0]["evidence_id"]]
    assert upsert["evidence"][0]["receipt_ref"] == "a" * 64      # citable back to the corpus


def test_ungrounded_topics_are_skipped_not_emitted_as_claims():
    upsert, skipped = rb.to_graph_upsert([_grounded(), _ungrounded()], _manifest())
    _validator().validate(upsert)
    assert skipped == 1
    assert len(upsert["claims"]) == 1                   # only the grounded one
    assert [c["value"]["topic_id"] for c in upsert["claims"]] == ["T06"]


def test_confidence_is_clamped_into_unit_interval():
    rec = _grounded(); rec["mass"] = 1.7               # nonsense mass must not escape [0,1]
    upsert, _ = rb.to_graph_upsert([rec], _manifest())
    assert 0.0 <= upsert["claims"][0]["confidence"] <= 1.0


def test_emit_writes_to_the_shared_graph_upserts_queue(tmp_path):
    q = DurableQueue(tmp_path / "graph-upserts")
    upsert, skipped = rb.emit_reconstruction([_grounded()], _manifest(), sink=q)
    assert q.qsize() == 1
    drained = q.get_nowait()
    assert drained["claims"][0]["predicate"] == "reconstruction.topic"


def test_emit_does_not_write_a_claimless_upsert(tmp_path):
    q = DurableQueue(tmp_path / "graph-upserts")
    upsert, skipped = rb.emit_reconstruction([_ungrounded()], _manifest(), sink=q)
    assert skipped == 1 and q.qsize() == 0             # nothing grounded → nothing emitted
