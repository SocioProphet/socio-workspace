"""canary_fix + quarantine executors: completing the action taxonomy.

quarantine  — isolate a subject (policy breach) by recording a durable marker; never fix.
canary_fix  — prove the fix mechanism on a guaranteed-input->provable-output canary, then
              apply to the real artifact; if the canary fails, the mechanism is untrusted so
              the real artifact is NOT touched and the responder escalates.
"""

import textwrap

import pytest
import yaml

from automation import executors, responder
from automation.durable_queue import DurableQueue, state_dir
from automation.policy import policy_from_mapping
from engines.mirror_drift_engine import STATUS_HEADER, build_payload


VALID_REGISTRY = textwrap.dedent(
    """\
    version: "1.0.0"
    updated_at: "2026-08-01"
    mirrors:
      - name: socios-installer
        org: SociOS-Linux
        url: https://github.com/SociOS-Linux/socios-installer
        upstream:
          url: https://github.com/coreos/coreos-installer
          ref: main
          head_sha: aaaa1111
          checked_at: "2026-08-01"
        mirror_head_sha: bbbb2222
        drift: {status: behind, note: needs sync}
    """
)
STALE_STATUS = STATUS_HEADER + "version: '0.0.0'\nmirrors: []\n"


@pytest.fixture
def drifted(tmp_path):
    reg = tmp_path / "registry.yaml"
    status = tmp_path / "status.yaml"
    reg.write_text(VALID_REGISTRY, encoding="utf-8")
    status.write_text(STALE_STATUS, encoding="utf-8")
    return reg, status


# --- quarantine -------------------------------------------------------------

def test_quarantine_records_marker(tmp_path):
    beacon = {"kind_class": "policy_violation", "system": "svc:evil",
              "detail": {"reason": "unsigned artifact"}, "evidence_ref": "ev://1"}
    res = executors.quarantine(beacon=beacon, quarantine_dir=tmp_path)
    assert res["quarantined"] is True
    assert res["subject"] == "svc:evil"
    q = DurableQueue(tmp_path)
    assert q.qsize() == 1
    rec = q.get_nowait()
    assert rec["subject"] == "svc:evil"
    assert rec["reason"] == "unsigned artifact"


def test_quarantine_without_subject_is_not_resolved(tmp_path):
    res = executors.quarantine(beacon={"kind_class": "policy_violation"}, quarantine_dir=tmp_path)
    assert res["quarantined"] is False
    assert DurableQueue(tmp_path).qsize() == 0


def test_full_loop_policy_violation_quarantines(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    inbox.put({"kind_class": "policy_violation", "system": "svc:evil",
               "evidence": {"detector": "opa", "reproducible": True, "stale": False}})
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True,
                             executor_paths={"quarantine_dir": tmp_path / "q"})
    r = out[0]
    assert r["action"] == "quarantine"          # not escalated: quarantining IS the resolution
    assert r["execution"]["quarantined"] is True
    assert DurableQueue(tmp_path / "q").qsize() == 1


# --- canary_fix -------------------------------------------------------------

def test_canary_fix_proves_mechanism_then_heals(drifted):
    reg, status = drifted
    beacon = {"kind_class": "mirror_drift", "system": "mirror"}
    res = executors.canary_fix(beacon=beacon, registry_path=reg, status_path=status)
    assert res["canary_passed"] is True
    assert res["healed"] is True
    assert executors.is_in_sync(reg, status)     # real artifact healed after canary proof


def test_canary_fix_no_mechanism_escalates():
    res = executors.canary_fix(beacon={"kind_class": "build_failure", "system": "ci"})
    assert res["healed"] is False
    assert res["canary_passed"] is False
    assert "no canary mechanism" in res["error"]


def test_canary_fix_failed_canary_leaves_real_untouched(drifted, monkeypatch):
    reg, status = drifted
    before = status.read_bytes()
    # a broken fix mechanism: the canary cannot heal its synthetic case
    monkeypatch.setattr(executors, "resync_mirror_drift", lambda **kw: {"healed": False})
    res = executors.canary_fix(beacon={"kind_class": "mirror_drift"}, registry_path=reg, status_path=status)
    assert res["canary_passed"] is False
    assert res["healed"] is False
    assert status.read_bytes() == before          # real artifact never touched


def test_full_loop_build_failure_canary_fix_escalates(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    # build_failure Law=probable -> verdict probable -> action canary_fix
    inbox.put({"kind_class": "build_failure", "system": "ci",
               "evidence": {"detector": "ci", "reproducible": True, "stale": False}})
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True)
    r = out[0]
    assert r["execution"]["canary_passed"] is False
    assert r["action"] == "escalate_human"        # no canary mechanism -> honest escalation


def test_full_loop_canary_fix_heals_when_policy_lowers_law(drifted, tmp_path, monkeypatch):
    reg, status = drifted
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    # governance choice: require canary-gating for mirror_drift by lowering its Law to probable
    pol = policy_from_mapping({"law_by_kind": {"mirror_drift": "probable"}})
    inbox.put({"kind_class": "mirror_drift", "system": "mirror",
               "evidence": {"detector": "d", "reproducible": True, "stale": False}})
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True, policy=pol,
                             executor_paths={"registry_path": reg, "status_path": status})
    r = out[0]
    assert r["action"] == "canary_fix"
    assert r["execution"]["canary_passed"] is True
    assert r["execution"]["healed"] is True
    assert executors.is_in_sync(reg, status)
