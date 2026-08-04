#!/usr/bin/env python3
"""Simulate the SAME triad mechanism scaled across a k-mesh of N backends.

The claim: nothing new is invented for scale. A mesh of any N is a balanced ternary tree of
triads; the identical rotation (mixed-radix nesting of the 120° turn) and majority quorum apply
at every level. This shows leadership stays evenly covered and redundancy compounds with depth,
for powers of 3 AND for arbitrary N (n-backends).

Run: python3 tools/simulate_kmesh.py
"""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.mesh_topology import (  # noqa: E402
    build_tree, depth, leaves, tree_healthy, tree_leader, turn_length,
)


def _coverage_spread(tree, horizon):
    counts = Counter(tree_leader(tree, e) for e in range(horizon))
    full = {leaf: counts.get(leaf, 0) for leaf in leaves(tree)}
    return min(full.values()), max(full.values())


def _mc_operational(tree, node_list, p, trials, rng):
    ok = 0
    for _ in range(trials):
        up = {n for n in node_list if rng.random() > p}
        ok += tree_healthy(tree, up)
    return ok / trials


def report():
    rng = random.Random(31337)
    print("=" * 74)
    print("SAME MECHANISM ACROSS THE K-MESH — N backends, recursive triads")
    print("=" * 74)

    print(f"\n{'N':>5}  {'depth':>5}  {'turn':>6}  {'coverage(lo..hi over 10 turns)':>32}")
    for N in (3, 9, 27, 81, 50, 100):
        nodes = [f"n{i:03d}" for i in range(N)]
        tree = build_tree(nodes)
        T = turn_length(tree)
        lo, hi = _coverage_spread(tree, T * 10)
        ratio = hi / lo if lo else float("inf")
        even = "PERFECT" if hi == lo else f"<= {ratio:.1f}x imbalance"
        print(f"{N:>5}  {depth(tree):>5}  {T:>6}  {f'{lo}..{hi}  {even}':>32}")
    print("  powers of 3 (3,9,27,81) are PERFECTLY even. Other N carry a bounded imbalance (a leaf")
    print("  under a 2-way split leads more often than one under a 3-way split) — same rotate() at")
    print("  every level, no special-casing. For exact evenness at arbitrary N: pad to 3^d, or")
    print("  weight the pick by each leaf's path-product. The mechanism is identical either way.")

    print("\nREDUNDANCY compounds with depth — Monte Carlo P(mesh operational) vs per-node fail p:")
    print(f"    {'N':>5}  {'p=0.05':>8}  {'p=0.10':>8}  {'p=0.20':>8}")
    for N in (3, 9, 27, 81):
        nodes = [f"n{i:03d}" for i in range(N)]
        tree = build_tree(nodes)
        row = [_mc_operational(tree, nodes, p, 50_000, rng) for p in (0.05, 0.10, 0.20)]
        print(f"    {N:>5}  {row[0]:>8.5f}  {row[1]:>8.5f}  {row[2]:>8.5f}")
    print("  a lone node is operational with prob (1-p); the recursive quorum-of-quorums holds far")
    print("  higher and IMPROVES with N at low p (more independent triads each absorbing a fault).")

    print("\n=> The triad IS the mesh, recursively. One rotation rule, one quorum rule, applied")
    print("   self-similarly from 3 backends to N. That is the mechanism for n-backends.")
    print("=" * 74)


if __name__ == "__main__":
    report()
