"""Continuity across devices on the mesh — clipboard, beam (AirDrop), handoff."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.continuity import (  # noqa: E402
    beam, clipboard_get, clipboard_set, handoff_get, handoff_set, inbox,
)
from automation.mesh_fs_store import MeshFsStore  # noqa: E402
from automation.storage_resilience import Placement

NODES = [f"n{i:02d}" for i in range(27)]
HOST = Placement(rs_k=6, rs_m=3, shard_replicas=2)


def _mesh():
    return MeshFsStore(Path(tempfile.mkdtemp()))


def test_universal_clipboard():
    m = _mesh()
    assert clipboard_get(m, NODES) is None            # empty at first
    clipboard_set(m, NODES, b"copied on the laptop", writer="laptop", placement=HOST)
    assert clipboard_get(m, NODES) == b"copied on the laptop"   # pasted on the phone
    clipboard_set(m, NODES, b"newer copy", writer="phone", placement=HOST)
    assert clipboard_get(m, NODES) == b"newer copy"   # last write wins


def test_beam_to_device_inbox():
    m = _mesh()
    beam(m, NODES, "phone", b"photo-1", writer="laptop", placement=HOST)
    beam(m, NODES, "phone", b"photo-2", writer="laptop", placement=HOST)
    beam(m, NODES, "tablet", b"not for phone", writer="laptop", placement=HOST)
    items = inbox(m, NODES, "phone")
    payloads = sorted(d for _, d in items)
    assert payloads == [b"photo-1", b"photo-2"]        # only phone's items, both delivered


def test_concurrent_beams_do_not_collide():
    m = _mesh()
    p1 = beam(m, NODES, "phone", b"a", writer="laptop", placement=HOST)
    p2 = beam(m, NODES, "phone", b"b", writer="watch", placement=HOST)
    assert p1 != p2 and len(inbox(m, NODES, "phone")) == 2   # unique names -> no lost update


def test_handoff_resume_on_another_device():
    m = _mesh()
    assert handoff_get(m, NODES, "editor:report.md") is None
    handoff_set(m, NODES, "editor:report.md", b"cursor@line42;draft-state", device="laptop", placement=HOST)
    got = handoff_get(m, NODES, "editor:report.md")
    assert got is not None
    state, device, version = got
    assert state == b"cursor@line42;draft-state" and device == "laptop" and version == 1
    # laptop moves on; phone takes over
    handoff_set(m, NODES, "editor:report.md", b"cursor@line80", device="phone", placement=HOST)
    _, device2, version2 = handoff_get(m, NODES, "editor:report.md")
    assert device2 == "phone" and version2 == 2


def test_continuity_survives_seizure():
    m = _mesh()
    clipboard_set(m, NODES, b"resilient clip " + os.urandom(30), writer="laptop", placement=HOST)
    for nd in ("n05", "n12", "n20"):
        m.seize(nd)
    reachable = set(NODES) - {"n05", "n12", "n20"}
    assert clipboard_get(m, NODES, reachable=reachable).startswith(b"resilient clip")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"continuity: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
