"""workspace_lock_drift detector: network-gated detect -> propose (never auto-apply pins).

A resolved lock pins repo refs to SHAs; regenerating it tracks live upstream, so the honest
action is a reviewable proposal, not a silent auto-bump. The detector resolves (here via an
offline `--fixture-map`; the daemon uses `--live`), compares to the committed lock ignoring the
volatile `generated_at`, and on drift emits a beacon carrying the freshly resolved lock as the
proposed file change. The responder caps `workspace_lock_drift` at propose_pr.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from automation import detectors, responder
from automation.durable_queue import DurableQueue, state_dir

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_MAP = ["--fixture-map", "tests/fixtures/workspace-resolver-map.synthetic.json"]
TOOL = ROOT / "tools" / "generate_workspace_resolved_lock.py"


def _fresh_lock() -> str:
    """The lock the fixture-map resolver produces right now (stdout, no --write)."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), *FIXTURE_MAP],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_no_drift_when_lock_matches(tmp_path):
    lock = tmp_path / "lock.json"
    lock.write_text(_fresh_lock(), encoding="utf-8")
    assert detectors.detect_workspace_lock_drift(resolver_args=FIXTURE_MAP, lock_path=lock) is None


def test_generated_at_is_ignored(tmp_path):
    # Same content but a different generated_at must NOT count as drift.
    data = json.loads(_fresh_lock())
    data["generated_at"] = "1999-01-01T00:00:00Z"
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps(data), encoding="utf-8")
    assert detectors.detect_workspace_lock_drift(resolver_args=FIXTURE_MAP, lock_path=lock) is None


def test_drift_emits_proposal(tmp_path):
    lock = tmp_path / "lock.json"
    lock.write_text('{"schema_version": "0", "repos": []}\n', encoding="utf-8")  # wrong content
    beacon = detectors.detect_workspace_lock_drift(resolver_args=FIXTURE_MAP, lock_path=lock)

    assert beacon is not None
    assert beacon["kind_class"] == "workspace_lock_drift"
    files = beacon["proposal"]["files"]
    assert "manifest/workspace.resolved.lock.json" in files
    assert json.loads(files["manifest/workspace.resolved.lock.json"])  # a valid lock is proposed


def test_unavailable_resolver_returns_none():
    # network-gated: no usable resolver -> cannot assess -> no beacon (no spam)
    assert detectors.detect_workspace_lock_drift(resolver_args=["--fixture-map", "/nope.json"]) is None


def test_full_loop_drift_records_proposal(tmp_path, monkeypatch):
    lock = tmp_path / "lock.json"
    lock.write_text('{"schema_version": "0", "repos": []}\n', encoding="utf-8")
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")

    emitted = detectors.run_detectors(
        inbox=inbox,
        detector_paths={"resolver_args": FIXTURE_MAP, "lock_path": lock},
        detectors=[detectors.detect_workspace_lock_drift],
    )
    assert len(emitted) == 1

    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True,
                             executor_paths={"proposals_dir": tmp_path / "proposals"})
    r = out[0]
    assert r["action"] == "propose_pr"          # bumps pins -> reviewed, never auto-applied
    assert r["execution"]["proposed"] is True
    assert DurableQueue(tmp_path / "proposals").qsize() == 1
