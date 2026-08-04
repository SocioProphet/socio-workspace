#!/usr/bin/env python3
"""Simulate storage resilience across the k-mesh under a HOSTILE threat model.

Scenario (the brief: "living in Tehran, supporting Israel"): the adversary SEIZES nodes and
PARTITIONS the network. The Merkle leaves of the proof fabric are placed across three storage
archetypes — TopoLVM flash (hot, seizable, encrypted), replicated block (warm, CP writes),
erasure-coded object (cold, dispersed) — and must stay DURABLE, CONFIDENTIAL, and deliberately
CAP-correct. This measures all three against seizure fraction and a partition.

Run: python3 tools/simulate_storage_resilience.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.mesh_topology import build_tree, depth, leaves, tree_healthy  # noqa: E402
from automation.storage_placement import load_all  # noqa: E402
from automation.storage_resilience import (  # noqa: E402
    BLOCK_REPLICATED, FLASH_LOCAL, OBJECT_DISPERSED, Placement, confidential,
    disperse_shards, disperse_with_replicas, durable, max_seizable_nodes,
    read_available_under_partition, write_consistent_under_partition,
)


def _mc_seizure(nodes, placement, frac, trials, rng):
    """Monte Carlo P(durable) and P(confidential) when a `frac` of nodes is seized at random."""
    shard_nodes = list(disperse_shards(nodes, placement).keys())
    n_seize = round(frac * len(nodes))
    dur = con = 0
    for _ in range(trials):
        seized = set(rng.sample(nodes, n_seize))
        survived = sum(1 for s in shard_nodes if s not in seized)
        seized_shards = len(shard_nodes) - survived
        dur += durable(survived, placement)
        con += confidential(seized_shards, placement)
    return dur / trials, con / trials


def _mc_seizure_replicated(nodes, placement, frac, trials, rng):
    """P(durable) with shard replication: a shard survives iff >=1 of its replica-nodes survives."""
    placed = disperse_with_replicas(nodes, placement)  # shard_id -> [nodes]
    n_seize = round(frac * len(nodes))
    dur = 0
    for _ in range(trials):
        seized = set(rng.sample(nodes, n_seize))
        survived_shards = sum(1 for copies in placed.values() if any(c not in seized for c in copies))
        dur += durable(survived_shards, placement)
    return dur / trials


def report():
    rng = random.Random(1948)
    N = 27
    nodes = [f"n{i:02d}" for i in range(N)]
    tree = build_tree(nodes)
    place = Placement(replicas=3, rs_k=6, rs_m=3, encrypted_at_rest=True)

    print("=" * 74)
    print("STORAGE RESILIENCE ACROSS THE K-MESH — hostile environment (seizure + partition)")
    print("=" * 74)
    print(f"mesh: {N} backends, ternary tree depth {depth(tree)}")
    print("archetypes (hot -> cold), each a real mount pattern:")
    for a in (FLASH_LOCAL, BLOCK_REPLICATED, OBJECT_DISPERSED):
        print(f"  {a.name:18} {a.tier:5} {a.mount:22} seizable={a.seizable} "
              f"replicated={a.replicated} erasure={a.erasure_coded}")
    print(f"placement per Merkle leaf: {place.replicas} block replicas + "
          f"RS({place.rs_k},{place.rs_m}) object shards (n={place.rs_n}, "
          f"{place.durability_overhead:.2f}× overhead)\n")

    # ── SEIZURE ───────────────────────────────────────────────────────────────────────────
    print("SEIZURE  (adversary physically captures nodes)")
    print(f"  durability: lose ANY {max_seizable_nodes(place)} of {place.rs_n} shards -> still "
          f"reconstruct from {place.rs_k}  (dispersed so one seized triad != the leaf)")
    print("  confidentiality: encrypted-at-rest -> a captured node yields CIPHERTEXT; holds under "
          "ANY seizure")
    print("  Monte Carlo P(state survives) vs fraction of the mesh seized:")
    print(f"    {'seized':>8}  {'P(durable)':>11}  {'P(confidential)':>16}")
    for frac in (0.10, 0.20, 0.33, 0.50, 0.66):
        pdur, pcon = _mc_seizure(nodes, place, frac, 100_000, rng)
        print(f"    {frac:>7.0%}  {pdur:>11.5f}  {pcon:>16.5f}")

    # hardened placement — how to reach MASSIVE resilience (more parity, wider dispersal)
    hard = Placement(replicas=3, rs_k=9, rs_m=9, encrypted_at_rest=True)
    print(f"\n  HARDENED placement RS({hard.rs_k},{hard.rs_m}) (n={hard.rs_n}, "
          f"{hard.durability_overhead:.2f}× overhead) — dial resilience up:")
    print(f"    {'seized':>8}  {'RS(6,3)':>9}  {'RS(9,9)':>9}")
    for frac in (0.33, 0.50, 0.66):
        base, _ = _mc_seizure(nodes, place, frac, 100_000, rng)
        hp, _ = _mc_seizure(nodes, hard, frac, 100_000, rng)
        print(f"    {frac:>7.0%}  {base:>9.5f}  {hp:>9.5f}")
    print("    -> parity is the knob: RS(9,9) is certain-durable at a THIRD seized and a coin-flip")
    print("       at half, vs RS(6,3) collapsing at a third — still only 2× storage. Surviving")
    print("       past half needs a wider mesh or shard replication (density beats a fixed n).")

    # erasure vs replication at equal durability intent
    print("\n  erasure coding vs replication (durability per byte):")
    print(f"    RS({place.rs_k},{place.rs_m}): {place.durability_overhead:.2f}× storage, tolerates "
          f"{place.rs_m}/{place.rs_n} = {place.rs_m/place.rs_n:.0%} shard loss")
    print("    triple-replication: 3.00× storage, tolerates 2/3 = 67% copy loss of ONE object")
    print("    -> erasure gives far more durability per stored byte; replication is the warm CP tier only")

    # ── CAP UNDER PARTITION ───────────────────────────────────────────────────────────────
    print("\nCAP UNDER PARTITION  (network split — stated posture, not accidental)")
    # split the home triad 2:1; majority side has the write quorum, minority is read-only
    maj_replicas, min_replicas = 2, 1
    shard_nodes = list(disperse_shards(nodes, place).keys())
    maj_shards = sum(1 for i, _ in enumerate(shard_nodes) if i % 3 != 2)  # ~2/3 of shards on majority
    min_shards = place.rs_n - maj_shards
    print(f"  split home triad {maj_replicas}:{min_replicas}; shards ~{maj_shards}:{min_shards}")
    print(f"  MAJORITY: write_consistent={write_consistent_under_partition(maj_replicas, place)}  "
          f"read_available={read_available_under_partition(maj_shards, place)}")
    print(f"  MINORITY: write_consistent={write_consistent_under_partition(min_replicas, place)}  "
          f"read_available={read_available_under_partition(min_shards, place)}")
    print("  => only ONE partition can write (CP: no fork of the truth); either side with >=k shards")
    print("     still serves reads (AP). Consistency for truth, availability for reading it.")

    # ── TopoLVM re-home on rotation ───────────────────────────────────────────────────────
    print("\nTOPOLVM / MOUNT PATTERN")
    print("  hot working set = leader's local NVMe (RWO). On a leadership ROTATION the volume")
    print("  re-homes to the new leader from the warm block replica — 'state follows TopoLVM',")
    print("  the volume follows the workload; no shared-disk single point, no cross-AZ RWO stall.")

    # ── DECLARED, GOVERNED TIERS (registry/mesh-storage-placement.yaml) ───────────────────
    print("\nDECLARED THREAT TIERS  (registry/mesh-storage-placement.yaml — reviewed config, not code)")
    tiers = load_all()
    order = [t for t in ("baseline", "hardened", "hostile") if t in tiers]
    print(f"    {'tier':>9}  {'scheme':>16}  {'overhead':>8}  {'P(dur)@33%':>10}  {'P(dur)@50%':>10}  {'@66%':>7}")
    for name in order:
        p = tiers[name]
        mc = _mc_seizure_replicated if p.shard_replicas > 1 else lambda n, pl, f, t, r: _mc_seizure(n, pl, f, t, r)[0]
        d33 = mc(nodes, p, 0.33, 60_000, rng)
        d50 = mc(nodes, p, 0.50, 60_000, rng)
        d66 = mc(nodes, p, 0.66, 60_000, rng)
        scheme = f"RS({p.rs_k},{p.rs_m})×{p.shard_replicas}"
        print(f"    {name:>9}  {scheme:>16}  {p.durability_overhead:>7.2f}×  {d33:>10.5f}  {d50:>10.5f}  {d66:>7.5f}")
    print("    baseline collapses past a third; hardened (more parity) holds a third; HOSTILE")
    print("    (shard_replicas=2) survives PAST half — P(shard lost)=frac² — at 3× storage. The")
    print("    posture is a declared tier the governance plane validates, swappable without a rebuild.")

    print("\nVERDICT: with parity sized to the threat (RS(9,9) here) the state is certain-durable")
    print("under a third of the mesh seized, confidential under ANY seizure (ciphertext),")
    print("partition-correct by design (CP writes / AP reads), and the hot tier re-homes with the")
    print("rotation. Resilience is a placement dial (parity + dispersal), not a rewrite.")
    print("=" * 74)


if __name__ == "__main__":
    report()
