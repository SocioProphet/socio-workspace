"""Prove the wiring: a decided `auto_fix` for a class with a registered convergence
invariant (today: `mirror_drift`) is driven through `automation.control_loop.heal()` —
via `automation.self_heal.remediate()` — instead of firing its executor once and moving
on. Before this change, `responder._execute` called the executor exactly once and trusted
whatever it returned; `heal()` sat in the codebase unused (control_loop.py, PR #556).

These tests use fakes for the invariant (observe) and the executor (act) — not a real
mirror-drift registry mismatch, which `tests/test_executor_integration.py` already covers
end-to-end on real files — specifically so the MULTI-STEP re-observe/re-act behavior of the
loop is visible and provable (a single-shot call can never show iterations > 1).
"""
from __future__ import annotations

import pytest

from automation import control_loop, executors, responder


def _mirror_drift_beacon() -> dict:
    # Evidence shape that `decide()` governs to a `sealed` verdict -> `auto_fix` action
    # under DEFAULT_POLICY (mirrors the beacon shape detectors.detect_mirror_drift emits).
    return {
        "kind_class": "mirror_drift",
        "system": "external-mirrors",
        "evidence": {"detector": "mirror_drift_engine.check", "reproducible": True, "stale": False},
        "evidence_ref": "file://status/mirror-drift.yaml",
    }


def test_execute_drives_mirror_drift_multistep_via_heal(monkeypatch):
    """A fake executor that needs TWO applications to converge proves this is a real
    control loop (re-observe, act again), not a single fire-and-forget call."""
    calls = {"observe": 0, "act": 0}
    state = {"error": 2.0}

    def fake_invariant(**_kwargs) -> float:
        calls["observe"] += 1
        return state["error"]

    def fake_resync(**_kwargs) -> dict:
        calls["act"] += 1
        state["error"] = max(0.0, state["error"] - 1.0)
        return {"executor": "resync_mirror_drift", "action_taken": "regenerated"}

    monkeypatch.setitem(control_loop.INVARIANTS, "mirror_drift", fake_invariant)
    monkeypatch.setattr(executors, "resync_mirror_drift", fake_resync)

    beacon = _mirror_drift_beacon()
    receipt = responder.decide(beacon)
    assert receipt["action"] == "auto_fix", receipt  # sanity: governed to auto_fix

    responder._execute(beacon, receipt, {})

    # genuinely multi-step: the executor was fired more than once, driven by re-observation
    assert calls["act"] == 2
    assert calls["observe"] == 3  # initial observe + one per act
    exe = receipt["execution"]
    assert exe["converged"] is True
    assert exe["iterations"] >= 2
    assert exe["mode"] == "auto_fix"
    assert exe["trace_hash"]          # sealed provenance (ControlLoop gene)
    assert exe["healed"] is True      # back-compat signal used by the resolved/escalate gate
    assert receipt["action"] == "auto_fix"  # not downgraded: it converged


def test_execute_fails_closed_when_mirror_drift_never_converges(monkeypatch):
    """An invariant that never improves must fail closed to quarantine-escalate, and the
    decision must be downgraded to a human escalation — never a silent dead-end."""

    def fake_invariant(**_kwargs) -> float:
        return 1.0  # never improves, no matter how many times we act

    def fake_resync(**_kwargs) -> dict:
        return {"executor": "resync_mirror_drift", "action_taken": "regenerated"}

    monkeypatch.setitem(control_loop.INVARIANTS, "mirror_drift", fake_invariant)
    monkeypatch.setattr(executors, "resync_mirror_drift", fake_resync)

    beacon = _mirror_drift_beacon()
    receipt = responder.decide(beacon)
    assert receipt["action"] == "auto_fix", receipt

    responder._execute(beacon, receipt, {})

    exe = receipt["execution"]
    assert exe["converged"] is False
    assert exe["fail_closed_state"] == "quarantine-escalate"
    assert exe["healed"] is False
    assert receipt["action"] == "escalate_human"  # downgraded, not silently dropped
    assert "did not resolve" in receipt["reason"]


