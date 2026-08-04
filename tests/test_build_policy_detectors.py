"""build_failure + policy_violation detectors — the last two SENSE classes.

policy_violation — reads the source-exposure gate report; a blocking finding -> quarantine.
build_failure    — network-gated (gh) latest-failed-workflow-on-main -> escalate (no local fix).
"""

import json

import pytest

from automation import detectors, responder
from automation.durable_queue import DurableQueue, state_dir


# --- policy_violation -------------------------------------------------------

def _report(tmp_path, **fields):
    p = tmp_path / "report.json"
    p.write_text(json.dumps(fields), encoding="utf-8")
    return p


def test_policy_violation_on_blocking_finding(tmp_path):
    rp = _report(tmp_path, result="fail", block=2, warn=0)
    beacons = detectors.detect_policy_violations(report_path=rp)
    assert len(beacons) == 1
    b = beacons[0]
    assert b["kind_class"] == "policy_violation"
    assert b["system"] == "policy:source-exposure"
    assert b["detail"]["block"] == 2


def test_no_violation_when_report_clean(tmp_path):
    assert detectors.detect_policy_violations(report_path=_report(tmp_path, result="pass", block=0)) == []


def test_no_report_returns_none(tmp_path):
    assert detectors.detect_policy_violations(report_path=tmp_path / "absent.json") == []


def test_full_loop_policy_violation_quarantines(tmp_path, monkeypatch):
    rp = _report(tmp_path, result="fail", block=1, warn=0)
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    detectors.run_detectors(inbox=inbox, detector_paths={"report_path": rp},
                            detectors=[detectors.detect_policy_violations])
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True,
                             executor_paths={"quarantine_dir": tmp_path / "q"})
    r = out[0]
    assert r["action"] == "quarantine"
    assert r["execution"]["quarantined"] is True
    assert DurableQueue(tmp_path / "q").qsize() == 1


# --- build_failure ----------------------------------------------------------

def _runs(*failed_names):
    return [{"name": n, "conclusion": "failure", "url": f"https://x/{n}"} for n in failed_names]


def test_build_failure_emits_per_failed_workflow():
    beacons = detectors.detect_build_failures(runs_source=lambda: _runs("validate", "ui"))
    kinds = {b["kind_class"] for b in beacons}
    systems = {b["system"] for b in beacons}
    assert kinds == {"build_failure"}
    assert systems == {"ci:validate", "ci:ui"}


def test_no_build_failure_when_none_failed():
    assert detectors.detect_build_failures(runs_source=lambda: []) == []


def test_build_failure_source_unavailable_returns_empty(monkeypatch):
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "gh: not authenticated"
    monkeypatch.setattr(detectors.subprocess, "run", lambda *a, **k: _Proc())
    assert detectors._latest_failed_workflows_on_main() == []   # network-gated


def test_full_loop_build_failure_escalates(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    detectors.run_detectors(inbox=inbox, detector_paths={"runs_source": lambda: _runs("validate")},
                            detectors=[detectors.detect_build_failures])
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True)
    r = out[0]
    # build_failure Law=probable -> canary_fix -> no canary mechanism -> escalate
    assert r["execution"]["canary_passed"] is False
    assert r["action"] == "escalate_human"
