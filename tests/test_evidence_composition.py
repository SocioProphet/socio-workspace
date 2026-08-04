"""Evidence composition: decide a SUBJECT over its composed signals (the MLN §9 delta).

The per-beacon model decided meet(Law, one-evidence). This composes multiple detector signals
about one subject and thresholds the composite: weak signals COMPOSE (three weak reach
sealed-strength), and a strict class's Law FENCES the subject (contradiction-tolerance). A
single-signal subject reduces exactly to the old behaviour.
"""

import pytest

from automation import responder
from automation.durable_queue import DurableQueue, state_dir


def _weak(system="external-mirrors", kind="mirror_drift"):
    return {"kind_class": kind, "system": system, "evidence": {"signal": True}}  # -> weak


def _sealed(system, kind):
    return {"kind_class": kind, "system": system,
            "evidence": {"detector": "d", "reproducible": True, "stale": False}}  # -> sealed


# --- evidence composes ------------------------------------------------------

def test_weak_signals_compose_to_a_stronger_action():
    # one weak on mirror_drift (Law sealed): meet(sealed, weak)=weak -> propose_pr
    assert responder.decide_composed([_weak()])["action"] == "propose_pr"
    # three weak about the SAME subject compose to sealed -> meet(sealed,sealed)=sealed -> auto_fix
    r = responder.decide_composed([_weak(), _weak(), _weak()])
    assert r["action"] == "auto_fix"
    assert r["n_signals"] == 3
    assert len(r["composed_from"]) == 3


# --- a strict class fences the subject (fail-closed composition) -------------

def test_strict_law_fences_a_subject_with_multiple_kinds():
    beacons = [_sealed("repo:x", "mirror_drift"),        # Law sealed (would auto_fix alone)
               _sealed("repo:x", "policy_violation")]    # Law quarantine (never auto-fix)
    r = responder.decide_composed(beacons)
    # effective Law = meet(sealed, quarantine) = quarantine; composed evidence = sealed
    assert r["verdict"] == "quarantine"
    assert r["action"] == "quarantine"                   # NOT auto_fix, though mirror_drift alone would


# --- singleton == old per-beacon behaviour ----------------------------------

def test_single_signal_reduces_to_per_beacon():
    b = _sealed("external-mirrors", "mirror_drift")
    r = responder.decide_composed([b])
    assert r["action"] == "auto_fix"
    assert "composed_from" not in r and "n_signals" not in r
    assert responder.decide(b)["action"] == r["action"]  # the wrapper agrees


# --- fail-closed gates apply across the whole subject -----------------------

def test_boundary_breach_in_any_signal_escalates_the_subject():
    breaching = {**_weak(), "plan": {"containment": 1.0}}
    r = responder.decide_composed([_weak(), breaching])
    assert r["action"] == "escalate_human"
    assert "boundary" in r["reason"]


# --- run_once groups by subject ---------------------------------------------

def _queues(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    return DurableQueue(state_dir() / "beacons"), DurableQueue(state_dir() / "decisions")


def test_run_once_composes_same_subject_into_one_decision(tmp_path, monkeypatch):
    inbox, decisions = _queues(tmp_path, monkeypatch)
    for _ in range(3):
        inbox.put(_weak(system="external-mirrors"))
    out = responder.run_once(inbox=inbox, decisions=decisions)
    assert len(out) == 1                     # 3 beacons about one subject -> 1 composed decision
    assert out[0]["action"] == "auto_fix"
    assert out[0]["n_signals"] == 3


def test_run_once_keeps_distinct_subjects_separate(tmp_path, monkeypatch):
    inbox, decisions = _queues(tmp_path, monkeypatch)
    inbox.put(_weak(system="vendored:a"))
    inbox.put(_weak(system="vendored:b"))
    out = responder.run_once(inbox=inbox, decisions=decisions)
    assert len(out) == 2                     # different subjects do not compose
    assert all("n_signals" not in r for r in out)
