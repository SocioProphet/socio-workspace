"""Tests for honest heartbeat liveness — both ways.

The point: a dead daemon must FAIL the probe. The old probe (import a module and
print ok) could never fail. These tests pin that the new probe fails on a missing
or stale heartbeat and passes only on a fresh one.
"""

import time

from automation import healthz, liveness


def test_no_heartbeat_reads_as_dead(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_HEARTBEAT_PATH", str(tmp_path / "hb"))
    assert liveness.age_seconds() is None
    assert liveness.is_alive() is False
    assert healthz.main([]) == 1  # no daemon has ever beat -> probe fails


def test_fresh_heartbeat_reads_as_alive(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_HEARTBEAT_PATH", str(tmp_path / "hb"))
    liveness.beat()
    assert liveness.is_alive() is True
    assert healthz.main([]) == 0


def test_stale_heartbeat_reads_as_dead(tmp_path, monkeypatch):
    # THE teeth: a daemon that stopped beating an hour ago is dead, and the probe
    # must say so (the exact failure the old import-only probe could not detect).
    hb = tmp_path / "hb"
    monkeypatch.setenv("SOCIOSPHERE_HEARTBEAT_PATH", str(hb))
    monkeypatch.setenv("SOCIOSPHERE_HEARTBEAT_MAX_AGE", "5")
    hb.write_text(str(time.time() - 3600), encoding="utf-8")
    assert liveness.is_alive(5.0) is False
    assert healthz.main([]) == 1
