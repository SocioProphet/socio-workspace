"""The propagation path over a REAL on-disk transport: write, seize (rm node dirs), reconstruct
from a bare root, and survive a process restart (a fresh store over the same directory)."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.holographic_ida import merkle_root  # noqa: E402
from automation.leaf_propagation import LeafUnavailable, fetch, propagate  # noqa: E402
from automation.manifest_store import publish_manifest, resolve_manifest  # noqa: E402
from automation.mesh_fs_store import MeshFsStore  # noqa: E402
from automation.storage_resilience import Placement

NODES = [f"n{i:02d}" for i in range(27)]
HOST = Placement(rs_k=6, rs_m=3, shard_replicas=2)  # replicated -> survives a third seized


def _store():
    return MeshFsStore(Path(tempfile.mkdtemp()))


def test_write_read_on_disk():
    fs = _store()
    leaf = b"on-disk governed leaf " + os.urandom(50)
    m = propagate(leaf, nodes=NODES, put=fs.put, placement=HOST)
    assert fetch(m, get=fs.get) == leaf


def test_fragments_actually_persisted_as_files():
    fs = _store()
    m = propagate(os.urandom(40), nodes=NODES, put=fs.put, placement=Placement(rs_k=6, rs_m=3))
    written = list(fs.root.rglob("frag-*"))
    assert len(written) == 9   # n fragments, R=1 -> 9 files on disk


def test_survives_a_fresh_store_over_the_same_dir():
    d = Path(tempfile.mkdtemp())
    leaf = os.urandom(60)
    m = propagate(leaf, nodes=NODES, put=MeshFsStore(d).put, placement=HOST)
    publish_manifest(m, nodes=NODES, put_blob=MeshFsStore(d).put_blob, replicas=5)
    # a brand-new process/store instance over the same directory can still read it back.
    fs2 = MeshFsStore(d)
    got = resolve_manifest(m.root, nodes=NODES, get_blob=fs2.get_blob, replicas=5)
    assert fetch(got, get=fs2.get) == leaf


def test_endtoend_seizure_on_real_disk_knowing_only_root():
    fs = _store()
    leaf = b"GOVERNED-LEAF :: " + os.urandom(64)
    m = propagate(leaf, nodes=NODES, put=fs.put, placement=HOST)
    publish_manifest(m, nodes=NODES, put_blob=fs.put_blob, replicas=5)
    root = m.root

    # adversary SEIZES a third of the mesh — physically removes those node directories.
    import random
    seized = random.Random(11).sample(NODES, 9)
    for node in seized:
        fs.seize(node)
    reachable = set(NODES) - set(seized)

    manifest = resolve_manifest(root, nodes=NODES, get_blob=fs.get_blob, replicas=5, reachable=reachable)
    back = fetch(manifest, get=fs.get, reachable=reachable)
    assert back == leaf and merkle_root(back) == root


def test_total_loss_is_unavailable_not_wrong():
    fs = _store()
    leaf = os.urandom(40)
    m = propagate(leaf, nodes=NODES, put=fs.put, placement=Placement(rs_k=6, rs_m=3))
    for node in NODES:
        fs.seize(node)                    # seize everything
    try:
        fetch(m, get=fs.get)
    except LeafUnavailable:
        pass                              # fail-closed: unavailable, never a wrong reconstruction
    else:
        raise AssertionError("total loss must be LeafUnavailable")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"mesh_fs_store: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
