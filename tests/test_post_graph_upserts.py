"""Crystal Atlas POST drainer + the run_once emit wiring (the live produce->deliver path)."""

import pytest

from automation import post_graph_upserts as pgu
from automation import responder
from automation.durable_queue import DurableQueue, state_dir


def _upsert():
    return {"tenant_id": "sociosphere", "nodes": [], "edges": [], "claims": [{"claim_id": "c"}],
            "evidence": []}


# --- the drainer ------------------------------------------------------------

def test_posts_and_drains_on_success(tmp_path):
    q = DurableQueue(tmp_path / "up"); q.put(_upsert()); q.put(_upsert())
    seen = []
    res = pgu.drain_and_post(upserts_dir=tmp_path / "up", dead_letter_dir=tmp_path / "dead",
                             poster=lambda u: seen.append(u) or 201)
    assert all(r["posted"] for r in res) and len(res) == 2
    assert len(seen) == 2                                  # the poster received the upserts
    assert q.qsize() == 0                                  # drained
    assert DurableQueue(tmp_path / "dead").qsize() == 0


def test_dead_letters_after_max_attempts_on_5xx(tmp_path):
    DurableQueue(tmp_path / "up").put(_upsert())
    res = pgu.drain_and_post(upserts_dir=tmp_path / "up", dead_letter_dir=tmp_path / "dead",
                             poster=lambda u: 500, max_attempts=3)
    assert res[0]["posted"] is False
    assert res[0]["attempts"] == 3 and res[0]["dead_lettered"] is True
    assert DurableQueue(tmp_path / "dead").qsize() == 1    # not lost — dead-lettered


def test_dead_letters_when_poster_raises(tmp_path):
    DurableQueue(tmp_path / "up").put(_upsert())
    def boom(u):
        raise ConnectionError("endpoint down")
    res = pgu.drain_and_post(upserts_dir=tmp_path / "up", dead_letter_dir=tmp_path / "dead",
                             poster=boom, max_attempts=2)
    assert res[0]["dead_lettered"] is True
    assert "endpoint down" in DurableQueue(tmp_path / "dead").get_nowait()["error"]


def test_main_skips_when_endpoint_unset(monkeypatch):
    monkeypatch.delenv(pgu.ENDPOINT_ENV, raising=False)
    assert pgu.main([]) == 0                               # no endpoint -> no-op, not a failure


# --- the emit wiring: run_once(emit_graph=True) records upserts -------------

def test_run_once_emit_graph_records_a_conformant_upsert(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons"); decisions = DurableQueue(state_dir() / "decisions")
    inbox.put({"kind_class": "stale_vendor", "system": "vendored:x",
               "evidence": {"detector": "d", "reproducible": True, "stale": False}})
    responder.run_once(inbox=inbox, decisions=decisions, emit_graph=True)

    upserts = DurableQueue(state_dir() / "graph-upserts")
    assert upserts.qsize() == 1
    up = upserts.get_nowait()
    assert up["claims"][0]["predicate"].startswith("self_heal.")
    assert up["evidence"] and up["nodes"]                  # the decision emitted claim + evidence + node
