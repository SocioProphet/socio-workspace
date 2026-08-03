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

# Ring-1 octonion safety axes; a plan touching any axis norm >= 1 may never auto-act.
BOUNDARY_AXES = (
    "legality", "containment", "provenance", "privacy",
    "performance", "reproducibility", "licensing", "governance",
)

# The LAW: the strongest verdict a failure CLASS is permitted to reach for auto-action.
# (A reversible re-sync may reach `sealed`; a cross-repo change caps at `weak`; a policy
# breach is never auto-fixed.)
LAW_BY_KIND: Dict[str, str] = {
    "mirror_drift": "sealed",
    "vendored_graph_drift": "sealed",  # reversible regenerate-from-source, like mirror_drift
    "build_failure": "probable",
    "stale_vendor": "weak",       # cross-repo: propose only, never auto-act
    "policy_violation": "quarantine",
    "unknown": "refuse",
}

# Verdict -> action.
VERDICT_ACTION: Dict[str, str] = {
    "sealed": "auto_fix",
    "probable": "canary_fix",
    "weak": "propose_pr",
    "quarantine": "quarantine",
    "refuse": "block",
}

IRI_BLOCK = 0.55  # Boundary SPEC block threshold

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


def boundary_breaches(beacon: dict) -> List[str]:
    plan = beacon.get("plan") or {}
    return [ax for ax in BOUNDARY_AXES if float(plan.get(ax, 0.0)) >= 1.0]


def _receipt(beacon: dict, *, verdict, action: str, reason: str) -> dict:
    """A decision receipt, addressed with a kernel SemanticAddress (warrant carried)."""
    addr = SemanticAddress(
        term=prim("SND"),  # Secondness: a brute event/fact
        iri=f"system://{beacon.get('system', 'unknown')}",
        inference="abduced",
        mood="assert",
        evidence_ref=beacon.get("evidence_ref"),
    )
    return {
        "beacon_kind": beacon.get("kind_class", "unknown"),
        "verdict": "BOTTOM" if verdict is BOTTOM else verdict,
        "action": action,
        "reason": reason,
        "address": addr.to_json(),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }


def decide(beacon: dict) -> dict:
    """boundary -> IRI -> meet(Law, Evidence) -> action. Fail-closed at every gate."""
    # 1. boundary fence (first, fail-closed)
    breached = boundary_breaches(beacon)
    if breached:
        return _receipt(beacon, verdict=BOTTOM, action="escalate_human",
                        reason=f"octonion boundary breached: {breached}")
    # 2. IRI gate
    iri = compute_iri(beacon)
    if iri >= IRI_BLOCK:
        return _receipt(beacon, verdict=BOTTOM, action="escalate_human",
                        reason=f"IRI {iri:.2f} >= block {IRI_BLOCK}")
    # 3. no evidence -> cannot decide -> human
    ev = evidence_verdict(beacon)
    if ev is None:
        return _receipt(beacon, verdict=BOTTOM, action="escalate_human",
                        reason="no evidence to assess (consent-hole)")
    # 4. the reasoned verdict: kernel meet of Law and Evidence
    law = LAW_BY_KIND.get(beacon.get("kind_class", "unknown"), "refuse")
    verdict = meet(law, ev)
    action = VERDICT_ACTION.get(verdict, "escalate_human")
    return _receipt(beacon, verdict=verdict, action=action,
                    reason=f"meet(law={law}, evidence={ev})={verdict}; IRI={iri:.2f}")


def _execute(beacon: dict, receipt: dict, executor_paths: Optional[dict]) -> None:
    """Carry out a decided action via a registered executor, recording the outcome.

    Dispatch: a class-specific (kind, action) executor first, else an action-level executor.
    Attaches `receipt["execution"]`. The situation is RESOLVED iff the executor healed the
    artifact or recorded a proposal; otherwise the decision is downgraded to a human
    escalation — an unverified fix, or an unfiled proposal, is not a resolution.
    """
    import inspect

    action = receipt.get("action")
    fn_name = EXECUTORS.get((beacon.get("kind_class"), action)) or ACTION_EXECUTORS.get(action)
    if not fn_name:
        return
    from automation import executors  # lazy: keeps yaml/engine import off the decision path
    fn = getattr(executors, fn_name)

    # Pass the beacon only to executors that accept it (e.g. propose_pr); reconcilers don't.
    kwargs = dict(executor_paths or {})
    if "beacon" in inspect.signature(fn).parameters:
        kwargs["beacon"] = beacon
    try:
        outcome = fn(**kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        outcome = {"executor": fn_name, "healed": False, "proposed": False, "error": str(exc)}

    receipt["execution"] = outcome
    resolved = bool(outcome.get("healed") or outcome.get("proposed"))
    if not resolved:
        receipt["action"] = "escalate_human"
        receipt["reason"] = f"{receipt.get('reason', '')} | executor '{fn_name}' did not resolve"


def run_once(inbox: Optional[DurableQueue] = None,
             decisions: Optional[DurableQueue] = None,
             *,
             execute: bool = False,
             executor_paths: Optional[dict] = None) -> List[dict]:
    """Drain the beacon inbox, decide each, emit decision receipts. Returns the receipts.

    With ``execute=True`` a decided auto_fix is carried out by its registered executor
    (verify-and-rollback); the daemon opts in, while pure decision paths stay side-effect
    free. ``executor_paths`` is forwarded to the executor (used by tests to target tmp dirs).
    """
    inbox = inbox if inbox is not None else DurableQueue(state_dir() / "beacons")
    decisions = decisions if decisions is not None else DurableQueue(state_dir() / "decisions")
    out: List[dict] = []
    while not inbox.empty():
        try:
            beacon = inbox.get_nowait()
        except Exception:
            break
        receipt = decide(beacon)
        if execute:
            _execute(beacon, receipt, executor_paths)
        decisions.put(receipt)
        out.append(receipt)
    return out
