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


# Evidence strength as an additive weight on the verdict lattice — the quantized form of the
# graph-brain MLN's real-valued implication weight (Result A). Composition is summing these.
_EVIDENCE_WEIGHT = {"weak": 1, "probable": 2, "sealed": 3}


def compose_evidence(beacons: List[dict]) -> Optional[str]:
    """Compose multiple detector signals about ONE subject into a single evidence verdict.

    Additive on the lattice (the MLN's "weak detectors compose": three weak signals reach
    sealed-strength where none would alone), capped at sealed. None = no beacon carried a
    warrant. This is the evidence-composition the per-beacon model lacked.
    """
    total = sum(_EVIDENCE_WEIGHT.get(evidence_verdict(b), 0) for b in beacons)
    if total <= 0:
        return None
    if total >= 3:
        return "sealed"
    if total == 2:
        return "probable"
    return "weak"


def effective_law(beacons: List[dict], policy: ResponsePolicy) -> str:
    """The Law ceiling for a subject = the MOST RESTRICTIVE Law among the kinds present.

    `meet` is the lattice-min, so a subject that is both mirror_drift (sealed) and
    policy_violation (quarantine) may never rise above quarantine. Fail-closed and
    contradiction-tolerant: a strong class cannot license auto-acting on a subject a stricter
    class fences — the composition analogue of "one detector cannot nuke a well-grounded claim".
    """
    laws = [policy.law_for(b.get("kind_class", "unknown")) for b in beacons]
    return meet(*laws) if laws else policy.default_law


def _compose_receipt(primary: dict, beacons: List[dict], *, verdict, action: str, reason: str) -> dict:
    from automation import envelope

    receipt = _receipt(primary, verdict=verdict, action=action, reason=reason)
    if len(beacons) > 1:
        receipt["composed_from"] = [
            {"kind_class": b.get("kind_class"), "system": b.get("system"),
             "evidence": evidence_verdict(b)} for b in beacons
        ]
        receipt["n_signals"] = len(beacons)
    # The receipt IS the estate's ProofArtifact: stamp the canonical envelope (propagating the
    # beacon's trace_id) and grade it on the EpistemicLevel scale. Re-graded after execution.
    receipt = envelope.stamp(receipt, trace_id=primary.get("trace_id"))
    receipt["epistemic_level"] = envelope.epistemic_level_for(receipt)
    return receipt


def decide_composed(beacons: List[dict], *, policy: Optional[ResponsePolicy] = None) -> dict:
    """Decide ONE subject over its COMPOSED evidence: boundary -> IRI -> meet(Law, ΣEvidence).

    The subject's signals are gathered, composed, and thresholded once — the MAP-threshold
    model of the MLN integration layer, quantized to the kernel's verdict lattice. Fail-closed
    at every gate (any beacon's boundary breach or max-IRI escalates the whole subject).
    A single-beacon subject reduces exactly to the old per-beacon `decide`.
    """
    policy = policy or DEFAULT_POLICY
    primary = max(beacons, key=lambda b: _EVIDENCE_WEIGHT.get(evidence_verdict(b), 0)) if beacons else {}

    # 1. boundary fence (union, fail-closed)
    breached = sorted({ax for b in beacons for ax in boundary_breaches(b, policy.boundary_axes)})
    if breached:
        return _compose_receipt(primary, beacons, verdict=BOTTOM, action="escalate_human",
                                reason=f"octonion boundary breached: {breached}")
    # 2. IRI gate (max across signals, fail-closed)
    iri = max((compute_iri(b) for b in beacons), default=0.0)
    if iri >= policy.iri_block:
        return _compose_receipt(primary, beacons, verdict=BOTTOM, action="escalate_human",
                                reason=f"IRI {iri:.2f} >= block {policy.iri_block}")
    # 3. composed evidence (no warrant anywhere -> BOTTOM -> human)
    ev = compose_evidence(beacons)
    if ev is None:
        return _compose_receipt(primary, beacons, verdict=BOTTOM, action="escalate_human",
                                reason="no evidence to assess (consent-hole)")
    # 4. the reasoned verdict: kernel meet of the effective Law and the composed Evidence
    law = effective_law(beacons, policy)
    verdict = meet(law, ev)
    action = policy.action_for(verdict)
    reason = f"meet(law={law}, evidence={ev})={verdict}; IRI={iri:.2f}"
    if len(beacons) > 1:
        kinds = sorted({b.get("kind_class", "unknown") for b in beacons})
        reason += f"; composed {len(beacons)} signals over {kinds}"
    return _compose_receipt(primary, beacons, verdict=verdict, action=action, reason=reason)


def decide(beacon: dict, *, policy: Optional[ResponsePolicy] = None) -> dict:
    """Decide a single beacon. Thin wrapper over `decide_composed` (a subject of one signal)."""
    return decide_composed([beacon], policy=policy)


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
    # Resolved iff the executor healed the artifact, filed a proposal, or quarantined the
    # subject. Anything else (a failed canary, a proposal with nothing to file, a subjectless
    # quarantine) is unresolved and escalates — no decision silently dead-ends.
    resolved = bool(outcome.get("healed") or outcome.get("proposed") or outcome.get("quarantined"))
    if not resolved:
        receipt["action"] = "escalate_human"
        receipt["reason"] = f"{receipt.get('reason', '')} | executor '{fn_name}' did not resolve"
    # Re-grade the EpistemicLevel now that we know the outcome (healed→proved, rolled_back→rejected…).
    from automation import envelope
    receipt["epistemic_level"] = envelope.epistemic_level_for(receipt)


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
    from collections import OrderedDict

    from automation.suppression import fingerprint

    active_policy = policy or DEFAULT_POLICY
    inbox = inbox if inbox is not None else DurableQueue(state_dir() / "beacons")
    decisions = decisions if decisions is not None else DurableQueue(state_dir() / "decisions")

    # 1. Drain and suppress-filter (a condition decided within the cooldown is skipped).
    survivors: List[dict] = []
    while not inbox.empty():
        try:
            beacon = inbox.get_nowait()
        except Exception:
            break
        if suppressor is not None and not suppressor.should_process(
            fingerprint(beacon), cooldown_seconds=active_policy.suppression_cooldown_seconds
        ):
            continue
        survivors.append(beacon)

    # 2. Group by SUBJECT so multiple signals about one thing compose into one decision.
    groups: "OrderedDict[str, List[dict]]" = OrderedDict()
    for beacon in survivors:
        groups.setdefault(str(beacon.get("system", "unknown")), []).append(beacon)

    # 3. Decide once per subject over the composed evidence; execute via the primary signal.
    out: List[dict] = []
    for group in groups.values():
        receipt = decide_composed(group, policy=active_policy)
        if execute:
            primary = max(group, key=lambda b: _EVIDENCE_WEIGHT.get(evidence_verdict(b), 0))
            _execute(primary, receipt, executor_paths)
        decisions.put(receipt)
        out.append(receipt)
    return out
