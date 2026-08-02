"""Tests for the durable cross-process event queue."""

import queue

import pytest

from automation.durable_queue import DurableQueue


def test_put_get_is_fifo(tmp_path):
    q = DurableQueue(tmp_path)
    assert q.empty() and q.qsize() == 0
    q.put({"n": 1})
    q.put({"n": 2})
    q.put({"n": 3})
    assert q.qsize() == 3 and not q.empty()
    assert [q.get_nowait()["n"] for _ in range(3)] == [1, 2, 3]
    assert q.empty()


def test_get_on_empty_raises(tmp_path):
    with pytest.raises(queue.Empty):
        DurableQueue(tmp_path).get_nowait()


def test_shared_across_instances(tmp_path):
    # producer and consumer are separate instances on one dir = two processes
    DurableQueue(tmp_path).put({"event": "push", "repo": "acme/x"})
    consumer = DurableQueue(tmp_path)
    assert consumer.qsize() == 1
    assert consumer.get_nowait()["repo"] == "acme/x"


def test_no_double_delivery(tmp_path):
    q = DurableQueue(tmp_path)
    q.put({"n": 1})
    assert q.get_nowait() == {"n": 1}
    with pytest.raises(queue.Empty):
        q.get_nowait()  # claimed items are not redelivered


def test_half_written_temp_files_are_invisible(tmp_path):
    q = DurableQueue(tmp_path)
    (tmp_path / ".tmp-partial.json").write_text("{ half", encoding="utf-8")
    assert q.empty() and q.qsize() == 0  # atomic-write temp is never consumed
