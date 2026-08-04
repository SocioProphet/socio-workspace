#!/usr/bin/env python3
"""Demo: a sovereign Drive across two devices — write on one, read on the other, survive seizure.

Two "devices" (a laptop and a phone, each its own local folder) share one mesh. The laptop writes
files; the phone reads them by name; the laptop edits one; the phone sees the new version; then a
third of the mesh is seized and the phone still reads everything. No custodian, no account — the
files live on your own nodes, addressed holographically, findable by name.

Run: python3 tools/demo_mesh_drive.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.mesh_fs_store import MeshFsStore  # noqa: E402
from automation.mesh_sync import get_file, list_files, pull_dir, push_dir, put_file  # noqa: E402
from automation.storage_resilience import Placement  # noqa: E402

NODES = [f"n{i:02d}" for i in range(27)]
HOST = Placement(rs_k=6, rs_m=3, shard_replicas=2)


def main():
    mesh = MeshFsStore(Path(tempfile.mkdtemp()))
    laptop = Path(tempfile.mkdtemp()); phone = Path(tempfile.mkdtemp())
    line = "=" * 74
    print(line); print("SOVEREIGN DRIVE — two devices, one mesh, no custodian"); print(line)

    (laptop / "notes").mkdir()
    (laptop / "notes" / "todo.md").write_text("buy milk")
    (laptop / "keys.txt").write_text("sovereign, not rented")
    pushed = push_dir(mesh, NODES, laptop, writer="laptop", placement=HOST)
    print(f"\nlaptop writes {len(pushed)} files -> mesh: {pushed}")

    print("\nphone lists the Drive (knows only the mesh):", list_files(mesh, NODES))
    pull_dir(mesh, NODES, phone)
    print("phone reads /notes/todo.md ->", (phone / "notes" / "todo.md").read_text())

    print("\nlaptop edits /notes/todo.md and re-syncs...")
    (laptop / "notes" / "todo.md").write_text("buy milk and eggs")
    push_dir(mesh, NODES, laptop, writer="laptop", placement=HOST)
    _, ref = get_file(mesh, NODES, "/notes/todo.md")
    pull_dir(mesh, NODES, phone)
    print(f"phone re-reads /notes/todo.md (v{ref.version}) ->", (phone / "notes" / "todo.md").read_text())

    seized = ["n03", "n11", "n19"]
    for nd in seized:
        mesh.seize(nd)
    reachable = set(NODES) - set(seized)
    data, ref = get_file(mesh, NODES, "/keys.txt", reachable=reachable)
    print(f"\nadversary seizes {len(seized)} of {len(NODES)} nodes; phone still reads /keys.txt ->",
          data.decode())

    print("\n" + line)
    print("Files found by name, versioned, reconstructed from a quorum, verified against their")
    print("Merkle roots — and they survive a raid. iCloud cannot say any of those things.")
    print(line)


if __name__ == "__main__":
    main()
