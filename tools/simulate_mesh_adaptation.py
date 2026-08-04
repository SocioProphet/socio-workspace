#!/usr/bin/env python3
"""Simulate the adaptive, threat-aware mesh over a threat TIMELINE.

Ties three ideas into one loop: per-vantage reports are aggregated HOLOGRAPHICALLY (robust to a
lying/partitioned few); the resolved signal drives an ADAPTIVE tier with escalate-fast /
de-escalate-slow asymmetry; and a risk/reward optimizer prices each tier as an ECONOMIC
allocation (the Economic Prophet money-flow parallel — storage capital flows to where it earns the
best risk-adjusted return). The timeline: calm -> an attack ramps (seizure + partition) -> subsides.

Run: python3 tools/simulate_mesh_adaptation.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.mesh_threat import (  # noqa: E402
    VantageReport, aggregate_vantages, assess_threat, load_threat_policy, optimal_tier,
)
from automation.storage_placement import load_all  # noqa: E402

# A scripted true threat fraction per epoch: calm, a rising attack, seizure+partition, then decay.
TRUE_THREAT = [0.02, 0.03, 0.02, 0.12, 0.28, 0.35, 0.30, 0.20,
               0.08, 0.05, 0.04, 0.03, 0.02, 0.02, 0.02, 0.02]
PARTITION_EPOCHS = {4, 5}  # a real network partition during the peak


def _vantage_reports(true_frac, partition, rng, n=5):
    """5 noisy vantages; one is a compromised/partitioned liar every epoch (Byzantine minority)."""
    reports = []
    for i in range(n - 1):
        reports.append(VantageReport(
            f"m{i}",
            max(0.0, true_frac + rng.uniform(-0.03, 0.03)),
            1 if (rng.random() < true_frac) else 0,
            partition and rng.random() < 0.8,
        ))
    reports.append(VantageReport("liar", 1.0, 99, True))  # always screams "all down"
    return reports


def report():
    rng = random.Random(2026)
    pol = load_threat_policy()
    places = load_all()
    V, unit = 1000.0, 1.0

    print("=" * 92)
    print("ADAPTIVE THREAT-AWARE MESH — holographic resolve -> adaptive tier -> economic optimum")
    print("=" * 92)
    print(f"{'ep':>3} {'true':>5} {'resolved':>9} {'part':>5} {'lvl':>8} {'tier(adaptive)':>15} "
          f"{'actuation':>17} {'tier(economic)':>15}")

    level, calm_dwell = "calm", 0
    for ep, true_frac in enumerate(TRUE_THREAT):
        partition = ep in PARTITION_EPOCHS
        sig = aggregate_vantages(_vantage_reports(true_frac, partition, rng), quorum=3)

        a = assess_threat(sig, previous_level=level, calm_dwell=calm_dwell, policy=pol)
        # track dwell: raw below current level increments calm streak, else resets
        from automation.mesh_threat import _raw_level, _rank
        raw = _raw_level(sig, pol)
        calm_dwell = calm_dwell + 1 if _rank(raw) < _rank(a.level) else 0
        level = a.proposed_level if a.actuation == "propose_deescalate" else a.level

        econ, _ = optimal_tier(places, threat_frac=sig.unreachable_fraction,
                               value_of_state=V, unit_storage_cost=unit)
        act = a.actuation + ("" if not a.proposed_level else f"->{a.proposed_level}")
        print(f"{ep:>3} {true_frac:>5.2f} {sig.unreachable_fraction:>9.2f} "
              f"{str(sig.partition):>5} {a.level:>8} {a.tier:>15} {act:>17} {econ:>15}")

    print("-" * 92)
    print("read it: the liar is outvoted every epoch (resolved ~ true). Tier ESCALATES the moment")
    print("the attack crosses threshold and HOLDS through the peak; once calm returns it does NOT")
    print("drop immediately — it waits the dwell, then PROPOSES a de-escalation (reviewed). The")
    print("economic column shows the same money-flow: capital into resilience as risk rises, out as")
    print("it clears — one risk/reward controller, the Economic Prophet framework over storage.")
    print("=" * 92)


if __name__ == "__main__":
    report()
