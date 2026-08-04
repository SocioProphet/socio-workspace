"""A real, on-disk mesh transport — each node is a directory of fragments and manifest blobs.

The propagation path (leaf_propagation, manifest_store) takes its I/O as injected ``put``/``get`` /
``put_blob``/``get_blob`` seams so the logic is testable in memory. This is the first CONCRETE
transport behind those seams: a filesystem store where each mesh node maps to a directory (a stand-
in for that node's object store / PVC), fragments and manifests are files, and writes are atomic
(temp + rename) so a reader never sees a half-written fragment. It persists across process restarts,
works across a simulated mesh of local directories, and maps directly to a per-node bucket or volume
in a real deployment — the same code, a different directory root per node.

Unreachability is modelled honestly: a node whose directory is absent (seized / partitioned away)
simply yields None on read, which the path treats as an unreachable fragment — never as healthy.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


class MeshFsStore:
    """Fragments at ``<root>/<node>/frag-<id>``; manifest blobs at ``<root>/<node>/blob-<h>``."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _node_dir(self, node: str) -> Path:
        # node ids are mesh-controlled labels; keep the path inside root regardless.
        safe = hashlib.sha256(node.encode("utf-8")).hexdigest()[:16] + "-" + "".join(
            c if c.isalnum() or c in "-_." else "_" for c in node)[:40]
        return self.root / safe

    def _write_atomic(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)  # atomic on POSIX — a reader sees the whole file or nothing

    def _read(self, path: Path) -> Optional[bytes]:
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None            # absent node/fragment == unreachable, not corrupt

    # ── fragment I/O (put/get seams for leaf_propagation) ────────────────────────────────────
    def put(self, node: str, frag: int, data: bytes) -> None:
        self._write_atomic(self._node_dir(node) / f"frag-{int(frag)}", data)

    def get(self, node: str, frag: int) -> Optional[bytes]:
        return self._read(self._node_dir(node) / f"frag-{int(frag)}")

    # ── blob I/O (put_blob/get_blob seams for manifest_store) ─────────────────────────────────
    def put_blob(self, node: str, key: str, data: bytes) -> None:
        self._write_atomic(self._node_dir(node) / self._blob_name(key), data)

    def get_blob(self, node: str, key: str) -> Optional[bytes]:
        return self._read(self._node_dir(node) / self._blob_name(key))

    @staticmethod
    def _blob_name(key: str) -> str:
        return "blob-" + hashlib.sha256(key.encode("utf-8")).hexdigest()

    # ── seizure model: a node's directory being gone == that node captured/partitioned away ───
    def seize(self, node: str) -> None:
        """Simulate seizure of a node: remove its whole store (irreversible from the mesh's view)."""
        import shutil
        d = self._node_dir(node)
        if d.exists():
            shutil.rmtree(d)
