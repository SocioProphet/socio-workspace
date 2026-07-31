from __future__ import annotations


def classify_conflict(local_dirty: bool, remote_delete: bool, authority_mode: str = "local_first") -> str:
    """Return the minimal conflict action aligned to the documented conflict matrix."""
    if local_dirty and remote_delete:
        return "manual_reconcile"
    if authority_mode == "local_first":
        return "local_wins"
    if authority_mode == "provider_first":
        return "remote_wins"
    return "manual_reconcile"
