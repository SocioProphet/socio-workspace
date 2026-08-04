"""The reasoned responder — the first real consumer of the semantic kernel.

Tier 1 made the loop run and honest, but left it open: detectors emit beacons that nobody
acts on. This closes the loop. It drains the beacon inbox (`state/beacons/`, filled by the
scheduler's `observe_and_beacon`) and, for each beacon, decides fix / alert / escalate /
withhold by REASONING with the vendored `procyber.semantic` kernel — not static rules:

    boundary fence  ->  IRI gate  ->  meet(Law, Evidence)  ->  action

- Boundary fence (Ring-1 octonion axes): any plan touching an axis norm >= 1 is force-
  escalated, never auto-executed.
- IRI gate (Boundary SPEC): identity-risk above the block threshold escalates regardless.
- Verdict = kernel `meet(law, evidence)` on the lattice
  {refuse < quarantine < weak < probable < sealed}. The meet cannot exceed either arm.
- Action = verdict -> {auto_fix | canary_fix | propose_pr | quarantine | block}.
- Unresolvable (no evidence / boundary breach / high IRI) -> kernel `BOTTOM` -> human queue
  (the consent-hole).

It imports the VENDORED kernel (`third_party/`, pinned by `third_party/procyber/VENDOR.json`).
If the kernel is absent or drifts, this consumer fails loudly — that is the integration
contract, and the cross-repo integration test enforces it.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

# --- make the vendored kernel importable ------------------------------------
_VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "third_party")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from procyber.semantic import BOTTOM, SemanticAddress, meet, prim  # vendored kernel

from automation.durable_queue import DurableQueue, state_dir

# Decision governance is a declared, overridable policy with an opinionated default
# (automation/policy.py + registry/self-heal-policy.yaml). These module-level names remain as
# read-only views onto the default policy for back-compat and quick reference; the live
# decision reads whatever ResponsePolicy is passed to `decide`/`run_once` (default: DEFAULT_POLICY).
from automation.policy import DEFAULT_POLICY, ResponsePolicy  # noqa: E402

BOUNDARY_AXES = DEFAULT_POLICY.boundary_axes
LAW_BY_KIND: Dict[str, str] = DEFAULT_POLICY.law_by_kind
VERDICT_ACTION: Dict[str, str] = DEFAULT_POLICY.verdict_action
IRI_BLOCK = DEFAULT_POLICY.iri_block

# (failure class, decided action) -> executor function name in automation.executors.
# Only wired for verified-safe, idempotent, roll-back-capable remediations.
EXECUTORS = {
    ("mirror_drift", "auto_fix"): "resync_mirror_drift",
    ("vendored_graph_drift", "auto_fix"): "reconcile_vendored_graph",
}

# Action-level executors are class-agnostic: any beacon decided to this action routes here
# (used when no class-specific (kind, action) executor is registered). propose_pr records a
# reviewable PR proposal for any class the responder caps at propose_pr.
ACTION_EXECUTORS = {
    "propose_pr": "propose_pr",
    "canary_fix": "canary_fix",   # canary the mechanism, then apply; escalate if unproven
    "quarantine": "quarantine",   # isolate + record; never auto-fix a policy breach
}


def evidence_verdict(beacon: dict) -> Optional[str]:
    """Map the beacon's warrant strength to a verdict ceiling; None means no evidence."""
    w = beacon.get("evidence") or {}
    if w.get("detector") and w.get("reproducible") and not w.get("stale"):
        return "sealed"
    if w.get("detector"):
        return "probable"
    if w.get("signal"):
        return "weak"
    return None  # no evidence -> cannot assess -> BOTTOM (consent-hole)


def compute_iri(beacon: dict) -> float:
    """IRI = alpha*EntropyUniqueness + beta*InjectionNormativity - gamma*ConsentCredits."""
    e = float(beacon.get("entropy_uniqueness", 0.0))
    inj = float(beacon.get("injection_normativity", 0.0))
    cc = float(beacon.get("consent_credits", 0.0))
    return max(0.0, 0.45 * e + 0.45 * inj - 0.20 * cc)


