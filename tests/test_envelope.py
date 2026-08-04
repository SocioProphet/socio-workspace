"""Canonical event envelope + EpistemicLevel (convergence step 2)."""

import textwrap

import pytest

from automation import detectors, envelope, responder
from automation.durable_queue import DurableQueue, state_dir


# --- the envelope primitives ------------------------------------------------

def test_ulid_shape():
    u = envelope.ulid()
    assert len(u) == 26
    assert all(c in envelope._CROCKFORD for c in u)
    assert envelope.ulid(now_ms=2) > envelope.ulid(now_ms=1)   # time-ordered high bits


def test_stamp_adds_full_envelope():
    e = envelope.stamp({"kind_class": "mirror_drift", "system": "x"})
    for k in ("message_id", "trace_id", "span_id", "emitted_at", "schema_version", "content_sha256"):
        assert k in e and e[k]
    assert len(e["span_id"]) == 16
    assert e["content_sha256"].startswith("sha256:")
    assert e["schema_version"] == "v1"


def test_content_hash_ignores_volatile_fields():
    a = envelope.stamp({"system": "x", "verdict": "weak", "observed_at": "t1"})
    b = envelope.stamp({"system": "x", "verdict": "weak", "observed_at": "t2"})
    assert a["content_sha256"] == b["content_sha256"]          # observed_at excluded
    c = envelope.stamp({"system": "x", "verdict": "sealed"})
    assert a["content_sha256"] != c["content_sha256"]          # real content differs


def test_stamp_preserves_existing_trace_id():
    assert envelope.stamp({"system": "x"}, trace_id="trace-abc")["trace_id"] == "trace-abc"
    assert envelope.stamp({"system": "x", "trace_id": "existing"})["trace_id"] == "existing"


@pytest.mark.parametrize("receipt,level", [
    ({"execution": {"rolled_back": True}}, "rejected"),
    ({"execution": {"healed": True}}, "proved"),
    ({"execution": {"quarantined": True}}, "bounded"),
    ({"execution": {"proposed": True}}, "synthetic"),
    ({"verdict": "BOTTOM"}, "speculative"),
    ({"verdict": "weak", "action": "propose_pr"}, "empirical"),
])
def test_epistemic_level_mapping(receipt, level):
    assert envelope.epistemic_level_for(receipt) == level
    assert level in envelope.EPISTEMIC_LEVELS


# --- the pipeline actually stamps -------------------------------------------

def test_receipt_carries_envelope_and_level():
    b = {"kind_class": "mirror_drift", "system": "external-mirrors",
         "evidence": {"detector": "d", "reproducible": True, "stale": False}}
    r = responder.decide(b)
    assert r["message_id"] and r["trace_id"] and r["content_sha256"].startswith("sha256:")
    assert r["epistemic_level"] == "empirical"                # decided auto_fix, not yet executed


def test_trace_id_propagates_beacon_to_receipt(tmp_path, monkeypatch):
    reg = tmp_path / "reg.yaml"
    reg.write_text(textwrap.dedent("""\
        sources:
          - source_id: libx
            version_scheme: semver
            upstream_latest_version: "2.0.0"
        artifacts:
          - artifact_id: libx@c
            source_id: libx
            vendored_version: "1.0.0"
            freshness_policy: track-minor
            disposition: remediation-required
    """), encoding="utf-8")
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons"); decisions = DurableQueue(state_dir() / "decisions")

    emitted = detectors.run_detectors(inbox=inbox, detector_paths={"register_path": reg},
                                      detectors=[detectors.detect_stale_vendors])
    beacon_trace = emitted[0]["trace_id"]
    assert beacon_trace                                        # the beacon was stamped
    out = responder.run_once(inbox=inbox, decisions=decisions)
    assert out[0]["trace_id"] == beacon_trace                 # same trace end-to-end


def test_healed_decision_is_graded_proved(tmp_path, monkeypatch):
    import yaml
    from engines.mirror_drift_engine import STATUS_HEADER, build_payload
    reg = tmp_path / "external-mirrors.yaml"; status = tmp_path / "mirror-drift.yaml"
    reg.write_text("version: '1.0.0'\nupdated_at: '2026-08-01'\nmirrors: []\n", encoding="utf-8")
    status.write_text(STATUS_HEADER + "version: '0.0.0'\nmirrors: []\n", encoding="utf-8")  # drift
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons"); decisions = DurableQueue(state_dir() / "decisions")
    inbox.put({"kind_class": "mirror_drift", "system": "external-mirrors",
               "evidence": {"detector": "d", "reproducible": True, "stale": False}})
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True,
                             executor_paths={"registry_path": reg, "status_path": status})
    assert out[0]["execution"]["healed"] is True
    assert out[0]["epistemic_level"] == "proved"              # re-graded after a verified heal
