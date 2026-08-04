"""Escalation suppression: one decision per condition per policy cooldown, durably."""

import pytest

from automation import responder
from automation.durable_queue import DurableQueue, state_dir
from automation.policy import policy_from_mapping
from automation.suppression import Suppressor, fingerprint


def _beacon(system="vendored:libx"):
    return {
        "kind_class": "stale_vendor",
        "system": system,
        "observed_at": "2026-08-03T00:00:00Z",
        "evidence": {"detector": "d", "reproducible": True, "stale": False},
    }


# --- fingerprint identifies the condition, not the observation --------------

def test_fingerprint_excludes_observation_fields():
    a = {"kind_class": "stale_vendor", "system": "vendored:x", "observed_at": "t1"}
    b = {"kind_class": "stale_vendor", "system": "vendored:x", "observed_at": "t2"}
    assert fingerprint(a) == fingerprint(b)              # same condition
    assert fingerprint(a) != fingerprint({"kind_class": "stale_vendor", "system": "vendored:y"})
    assert fingerprint(a) != fingerprint({"kind_class": "mirror_drift", "system": "vendored:x"})


# --- the cooldown store -----------------------------------------------------

def test_should_process_respects_cooldown(tmp_path):
    s = Suppressor(tmp_path / "s.json")
    assert s.should_process("fp", cooldown_seconds=100, now=1000) is True    # first: process + record
    assert s.should_process("fp", cooldown_seconds=100, now=1050) is False   # within window: suppress
    assert s.should_process("fp", cooldown_seconds=100, now=1120) is True    # past window: process + re-arm
    assert s.should_process("fp", cooldown_seconds=100, now=1150) is False   # window is from 1120


def test_cooldown_zero_disables_suppression(tmp_path):
    s = Suppressor(tmp_path / "s.json")
    assert s.should_process("fp", cooldown_seconds=0, now=1) is True
    assert s.should_process("fp", cooldown_seconds=0, now=1) is True


def test_suppression_is_durable_across_instances(tmp_path):
    p = tmp_path / "s.json"
    assert Suppressor(p).should_process("fp", cooldown_seconds=100, now=1000) is True
    # a fresh instance (daemon restart) still sees the recorded decision
    assert Suppressor(p).should_process("fp", cooldown_seconds=100, now=1050) is False


# --- run_once integration ---------------------------------------------------

def _queues(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    return DurableQueue(state_dir() / "beacons"), DurableQueue(state_dir() / "decisions")


def test_run_once_suppresses_repeat_condition(tmp_path, monkeypatch):
    inbox, decisions = _queues(tmp_path, monkeypatch)
    sup = Suppressor(tmp_path / "sup.json")
    pol = policy_from_mapping({"suppression_cooldown_seconds": 3600})

    inbox.put(_beacon())
    assert len(responder.run_once(inbox=inbox, decisions=decisions, policy=pol, suppressor=sup)) == 1

    inbox.put(_beacon())                                  # same condition next cycle
    assert len(responder.run_once(inbox=inbox, decisions=decisions, policy=pol, suppressor=sup)) == 0

    inbox.put(_beacon(system="vendored:liby"))            # a different condition is not suppressed
    assert len(responder.run_once(inbox=inbox, decisions=decisions, policy=pol, suppressor=sup)) == 1


def test_run_once_without_suppressor_processes_every_time(tmp_path, monkeypatch):
    inbox, decisions = _queues(tmp_path, monkeypatch)
    inbox.put(_beacon())
    assert len(responder.run_once(inbox=inbox, decisions=decisions)) == 1
    inbox.put(_beacon())
    assert len(responder.run_once(inbox=inbox, decisions=decisions)) == 1   # no suppression by default


def test_run_once_cooldown_zero_processes_every_time(tmp_path, monkeypatch):
    inbox, decisions = _queues(tmp_path, monkeypatch)
    sup = Suppressor(tmp_path / "sup.json")
    pol = policy_from_mapping({"suppression_cooldown_seconds": 0})
    inbox.put(_beacon())
    assert len(responder.run_once(inbox=inbox, decisions=decisions, policy=pol, suppressor=sup)) == 1
    inbox.put(_beacon())
    assert len(responder.run_once(inbox=inbox, decisions=decisions, policy=pol, suppressor=sup)) == 1
