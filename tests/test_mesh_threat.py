"""Tests for the adaptive, threat-aware mesh: holographic aggregation + escalate/de-escalate
asymmetry + the risk/reward (Economic Prophet) tier optimizer."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.mesh_threat import (  # noqa: E402
    ThreatSignals, VantageReport, aggregate_vantages, assess_threat, load_threat_policy,
    optimal_tier,
)
from automation.storage_placement import load_all  # noqa: E402
from automation.storage_resilience import Placement  # noqa: E402

POL = load_threat_policy()


# ── holographic aggregation ──────────────────────────────────────────────────────────────────

def test_median_outvotes_a_lying_partitioned_vantage():
    reports = [VantageReport(f"m{i}", 0.05, 0, False) for i in range(4)]
    reports.append(VantageReport("liar", 1.0, 50, True))  # one node screaming "all down"
    sig = aggregate_vantages(reports, quorum=3)
    assert sig.unreachable_fraction == 0.05 and sig.anomalies == 0 and not sig.partition


def test_majority_partition_is_believed():
    reports = [VantageReport(f"m{i}", 0.3, 0, True) for i in range(3)]
    assert aggregate_vantages(reports, quorum=3).partition


def test_below_quorum_is_blind_failclosed():
    sig = aggregate_vantages([VantageReport("m0", 0.0, 0, False)], quorum=3)
    assert sig.vantages == 0  # blind -> assess_threat will treat as hostile


# ── escalate-fast / de-escalate-slow asymmetry ────────────────────────────────────────────────

def _sig(unreachable=0.0, anomalies=0, partition=False, vantages=3):
    return ThreatSignals(unreachable, anomalies, partition, vantages)


def test_escalation_is_automatic():
    a = assess_threat(_sig(unreachable=0.3, anomalies=4), previous_level="calm", calm_dwell=0, policy=POL)
    assert a.level == "hostile" and a.actuation == "auto_escalate" and a.tier == "hostile"


def test_deescalation_holds_until_dwell():
    # calm signal but we were hostile; not enough calm epochs yet -> HOLD hostile
    a = assess_threat(_sig(), previous_level="hostile", calm_dwell=2, policy=POL)
    assert a.level == "hostile" and a.actuation == "hold"


def test_deescalation_is_proposed_after_dwell():
    a = assess_threat(_sig(), previous_level="hostile", calm_dwell=POL.deescalate_dwell, policy=POL)
    assert a.actuation == "propose_deescalate" and a.proposed_level == "calm"
    assert a.level == "hostile"  # still hostile until the proposal is reviewed


def test_blind_signal_fails_toward_hostile():
    a = assess_threat(_sig(vantages=0), previous_level="calm", calm_dwell=0, policy=POL)
    assert a.level == "hostile" and a.actuation == "auto_escalate"


# ── risk/reward economic optimizer ────────────────────────────────────────────────────────────

def test_high_threat_allocates_to_hostile_tier():
    best, _ = optimal_tier(load_all(), threat_frac=0.5, value_of_state=1000, unit_storage_cost=1.0)
    assert best == "hostile"


def test_calm_threat_does_not_overspend_when_state_is_cheap():
    # when the state is cheap relative to storage cost, the optimizer harvests efficiency
    best, _ = optimal_tier(load_all(), threat_frac=0.02, value_of_state=5, unit_storage_cost=1.0)
    assert best == "baseline"


def test_tie_breaks_toward_more_resilience():
    # two tiers with identical survival at this threat -> the optimizer prefers the safer (costlier)
    a = Placement(rs_k=3, rs_m=3, shard_replicas=1)   # n=6
    b = Placement(rs_k=3, rs_m=3, shard_replicas=2)   # n=6, R=2 -> higher survival, higher cost
    best, ranked = optimal_tier({"lo": a, "hi": b}, threat_frac=0.0,
                                value_of_state=1000, unit_storage_cost=0.0)  # zero cost -> tie on EV
    assert best == "hi"  # equal EV at zero cost, break toward more resilience


def test_survival_probability_monotone():
    p = Placement(rs_k=6, rs_m=3, shard_replicas=1)
    assert p.survival_probability(0.0) == 1.0
    assert p.survival_probability(0.1) > p.survival_probability(0.4)
    # replication raises survival at a fixed threat
    hostile = Placement(rs_k=6, rs_m=3, shard_replicas=2)
    assert hostile.survival_probability(0.4) > p.survival_probability(0.4)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"mesh_threat: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
