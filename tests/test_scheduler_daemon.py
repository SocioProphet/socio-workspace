"""Tests for the scheduler daemon entrypoint, observe-and-beacon, and the closed loop."""

import pytest

from automation import scheduler
from automation.durable_queue import DurableQueue, state_dir


def test_daemon_entrypoint_exists():
    # The fix for "python -m automation.scheduler exits immediately": a real,
    # callable entrypoint must now exist.
    assert callable(scheduler.main)
    assert callable(scheduler.run)
    assert callable(scheduler.build_scheduler)


def test_observe_and_beacon_emits_to_responder_inbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))
    scheduler.observe_and_beacon({"event": "push", "repo": "acme/x"})
    inbox = DurableQueue(state_dir() / "beacons")
    assert inbox.qsize() == 1
    beacon = inbox.get_nowait()
    assert beacon["kind"] == "event_observed"
    assert beacon["event"]["repo"] == "acme/x"
    assert "deferred" in beacon["decision"]  # honest: no auto-action taken


def test_build_scheduler_uses_durable_queue_and_beacon_handler(tmp_path, monkeypatch):
    pytest.importorskip("apscheduler")
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))
    s = scheduler.build_scheduler()
    assert isinstance(s.event_queue, DurableQueue)
    assert s.propagation_handler is scheduler.observe_and_beacon


def test_end_to_end_enqueue_then_drain_produces_beacon(tmp_path, monkeypatch):
    # webhook-produced event (a separate DurableQueue instance on the shared dir)
    # is drained by the scheduler and turned into a beacon — the loop is closed.
    pytest.importorskip("apscheduler")
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))
    produced = DurableQueue()  # default dir under SOCIOSPHERE_STATE_DIR
    produced.put({"event": "push", "repo": "acme/x", "ref": "refs/heads/main"})

    s = scheduler.build_scheduler(event_queue=DurableQueue())  # same default dir
    s._process_queue()  # drain once

    assert DurableQueue().empty()  # event consumed
    inbox = DurableQueue(state_dir() / "beacons")
    assert inbox.qsize() == 1  # and a beacon was emitted for it
