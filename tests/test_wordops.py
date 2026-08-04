"""WordOps incident router — escalation-class decisions become room-safe incidents."""

import pytest

from automation import responder, wordops
from automation.durable_queue import DurableQueue, state_dir


def _receipt(action, verdict="weak"):
    b = {"kind_class": "policy_violation", "system": "svc:x",
         "evidence": {"detector": "opa", "reproducible": True, "stale": False}}
    r = responder.decide(b)                       # stamped receipt with address/content_sha256
    r["action"], r["verdict"] = action, verdict   # force the action under test
    return r


def test_quarantine_maps_to_a4_containment():
    inc = wordops.to_incident(_receipt("quarantine", "quarantine"))
    assert inc["autonomy_class"] == "A4"
    assert inc["severity"] == "high"


def test_escalate_maps_to_a0_human():
    inc = wordops.to_incident(_receipt("escalate_human", "BOTTOM"))
    assert inc["autonomy_class"] == "A0"
    assert inc["severity"] == "warning"


def test_incident_is_room_safe_references_the_warrant():
    r = _receipt("escalate_human")
    inc = wordops.to_incident(r)
    # the warrant is REFERENCED (hash + claim), not pasted — no raw detail in the incident
    assert inc["receipt_hash"] == r["content_sha256"]
    assert inc["claim_ref"] == r["message_id"]
    assert "detail" not in inc
    assert inc["receipt_hash"][:23] in inc["summary"]


def test_route_only_escalation_classes(tmp_path):
    sink = DurableQueue(tmp_path / "inc")
    assert wordops.route(_receipt("auto_fix", "sealed"), sink=sink) is None   # a heal opens no room
    assert wordops.route(_receipt("propose_pr"), sink=sink) is None           # a proposal opens no room
    assert sink.qsize() == 0
    assert wordops.route(_receipt("escalate_human"), sink=sink) is not None
    assert wordops.route(_receipt("quarantine", "quarantine"), sink=sink) is not None
    assert sink.qsize() == 2


def test_full_loop_escalation_produces_an_incident(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons"); decisions = DurableQueue(state_dir() / "decisions")
    inbox.put({"kind_class": "policy_violation", "system": "svc:evil",
               "evidence": {"detector": "opa", "reproducible": True, "stale": False}})
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True,
                             executor_paths={"quarantine_dir": tmp_path / "q"})
    inc = wordops.route(out[0], sink=DurableQueue(tmp_path / "inc"))
    assert out[0]["action"] == "quarantine"
    assert inc is not None and inc["autonomy_class"] == "A4"
