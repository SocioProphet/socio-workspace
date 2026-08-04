"""Telemetry + alerting over the self-heal receipt streams."""

import pytest

from automation import telemetry
from automation.durable_queue import DurableQueue


def _seed(state):
    dec = DurableQueue(state / "decisions")
    dec.put({"beacon_kind": "mirror_drift", "verdict": "sealed", "action": "auto_fix",
             "execution": {"healed": True}})
    dec.put({"beacon_kind": "stale_vendor", "verdict": "weak", "action": "escalate_human",
             "execution": {"proposed": False}})            # a DECLINE (no local fix) — NOT a failure
    dec.put({"beacon_kind": "mirror_drift", "verdict": "sealed", "action": "auto_fix",
             "execution": {"healed": False, "rolled_back": True}})  # attempted + undone = failure
    dec.put({"beacon_kind": "workspace_lock_drift", "verdict": "weak", "action": "propose_pr",
             "execution": {"proposed": True}})
    dec.put({"beacon_kind": "policy_violation", "verdict": "quarantine", "action": "quarantine",
             "execution": {"quarantined": True}})
    dec.put({"beacon_kind": "mirror_drift", "verdict": "BOTTOM", "action": "escalate_human"})
    return dec


def test_collect_counts(tmp_path):
    _seed(tmp_path)
    m = telemetry.collect(state=tmp_path)
    assert m["decisions_total"] == 6
    assert m["heals_total"] == 1
    assert m["proposals_total"] == 1
    assert m["quarantines_total"] == 1
    assert m["escalations_total"] == 2
    assert m["healing_failures_total"] == 1          # only the rolled-back auto_fix; the decline does NOT count
    assert m["by_action"]["escalate_human"] == 2
    assert m["by_kind"]["mirror_drift"] == 3
    assert m["queue_depth"]["decisions"] == 6


def test_decline_is_not_a_healing_failure(tmp_path):
    # a propose_pr that correctly declined (no computable fix) must not inflate the drift signal
    DurableQueue(tmp_path / "decisions").put(
        {"beacon_kind": "stale_vendor", "action": "escalate_human", "execution": {"proposed": False}})
    assert telemetry.collect(state=tmp_path)["healing_failures_total"] == 0


def test_collect_is_non_destructive(tmp_path):
    dec = _seed(tmp_path)
    telemetry.collect(state=tmp_path)
    telemetry.collect(state=tmp_path)
    assert dec.qsize() == 6                            # scraping never drains the queue


def test_render_prometheus(tmp_path):
    _seed(tmp_path)
    text = telemetry.render_prometheus(telemetry.collect(state=tmp_path))
    assert "# TYPE sociosphere_selfheal_heals_total counter" in text
    assert "sociosphere_selfheal_heals_total 1" in text
    assert 'sociosphere_selfheal_decisions_by_action{action="escalate_human"} 2' in text
    assert 'sociosphere_selfheal_queue_depth{queue="decisions"} 6' in text


def test_alerts_fire_on_real_conditions(tmp_path):
    _seed(tmp_path)
    firing = telemetry.alerts(telemetry.collect(state=tmp_path), escalation_threshold=2)
    kinds = {a["kind"] for a in firing}
    assert "quarantine" in kinds                       # a policy breach was isolated
    assert "healing_failure" in kinds                  # an executor did not resolve
    assert "escalation_backlog" in kinds               # 2 escalations >= threshold 2


def test_no_alerts_when_clean(tmp_path):
    dec = DurableQueue(tmp_path / "decisions")
    dec.put({"beacon_kind": "mirror_drift", "verdict": "sealed", "action": "auto_fix",
             "execution": {"healed": True}})
    assert telemetry.alerts(telemetry.collect(state=tmp_path)) == []


def test_escalation_threshold_gates_alert(tmp_path):
    dec = DurableQueue(tmp_path / "decisions")
    dec.put({"beacon_kind": "x", "verdict": "BOTTOM", "action": "escalate_human"})
    m = telemetry.collect(state=tmp_path)
    assert telemetry.alerts(m, escalation_threshold=5) == []       # 1 < 5, no alert
    assert any(a["kind"] == "escalation_backlog"
               for a in telemetry.alerts(m, escalation_threshold=1))


def test_write_metrics_file(tmp_path):
    _seed(tmp_path)
    text = telemetry.render_prometheus(telemetry.collect(state=tmp_path))
    out = telemetry.write_metrics_file(text, path=tmp_path / "metrics.prom")
    assert out.read_text("utf-8") == text


def test_cli_alerts_exit_code(tmp_path, monkeypatch, capsys):
    _seed(tmp_path)
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))
    assert telemetry.main(["--alerts"]) == 1           # alerts firing -> nonzero (probe with teeth)
    assert telemetry.main([]) == 0                      # metrics print -> ok
    assert "sociosphere_selfheal" in capsys.readouterr().out
