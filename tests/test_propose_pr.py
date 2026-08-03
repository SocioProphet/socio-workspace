"""propose_pr executor: the ACT machinery for cross-repo / low-confidence decisions.

Teeth:
  - default (no opener)      -> a durable proposal is recorded; NOT opened; resolved.
  - injected opener          -> the PR is opened via the opener; resolved.
  - invalid/missing proposal -> not resolved -> responder escalates to a human.
  - opener raises            -> not resolved -> responder escalates.

Safe by default: nothing here contacts GitHub. The daemon records proposals; only an
explicitly injected (credentialed) opener actually opens a PR.
"""

import pytest

from automation import executors, responder
from automation.durable_queue import DurableQueue, state_dir


def _beacon(with_proposal=True, kind="stale_vendor"):
    b = {
        "kind_class": kind,
        "system": "vendor-x",
        "evidence": {"detector": "vendor-freshness", "reproducible": True, "stale": False},
        "evidence_ref": "ev://vendor/x",
    }
    if with_proposal:
        b["proposal"] = {
            "branch": "auto/bump-vendor-x",
            "title": "Bump vendor x to latest",
            "body": "Automated proposal from the reasoned responder.",
            "files": {"registry/vendor-freshness.yaml": "new: content\n"},
        }
    return b


# --- executor in isolation --------------------------------------------------

def test_records_proposal_by_default(tmp_path):
    res = executors.propose_pr(beacon=_beacon(), proposals_dir=tmp_path)

    assert res["proposed"] is True
    assert res["opened"] is False
    assert res["proposal_ref"]
    # durably recorded for a human / credentialed CI job to open
    q = DurableQueue(tmp_path)
    assert q.qsize() == 1
    rec = q.get_nowait()
    assert rec["proposal"]["branch"] == "auto/bump-vendor-x"
    assert rec["proposal"]["base"] == "main"          # default base filled in
    assert rec["beacon_kind"] == "stale_vendor"


def test_opens_pr_when_opener_injected():
    seen = {}

    def opener(proposal):
        seen.update(proposal)
        return "https://github.com/SocioProphet/sociosphere/pull/999"

    res = executors.propose_pr(beacon=_beacon(), opener=opener)

    assert res["proposed"] is True
    assert res["opened"] is True
    assert res["pr_url"].endswith("/pull/999")
    assert seen["title"] == "Bump vendor x to latest"   # opener received the proposal


def test_invalid_proposal_is_not_proposed(tmp_path):
    res = executors.propose_pr(beacon=_beacon(with_proposal=False), proposals_dir=tmp_path)
    assert res["proposed"] is False
    assert "error" in res
    assert DurableQueue(tmp_path).qsize() == 0          # nothing recorded


def test_proposal_missing_files_is_rejected(tmp_path):
    b = _beacon()
    b["proposal"].pop("files")
    res = executors.propose_pr(beacon=b, proposals_dir=tmp_path)
    assert res["proposed"] is False


def test_opener_failure_is_not_proposed():
    def opener(_):
        raise RuntimeError("gh auth missing")

    res = executors.propose_pr(beacon=_beacon(), opener=opener)
    assert res["proposed"] is False
    assert "gh auth missing" in res["error"]


def test_identical_proposals_get_stable_ref(tmp_path):
    a = executors.propose_pr(beacon=_beacon(), proposals_dir=tmp_path)
    b = executors.propose_pr(beacon=_beacon(), proposals_dir=tmp_path)
    assert a["proposal_ref"] == b["proposal_ref"]       # content-addressed, dedup-friendly


# --- full loop through the responder ----------------------------------------

def test_full_loop_stale_vendor_records_proposal(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    proposals = tmp_path / "proposals"
    inbox.put(_beacon())

    out = responder.run_once(
        inbox=inbox, decisions=decisions, execute=True,
        executor_paths={"proposals_dir": proposals},
    )

    assert len(out) == 1
    r = out[0]
    assert r["action"] == "propose_pr"          # capped at propose (cross-repo), not escalated
    assert r["execution"]["proposed"] is True
    assert DurableQueue(proposals).qsize() == 1


def test_full_loop_propose_without_proposal_escalates(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    inbox.put(_beacon(with_proposal=False))

    out = responder.run_once(
        inbox=inbox, decisions=decisions, execute=True,
        executor_paths={"proposals_dir": tmp_path / "proposals"},
    )

    r = out[0]
    assert r["execution"]["proposed"] is False
    assert r["action"] == "escalate_human"      # a decision with no fileable proposal -> human
