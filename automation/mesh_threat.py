"""Adaptive, threat-aware mesh: resolve the threat HOLOGRAPHICALLY, then adapt the placement.

Two ideas, composed:

1. HOLOGRAPHIC AGGREGATION. No single vantage sees the true mesh state — a *partitioned* node
   believes the whole mesh is unreachable; a *compromised* one lies. So the mesh-wide threat
   signal is not read off any one node; it is RESOLVED from a quorum of per-vantage fragments,
   the way any k of n RS shards reconstruct a whole leaf. We use median/majority over the vantage
   reports, which is Byzantine-robust to a minority of lying or partitioned vantages — a lone node
   screaming "everything is down" is outvoted by the quorum that can still see each other.

2. ADAPTIVE, THREAT-AWARE PLACEMENT with a deliberate ASYMMETRY:
     * ESCALATE automatically and immediately — it is always safe to become MORE resilient, so a
       rising threat auto-applies the harder tier (no human in the loop to slow the response down).
     * DE-ESCALATE only under review, and only after sustained calm (a dwell window) — dropping
       resilience is the dangerous direction, and an adversary must not be able to induce a drop by
       faking calm. So a fall in threat is PROPOSED, never auto-applied.
     * FAIL TOWARD HOSTILE — if the vantages can't form a quorum (we're blind), assume the worst.

   The policy (thresholds, dwell, level->tier) is declared in registry/mesh-storage-placement.yaml
   so the adaptation RULE is itself governed, not buried in code.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY = _ROOT / "registry" / "mesh-storage-placement.yaml"

# Ordered threat levels (index = severity). tier mapping is in the policy.
LEVELS = ("calm", "elevated", "hostile")


def _rank(level: str) -> int:
    return LEVELS.index(level)


@dataclass(frozen=True)
class VantageReport:
    """What ONE node/vantage locally observes — inherently partial and possibly wrong."""
    vantage: str
    unreachable_fraction: float   # fraction of the mesh THIS node cannot reach
    anomalies_seen: int           # integrity anomalies this vantage witnessed
    partition_suspected: bool = False


@dataclass(frozen=True)
class ThreatSignals:
    """The mesh-wide signal, holographically resolved from a quorum of vantages."""
    unreachable_fraction: float
    anomalies: int
    partition: bool
    vantages: int                 # how many reports resolved this (0 = blind)


def aggregate_vantages(reports: Sequence[VantageReport], *, quorum: int) -> ThreatSignals:
    """Resolve the true mesh threat from partial vantage reports — Byzantine-robust.

    Fewer than ``quorum`` reports = we are effectively blind; returns a blind signal (vantages=0)
    which assess_threat treats as fail-closed (hostile). Otherwise: unreachable_fraction is the
    MEDIAN across vantages (a lone partitioned node reporting 1.0 cannot move it), anomalies is the
    median witnessed count (corroboration, not a single alarm), and partition is declared only when
    a MAJORITY of vantages suspect it (a local partition is not a mesh partition).
    """
    reports = list(reports)
    if len(reports) < quorum or not reports:
        return ThreatSignals(unreachable_fraction=1.0, anomalies=10 ** 9, partition=True, vantages=0)
    unreachable = statistics.median(r.unreachable_fraction for r in reports)
    anomalies = int(statistics.median(r.anomalies_seen for r in reports))
    partition = sum(1 for r in reports if r.partition_suspected) > len(reports) / 2
    return ThreatSignals(unreachable_fraction=unreachable, anomalies=anomalies,
                         partition=partition, vantages=len(reports))


# ── policy (declared in the registry) ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ThreatPolicy:
    tier_by_level: Dict[str, str]          # level -> placement tier name
    elevated_min_unreachable: float
    elevated_min_anomalies: int
    hostile_min_unreachable: float
    hostile_min_anomalies: int
    deescalate_dwell: int                  # consecutive calm epochs required to PROPOSE a drop


def load_threat_policy(path: Optional[Path] = None) -> ThreatPolicy:
    import yaml
    path = Path(path) if path is not None else _REGISTRY
    data = (yaml.safe_load(path.read_text("utf-8")) or {}).get("threat_policy") or {}
    tier_by_level = data.get("tier_by_level") or {}
    if set(tier_by_level) != set(LEVELS):
        raise ValueError(f"threat_policy.tier_by_level must map exactly {LEVELS}")
    esc = data.get("escalate_if") or {}
    return ThreatPolicy(
        tier_by_level=dict(tier_by_level),
        elevated_min_unreachable=float((esc.get("elevated") or {}).get("min_unreachable", 0.10)),
        elevated_min_anomalies=int((esc.get("elevated") or {}).get("min_anomalies", 1)),
        hostile_min_unreachable=float((esc.get("hostile") or {}).get("min_unreachable", 0.25)),
        hostile_min_anomalies=int((esc.get("hostile") or {}).get("min_anomalies", 3)),
        deescalate_dwell=int(data.get("deescalate_dwell", 6)),
    )


def _raw_level(signals: ThreatSignals, policy: ThreatPolicy) -> str:
    if signals.vantages == 0:
        return "hostile"                    # blind -> fail toward hostile
    if (signals.partition
            or signals.unreachable_fraction >= policy.hostile_min_unreachable
            or signals.anomalies >= policy.hostile_min_anomalies):
        return "hostile"
    if (signals.unreachable_fraction >= policy.elevated_min_unreachable
            or signals.anomalies >= policy.elevated_min_anomalies):
        return "elevated"
    return "calm"


@dataclass(frozen=True)
class ThreatAssessment:
    level: str                              # the EFFECTIVE level now in force (never auto-dropped)
    tier: str                               # placement tier to apply now
    actuation: str                          # auto_escalate | hold | propose_deescalate
    proposed_level: Optional[str] = None    # a lower level to PROPOSE (reviewed), if dwell met
    proposed_tier: Optional[str] = None
    reasons: tuple = field(default=())


def assess_threat(signals: ThreatSignals, *, previous_level: str, calm_dwell: int,
                  policy: ThreatPolicy) -> ThreatAssessment:
    """Decide the effective level + tier with the escalate-fast / de-escalate-slow asymmetry.

    ``calm_dwell`` is how many consecutive epochs the raw level has sat BELOW ``previous_level``.
    Escalation is automatic (safe); de-escalation is only PROPOSED, and only once dwell is met.
    """
    raw = _raw_level(signals, policy)
    reasons: List[str] = [f"raw={raw} (unreachable={signals.unreachable_fraction:.2f}, "
                          f"anomalies={signals.anomalies}, partition={signals.partition}, "
                          f"vantages={signals.vantages})"]

    if _rank(raw) > _rank(previous_level):
        reasons.append(f"ESCALATE {previous_level}->{raw} (auto: more resilience is always safe)")
        return ThreatAssessment(level=raw, tier=policy.tier_by_level[raw],
                                actuation="auto_escalate", reasons=tuple(reasons))

    if _rank(raw) < _rank(previous_level):
        if calm_dwell >= policy.deescalate_dwell:
            reasons.append(f"PROPOSE de-escalate {previous_level}->{raw} "
                           f"(calm {calm_dwell}>={policy.deescalate_dwell} epochs; reviewed)")
            return ThreatAssessment(level=previous_level, tier=policy.tier_by_level[previous_level],
                                    actuation="propose_deescalate", proposed_level=raw,
                                    proposed_tier=policy.tier_by_level[raw], reasons=tuple(reasons))
        reasons.append(f"HOLD {previous_level} (calm only {calm_dwell}<{policy.deescalate_dwell} "
                       f"epochs — do not drop resilience yet)")
        return ThreatAssessment(level=previous_level, tier=policy.tier_by_level[previous_level],
                                actuation="hold", reasons=tuple(reasons))

    return ThreatAssessment(level=previous_level, tier=policy.tier_by_level[previous_level],
                            actuation="hold", reasons=tuple(reasons))


# ── risk/reward tier selection — the Economic Prophet money-flow framing ─────────────────────
#
# Threshold tiers are a coarse control. The finer one is economic: storage overhead is CAPITAL,
# the threat is RISK, and resilience "capital" should flow to the tier with the best risk-adjusted
# return — survival of valuable state. This is exactly the Economic Prophet position-sizing frame,
# a digital parallel of money flow: expected value = V·P(survive | threat) − cost(overhead), and
# you allocate to argmax. Under high threat P(survive) dominates -> spend (buy resilience); under
# calm the cost term dominates -> harvest efficiency (cheap tier). Same asymmetry as risk
# management: over-hedging is cheap, under-hedging is ruin — so ties break toward MORE resilience.

@dataclass(frozen=True)
class TierChoice:
    tier: str
    expected_value: float
    p_survive: float
    cost: float
    overhead: float


def optimal_tier(placements: Dict[str, "object"], *, threat_frac: float, value_of_state: float,
                 unit_storage_cost: float) -> "tuple":
    """Pick the placement tier that maximizes risk-adjusted expected value at ``threat_frac``.

    ``placements`` maps tier name -> Placement (each exposes survival_probability + durability_
    overhead). Returns ``(best_tier_name, [TierChoice ranked])``. EV = V·P(survive) − overhead·unit
    cost. Ties (within 1e-9) break toward the HIGHER overhead — over-provisioning resilience is the
    cheap mistake, under-provisioning is the ruinous one (loss aversion, made mechanical)."""
    ranked: List[TierChoice] = []
    for name, place in placements.items():
        p = place.survival_probability(threat_frac)
        overhead = place.durability_overhead
        cost = overhead * unit_storage_cost
        ranked.append(TierChoice(tier=name, expected_value=value_of_state * p - cost,
                                 p_survive=p, cost=cost, overhead=overhead))
    # sort by EV desc, then by OVERHEAD desc: a tie in expected value breaks toward more resilience
    # (over-provisioning is the cheap mistake, under-provisioning the ruinous one — loss aversion).
    ranked.sort(key=lambda c: (c.expected_value, c.overhead), reverse=True)
    return ranked[0].tier, ranked
