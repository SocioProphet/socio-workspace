"""The live write/read path — make holographic propagation HAPPEN on every Merkle leaf.

#605 proved the dispersal primitive (any k-of-n reconstructs the whole leaf, Merkle-verified). This
is the path that uses it: ``propagate`` disperses a leaf at the tier the adaptive posture currently
selects and places the fragments across the mesh; ``fetch`` gathers a quorum of fragments from
whatever nodes are reachable and reconstructs, verifying against the Merkle root. Together they are
the "write" and "read" of the governed proof fabric's state.

Two seams are INJECTED (``put`` / ``get``), because the actual fragment I/O — writing bytes to a
node's object store, reading them back — is node-runtime and environment-specific. The library owns
the dispersal, placement, quorum, and integrity logic (all testable with an in-memory store) and
takes the transport as a function, the same pattern as pr_opener's runner and vantage's reach.

Trust properties this path realizes end to end:
  * ADAPTIVE  — writes disperse at ``load_runtime_placement()``'s tier, so an escalation makes new
                leaves land with more parity automatically (the effect link #604 closed).
  * CAP READ  — fetch reconstructs from ANY k reachable fragments, so a partition holding a quorum
                still serves reads (AP), while the write quorum keeps truth un-forked (CP).
  * BYZANTINE — a corrupted/lying fragment fails the Merkle root; fetch ROUTES AROUND it by trying
                other k-subsets of the reachable fragments until one reconstructs the committed root.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from automation.holographic_ida import disperse, merkle_root, reconstruct
from automation.mesh_topology import build_tree, leaves
from automation.storage_placement import load_runtime_placement
from automation.storage_resilience import Placement

# put(node, fragment_id, fragment_bytes) -> None ; get(node, fragment_id) -> bytes | None
PutFn = Callable[[str, int, bytes], None]
GetFn = Callable[[str, int], Optional[bytes]]


class LeafUnavailable(Exception):
    """Fewer than k fragments were reachable — the leaf cannot be reconstructed from this vantage."""


class IntegrityError(Exception):
    """No k-subset of the reachable fragments reconstructs the committed Merkle root (too much
    corruption / too many Byzantine fragments to route around)."""


@dataclass(frozen=True)
class PropagationManifest:
    """Where a leaf's fragments live + how to verify a reconstruction. The manifest itself is small
    and can be replicated freely; it carries no leaf bytes, only the commitment and the placement."""
    root: str                             # sha256 Merkle commitment of the leaf
    k: int
    n: int
    orig_len: int
    tier: str                             # provenance: which placement tier this leaf was written at
    replicas: int                         # copies of each fragment (shard_replicas)
    fragment_nodes: Dict[int, List[str]]  # fragment_id -> the nodes holding a copy of it


def _place(nodes: Sequence[str], xs: Sequence[int], replicas: int) -> Dict[int, List[str]]:
    """Map each fragment id to ``replicas`` DISTINCT mesh nodes, strided across the triad tree so
    copies and neighbouring fragments land in different subtrees (no single triad is decisive, and a
    fragment survives while any one of its copies does)."""
    ordered = leaves(build_tree(list(nodes)))
    total = len(xs) * replicas
    if total > len(ordered):
        raise ValueError(f"need {total} distinct nodes for {len(xs)} fragments × {replicas} "
                         f"replicas; mesh has {len(ordered)}")
    stride = max(1, len(ordered) // total)
    mapping: Dict[int, List[str]] = {x: [] for x in xs}
    slot = 0
    for x in xs:
        for _ in range(replicas):
            mapping[x].append(ordered[(slot * stride) % len(ordered)])
            slot += 1
    return mapping


def propagate(leaf: bytes, *, nodes: Sequence[str], put: PutFn,
              placement: Optional[Placement] = None, tier: str = "runtime") -> PropagationManifest:
    """WRITE a leaf: disperse it at the current (or given) tier and place its fragments on the mesh.

    With no explicit ``placement`` the tier is whatever the live threat posture selects
    (``load_runtime_placement``), so an escalation raises the parity AND the shard replication of
    new writes with no code change. Each fragment copy is handed to ``put`` for node-local storage.
    Returns the manifest a reader needs — commitment + placement — and never the leaf bytes.
    """
    placement = placement if placement is not None else load_runtime_placement()
    k, n, r = placement.rs_k, placement.rs_n, placement.shard_replicas
    d = disperse(leaf, k, n)
    mapping = _place(nodes, d.xs, r)
    for x, node_list in mapping.items():
        for node in node_list:
            put(node, x, d.fragments[x])
    return PropagationManifest(root=merkle_root(leaf), k=k, n=n, orig_len=d.orig_len,
                               tier=tier, replicas=r, fragment_nodes=mapping)


def fetch(manifest: PropagationManifest, *, get: GetFn,
          reachable: Optional[set] = None, max_attempts: int = 500) -> bytes:
    """READ a leaf: gather a quorum of fragments from reachable nodes and reconstruct, Merkle-verified.

    Fail-closed and Byzantine-robust:
      * fewer than k fragments reachable -> LeafUnavailable (a minority partition cannot read).
      * a reconstruction is returned ONLY if it matches the committed Merkle root; a corrupted
        fragment yields a wrong root, so fetch tries other k-subsets of the reachable fragments
        (routing around the liar) until one verifies, or IntegrityError if none does.
    (The subset search is the simple, correct decoder given the Merkle-root oracle; a production
    reader would use Berlekamp-Welch RS error correction to locate corrupt fragments directly.)
    """
    avail: Dict[int, bytes] = {}
    for x, node_list in manifest.fragment_nodes.items():
        for node in node_list:                       # a fragment survives if ANY of its copies does
            if reachable is not None and node not in reachable:
                continue
            try:
                b = get(node, x)
            except Exception:  # noqa: BLE001 — an errored fetch is an unreachable copy, not a healthy one
                b = None
            if b is not None:
                avail[x] = b
                break                                # one good copy of this fragment suffices
    if len(avail) < manifest.k:
        raise LeafUnavailable(f"{len(avail)} fragments reachable; need {manifest.k}")

    xs = sorted(avail)
    # Fast path: the full-reachable first-k almost always is clean.
    attempts = 0
    for combo in itertools.combinations(xs, manifest.k):
        attempts += 1
        if attempts > max_attempts:
            break
        rec = reconstruct({x: avail[x] for x in combo}, manifest.k, manifest.orig_len)
        if merkle_root(rec) == manifest.root:
            return rec
    raise IntegrityError("no reachable k-subset reconstructs the committed root "
                         f"(tried {attempts} of C({len(xs)},{manifest.k}))")


def in_memory_store() -> tuple:
    """A (put, get, store) triple backing fragments in a dict — for tests, demos, and single-host
    runs. ``store`` maps (node, fragment_id) -> bytes; put/get close over it."""
    store: Dict[tuple, bytes] = {}

    def put(node: str, frag: int, data: bytes) -> None:
        store[(node, frag)] = data

    def get(node: str, frag: int) -> Optional[bytes]:
        return store.get((node, frag))

    return put, get, store
