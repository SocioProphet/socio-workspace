"""Cross-repo integration proof: the responder REASONS with the vendored kernel.

These tests are the honest scoreboard for the claim "the semantic framework is actually
integrated." They fail if:

  - the vendored `procyber.semantic` kernel is absent or unimportable,
  - the responder stops delegating its verdict to the kernel's `meet` (a reimplementation
    would drift from the kernel and this test would catch it),
  - any fail-closed gate (boundary / IRI / no-evidence) stops escalating,
  - the end-to-end path inbox -> responder -> kernel -> decisions breaks.

Teeth point BOTH ways: one test asserts the responder MUST auto-act on a clean, well-
warranted beacon (a responder that never acts is useless), and others assert it MUST refuse
to auto-act when a boundary is crossed, identity risk is high, or evidence is absent.
"""

import pytest

# Import the responder first: importing it puts third_party/ on sys.path, after which the
# vendored kernel is importable directly. If either import fails, integration is broken.
from automation import responder
from procyber.semantic import BOTTOM, meet  # the VENDORED kernel


# --- must-act direction -----------------------------------------------------

def _clean_strong_drift():
    return {
        "kind_class": "mirror_drift",           # law: sealed (reversible re-sync)
        "system": "mirror",
        "evidence": {"detector": "drift-detector", "reproducible": True, "stale": False},
        "evidence_ref": "ev://drift/1",
    }


def test_clean_strong_beacon_auto_fixes():
    """A reversible failure with strong, fresh, reproducible evidence -> auto_fix."""
    r = responder.decide(_clean_strong_drift())
    assert r["verdict"] == "sealed"
    assert r["action"] == "auto_fix"


# --- must-refuse direction (teeth) ------------------------------------------

def test_boundary_breach_force_escalates_even_with_strong_evidence():
    """Crossing an octonion safety axis overrides a sealed verdict -> human."""
    b = _clean_strong_drift()
    b["plan"] = {"containment": 1.0}
    r = responder.decide(b)
    assert r["verdict"] == "BOTTOM"
    assert r["action"] == "escalate_human"
    assert "containment" in r["reason"]


def test_high_iri_force_escalates():
    """Identity risk >= block threshold escalates regardless of evidence."""
    b = _clean_strong_drift()
    b["entropy_uniqueness"] = 1.0
    b["injection_normativity"] = 1.0
    r = responder.decide(b)
    assert r["verdict"] == "BOTTOM"
    assert r["action"] == "escalate_human"
    assert "IRI" in r["reason"]


def test_weak_evidence_never_auto_fixes():
    """Same reversible law but only a weak signal -> propose_pr, not auto_fix."""
    b = _clean_strong_drift()
    b["evidence"] = {"signal": True}
    r = responder.decide(b)
    assert r["verdict"] == "weak"
    assert r["action"] == "propose_pr"


def test_no_evidence_is_bottom_to_human():
    """No warrant at all -> cannot assess -> BOTTOM -> human (the consent-hole)."""
    r = responder.decide({"kind_class": "mirror_drift", "system": "mirror"})
    assert r["verdict"] == "BOTTOM"
    assert r["action"] == "escalate_human"


def test_minimal_tier1_beacon_escalates_not_silently_acts():
    """The Tier-1 observe_and_beacon beacon carries no warrant -> honestly escalates."""
    r = responder.decide({"kind": "event_observed", "event": {"repo": "x"}})
    assert r["verdict"] == "BOTTOM"
    assert r["action"] == "escalate_human"


def test_cross_repo_change_caps_at_propose():
    """A stale-vendor (cross-repo) failure may never auto-act, even with sealed evidence."""
    r = responder.decide({
        "kind_class": "stale_vendor", "system": "vendor",
        "evidence": {"detector": "freshness", "reproducible": True, "stale": False},
    })
    assert r["verdict"] == "weak"
    assert r["action"] == "propose_pr"


def test_policy_violation_never_auto_fixed():
    """A policy breach quarantines; it is never auto-fixed however strong the evidence."""
    r = responder.decide({
        "kind_class": "policy_violation", "system": "policy",
        "evidence": {"detector": "opa", "reproducible": True, "stale": False},
    })
    assert r["verdict"] == "quarantine"
    assert r["action"] == "quarantine"


# --- the integration contract: the verdict IS the kernel's meet -------------

def test_verdict_is_the_vendored_kernel_meet():
    """Prove the responder delegates to the kernel, not a private reimplementation.

    We compute the expected verdict by calling the vendored `meet` directly with the same
    (law, evidence) the responder uses. If someone swaps the kernel or forks the logic,
    the two diverge and this fails.
    """
    b = {
        "kind_class": "build_failure",  # law: probable
        "system": "ci",
        "evidence": {"detector": "ci", "reproducible": True, "stale": False},  # evidence: sealed
    }
    r = responder.decide(b)
    expected = meet(responder.LAW_BY_KIND["build_failure"], "sealed")  # probable
    assert r["verdict"] == expected == "probable"
    assert r["action"] == responder.VERDICT_ACTION[expected]


def test_meet_cannot_exceed_the_law_arm():
    """Lattice invariant on the actual kernel: meet(law, ev) <= law for every evidence."""
    from procyber.semantic import VERDICT_ORDER
    for law in VERDICT_ORDER:
        for ev in VERDICT_ORDER:
            m = meet(law, ev)
            assert VERDICT_ORDER.index(m) <= VERDICT_ORDER.index(law)
            assert VERDICT_ORDER.index(m) <= VERDICT_ORDER.index(ev)


# --- end-to-end: inbox -> responder -> kernel -> decisions ------------------

def test_end_to_end_inbox_to_decisions(tmp_path, monkeypatch):
    """Put a beacon on the durable inbox; run_once drains it and emits a decision receipt.

    This exercises the whole wired path with real DurableQueues on disk — the same code the
    scheduler runs — not just the pure `decide` function.
    """
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path))
    from automation.durable_queue import DurableQueue, state_dir

    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    inbox.put(_clean_strong_drift())

    out = responder.run_once(inbox=inbox, decisions=decisions)

    assert len(out) == 1
    assert out[0]["verdict"] == "sealed"
    assert out[0]["action"] == "auto_fix"
    # the receipt is durably queued for downstream consumers / audit
    assert decisions.qsize() == 1
    persisted = decisions.get_nowait()
    assert persisted["action"] == "auto_fix"
    # and it carries a kernel SemanticAddress warrant
    assert persisted["address"]["specVersion"]  # kernel-stamped
    assert inbox.empty()


def test_canary_guaranteed_input_gives_provable_verdict():
    """Canary discipline: a fixed, known-good input must yield a fixed, known verdict.

    If this drifts, the reasoner changed underneath us — a guaranteed input proving a
    guaranteed output (the estate's canary maxim), applied to the responder itself.
    """
    canary = {
        "kind_class": "mirror_drift", "system": "canary",
        "evidence": {"detector": "canary", "reproducible": True, "stale": False},
        "evidence_ref": "ev://canary",
    }
    r = responder.decide(canary)
    assert (r["verdict"], r["action"]) == ("sealed", "auto_fix")
