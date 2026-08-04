"""Learning loop: safe, advisory policy-demotion recommendations from the receipt stream."""

import pytest

from automation import learning
from automation.durable_queue import DurableQueue
from automation.policy import DEFAULT_POLICY, load_policy


def _seed(state, kind, *, attempts, failures, resolved_kind="healed"):
    dec = DurableQueue(state / "decisions")
    for i in range(attempts):
        failed = i < failures
        ex = {resolved_kind: not failed}
        dec.put({"beacon_kind": kind, "action": "auto_fix", "execution": ex})


def test_demotes_a_class_that_mostly_fails(tmp_path):
    _seed(tmp_path, "mirror_drift", attempts=8, failures=6)   # 75% failing
    recs = learning.analyze(tmp_path, min_samples=4, failure_threshold=0.5)
    assert len(recs) == 1
    r = recs[0]
    assert r["kind_class"] == "mirror_drift"
    assert r["current_law"] == "sealed"
    assert r["recommended_law"] == "probable"                # one step DOWN the lattice
    assert r["failures"] == 6 and r["attempts"] == 8


def test_no_recommendation_below_min_samples(tmp_path):
    _seed(tmp_path, "mirror_drift", attempts=3, failures=3)   # all fail but too few
    assert learning.analyze(tmp_path, min_samples=4) == []


def test_no_recommendation_when_mostly_succeeding(tmp_path):
    _seed(tmp_path, "mirror_drift", attempts=10, failures=2)  # 20% failing
    assert learning.analyze(tmp_path, min_samples=4, failure_threshold=0.5) == []


def test_no_recommendation_at_lattice_floor(tmp_path):
    # 'unknown' Law is refuse (the floor) — nothing safe to demote to.
    _seed(tmp_path, "unknown", attempts=8, failures=8)
    assert learning.analyze(tmp_path, min_samples=4, failure_threshold=0.5) == []


def test_recommendation_is_advisory_not_applied(tmp_path):
    _seed(tmp_path, "mirror_drift", attempts=8, failures=8)
    learning.run_once(tmp_path, min_samples=4, failure_threshold=0.5)
    # governance is unchanged: the code default still says mirror_drift = sealed
    assert DEFAULT_POLICY.law_for("mirror_drift") == "sealed"
    assert load_policy().law_for("mirror_drift") == "sealed"


def test_run_once_records_recommendations(tmp_path):
    _seed(tmp_path, "vendored_graph_drift", attempts=6, failures=5)
    recs = learning.run_once(tmp_path, min_samples=4, failure_threshold=0.5)
    assert len(recs) == 1
    sink = DurableQueue(tmp_path / "policy-recommendations")
    assert sink.qsize() == 1
    assert sink.get_nowait()["kind_class"] == "vendored_graph_drift"


def test_pure_decisions_without_execution_are_ignored(tmp_path):
    # receipts with no executor run (e.g. escalations) are not outcomes to learn from
    dec = DurableQueue(tmp_path / "decisions")
    for _ in range(20):
        dec.put({"beacon_kind": "stale_vendor", "action": "escalate_human"})
    assert learning.analyze(tmp_path, min_samples=4) == []
