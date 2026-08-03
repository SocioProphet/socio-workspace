"""The SECOND full vertical slice, on real tools: the vendored-artifact graph.

Unlike mirror-drift (in-process, path-parameterised), this reconciler drives the real
tools/check_vendored_artifact_graph.py and tools/lift_vendor_freshness_to_graph.py as
subprocesses against the committed files. To stay safe, `restore_real_files` snapshots the
touched files up front and restores them after every test (even on failure), and the tests
assert the tree is returned to its committed bytes.

Teeth both ways, end to end:
  - break the DERIVED graph        -> detect -> decide auto_fix -> lift regenerates ->
                                      VERIFIED healed on disk, tree clean.
  - break the SOURCE register        -> regeneration cannot verify -> rollback -> the good
                                      graph is preserved and the decision escalates to a human.
"""

import subprocess
import sys

import pytest

from automation import detectors, executors, responder
from automation.durable_queue import DurableQueue, state_dir

GRAPH = executors.VENDORED_GRAPH_PATH
REGISTER = executors._ROOT / "registry" / "vendor-freshness.yaml"


@pytest.fixture
def restore_real_files():
    """Snapshot the real files this slice touches; restore them after the test."""
    snap = {p: p.read_bytes() for p in (GRAPH, REGISTER)}
    try:
        yield snap
    finally:
        for p, b in snap.items():
            p.write_bytes(b)


def _tree_matches(snap) -> bool:
    return all(p.read_bytes() == b for p, b in snap.items())


# --- guard: the real tree starts in sync (a control that acts on nothing is suspect) ---

def test_real_tree_in_sync_no_beacon_and_noop(restore_real_files):
    assert executors.vendored_graph_in_sync() is True
    assert detectors.detect_vendored_graph_drift() is None

    res = executors.reconcile_vendored_graph()
    assert res["action_taken"] == "noop"
    assert res["healed"] is True
    assert _tree_matches(restore_real_files)  # nothing changed


# --- break the derived artifact -> heal, verified on disk ---------------------

def test_live_break_derived_graph_then_heal(restore_real_files, tmp_path, monkeypatch):
    # BREAK: corrupt the committed derived graph.
    GRAPH.write_text("@@@ not the real vendored-artifact graph @@@\n", encoding="utf-8")
    assert executors.vendored_graph_in_sync() is False

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")

    # SENSE (only this detector; it reads the real tree)
    emitted = detectors.run_detectors(inbox=inbox, detectors=[detectors.detect_vendored_graph_drift])
    assert len(emitted) == 1
    assert emitted[0]["kind_class"] == "vendored_graph_drift"

    # DECIDE + ACT + VERIFY
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True)

    assert len(out) == 1
    assert out[0]["action"] == "auto_fix"
    assert out[0]["execution"]["healed"] is True
    # VERIFIED on disk by the real checker, and the graph is back to committed bytes.
    assert executors.vendored_graph_in_sync() is True
    assert _tree_matches(restore_real_files)


# --- break the source register -> cannot verify -> rollback + escalate --------

def test_live_break_source_register_escalates_and_preserves(restore_real_files, tmp_path, monkeypatch):
    good_graph = GRAPH.read_bytes()
    # BREAK THE SOURCE OF TRUTH: make the register unparseable.
    REGISTER.write_text("{[ this is not valid yaml :\n", encoding="utf-8")
    assert executors.vendored_graph_in_sync() is False  # checker fails on the bad source

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")

    detectors.run_detectors(inbox=inbox, detectors=[detectors.detect_vendored_graph_drift])
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True)

    assert len(out) == 1
    assert out[0]["execution"]["healed"] is False
    assert out[0]["action"] == "escalate_human"     # unverifiable fix -> human
    assert GRAPH.read_bytes() == good_graph          # good graph preserved (rollback/no-clobber)
