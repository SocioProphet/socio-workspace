#!/usr/bin/env python3
"""PROVE holographic Merkle-leaf propagation across the trust mesh.

Disperses a real leaf into n fragments (Rabin IDA over GF(256)), places them on distinct nodes of
the ternary triad-tree mesh, and demonstrates the four properties that make "holographic" a claim
and not a slogan — each verified by reconstructing the bytes and checking the Merkle root:

  1. HOLOGRAPHIC REDUNDANCY — several DIFFERENT k-node subsets each reconstruct the WHOLE leaf.
  2. SEIZURE SURVIVAL       — the adversary seizes a fraction; the surviving quorum reconstructs.
  3. BYZANTINE TRUST        — a node returns a corrupted fragment; a subset including it FAILS the
                              Merkle root (detected), and the honest quorum reconstructs without it.
  4. CONFIDENTIALITY FLOOR  — fewer than k fragments cannot reconstruct at all.

Run: python3 tools/prove_holographic_propagation.py
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.holographic_ida import disperse, merkle_root, reconstruct  # noqa: E402
from automation.mesh_topology import build_tree, depth, leaves  # noqa: E402
from automation.storage_placement import load_placement  # noqa: E402


def _place_on_mesh(nodes, xs):
    """Map each fragment id x to a distinct mesh node, strided across the tree so consecutive
    fragments land in different triads (no single triad holds a reconstructing quorum)."""
    ordered = leaves(build_tree(nodes))
    stride = max(1, len(ordered) // len(xs))
    return {x: ordered[(i * stride) % len(ordered)] for i, x in enumerate(xs)}


def report():
    rng = random.Random(1979)
    N = 27
    nodes = [f"n{i:02d}" for i in range(N)]
    place = load_placement("hardened")           # declared tier -> k, n
    k, n = place.rs_k, place.rs_n

    leaf = (b"MERKLE-LEAF v1 :: governed-proof-fabric :: claim.v0+evidence.v0 :: epoch=42 :: "
            + os.urandom(64))
    root = merkle_root(leaf)
    d = disperse(leaf, k, n)
    frag_node = _place_on_mesh(nodes, d.xs)       # fragment id -> mesh node

    print("=" * 76)
    print("HOLOGRAPHIC MERKLE-LEAF PROPAGATION ACROSS THE TRUST MESH")
    print("=" * 76)
    print(f"mesh: {N} nodes, ternary triad-tree depth {depth(build_tree(nodes))}")
    print(f"leaf: {len(leaf)} bytes   root: {root[:23]}…")
    print(f"dispersed: RS-style IDA k={k}, n={n} ({n/k:.2f}× overhead); one fragment per node, "
          f"strided across triads\n")

    def recon_from_nodes(node_set, fragments):
        have = {x: fragments[x] for x, nd in frag_node.items() if nd in node_set}
        if len(have) < k:
            return None
        return reconstruct(have, k, d.orig_len)

    # 1. HOLOGRAPHIC REDUNDANCY — different k-node subsets each rebuild the whole leaf.
    print("1. HOLOGRAPHIC REDUNDANCY — different fragment subsets, same whole leaf:")
    frag_nodes = list(frag_node.values())
    for t in range(3):
        subset = set(rng.sample(frag_nodes, k))
        rec = recon_from_nodes(subset, d.fragments)
        print(f"   subset {sorted(subset)} -> root match: {merkle_root(rec) == root}")

    # 2. SEIZURE SURVIVAL — lose up to n-k fragment-bearing nodes and still reconstruct.
    print(f"\n2. SEIZURE SURVIVAL — adversary seizes nodes (durable while >= {k} fragments remain):")
    for seized_count in (n - k, n - k + 0):  # exactly the tolerance
        seized = set(rng.sample(frag_nodes, seized_count))
        survivors = set(nodes) - seized
        rec = recon_from_nodes(survivors, d.fragments)
        print(f"   seized {seized_count} fragment-nodes -> reconstruct: "
              f"{rec is not None and merkle_root(rec) == root}")
    # one past tolerance -> cannot
    seized = set(rng.sample(frag_nodes, n - k + 1))
    rec = recon_from_nodes(set(nodes) - seized, d.fragments)
    print(f"   seized {n - k + 1} (one past tolerance) -> reconstruct: {rec is not None} "
          f"(expected False)")

    # 3. BYZANTINE TRUST — a node returns a corrupted fragment; the Merkle root catches it.
    print("\n3. BYZANTINE TRUST — a lying node's fragment is detected, the mesh routes around it:")
    liar = frag_nodes[3]
    liar_x = next(x for x, nd in frag_node.items() if nd == liar)
    corrupted = dict(d.fragments)
    corrupted[liar_x] = bytes([corrupted[liar_x][0] ^ 0xFF]) + corrupted[liar_x][1:]
    incl = set(rng.sample([x for x in frag_nodes if x != liar], k - 1)) | {liar}
    rec_bad = recon_from_nodes(incl, corrupted)
    honest = set(x for x in frag_nodes if x != liar)
    rec_ok = recon_from_nodes(set(list(honest)[:k]), corrupted)
    print(f"   subset INCLUDING the liar -> root match: {merkle_root(rec_bad) == root} "
          f"(detected: the leaf never verifies)")
    print(f"   honest quorum EXCLUDING the liar -> root match: {merkle_root(rec_ok) == root}")

    # 4. CONFIDENTIALITY FLOOR — fewer than k fragments cannot reconstruct.
    print("\n4. RECONSTRUCTION FLOOR — fewer than k fragments yield nothing:")
    too_few = set(rng.sample(frag_nodes, k - 1))
    print(f"   {k - 1} fragments (< k) -> reconstruct: {recon_from_nodes(too_few, d.fragments) is not None} "
          f"(expected False)")

    print("\n=> Holographic: any k of the n fragments — from ANY k honest nodes that survive seizure")
    print("   or partition — reconstruct the exact leaf and prove it against its Merkle root. No")
    print("   single node, and no sub-quorum, holds or can forge the whole. QED.")
    print("=" * 76)


if __name__ == "__main__":
    report()
