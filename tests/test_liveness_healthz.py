"""Honest liveness — heartbeat AND progress, both ways.

A dead daemon must FAIL the probe (heartbeat). And the residual "instruments lie" case — a
daemon whose loop beats but whose decision cycle crashes every tick — must read as DEGRADED,
not green. These tests pin both.
"""

import time

import pytest

from automation import healthz, liveness


@pytest.fixture(autouse=True)
def _paths(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_HEARTBEAT_PATH", str(tmp_path / "hb"))
    monkeypatch.setenv("SOCIOSPHERE_PROGRESS_PATH", str(tmp_path / "pg"))
    return tmp_path


# --- heartbeat (is the loop alive?) -----------------------------------------

def test_no_heartbeat_reads_as_dead():
    assert liveness.age_seconds() is None
    assert healthz.main([]) == 1  # no daemon has ever beat -> probe fails


def test_stale_heartbeat_reads_as_dead(_paths, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_HEARTBEAT_MAX_AGE", "5")
    (_paths / "hb").write_text(str(time.time() - 3600), encoding="utf-8")
    liveness.progress()                                   # progress fresh, but the loop stalled
    assert healthz.main([]) == 1                          # heartbeat wins: dead


# --- progress (is the decision cycle actually working?) ---------------------

def test_fresh_heartbeat_and_progress_reads_as_alive():
    liveness.beat()
    liveness.progress()
    assert healthz.main([]) == 0


def test_fresh_heartbeat_but_no_progress_is_degraded():
    liveness.beat()                                       # loop beats...
    # ...but the responder job never completed -> no progress file
    assert liveness.progress_age_seconds() is None
    assert healthz.main([]) == 1                          # alive-but-dead -> degraded


def test_fresh_heartbeat_but_stale_progress_is_degraded(_paths, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_PROGRESS_MAX_AGE", "5")
    liveness.beat()                                       # loop still beating now
    (_paths / "pg").write_text(str(time.time() - 3600), encoding="utf-8")  # jobs failing for an hour
    assert healthz.main([]) == 1                          # the residual liveness-lie, caught


def test_progress_roundtrip():
    liveness.progress()
    age = liveness.progress_age_seconds()
    assert age is not None and age < 5
