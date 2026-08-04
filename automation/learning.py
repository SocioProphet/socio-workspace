"""Learning loop: turn the receipt stream into governed policy RECOMMENDATIONS.

The self-heal loop now produces a real receipt stream (state/decisions). This closes the loop
onto the kernel's own verdict lattice: it observes, per failure CLASS, how often the executor
actually resolved vs. failed, and — when a class's fixes are not verifying with enough evidence
— recommends DEMOTING its Law one step DOWN the lattice
(`sealed -> probable -> weak -> quarantine -> refuse`), so a class that cannot heal cleanly
stops auto-acting and starts proposing / escalating.

It learns in the SAFE direction only: it never recommends promoting a class (more autonomy),
and it never mutates governance itself. Recommendations are written durably and logged for a
human to apply by editing `registry/self-heal-policy.yaml` — the same declared, drift-guarded
policy the responder reads. Governance stays human-owned; learning just proposes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from automation.durable_queue import DurableQueue, state_dir
from automation.policy import VERDICTS, ResponsePolicy, load_policy

DEFAULT_MIN_SAMPLES = 10          # need enough attempts before recommending a change
DEFAULT_FAILURE_THRESHOLD = 0.5   # demote when >= half of attempts did not resolve


def _demote(law: str) -> Optional[str]:
    """One step DOWN the verdict lattice, or None if already at the floor (refuse)."""
    try:
        idx = VERDICTS.index(law)
    except ValueError:
        return None
    return VERDICTS[idx - 1] if idx > 0 else None


def _outcomes_by_kind(decisions: List[dict]) -> dict:
    """Per class: attempts (an executor ran) and failures (it did not resolve)."""
    stats: dict = {}
    for r in decisions:
        ex = r.get("execution")
        if not ex:
            continue  # no executor ran (pure decision) — not an outcome to learn from
        kind = str(r.get("beacon_kind", "unknown"))
        s = stats.setdefault(kind, {"attempts": 0, "failures": 0})
        s["attempts"] += 1
        if not (ex.get("healed") or ex.get("proposed") or ex.get("quarantined")):
            s["failures"] += 1
    return stats


def analyze(state: Optional[Path] = None, *, policy: Optional[ResponsePolicy] = None,
            min_samples: int = DEFAULT_MIN_SAMPLES,
            failure_threshold: float = DEFAULT_FAILURE_THRESHOLD) -> List[dict]:
    """Return safe demotion recommendations from the receipt stream. Does not mutate anything."""
    root = Path(state) if state is not None else state_dir()
    policy = policy or load_policy()
    decisions = DurableQueue(root / "decisions").peek_all()
    stats = _outcomes_by_kind(decisions)

    recs: List[dict] = []
    for kind, s in sorted(stats.items()):
        attempts, failures = s["attempts"], s["failures"]
        if attempts < min_samples:
            continue
        rate = failures / attempts
        if rate < failure_threshold:
            continue
        current = policy.law_for(kind)
        recommended = _demote(current)
        if recommended is None or recommended == current:
            continue  # already at the floor — nothing safe to recommend
        recs.append({
            "kind_class": kind,
            "current_law": current,
            "recommended_law": recommended,
            "attempts": attempts,
            "failures": failures,
            "failure_rate": round(rate, 3),
            "rationale": (
                f"{failures}/{attempts} ({rate:.0%}) of {kind} remediations did not resolve; "
                f"demote Law {current} -> {recommended} so it proposes/escalates instead of auto-acting"
            ),
            "apply": f"edit registry/self-heal-policy.yaml: law_by_kind.{kind}: {recommended}",
            "recommended_at": datetime.now(timezone.utc).isoformat(),
        })
    return recs


def run_once(state: Optional[Path] = None, **kw) -> List[dict]:
    """Analyze and durably record recommendations (for a human / the policy owner)."""
    root = Path(state) if state is not None else state_dir()
    recs = analyze(root, **kw)
    if recs:
        sink = DurableQueue(root / "policy-recommendations")
        for rec in recs:
            sink.put(rec)
    return recs


def main(argv: Optional[List[str]] = None) -> int:
    recs = analyze()
    for rec in recs:
        print(f"RECOMMEND demote {rec['kind_class']}: {rec['current_law']} -> "
              f"{rec['recommended_law']} ({rec['failure_rate']:.0%} of {rec['attempts']} failed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
