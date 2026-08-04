"""Tests for the live write/read propagation path — the thing that makes holographic dispersal
HAPPEN on every leaf: adaptive write, CAP read, Byzantine route-around, fail-closed below quorum."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.leaf_propagation import (  # noqa: E402
    IntegrityError, LeafUnavailable, fetch, in_memory_store, propagate,
)
from automation.storage_placement import load_placement  # noqa: E402
from automation.storage_resilience import Placement

NODES = [f"n{i:02d}" for i in range(27)]
P = Placement(rs_k=6, rs_m=3)  # k=6, n=9, R=1


def _all_nodes(m):
    return [nd for lst in m.fragment_nodes.values() for nd in lst]


def test_write_then_read_roundtrip():
    put, get, _ = in_memory_store()
    leaf = b"the whole governed leaf " + os.urandom(40)
    m = propagate(leaf, nodes=NODES, put=put, placement=P)
    assert m.k == 6 and m.n == 9 and len(set(_all_nodes(m))) == 9  # R=1 -> 9 distinct nodes
    assert fetch(m, get=get) == leaf


def test_manifest_carries_commitment_not_bytes():
    put, get, _ = in_memory_store()
    leaf = os.urandom(64)
    m = propagate(leaf, nodes=NODES, put=put, placement=P, tier="hardened")
    assert m.root.startswith("sha256:") and m.tier == "hardened" and m.replicas == 1


def test_read_from_exactly_k_reachable():
    put, get, _ = in_memory_store()
    leaf = os.urandom(50)
    m = propagate(leaf, nodes=NODES, put=put, placement=P)
    frag_nodes = _all_nodes(m)  # R=1 -> one node per fragment, 9 total
    assert fetch(m, get=get, reachable=set(frag_nodes[:6])) == leaf  # exactly k -> reads (AP)


def test_below_quorum_is_unavailable():
    put, get, _ = in_memory_store()
    leaf = os.urandom(50)
    m = propagate(leaf, nodes=NODES, put=put, placement=P)
    frag_nodes = _all_nodes(m)
    try:
        fetch(m, get=get, reachable=set(frag_nodes[:5]))  # k-1
    except LeafUnavailable:
        pass
    else:
        raise AssertionError("k-1 reachable must be LeafUnavailable")


def test_byzantine_fragment_is_routed_around():
    put, get, store = in_memory_store()
    leaf = os.urandom(60)
    m = propagate(leaf, nodes=NODES, put=put, placement=P)
    x = list(m.fragment_nodes)[3]
    key = (m.fragment_nodes[x][0], f"{m.root}#{x}")   # content-scoped fragment key
    store[key] = bytes([store[key][0] ^ 0xFF]) + store[key][1:]  # corrupt it
    assert fetch(m, get=get) == leaf  # n=9 > k=6 slack -> a clean subset verifies the root


def test_too_much_corruption_raises_integrity_error():
    # corrupt n-k+1 = 4 fragments -> fewer than k clean -> no verifying subset.
    put, get, store = in_memory_store()
    leaf = os.urandom(60)
    m = propagate(leaf, nodes=NODES, put=put, placement=P)
    for x in list(m.fragment_nodes)[:4]:
        key = (m.fragment_nodes[x][0], f"{m.root}#{x}")
        store[key] = bytes([store[key][0] ^ 0xFF]) + store[key][1:]
    try:
        fetch(m, get=get)
    except IntegrityError:
        pass
    else:
        raise AssertionError("with < k clean fragments, fetch must raise IntegrityError")


def test_errored_get_treated_as_unreachable():
    put, get, _ = in_memory_store()
    leaf = os.urandom(40)
    m = propagate(leaf, nodes=NODES, put=put, placement=P)
    dead = set(_all_nodes(m)[:2])

    def flaky_get(node, frag):
        if node in dead:
            raise ConnectionError("timeout")
        return get(node, frag)

    assert fetch(m, get=flaky_get) == leaf  # 7 healthy >= k=6 -> still reads


def test_replication_survives_seizure_that_kills_the_unreplicated_tier():
    """The adaptive point the demo exposed: under the SAME seizure, the hostile tier (shard_replicas
    =2) reconstructs where baseline (R=1) cannot — a fragment survives while any copy does."""
    put, get, _ = in_memory_store()
    base = load_placement("baseline")   # R=1
    host = load_placement("hostile")    # R=2
    leaf_b = os.urandom(50)
    leaf_h = os.urandom(50)
    mb = propagate(leaf_b, nodes=NODES, put=put, placement=base, tier="baseline")
    mh = propagate(leaf_h, nodes=NODES, put=put, placement=host, tier="hostile")
    # seize the 4 distinct nodes holding baseline fragments 0..3 -> baseline loses n-k+1=4 -> dead.
    kill = set(_all_nodes(mb)[:4])
    reachable = set(NODES) - kill
    try:
        fetch(mb, get=get, reachable=reachable)
        base_survived = True
    except (LeafUnavailable, IntegrityError):
        base_survived = False
    # hostile: each fragment has a 2nd copy elsewhere, so the same kill set leaves a quorum.
    host_survived = fetch(mh, get=get, reachable=reachable) == leaf_h
    assert host_survived and not base_survived


def test_write_defaults_to_runtime_placement():
    put, get, _ = in_memory_store()
    leaf = os.urandom(30)
    m = propagate(leaf, nodes=NODES, put=put)  # no placement -> runtime floor (hardened)
    assert m.n <= len(NODES) and fetch(m, get=get) == leaf


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"leaf_propagation: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
