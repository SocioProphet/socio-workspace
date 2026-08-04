"""Unified self-heal actuation — one sealed control model for every remediation mode.

This is the synthesis of two arms that grew in parallel:

  * ControlLoop (automation.control_loop) — bounded, convergent, fail-closed; it
    VERIFIES by re-observing reality after acting (never trusts an exit code) and
    seals its trace. Its weakness: it only knew how to drive an in-place *auto_fix*
    executor to convergence.
  * pr_opener / open_recorded_proposals — actually OPENS a fix PR (credential split,
    idempotent, cross-repo), with fail-closed-*with-detail* and a dead-letter. Its
    weakness: it reinvented bounded/fail-closed control and had no sealed provenance.

The unifying insight: **opening a reviewable fix PR is itself convergence** — the
target is "a remediation the system can't apply autonomously now exists on a human's
desk." So `propose_pr` is not a special case bolted beside the loop; it is a
ControlLoop whose invariant is "a PR exists", converged when `open_pr` succeeds and
fail-closed-to-human when it cannot. `auto_fix` remains the ControlLoop whose
invariant is "the artifact is in sync". Two invariants, one loop, one sealed
`LoopResult` — so the responder, the daemon, and the audit trail speak one language.

Genes kept from each arm:
  * from ControlLoop → the whole substrate: bound, convergence-by-re-observe, sealed trace.
  * from pr_opener   → the real actuation, AND fail-closed *with the error detail*
    captured (the loop still swallows-and-re-observes, but the operator gets the reason).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from automation.control_loop import ControlLoop, LoopResult, heal
from automation.pr_opener import open_pr


def remediate_via_pr(
    proposal: dict,
    *,
    opener: Callable = open_pr,
    repo_dir: Optional[Path] = None,
    runner=None,
    loop_kwargs: Optional[dict] = None,
) -> dict:
    """Open a fix PR for *proposal* as a ControlLoop; return the sealed result + pr_url.

    observe() == "does a reviewable PR exist yet?" (0.0 once opened, else 1.0);
    act()     == open the PR. Reaching error 0 (a PR exists) IS convergence — that matches
    the responder's `proposed: True == resolved-into-a-human-path` semantics. If the open
    keeps failing the loop fail-closes to `quarantine-escalate`, and the operator still gets
    the captured error, not just a red.
    """
    captured: dict = {}

    def observe() -> float:
        return 0.0 if captured.get("pr_url") else 1.0

    def act() -> None:
        kwargs = {"repo_dir": repo_dir}
        if runner is not None:
            kwargs["runner"] = runner
        try:
            captured["pr_url"] = opener(proposal, **kwargs)
        except Exception as exc:
            # Preserve the failure detail (pr_opener's gene) before letting the loop
            # swallow-and-re-observe (control_loop's gene): honest reason + fail-closed.
            captured["error"] = str(exc)
            raise

    kw = {"max_iterations": 2, "patience": 2, "target": 0.0,
          "safe_state": "quarantine-escalate", **(loop_kwargs or {})}
    result: LoopResult = ControlLoop(**kw).run(observe, act)

    sealed = result.to_json()           # carries trace + trace_hash (provenance)
    sealed["mode"] = "propose_pr"
    sealed["pr_url"] = captured.get("pr_url")
    if not result.converged:
        sealed["error"] = captured.get("error", "PR could not be opened")
        # make the safe state carry the artifact when we DID open something before stalling
        if captured.get("pr_url"):
            sealed["fail_closed_state"] = f"human-review:{captured['pr_url']}"
    return sealed


def remediate(
    beacon: dict,
    receipt: dict,
    *,
    executor_fn: Optional[Callable] = None,
    executor_paths: Optional[dict] = None,
    opener: Callable = open_pr,
    repo_dir: Optional[Path] = None,
    runner=None,
    loop_kwargs: Optional[dict] = None,
) -> dict:
    """Route a decided action to its remediation loop; always return a sealed result.

    - ``auto_fix``    → drive ``executor_fn`` under ControlLoop until the class invariant
      converges (verify-the-artifact healing).
    - ``propose_pr``  → open a reviewable fix PR as a ControlLoop (:func:`remediate_via_pr`).
    - anything else   → not an autonomous remediation; return a non-converged sealed result
      so the caller escalates. One shape for every path.
    """
    action = receipt.get("action")
    if action == "auto_fix" and executor_fn is not None:
        result = heal(beacon.get("kind_class", "unknown"), executor_fn,
                      executor_paths or {}, **(loop_kwargs or {}))
        sealed = result.to_json()
        sealed["mode"] = "auto_fix"
        return sealed
    if action == "propose_pr":
        return remediate_via_pr(beacon.get("proposal") or {}, opener=opener,
                                repo_dir=repo_dir, runner=runner, loop_kwargs=loop_kwargs)
    return {
        "converged": False, "mode": action or "unknown",
        "fail_closed_state": "escalate-human",
        "reason": f"action '{action}' is not an autonomous remediation",
    }
