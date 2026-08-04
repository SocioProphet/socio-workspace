#!/usr/bin/env python3
"""Demo: the live write/read path, adaptive and seizure-surviving, end to end.

Writes a leaf at the calm posture, then simulates a threat ESCALATION (which raises the placement
tier), writes a second leaf that lands with MORE parity automatically, seizes a chunk of the mesh,
and reads both back — each reconstruction Merkle-verified. Runs against an in-memory store.

Run: python3 tools/demo_leaf_write_read.py
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.holographic_ida import merkle_root  # noqa: E402
from automation.leaf_propagation import LeafUnavailable, fetch, in_memory_store, propagate  # noqa: E402
from automation.storage_placement import load_placement  # noqa: E402


def main():
    rng = random.Random(2024)
    nodes = [f"n{i:02d}" for i in range(27)]
    put, get, _ = in_memory_store()

    print("=" * 72)
    print("ADAPTIVE HOLOGRAPHIC LEAF PROPAGATION — write / escalate / seize / read")
    print("=" * 72)

    # 1. calm posture — write a leaf at the baseline tier (RS(6,3), no shard replication)
    calm = load_placement("baseline")
    leaf_a = b"LEAF-A @ calm :: " + os.urandom(48)
    ma = propagate(leaf_a, nodes=nodes, put=put, placement=calm, tier="baseline")
    print(f"write A @ baseline: RS({ma.k},{ma.n - ma.k}) x{ma.replicas} -> {ma.n} fragments, "
          f"{ma.replicas} copy each  root {ma.root[:19]}…")

    # 2. threat escalates -> the posture selects a harder tier; new writes adapt automatically
    hostile = load_placement("hostile")
    leaf_b = b"LEAF-B @ hostile :: " + os.urandom(48)
    mb = propagate(leaf_b, nodes=nodes, put=put, placement=hostile, tier="hostile")
    print(f"ESCALATE -> write B @ hostile: RS({mb.k},{mb.n - mb.k}) x{mb.replicas} -> {mb.n} "
          f"fragments, {mb.replicas} copies each (more resilience, no code change)  root {mb.root[:19]}…")

    # 3. adversary seizes the nodes holding a decisive chunk of A's (unreplicated) fragments — enough
    #    to push A below its quorum. B's fragments each have a second copy elsewhere.
    a_nodes = [nd for lst in ma.fragment_nodes.values() for nd in lst]
    seized = set(a_nodes[:ma.n - ma.k + 1])          # one past A's tolerance
    reachable = set(nodes) - seized
    print(f"\nSEIZE: adversary takes {len(seized)} nodes (targets A's fragments); {len(reachable)} reachable")

    # 4. read both back from the survivors, Merkle-verified
    for name, m in (("A (baseline)", ma), ("B (hostile)", mb)):
        try:
            leaf = fetch(m, get=get, reachable=reachable)
            print(f"read {name}: reconstructed {len(leaf)} bytes, Merkle root verified: "
                  f"{merkle_root(leaf) == m.root}")
        except LeafUnavailable as e:
            print(f"read {name}: UNAVAILABLE ({e})")

    print("\n=> Under the SAME seizure the baseline leaf is lost but the escalated (replicated) leaf")
    print("   survives and reconstructs, Merkle-verified. The posture change is realized on writes.")
    print("=" * 72)


if __name__ == "__main__":
    main()
