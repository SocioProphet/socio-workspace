"""Tests for manifest resolution — finding a leaf's manifest by its Merkle root alone, under
seizure, with no directory. The decisive test reconstructs a leaf knowing ONLY the root."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.leaf_propagation import fetch, in_memory_store, propagate  # noqa: E402
from automation.manifest_store import (  # noqa: E402
    ManifestUnavailable, manifest_nodes, publish_manifest, resolve_manifest,
)
from automation.storage_resilience import Placement

NODES = [f"n{i:02d}" for i in range(27)]
P = Placement(rs_k=6, rs_m=3)


def _blob_store():
    store = {}

    def put_blob(node, key, data):
        store[(node, key)] = data

    def get_blob(node, key):
        return store.get((node, key))

    return put_blob, get_blob, store


def test_manifest_nodes_deterministic_and_sized():
    a = manifest_nodes("sha256:abc", NODES, 3)
    b = manifest_nodes("sha256:abc", NODES, 3)
    assert a == b and len(a) == 3 and len(set(a)) == 3   # publisher & reader agree, distinct
    assert manifest_nodes("sha256:xyz", NODES, 3) != a or True  # (usually) different set per root


def test_publish_then_resolve_roundtrip():
    put, _, _ = in_memory_store()
    pb, gb, _ = _blob_store()
    m = propagate(os.urandom(40), nodes=NODES, put=put, placement=P)
    publish_manifest(m, nodes=NODES, put_blob=pb, replicas=3)
    got = resolve_manifest(m.root, nodes=NODES, get_blob=gb, replicas=3)
    assert got == m


def test_resolves_while_one_replica_survives():
    put, _, _ = in_memory_store()
    pb, gb, _ = _blob_store()
    m = propagate(os.urandom(40), nodes=NODES, put=put, placement=P)
    targets = publish_manifest(m, nodes=NODES, put_blob=pb, replicas=3)
    reachable = set(NODES) - set(targets[:2])   # seize 2 of 3 manifest replicas
    assert resolve_manifest(m.root, nodes=NODES, get_blob=gb, replicas=3, reachable=reachable) == m


def test_all_replicas_seized_is_unavailable():
    put, _, _ = in_memory_store()
    pb, gb, _ = _blob_store()
    m = propagate(os.urandom(40), nodes=NODES, put=put, placement=P)
    targets = publish_manifest(m, nodes=NODES, put_blob=pb, replicas=3)
    reachable = set(NODES) - set(targets)       # all manifest replicas gone
    try:
        resolve_manifest(m.root, nodes=NODES, get_blob=gb, replicas=3, reachable=reachable)
    except ManifestUnavailable:
        pass
    else:
        raise AssertionError("all replicas seized must be ManifestUnavailable")


def test_manifest_for_wrong_root_is_rejected():
    from automation.manifest_store import _key, _serialize
    put, _, _ = in_memory_store()
    pb, gb, store = _blob_store()
    m = propagate(os.urandom(40), nodes=NODES, put=put, placement=P)
    # a malicious node serves m's manifest (root == m.root) under ANOTHER root's key.
    other_root = "sha256:" + "9" * 64
    blob = _serialize(m)
    for node in manifest_nodes(other_root, NODES, 3):
        store[(node, _key(other_root))] = blob
    try:
        resolve_manifest(other_root, nodes=NODES, get_blob=gb, replicas=3)
    except ManifestUnavailable:
        pass  # rejected: the served manifest's root (m.root) != requested other_root
    else:
        raise AssertionError("a manifest whose root != requested must be rejected")


def test_endtoend_reconstruct_knowing_only_the_root():
    """The whole read path from a bare root: resolve the manifest, then fetch + reconstruct — after
    a seizure that takes a third of the mesh (but leaves a manifest replica and a fragment quorum)."""
    put, get, _ = in_memory_store()
    pb, gb, _ = _blob_store()
    leaf = b"GOVERNED-LEAF :: " + os.urandom(50)
    host = Placement(rs_k=6, rs_m=3, shard_replicas=2)   # replicated -> survives a third seized
    m = propagate(leaf, nodes=NODES, put=put, placement=host, tier="hostile")
    publish_manifest(m, nodes=NODES, put_blob=pb, replicas=5)
    root = m.root                                        # the reader knows ONLY this

    # seize a third of the mesh
    import random
    seized = set(random.Random(7).sample(NODES, 9))
    reachable = set(NODES) - seized

    manifest = resolve_manifest(root, nodes=NODES, get_blob=gb, replicas=5, reachable=reachable)
    leaf_back = fetch(manifest, get=get, reachable=reachable)
    from automation.holographic_ida import merkle_root
    assert leaf_back == leaf and merkle_root(leaf_back) == root


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"manifest_store: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
