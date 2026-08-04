#!/usr/bin/env python3
"""Simulate the fractal triad-of-triads rotation: coverage, density, redundancy.

The architecture is self-similar. The macro-triad is 3 clusters; each cluster is a micro-triad of
3 masters. Global leadership nests the SAME 120° rotation (automation.triad_rotation.rotate) at
both levels: the leading CLUSTER rotates once every 3 micro-epochs, and the leader MASTER within
it rotates every micro-epoch. So the inner rotation is the outer rotation one level down — a
fractal. This script measures the three things the design claims:

  * COVERAGE   — leadership is spread evenly over all 9 nodes (triangular evenness, composed).
  * DENSITY    — how often the role turns over (rotations/day; hours-as-leader per node).
  * REDUNDANCY — how many master failures the fractal absorbs before it cannot assess/heal
                 (macro quorum of clusters, each a micro quorum of masters), vs a single leader.

Run: python3 tools/simulate_triad_rotation.py
"""
from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.triad_rotation import load_schedule, rotate  # noqa: E402

CLUSTERS = ["C0", "C1", "C2"]
MASTERS = ["M0", "M1", "M2"]
NODES = [f"{c}.{m}" for c in CLUSTERS for m in MASTERS]  # 9 leaves of the fractal


def global_leader(epoch: int, *, step: int = 1) -> str:
    """The single global leader at ``epoch`` = leader master of the leading cluster.

    Self-similar nesting: the cluster rotates on epoch//3 (a macro turn spans 3 micro turns),
    the master rotates on epoch. Over 9 epochs every (cluster, master) pair leads exactly once.
    """
    lead_cluster = rotate(CLUSTERS, epoch // 3, step=step).leader
    lead_master = rotate(MASTERS, epoch, step=step).leader
    return f"{lead_cluster}.{lead_master}"


def cluster_healthy(up_masters: set, cluster: str) -> bool:
    """A micro-triad is healthy iff a master quorum (2 of 3) is up."""
    return sum(1 for m in MASTERS if f"{cluster}.{m}" in up_masters) >= 2


def system_operational(up_masters: set) -> bool:
    """The fractal can still assess+failback iff a macro quorum (2 of 3) of clusters is healthy."""
    return sum(1 for c in CLUSTERS if cluster_healthy(up_masters, c)) >= 2


def min_failures_to_break() -> int:
    """Smallest number of node failures that can render the system non-operational (worst-placed)."""
    for k in range(1, len(NODES) + 1):
        for down in itertools.combinations(NODES, k):
            if not system_operational(set(NODES) - set(down)):
                return k
    return len(NODES) + 1


def report() -> None:
    sched = load_schedule()
    step = sched.step
    print("=" * 72)
    print("FRACTAL TRIAD-OF-TRIADS ROTATION — SIMULATION")
    print("=" * 72)
    print(f"declared schedule: {len(sched.masters)} masters, step={step} (120°×{step}/epoch), "
          f"period={sched.period_s:.0f}s")
    print(f"fractal: {len(CLUSTERS)} clusters × {len(MASTERS)} masters = {len(NODES)} nodes\n")

    # ── COVERAGE ────────────────────────────────────────────────────────────────────────────
    turns = 100  # 100 full fractal turns
    horizon = 9 * turns
    counts = {n: 0 for n in NODES}
    for e in range(horizon):
        counts[global_leader(e, step=step)] += 1
    lo, hi = min(counts.values()), max(counts.values())
    print(f"COVERAGE  over {horizon} epochs ({turns} fractal turns)")
    print(f"  every node led between {lo} and {hi} times (ideal {horizon // len(NODES)})")
    print(f"  spread hi-lo = {hi - lo}  ->  {'PERFECTLY EVEN' if hi == lo else 'UNEVEN'}")
    # self-similarity: cluster-level leadership is ALSO perfectly even, same shape one level up
    cl = {c: 0 for c in CLUSTERS}
    for e in range(horizon):
        cl[rotate(CLUSTERS, e // 3, step=step).leader] += 1
    print(f"  cluster-level lead counts {list(cl.values())} — identical shape at the macro level "
          f"(self-similar)\n")

    # ── DENSITY ─────────────────────────────────────────────────────────────────────────────
    per_day = 86400 / sched.period_s
    print("DENSITY")
    print(f"  leader turns over every {sched.period_s:.0f}s -> {per_day:.0f} rotations/day")
    print(f"  each of {len(NODES)} nodes is global leader {per_day / len(NODES):.2f} h/day "
          f"(bounded single-node exposure)")
    print(f"  within a cluster a master leads {per_day / len(MASTERS):.0f} h of that cluster's "
          f"lead-day — the same 1/3 share, nested\n")

    # ── REDUNDANCY ──────────────────────────────────────────────────────────────────────────
    k_break = min_failures_to_break()
    print("REDUNDANCY")
    print(f"  tolerates ANY {k_break - 1} simultaneous master failure(s); "
          f"needs {k_break} well-placed failures to break")
    print(f"  (break = <2 healthy clusters; each unhealthy cluster needs 2 masters down "
          f"-> {k_break} minimum)")
    rng = random.Random(1729)
    trials = 200_000
    print("  Monte Carlo P(operational) vs independent per-node failure prob p:")
    print(f"    {'p':>6}  {'fractal(9)':>12}  {'single leader':>14}  {'× better unavail':>16}")
    for p in (0.01, 0.05, 0.10, 0.20, 0.30):
        ok = 0
        for _ in range(trials):
            up = {n for n in NODES if rng.random() > p}
            if system_operational(up):
                ok += 1
        frac = ok / trials
        single = 1 - p  # a lone leader is up with prob (1-p)
        # improvement in UNAVAILABILITY (smaller is better): single_unavail / fractal_unavail
        fu, su = max(1 - frac, 1e-9), max(1 - single, 1e-9)
        print(f"    {p:>6.2f}  {frac:>12.5f}  {single:>14.5f}  {su / fu:>15.1f}×")
    print()
    print("VERDICT: coverage is perfectly even (triangular evenness composes across levels),")
    print("density bounds single-node leader exposure, and the fractal quorum-of-quorums makes")
    print("the system far more available than any single leader at every realistic failure rate.")
    print("=" * 72)


if __name__ == "__main__":
    report()
