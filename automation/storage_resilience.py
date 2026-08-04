"""Storage resilience across the k-mesh — built for a hostile environment.

Threat model (the user's framing: "living in Tehran, supporting Israel"): nodes get SEIZED, links
get PARTITIONED, the adversary is powerful and patient. The state — the Merkle leaves of the
governed proof fabric — must satisfy three properties simultaneously:

  * DURABILITY     — the honest remainder can always reconstruct after the adversary seizes a
                     bounded fraction of nodes (erasure coding: lose any ``m`` of ``k+m`` shards).
  * CONFIDENTIALITY — no seizable subset below the reconstruction threshold learns the plaintext
                     (encrypt-at-rest on the seizable tiers + shards are ciphertext, need ``k`` to
                     even assemble the structure). A captured node yields ciphertext, not secrets.
  * AVAILABILITY / CONSISTENCY — a deliberate CAP posture under partition, not an accident.

This is Lazerus's dual-plane commitment (Merkle content + Reed-Solomon syndromes) placed across
three storage archetypes, each a real Kubernetes mount pattern, ordered hot->cold:

  FLASH_LOCAL      TopoLVM local NVMe (RWO). Fastest; the leader's working set. SEIZABLE (physical
                   capture = data capture) so it MUST be encrypted-at-rest. "State follows TopoLVM":
                   on a leadership rotation the hot volume re-homes to the new leader from the warm
                   replica (the volume follows the workload).
  BLOCK_REPLICATED replicated network block across the leaf's home triad (RWO w/ failover).
                   Survives loss of a minority of the triad; the CONSISTENT (CP) write tier.
  OBJECT_DISPERSED erasure-coded object shards (RS k-of-n) dispersed across the WIDER mesh,
                   immutable. No node holds the whole leaf; survives seizure of up to ``m`` shards.
                   The DURABLE, seizure-resilient cold tier — the thing that outlives a raid.

CAP choice, stated: for the CANONICAL state we are CP on writes (a write needs a replica/mesh
quorum, so a minority partition CANNOT fork the truth — fail-closed, no split-brain) and AP on
reads (any partition holding >= k shards can reconstruct and serve read-only). Consistency for
truth, availability for reading it — the split the estate already makes for the macro-triad.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from automation.mesh_topology import build_tree, leaves


@dataclass(frozen=True)
class Archetype:
    name: str
    tier: str          # hot | warm | cold
    mount: str
    seizable: bool     # does capturing ONE node expose this leaf's plaintext?
    replicated: bool
    erasure_coded: bool


FLASH_LOCAL = Archetype("topolvm-flash", "hot", "RWO-local-nvme (encrypted)",
                        seizable=True, replicated=False, erasure_coded=False)
BLOCK_REPLICATED = Archetype("block-replicated", "warm", "RWO-failover",
                             seizable=True, replicated=True, erasure_coded=False)
OBJECT_DISPERSED = Archetype("object-dispersed", "cold", "immutable-erasure",
                             seizable=False, replicated=False, erasure_coded=True)


@dataclass(frozen=True)
class Placement:
    """How one Merkle leaf is laid down across the tiers."""
    replicas: int = 3          # warm block replicas across the home triad
    rs_k: int = 6              # RS data shards — need k to reconstruct
    rs_m: int = 3              # RS parity shards — tolerate losing any m
    encrypted_at_rest: bool = True
    shard_replicas: int = 1    # copies of EACH cold shard, dispersed to distinct nodes (R=1 = none)

    @property
    def rs_n(self) -> int:
        return self.rs_k + self.rs_m

    @property
    def durability_overhead(self) -> float:
        """Storage blow-up of the cold tier: n·R/k. RS(6,3) R=1 = 1.5×; R=2 = 3× (buys past-half
        seizure survival — parity alone tops out near half the mesh; replicating shards beats it)."""
        return self.rs_n * self.shard_replicas / self.rs_k

    def expected_durable_under_seizure(self, frac: float) -> float:
        """Analytic durability under an independent per-node seizure probability ``frac``.

        A shard is lost only if ALL R of its replicas are seized -> P(shard lost) = frac**R, so a
        shard survives w.p. 1 - frac**R. With n shards the expected number surviving is
        n·(1 - frac**R); the leaf is durable when that is >= k. Replication (R>1) shrinks the loss
        term geometrically, which is why it pushes durability PAST half the mesh being seized where
        parity alone cannot. (Mean-field estimate; the simulation confirms it empirically.)"""
        survive_p = 1.0 - (frac ** self.shard_replicas)
        return self.rs_n * survive_p >= self.rs_k


# ── the resilience predicates (pure, testable) ───────────────────────────────────────────────

def durable(surviving_shards: int, placement: Placement) -> bool:
    """Reconstructable iff at least ``k`` of the ``n`` dispersed shards survive on honest nodes."""
    return surviving_shards >= placement.rs_k


def confidential(seized_shards: int, placement: Placement) -> bool:
    """Plaintext protected. Encrypted-at-rest -> a seized shard is ciphertext, so confidentiality
    holds under ANY seizure; unencrypted -> the adversary must be kept below the ``k`` threshold."""
    if placement.encrypted_at_rest:
        return True
    return seized_shards < placement.rs_k


def write_consistent_under_partition(reachable_replicas: int, placement: Placement) -> bool:
    """CP write: a canonical write commits only with a strict-majority replica quorum reachable,
    so a minority partition cannot fork the truth (fail-closed rather than split-brain)."""
    return reachable_replicas >= (placement.replicas // 2) + 1


def read_available_under_partition(reachable_shards: int, placement: Placement) -> bool:
    """AP read: any partition that can reach >= k shards reconstructs and serves read-only."""
    return reachable_shards >= placement.rs_k


def max_seizable_nodes(placement: Placement) -> int:
    """How many shard-bearing nodes the adversary may seize and STILL leave the state durable."""
    return placement.rs_m  # lose any m of n and k remain


# ── shard placement over the mesh (dispersed so no small subset is decisive) ──────────────────

def disperse_shards(nodes: List[str], placement: Placement) -> dict:
    """Assign the n RS shards of one leaf to distinct mesh nodes, spread across the tree's leaves
    round-robin (so the n shards land in as many different triads/subtrees as possible — a seizure
    of one triad takes at most a few shards, never the whole leaf)."""
    tree = build_tree(nodes)
    ordered = leaves(tree)
    if placement.rs_n > len(ordered):
        raise ValueError(f"need {placement.rs_n} distinct nodes for the shards; mesh has {len(ordered)}")
    # stride across the ordered leaves so consecutive shards land in different subtrees
    stride = max(1, len(ordered) // placement.rs_n)
    return {ordered[(i * stride) % len(ordered)]: f"shard-{i}" for i in range(placement.rs_n)}


def disperse_with_replicas(nodes: List[str], placement: Placement) -> dict:
    """Assign each of the n shards to ``shard_replicas`` DISTINCT nodes, spread across the mesh.

    Returns ``{shard_id: [node, ...]}`` with n·R total copies on distinct nodes. A shard survives a
    seizure iff at least one of its replica-nodes is not seized — so P(shard lost) = frac**R — which
    is how replication buys past-half durability the parity alone cannot reach.
    """
    tree = build_tree(nodes)
    ordered = leaves(tree)
    total = placement.rs_n * placement.shard_replicas
    if total > len(ordered):
        raise ValueError(f"need {total} distinct nodes for {placement.rs_n} shards × "
                         f"{placement.shard_replicas} replicas; mesh has {len(ordered)}")
    stride = max(1, len(ordered) // total)
    out: dict = {f"shard-{s}": [] for s in range(placement.rs_n)}
    slot = 0
    for s in range(placement.rs_n):
        for _ in range(placement.shard_replicas):
            out[f"shard-{s}"].append(ordered[(slot * stride) % len(ordered)])
            slot += 1
    return out
