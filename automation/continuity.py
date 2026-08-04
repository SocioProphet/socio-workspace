"""Continuity over the mesh — universal clipboard, beam (AirDrop), and handoff.

Apple's continuity magic — copy on one device and paste on another, AirDrop a file, hand off an
activity mid-task — is the second half of "it just works." All of it is thin on top of the sovereign
Drive: continuity is just a few well-known names in the same namespace, so it inherits versioning,
seizure-survival, and Merkle-verified content for free, and it runs over disk or the network
unchanged. No proximity radios, no Apple ID, no cloud relay — device to device across your own mesh.

  * CLIPBOARD — a single well-known slot (last-writer-wins): set on one device, get on another.
  * BEAM      — send bytes to a specific device's inbox; each item gets a unique name so concurrent
                sends never collide (grow-only), and the recipient lists + fetches them.
  * HANDOFF   — a per-activity pointer to the current state + which device owns it, so another
                device can resume exactly where you left off.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Sequence, Tuple

from automation.mesh_namespace import NamespaceRef
from automation.mesh_sync import get_file, list_files, put_file
from automation.storage_resilience import Placement

CLIPBOARD = "/continuity/clipboard"
_INBOX = "/continuity/inbox/"
_HANDOFF = "/continuity/handoff/"


# ── universal clipboard ──────────────────────────────────────────────────────────────────────

def clipboard_set(store, nodes: Sequence[str], data: bytes, *, writer: str,
                  placement: Optional[Placement] = None) -> None:
    put_file(store, nodes, CLIPBOARD, data, writer=writer, placement=placement)


def clipboard_get(store, nodes: Sequence[str], *, reachable: Optional[set] = None) -> Optional[bytes]:
    from automation.mesh_sync import FileNotFound
    try:
        data, _ = get_file(store, nodes, CLIPBOARD, reachable=reachable)
        return data
    except FileNotFound:
        return None


# ── beam (AirDrop): send to a device's inbox ─────────────────────────────────────────────────

def beam(store, nodes: Sequence[str], to_device: str, data: bytes, *, writer: str,
         placement: Optional[Placement] = None) -> str:
    """Send ``data`` to ``to_device``'s inbox. Returns the item's logical path. Each item is a
    UNIQUE name, so two devices beaming at once never overwrite each other (grow-only)."""
    path = f"{_INBOX}{to_device}/{uuid.uuid4().hex}"
    put_file(store, nodes, path, data, writer=writer, placement=placement)
    return path


def inbox(store, nodes: Sequence[str], device: str, *,
          reachable: Optional[set] = None) -> List[Tuple[str, bytes]]:
    """Everything beamed to ``device`` — (path, bytes) per item. The recipient tracks what it has
    already consumed locally; the mesh keeps every item until then (no server-side delete needed)."""
    prefix = f"{_INBOX}{device}/"
    out: List[Tuple[str, bytes]] = []
    for path in list_files(store, nodes, reachable=reachable):
        if path.startswith(prefix):
            data, _ = get_file(store, nodes, path, reachable=reachable)
            out.append((path, data))
    return out


# ── handoff: resume an activity on another device ────────────────────────────────────────────

def handoff_set(store, nodes: Sequence[str], activity: str, state: bytes, *, device: str,
                placement: Optional[Placement] = None) -> NamespaceRef:
    """Publish the current state of ``activity`` (e.g. "editor:report.md"); ``device`` is recorded
    as the owner (the ref's writer), so another device knows where it was handed off from."""
    return put_file(store, nodes, f"{_HANDOFF}{activity}", state, writer=device, placement=placement)


def handoff_get(store, nodes: Sequence[str], activity: str, *,
                reachable: Optional[set] = None) -> Optional[Tuple[bytes, str, int]]:
    """Resume ``activity``: returns (state, owning_device, version), or None if never handed off."""
    from automation.mesh_sync import FileNotFound
    try:
        data, ref = get_file(store, nodes, f"{_HANDOFF}{activity}", reachable=reachable)
        return data, ref.writer, ref.version
    except FileNotFound:
        return None
