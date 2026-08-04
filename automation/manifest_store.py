"""Make a leaf's manifest findable by its Merkle root alone — no directory, under seizure.

``leaf_propagation.fetch`` needs the manifest (where the fragments live). But the manifest is then a
single point of failure: lose it and the surviving fragments are unfindable. This replicates the
manifest to a set of nodes chosen DETERMINISTICALLY from the root by rendezvous (highest-random-
weight) hashing — so a reader who knows only the root computes the SAME candidate nodes and reads
the manifest from any one that survives, with no coordination and no lookup service. The manifest is
tiny (commitment + placement, never leaf bytes), so full replication to a handful of nodes is cheap.

Trust: a reader accepts a served manifest only if its ``root`` matches the one requested; a node
that serves a manifest for a different root is rejected. A manifest that lies about fragment
locations cannot forge a leaf — ``fetch`` re-verifies every reconstruction against the root — so the
worst a bad manifest can do is cause a detected failure, never a silent wrong read.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, List, Optional, Sequence

from automation.leaf_propagation import PropagationManifest

# put_blob(node, key, bytes) -> None ; get_blob(node, key) -> bytes | None
PutBlob = Callable[[str, str, bytes], None]
GetBlob = Callable[[str, str], Optional[bytes]]


class ManifestUnavailable(Exception):
    """The manifest for a root is not reachable on any of its deterministic replica nodes."""


def _weight(root: str, node: str) -> bytes:
    return hashlib.sha256((root + "|" + node).encode("utf-8")).digest()


def manifest_nodes(root: str, nodes: Sequence[str], replicas: int) -> List[str]:
    """The deterministic set of nodes that hold ``root``'s manifest — the ``replicas`` nodes of
    highest rendezvous weight for this root. Publisher and reader compute this identically."""
    if replicas < 1 or replicas > len(nodes):
        raise ValueError(f"replicas must be in 1..{len(nodes)}")
    ranked = sorted(set(nodes), key=lambda n: _weight(root, n), reverse=True)
    return ranked[:replicas]


def _key(root: str) -> str:
    return f"manifest:{root}"


def _serialize(m: PropagationManifest) -> bytes:
    return json.dumps({
        "root": m.root, "k": m.k, "n": m.n, "orig_len": m.orig_len, "tier": m.tier,
        "replicas": m.replicas,
        "fragment_nodes": {str(x): list(nl) for x, nl in m.fragment_nodes.items()},
    }, sort_keys=True).encode("utf-8")


def _deserialize(blob: bytes) -> PropagationManifest:
    d = json.loads(blob)
    return PropagationManifest(
        root=d["root"], k=int(d["k"]), n=int(d["n"]), orig_len=int(d["orig_len"]),
        tier=d["tier"], replicas=int(d["replicas"]),
        fragment_nodes={int(x): list(nl) for x, nl in d["fragment_nodes"].items()},
    )


def publish_manifest(manifest: PropagationManifest, *, nodes: Sequence[str], put_blob: PutBlob,
                     replicas: int = 3) -> List[str]:
    """Replicate ``manifest`` to its ``replicas`` deterministic nodes. Returns the target nodes."""
    blob = _serialize(manifest)
    targets = manifest_nodes(manifest.root, nodes, replicas)
    for node in targets:
        put_blob(node, _key(manifest.root), blob)
    return targets


def resolve_manifest(root: str, *, nodes: Sequence[str], get_blob: GetBlob,
                     replicas: int = 3, reachable: Optional[set] = None) -> PropagationManifest:
    """Find and return the manifest for ``root`` from any reachable replica. Fail-closed: raises
    ManifestUnavailable if none of its replica nodes is reachable / holds it."""
    for node in manifest_nodes(root, nodes, replicas):
        if reachable is not None and node not in reachable:
            continue
        try:
            blob = get_blob(node, _key(root))
        except Exception:  # noqa: BLE001 — an errored read is an unreachable replica, not absence of proof
            blob = None
        if blob is None:
            continue
        m = _deserialize(blob)
        if m.root != root:
            continue  # this node served a manifest for a DIFFERENT root — reject, try the next
        return m
    raise ManifestUnavailable(f"manifest for {root} not reachable on any of its {replicas} replicas")