def test_vendored_graph_drift_auto_fix_stays_single_shot(monkeypatch):
    """`vendored_graph_drift` has NO registered invariant (control_loop.INVARIANTS only
    knows `mirror_drift`), so it must keep the existing single-shot executor call rather
    than being routed through heal() (which would immediately fail-closed for an unknown
    invariant and regress a class that works fine today)."""
    calls = {"n": 0}

    def fake_reconcile(**_kwargs) -> dict:
        calls["n"] += 1
        return {"executor": "reconcile_vendored_graph", "healed": True, "rolled_back": False}

    monkeypatch.setattr(executors, "reconcile_vendored_graph", fake_reconcile)

    beacon = {
        "kind_class": "vendored_graph_drift",
        "system": "vendored-artifact-graph",
        "evidence": {"detector": "vendored_graph_check", "reproducible": True, "stale": False},
    }
    receipt = responder.decide(beacon)
    assert receipt["action"] == "auto_fix", receipt

    responder._execute(beacon, receipt, {})

    assert calls["n"] == 1  # single-shot, as before — no loop wrapping an unverifiable class
    assert receipt["execution"]["healed"] is True
    assert "converged" not in receipt["execution"]  # not routed through remediate()/heal()
    assert receipt["action"] == "auto_fix"


def test_scheduler_run_responder_drives_mirror_drift_via_heal_end_to_end(monkeypatch, tmp_path):
    """The real daemon path: scheduler._run_responder() -> responder.run_once(execute=True)
    -> _execute() -> heal() for a beacon sitting in the on-disk inbox, with a fake invariant
    so no real registry file is needed."""
    pytest.importorskip("apscheduler")
    from automation import scheduler
    from automation.durable_queue import DurableQueue, state_dir

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))

    state = {"error": 1.0}

    def fake_invariant(**_kwargs) -> float:
        return state["error"]

    def fake_resync(**_kwargs) -> dict:
        state["error"] = 0.0
        return {"executor": "resync_mirror_drift", "action_taken": "regenerated"}

    monkeypatch.setitem(control_loop.INVARIANTS, "mirror_drift", fake_invariant)
    monkeypatch.setattr(executors, "resync_mirror_drift", fake_resync)

    DurableQueue(state_dir() / "beacons").put(_mirror_drift_beacon())

    s = scheduler.build_scheduler()
    s._run_responder()

    assert s.get_metrics()["jobs_failed"] == 0
    decisions = DurableQueue(state_dir() / "decisions")
    assert decisions.qsize() == 1
    receipt = decisions.get_nowait()
    assert receipt["action"] == "auto_fix"
    assert receipt["execution"]["converged"] is True
    assert receipt["execution"]["trace_hash"]


def test_scheduler_run_responder_escalates_when_mirror_drift_stuck(monkeypatch, tmp_path):
    """Same daemon path, but the invariant never improves: the scheduler's decision record
    must show a human escalation, not a swallowed failure."""
    pytest.importorskip("apscheduler")
    from automation import scheduler
    from automation.durable_queue import DurableQueue, state_dir

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))

    def fake_invariant(**_kwargs) -> float:
        return 1.0

    def fake_resync(**_kwargs) -> dict:
        return {"executor": "resync_mirror_drift", "action_taken": "regenerated"}

    monkeypatch.setitem(control_loop.INVARIANTS, "mirror_drift", fake_invariant)
    monkeypatch.setattr(executors, "resync_mirror_drift", fake_resync)

    DurableQueue(state_dir() / "beacons").put(_mirror_drift_beacon())

    s = scheduler.build_scheduler()
    s._run_responder()

    assert s.get_metrics()["jobs_failed"] == 0  # a fail-closed loop is not a scheduler failure
    decisions = DurableQueue(state_dir() / "decisions")
    receipt = decisions.get_nowait()
    assert receipt["action"] == "escalate_human"
    assert receipt["execution"]["fail_closed_state"] == "quarantine-escalate"
