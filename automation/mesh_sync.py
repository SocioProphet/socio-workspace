"""A sovereign Drive on the mesh — the iCloud-Drive experience, without the custodian.

Composes the three primitives into a file service that "just works" across devices:
  * CONTENT — a file's bytes are dispersed holographically (leaf_propagation): any k-of-n fragments
    reconstruct it, Merkle-verified, surviving a third of the mesh seized.
  * LOCATION — the fragment manifest is findable by the content's Merkle root (manifest_store).
  * NAME — a mutable, versioned pointer maps the human path to the current root (mesh_namespace),
    so any device resolves "the current /notes/todo.md" by name, and it updates on every write.

The result: put a file on one device, read it by name on another; edit it, the other device sees the
new version; and none of it lives with a custodian who can lock you out — it lives on your own nodes,
survives seizure, and every version is provable against its Merkle root. That is the thing iCloud
structurally cannot offer: it IS the custody it sells you.

The store is injected (any object with put/get/put_blob/get_blob — MeshFsStore on disk, MeshHttpStore
over the network), so the same Drive runs on local volumes or across physical nodes unchanged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from automation.leaf_propagation import fetch, propagate
from automation.manifest_store import publish_manifest, resolve_manifest
from automation.mesh_namespace import (
    NamespaceRef, publish_blob, publish_ref, read_all, resolve_ref,
)
from automation.storage_resilience import Placement

_INDEX = "__index__"


class FileNotFound(Exception):
    """No reachable name pointer for this path (unknown, or its replicas are all seized)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _index_read(store, nodes: Sequence[str], replicas: int, reachable: Optional[set] = None) -> set:
    """The directory listing — a grow-only union of every reachable index replica's path set."""
    paths: set = set()
    for b in read_all(_INDEX, nodes=nodes, get_blob=store.get_blob, replicas=replicas, reachable=reachable):
        try:
            paths |= set(json.loads(b))
        except (ValueError, TypeError):
            continue
    return paths


def _index_add(store, nodes: Sequence[str], path: str, replicas: int) -> None:
    paths = _index_read(store, nodes, replicas)
    paths.add(path)
    publish_blob(_INDEX, json.dumps(sorted(paths)).encode("utf-8"),
                 nodes=nodes, put_blob=store.put_blob, replicas=replicas)


def put_file(store, nodes: Sequence[str], path: str, data: bytes, *, writer: str,
             placement: Optional[Placement] = None, replicas: int = 5) -> NamespaceRef:
    """WRITE a file: disperse its bytes, publish the manifest, bump the versioned name pointer, and
    add it to the directory index. Returns the new ref (version, root)."""
    m = propagate(data, nodes=nodes, put=store.put, placement=placement)
    publish_manifest(m, nodes=nodes, put_blob=store.put_blob, replicas=replicas)
    cur = resolve_ref(path, nodes=nodes, get_blob=store.get_blob, replicas=replicas)
    version = (cur.version + 1) if cur else 1
    ref = NamespaceRef(path=path, root=m.root, version=version, updated_at=_now(), writer=writer)
    publish_ref(ref, nodes=nodes, put_blob=store.put_blob, replicas=replicas)
    _index_add(store, nodes, path, replicas)
    return ref


def get_file(store, nodes: Sequence[str], path: str, *, replicas: int = 5,
             reachable: Optional[set] = None) -> Tuple[bytes, NamespaceRef]:
    """READ a file by NAME: resolve the current pointer, find its manifest by root, reconstruct a
    quorum of fragments (Merkle-verified). Raises FileNotFound if the name isn't reachable."""
    ref = resolve_ref(path, nodes=nodes, get_blob=store.get_blob, replicas=replicas, reachable=reachable)
    if ref is None:
        raise FileNotFound(path)
    m = resolve_manifest(ref.root, nodes=nodes, get_blob=store.get_blob, replicas=replicas, reachable=reachable)
    return fetch(m, get=store.get, reachable=reachable), ref


def list_files(store, nodes: Sequence[str], *, replicas: int = 5,
               reachable: Optional[set] = None) -> List[str]:
    return sorted(_index_read(store, nodes, replicas, reachable))


# ── directory reconcile — the "it just syncs" loop across devices ────────────────────────────

def push_dir(store, nodes: Sequence[str], local_dir: Path, *, writer: str,
             placement: Optional[Placement] = None, replicas: int = 5) -> List[str]:
    """Upload every file under ``local_dir`` (logical path = its path relative to the dir)."""
    local_dir = Path(local_dir)
    pushed: List[str] = []
    for p in sorted(local_dir.rglob("*")):
        if p.is_file():
            rel = "/" + str(p.relative_to(local_dir)).replace("\\", "/")
            put_file(store, nodes, rel, p.read_bytes(), writer=writer, placement=placement, replicas=replicas)
            pushed.append(rel)
    return pushed


def pull_dir(store, nodes: Sequence[str], local_dir: Path, *, replicas: int = 5,
             reachable: Optional[set] = None) -> List[str]:
    """Materialize every named file into ``local_dir`` — the other device's view of the Drive."""
    local_dir = Path(local_dir)
    pulled: List[str] = []
    for path in list_files(store, nodes, replicas=replicas, reachable=reachable):
        try:
            data, _ = get_file(store, nodes, path, replicas=replicas, reachable=reachable)
        except FileNotFound:
            continue
        dest = local_dir / path.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        pulled.append(path)
    return pulled