def boundary_breaches(beacon: dict, axes: Optional[tuple] = None) -> List[str]:
    plan = beacon.get("plan") or {}
    return [ax for ax in (axes or BOUNDARY_AXES) if float(plan.get(ax, 0.0)) >= 1.0]


def _receipt(beacon: dict, *, verdict, action: str, reason: str) -> dict:
    """A decision receipt, addressed with a kernel SemanticAddress (warrant carried)."""
    addr = SemanticAddress(
        term=prim("SND"),  # Secondness: a brute event/fact
        iri=f"system://{beacon.get('system', 'unknown')}",
        inference="abduced",
        mood="assert",
        evidence_ref=beacon.get("evidence_ref"),
    )
    receipt = {
        "beacon_kind": beacon.get("kind_class", "unknown"),
        "verdict": "BOTTOM" if verdict is BOTTOM else verdict,
        "action": action,
        "reason": reason,
        "address": addr.to_json(),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    # Carry the beacon's detail so an escalation is actionable (e.g. which vendored
    # dependency is stale, by how much) without re-reading the consumed beacon.
    if beacon.get("detail") is not None:
        receipt["detail"] = beacon["detail"]
    return receipt


def decide(beacon: dict, *, policy: Optional[ResponsePolicy] = None) -> dict:
    """boundary -> IRI -> meet(Law, Evidence) -> action. Fail-closed at every gate.

    Governed by `policy` (default: the opinionated DEFAULT_POLICY). Pass a loaded policy to
    have the declared governance (registry/self-heal-policy.yaml) drive the decision.
    """
    policy = policy or DEFAULT_POLICY
    # 1. boundary fence (first, fail-closed)
    breached = boundary_breaches(beacon, policy.boundary_axes)
    if breached:
        return _receipt(beacon, verdict=BOTTOM, action="escalate_human",
                        reason=f"octonion boundary breached: {breached}")
    # 2. IRI gate
    iri = compute_iri(beacon)
    if iri >= policy.iri_block:
        return _receipt(beacon, verdict=BOTTOM, action="escalate_human",
                        reason=f"IRI {iri:.2f} >= block {policy.iri_block}")
    # 3. no evidence -> cannot decide -> human
    ev = evidence_verdict(beacon)
    if ev is None:
        return _receipt(beacon, verdict=BOTTOM, action="escalate_human",
                        reason="no evidence to assess (consent-hole)")
    # 4. the reasoned verdict: kernel meet of Law and Evidence
    law = policy.law_for(beacon.get("kind_class", "unknown"))
    verdict = meet(law, ev)
    action = policy.action_for(verdict)
    return _receipt(beacon, verdict=verdict, action=action,
                    reason=f"meet(law={law}, evidence={ev})={verdict}; IRI={iri:.2f}")


def _execute(beacon: dict, receipt: dict, executor_paths: Optional[dict]) -> None:
    """Carry out a decided action via a registered executor, recording the outcome.

    Dispatch: a class-specific (kind, action) executor first, else an action-level executor.
    Attaches `receipt["execution"]`. The situation is RESOLVED iff the executor healed the
    artifact or recorded a proposal; otherwise the decision is downgraded to a human
    escalation — an unverified fix, or an unfiled proposal, is not a resolution.

    A class-specific ``auto_fix`` whose kind_class has a registered convergence invariant
    (`automation.control_loop.INVARIANTS`; today only `mirror_drift`) is driven through
    `automation.self_heal.remediate()` — the ControlLoop closes the loop: RE-OBSERVE after
    acting, keep acting until the invariant holds or the loop fails closed to
    `quarantine-escalate` — instead of firing the executor once and trusting its return value.
    Everything else (canary_fix, quarantine, propose_pr-record, and any auto_fix class with no
    registered invariant such as `vendored_graph_drift`) keeps the existing single-shot call:
    those already have their own bounded mechanism (canary-then-apply, isolate-once,
    record-only) or, for an unregistered invariant, ControlLoop cannot verify convergence
    anyway (`heal()` would immediately fail-closed) — so routing them through it would only
    add a fail-closed detour, not a real closed loop.
    """
    import inspect

    action = receipt.get("action")
    kind_class = beacon.get("kind_class")
    fn_name = EXECUTORS.get((kind_class, action)) or ACTION_EXECUTORS.get(action)
    if not fn_name:
        return
    from automation import executors  # lazy: keeps yaml/engine import off the decision path
    fn = getattr(executors, fn_name)

    # Pass the beacon only to executors that accept it (e.g. propose_pr); reconcilers don't.
    kwargs = dict(executor_paths or {})
    if "beacon" in inspect.signature(fn).parameters:
        kwargs["beacon"] = beacon

    from automation.control_loop import INVARIANTS

    is_class_auto_fix = (kind_class, action) in EXECUTORS and action == "auto_fix"
    if is_class_auto_fix and kind_class in INVARIANTS:
        # Closed-loop path: heal() re-observes the invariant after each act() and only
        # stops on convergence or a bounded, fail-closed give-up. The default deadline
        # (30s) and max_iterations (5) comfortably fit inside the responder's 1-minute
        # scheduler interval (automation/scheduler.py `_register_jobs`, job id
        # "responder"), so no per-call override is needed here.
        from automation.self_heal import remediate

        outcome = remediate(beacon, receipt, executor_fn=fn, executor_paths=kwargs)
        outcome.setdefault("executor", fn_name)
        # Back-compat / uniform resolution signal alongside the sealed LoopResult fields
        # (converged, iterations, trace, trace_hash, fail_closed_state, reason) that
        # `remediate()` already attaches — the receipt keeps recording the full trace.
        outcome["healed"] = bool(outcome.get("converged"))
    else:
        try:
            outcome = fn(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            outcome = {"executor": fn_name, "healed": False, "proposed": False, "error": str(exc)}

    receipt["execution"] = outcome
    # Resolved iff the executor healed the artifact, filed a proposal, or quarantined the
    # subject. Anything else (a failed canary, a proposal with nothing to file, a subjectless
    # quarantine, or a control loop that never converged) is unresolved and escalates — no
    # decision silently dead-ends.
    resolved = bool(outcome.get("healed") or outcome.get("proposed") or outcome.get("quarantined"))
    if not resolved:
        receipt["action"] = "escalate_human"
        receipt["reason"] = f"{receipt.get('reason', '')} | executor '{fn_name}' did not resolve"


def run_once(inbox: Optional[DurableQueue] = None,
             decisions: Optional[DurableQueue] = None,
             *,
             execute: bool = False,
             executor_paths: Optional[dict] = None,
             policy: Optional[ResponsePolicy] = None,
             suppressor=None) -> List[dict]:
    """Drain the beacon inbox, decide each, emit decision receipts. Returns the receipts.

    With ``execute=True`` a decided auto_fix is carried out by its registered executor
    (verify-and-rollback); the daemon opts in, while pure decision paths stay side-effect
    free. ``executor_paths`` is forwarded to the executor (used by tests to target tmp dirs).
    ``policy`` governs the decision (default: the opinionated DEFAULT_POLICY). When a
    ``suppressor`` is provided, a condition already decided within the policy cooldown is
    skipped, so a persistent (e.g. cross-repo) failure is not re-escalated every cycle.
    """
    from automation.suppression import fingerprint

    active_policy = policy or DEFAULT_POLICY
    inbox = inbox if inbox is not None else DurableQueue(state_dir() / "beacons")
    decisions = decisions if decisions is not None else DurableQueue(state_dir() / "decisions")
    out: List[dict] = []
    while not inbox.empty():
        try:
            beacon = inbox.get_nowait()
        except Exception:
            break
        if suppressor is not None and not suppressor.should_process(
            fingerprint(beacon), cooldown_seconds=active_policy.suppression_cooldown_seconds
        ):
            continue  # this condition was decided within the cooldown window
        receipt = decide(beacon, policy=active_policy)
        if execute:
            _execute(beacon, receipt, executor_paths)
        decisions.put(receipt)
        out.append(receipt)
    return out
