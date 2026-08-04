"""The sovereign Drive: write by name on one device, read it on another, survive seizure."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.mesh_fs_store import MeshFsStore  # noqa: E402
from automation.mesh_namespace import NamespaceRef, publish_ref, resolve_ref  # noqa: E402
from automation.mesh_sync import (  # noqa: E402
    FileNotFound, get_file, list_files, pull_dir, push_dir, put_file,
)
from automation.storage_resilience import Placement

NODES = [f"n{i:02d}" for i in range(27)]
HOST = Placement(rs_k=6, rs_m=3, shard_replicas=2)  # replicated -> survives seizure


def _mesh():
    return MeshFsStore(Path(tempfile.mkdtemp()))


def test_write_by_name_read_by_name():
    m = _mesh()
    put_file(m, NODES, "/notes/todo.md", b"buy milk", writer="laptop", placement=HOST)
    data, ref = get_file(m, NODES, "/notes/todo.md")
    assert data == b"buy milk" and ref.version == 1


def test_update_bumps_version_and_content():
    m = _mesh()
    put_file(m, NODES, "/doc.txt", b"v1", writer="laptop", placement=HOST)
    put_file(m, NODES, "/doc.txt", b"v2 longer content", writer="laptop", placement=HOST)
    data, ref = get_file(m, NODES, "/doc.txt")
    assert data == b"v2 longer content" and ref.version == 2


def test_unknown_name_raises():
    m = _mesh()
    try:
        get_file(m, NODES, "/nope.txt")
    except FileNotFound:
        pass
    else:
        raise AssertionError("unknown name must raise FileNotFound")


def test_list_files():
    m = _mesh()
    for p in ("/a.txt", "/b/c.txt", "/a.txt"):  # a.txt twice -> one entry
        put_file(m, NODES, p, os.urandom(20), writer="laptop", placement=HOST)
    assert list_files(m, NODES) == ["/a.txt", "/b/c.txt"]


def test_last_writer_wins_across_replicas():
    m = _mesh()
    publish_ref(NamespaceRef("/x", "sha256:" + "1"*64, 1, "2026-01-01T00:00:00Z", "phone"),
                nodes=NODES, put_blob=m.put_blob, replicas=5)
    publish_ref(NamespaceRef("/x", "sha256:" + "2"*64, 2, "2026-01-02T00:00:00Z", "laptop"),
                nodes=NODES, put_blob=m.put_blob, replicas=5)
    r = resolve_ref("/x", nodes=NODES, get_blob=m.get_blob, replicas=5)
    assert r.version == 2 and r.writer == "laptop"  # the later write wins


def test_survives_seizure():
    m = _mesh()
    put_file(m, NODES, "/secret.txt", b"survives the raid " + os.urandom(40),
             writer="laptop", placement=HOST)
    for node in ("n03", "n11", "n19"):  # seize a chunk of the mesh
        m.seize(node)
    reachable = set(NODES) - {"n03", "n11", "n19"}
    data, ref = get_file(m, NODES, "/secret.txt", reachable=reachable)
    assert data.startswith(b"survives the raid")


def test_two_device_dir_sync_roundtrip():
    """Device A pushes a folder; device B (its own local dir, same mesh) pulls the whole Drive."""
    m = _mesh()
    devA = Path(tempfile.mkdtemp()); devB = Path(tempfile.mkdtemp())
    (devA / "notes").mkdir()
    (devA / "notes" / "todo.md").write_bytes(b"buy milk")
    (devA / "photo.bin").write_bytes(os.urandom(200))
    pushed = push_dir(m, NODES, devA, writer="laptop", placement=HOST)
    assert set(pushed) == {"/notes/todo.md", "/photo.bin"}

    pulled = pull_dir(m, NODES, devB)
    assert set(pulled) == {"/notes/todo.md", "/photo.bin"}
    assert (devB / "notes" / "todo.md").read_bytes() == b"buy milk"
    assert (devB / "photo.bin").read_bytes() == (devA / "photo.bin").read_bytes()

    # edit on A, re-push, re-pull on B -> B sees the new version
    (devA / "notes" / "todo.md").write_bytes(b"buy milk and eggs")
    push_dir(m, NODES, devA, writer="laptop", placement=HOST)
    pull_dir(m, NODES, devB)
    assert (devB / "notes" / "todo.md").read_bytes() == b"buy milk and eggs"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"mesh_sync: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
