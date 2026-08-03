"""Hermetic teeth for the generic reconcile() engine.

Uses fake Reconcilers (in-memory check/regenerate over a tmp artifact) so the verify +
rollback logic is proven exhaustively without touching any real tool or repo file:

  in sync            -> noop, regenerate never called
  drift, regen fixes -> regenerated + healed, verified by re-check
  check raises        -> abort (source un-assessable), artifact untouched
  regenerate raises   -> rollback to the prior artifact
  verify still fails  -> rollback to the prior artifact
"""

import pytest

from automation.executors import Reconciler, reconcile


def _art(tmp_path):
    p = tmp_path / "artifact.txt"
    p.write_text("PRIOR", encoding="utf-8")
    return p


def test_noop_when_in_sync(tmp_path):
    art = _art(tmp_path)
    calls = {"regen": 0}

    def regen():
        calls["regen"] += 1

    r = Reconciler(name="fake", check=lambda: True, regenerate=regen, artifacts=[art])
    res = reconcile(r)

    assert res["action_taken"] == "noop"
    assert res["healed"] is True
    assert calls["regen"] == 0            # never act when nothing is wrong
    assert art.read_text() == "PRIOR"


def test_heals_when_regenerate_fixes(tmp_path):
    art = _art(tmp_path)
    state = {"synced": False}

    def check():
        return state["synced"]

    def regen():
        art.write_text("REGENERATED", encoding="utf-8")
        state["synced"] = True

    res = reconcile(Reconciler("fake", check, regen, [art]))

    assert res["action_taken"] == "regenerated"
    assert res["healed"] is True
    assert res["rolled_back"] is False
    assert art.read_text() == "REGENERATED"


def test_abort_when_check_raises(tmp_path):
    art = _art(tmp_path)
    calls = {"regen": 0}

    def check():
        raise RuntimeError("source unreadable")

    def regen():
        calls["regen"] += 1

    res = reconcile(Reconciler("fake", check, regen, [art]))

    assert res["action_taken"] == "abort"
    assert res["healed"] is False
    assert calls["regen"] == 0            # refuse to act on an un-assessable source
    assert art.read_text() == "PRIOR"     # untouched


def test_rollback_when_regenerate_raises(tmp_path):
    art = _art(tmp_path)

    def regen():
        art.write_text("HALF-WRITTEN GARBAGE", encoding="utf-8")
        raise RuntimeError("boom mid-regeneration")

    res = reconcile(Reconciler("fake", check=lambda: False, regenerate=regen, artifacts=[art]))

    assert res["healed"] is False
    assert res["rolled_back"] is True
    assert art.read_text() == "PRIOR"     # restored


def test_rollback_when_verification_still_fails(tmp_path):
    art = _art(tmp_path)

    def regen():
        art.write_text("REGENERATED BUT STILL WRONG", encoding="utf-8")

    # check never returns True -> post-regeneration verify fails -> roll back
    res = reconcile(Reconciler("fake", check=lambda: False, regenerate=regen, artifacts=[art]))

    assert res["healed"] is False
    assert res["rolled_back"] is True
    assert art.read_text() == "PRIOR"     # restored, never left worse


def test_rollback_restores_absent_artifact(tmp_path):
    art = tmp_path / "artifact.txt"       # does not exist initially

    def regen():
        art.write_text("NEW", encoding="utf-8")

    res = reconcile(Reconciler("fake", check=lambda: False, regenerate=regen, artifacts=[art]))

    assert res["healed"] is False
    assert res["rolled_back"] is True
    assert not art.exists()               # restored to "absent"
