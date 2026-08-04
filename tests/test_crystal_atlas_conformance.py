"""Self-heal decisions conform to Crystal Atlas graph-upsert-request.v0 (real schema validation).

The alignment claim — "a self-heal decision IS a valid Crystal Atlas claim backed by evidence" —
is validated against the VENDORED, pinned schemas with jsonschema, not asserted. Plus a pin
check that the vendored schemas match their recorded hashes (no silent drift from prophet-platform).
"""

import hashlib
import json
from pathlib import Path

import pytest

from automation import crystal_atlas, envelope, responder
from automation.durable_queue import DurableQueue

referencing = pytest.importorskip("referencing")
jsonschema = pytest.importorskip("jsonschema")
from referencing import Registry, Resource  # noqa: E402

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "third_party" / "crystal-atlas-schemas"


def _validator():
    resources = [
        (p.name, Resource.from_contents(json.loads(p.read_text("utf-8"))))
        for p in SCHEMA_DIR.glob("*.schema.json")
    ]
    registry = Registry().with_resources(resources)
    upsert_schema = json.loads((SCHEMA_DIR / "graph-upsert-request.v0.schema.json").read_text("utf-8"))
    return jsonschema.Draft202012Validator(upsert_schema, registry=registry)


def _decision(kind, system, evidence, *, stamp_beacon=True):
    b = {"kind_class": kind, "system": system, "evidence": evidence,
         "evidence_ref": f"file://x/{system}", "observed_at": "2026-08-04T00:00:00+00:00"}
    if stamp_beacon:
        b = envelope.stamp(b)
    return responder.decide_composed([b]), [b]


# --- the vendored schemas are pinned ----------------------------------------

def test_vendored_schemas_match_pin():
    manifest = json.loads((SCHEMA_DIR / "VENDOR.json").read_text("utf-8"))
    for name, sha in manifest["files"].items():
        actual = hashlib.sha256((SCHEMA_DIR / name).read_bytes()).hexdigest()
        assert actual == sha, f"vendored {name} drifted from prophet-platform@{manifest['source_commit']}"


# --- the adapter output is a valid graph-upsert-request.v0 ------------------

@pytest.mark.parametrize("kind,ev,expect_action", [
    ("mirror_drift", {"detector": "d", "reproducible": True, "stale": False}, "auto_fix"),
    ("stale_vendor", {"detector": "d", "reproducible": True, "stale": False}, "propose_pr"),
    ("policy_violation", {"detector": "opa", "reproducible": True, "stale": False}, "quarantine"),
    ("build_failure", {"detector": "ci", "reproducible": True, "stale": False}, "canary_fix"),
])
def test_decision_conforms_to_graph_upsert(kind, ev, expect_action):
    receipt, beacons = _decision(kind, f"subj:{kind}", ev)
    assert receipt["action"] == expect_action
    upsert = crystal_atlas.to_graph_upsert(receipt, beacons)
    _validator().validate(upsert)                    # raises if not conformant

    claim = upsert["claims"][0]
    assert claim["predicate"] == f"self_heal.{expect_action}"
    assert claim["subject_ref"] == upsert["nodes"][0]["node_id"]
    assert claim["evidence_refs"] == [upsert["evidence"][0]["evidence_id"]]
    assert upsert["evidence"][0]["receipt_ref"] == receipt["content_sha256"]  # citable back to the decision


def test_build_failure_subject_is_a_workflow_run():
    receipt, beacons = _decision("build_failure", "ci:validate",
                                 {"detector": "ci", "reproducible": True, "stale": False})
    upsert = crystal_atlas.to_graph_upsert(receipt, beacons)
    _validator().validate(upsert)
    assert upsert["nodes"][0]["node_kind"] == "workflow_run"


def test_unstamped_beacon_still_conforms():
    # a beacon obtained by calling a detector directly (no envelope) must still produce valid output
    receipt, beacons = _decision("mirror_drift", "external-mirrors",
                                 {"signal": True}, stamp_beacon=False)
    crystal_atlas_upsert = crystal_atlas.to_graph_upsert(receipt, beacons)
    _validator().validate(crystal_atlas_upsert)


def test_emit_records_upsert_durably(tmp_path):
    receipt, beacons = _decision("mirror_drift", "external-mirrors",
                                 {"detector": "d", "reproducible": True, "stale": False})
    sink = DurableQueue(tmp_path / "graph-upserts")
    crystal_atlas.emit_graph_upsert(receipt, beacons, sink=sink)
    assert sink.qsize() == 1
    _validator().validate(sink.get_nowait())          # what we durably recorded is conformant
