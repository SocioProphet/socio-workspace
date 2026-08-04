"""The mutable name layer — path → current content, versioned, survives seizure.

Holographic dispersal (leaf_propagation) stores IMMUTABLE content addressed by its Merkle root.
A Drive needs the other half: a MUTABLE pointer from a human name ("/notes/todo.md") to the root
of its current version, resolvable by name from any device, that updates when the file changes.
This is that pointer — a last-writer-wins register per path, replicated to a deterministic set of
nodes (rendezvous / HRW hashing of the name), so a reader who knows only the path finds the current
version, and it survives a node being seized exactly like the manifests do.

Conflict handling is deliberate and simple (matching what a single-user, multi-device Drive needs):
resolve reads every reachable replica and returns the HIGHEST (version, timestamp, writer) — a
last-writer-wins register. Concurrent edits from two devices don't corrupt; the later write wins and
the earlier remains fetchable by its root (a conflict-copy policy is a follow-up, not a data loss).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence

PutBlob = Callable[[str, str, bytes], None]
GetBlob = Callable[[str, str], Optional[bytes]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _weight(key: str, node: str) -> bytes:
    return hashlib.sha256((key + "|" + node).encode("utf-8")).digest()


def ref_nodes(key: str, nodes: Sequence[str], replicas: int) -> List[str]:
    """The deterministic replica set for a name — the ``replicas`` highest-rendezvous-weight nodes.
    Writer and reader compute this identically, so a name is findable with no directory service."""
    if replicas < 1 or replicas > len(nodes):
        raise ValueError(f"replicas must be in 1..{len(nodes)}")
    return sorted(set(nodes), key=lambda n: _weight(key, n), reverse=True)[:replicas]


def _blob_key(name: str) -> str:
    return "ns:" + name


def publish_blob(name: str, blob: bytes, *, nodes: Sequence[str], put_blob: PutBlob,
                 replicas: int = 5) -> List[str]:
    """Replicate ``blob`` under ``name`` to that name's rendezvous nodes. Returns the targets."""
    targets = ref_nodes(name, nodes, replicas)
    for node in targets:
        put_blob(node, _blob_key(name), blob)
    return targets


def read_all(name: str, *, nodes: Sequence[str], get_blob: GetBlob, replicas: int = 5,
             reachable: Optional[set] = None) -> List[bytes]:
    """Every reachable replica's bytes for ``name`` (they may disagree — the caller merges)."""
    out: List[bytes] = []
    for node in ref_nodes(name, nodes, replicas):
        if reachable is not None and node not in reachable:
            continue
        try:
            b = get_blob(node, _blob_key(name))
        except Exception:  # noqa: BLE001 — an errored read is an unreachable replica, not absence
            b = None
        if b is not None:
            out.append(b)
    return out


@dataclass(frozen=True)
class NamespaceRef:
    path: str        # the logical name, e.g. "/notes/todo.md"
    root: str        # manifest root (sha256:…) of the current content version
    version: int     # monotonic per path
    updated_at: str
    writer: str      # device id — the last-writer-wins tiebreak

    def _key(self):  # the ordering used to pick the winner across replicas
        return (self.version, self.updated_at, self.writer)

    def to_bytes(self) -> bytes:
        return json.dumps({"path": self.path, "root": self.root, "version": self.version,
                           "updated_at": self.updated_at, "writer": self.writer},
                          sort_keys=True).encode("utf-8")

    @staticmethod
    def from_bytes(b: bytes) -> "NamespaceRef":
        d = json.loads(b)
        return NamespaceRef(path=d["path"], root=d["root"], version=int(d["version"]),
                            updated_at=d["updated_at"], writer=d["writer"])


def publish_ref(ref: NamespaceRef, *, nodes: Sequence[str], put_blob: PutBlob,
                replicas: int = 5) -> List[str]:
    return publish_blob(ref.path, ref.to_bytes(), nodes=nodes, put_blob=put_blob, replicas=replicas)


def resolve_ref(path: str, *, nodes: Sequence[str], get_blob: GetBlob, replicas: int = 5,
                reachable: Optional[set] = None) -> Optional[NamespaceRef]:
    """The current pointer for ``path`` — the last-writer-wins winner across reachable replicas,
    or None if the name isn't reachable / doesn't exist."""
    best: Optional[NamespaceRef] = None
    for b in read_all(path, nodes=nodes, get_blob=get_blob, replicas=replicas, reachable=reachable):
        try:
            r = NamespaceRef.from_bytes(b)
        except (ValueError, KeyError):
            continue
        if r.path != path:
            continue  # a replica serving the wrong name — reject
        if best is None or r._key() > best._key():
            best = r
    return best
