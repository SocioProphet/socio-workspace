"""The canonical event envelope + EpistemicLevel — the estate's shared provenance vocabulary.

Debater 2.0 and the Stardust-successor architecture stamp every event with one envelope
(`message_id` ULID, `trace_id` UUIDv4, `span_id` 16-hex, `emitted_at` RFC3339, `schema_version`,
`content_sha256`) and grade every claim with an EpistemicLevel. This module lets the self-heal
loop speak that vocabulary, so its beacons and decision receipts are legible to Sherlock, the
audit ledger, and the rest of the reasoning spine — convergence step 2. No new dependencies.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

SCHEMA_VERSION = "v1"

# The estate's governing EpistemicLevel color system (Stardust-successor), weakest warrant last.
EPISTEMIC_LEVELS = ("proved", "bounded", "empirical", "synthetic", "speculative", "rejected")

_ENVELOPE_KEYS = {"message_id", "trace_id", "span_id", "emitted_at", "schema_version",
                  "content_sha256", "epistemic_level"}
_VOLATILE_KEYS = {"observed_at", "decided_at", "address"}
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(now_ms: Optional[int] = None) -> str:
    """A ULID: 48-bit millisecond time + 80-bit randomness, Crockford base32 (26 chars)."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    value = ((now_ms & ((1 << 48) - 1)) << 80) | int.from_bytes(os.urandom(10), "big")
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def _now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def content_hash(payload: dict) -> str:
    """sha256 over the canonical (sorted) JSON of the semantic payload — deterministic."""
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def stamp(event: dict, *, trace_id: Optional[str] = None) -> dict:
    """Return a copy of `event` with the canonical envelope attached (idempotent per field).

    `content_sha256` is computed over the event's SEMANTIC content (envelope + volatile fields
    excluded), so the same condition hashes the same regardless of when it was observed.
    An existing `trace_id` on the event is preserved (trace propagates across the pipeline).
    """
    e = dict(event)
    e.setdefault("message_id", ulid())
    e.setdefault("trace_id", trace_id or e.get("trace_id") or str(uuid.uuid4()))
    e.setdefault("span_id", os.urandom(8).hex())
    e.setdefault("emitted_at", _now_z())
    e.setdefault("schema_version", SCHEMA_VERSION)
    payload = {k: v for k, v in e.items() if k not in _ENVELOPE_KEYS and k not in _VOLATILE_KEYS}
    e["content_sha256"] = content_hash(payload)
    return e


def epistemic_level_for(receipt: dict) -> str:
    """Grade a decision receipt on the estate's EpistemicLevel scale.

    Outcome first (what the executor actually did), else the decision's warrant:
      rolled_back  -> rejected    (attempted and undone; the retained failed adjudication)
      healed       -> proved      (machine-checked: the artifact re-verifies)
      quarantined  -> bounded     (isolated within declared limits)
      proposed     -> synthetic   (a generated proposal, awaiting human review)
      BOTTOM       -> speculative  (no warrant to act)
      otherwise    -> empirical    (a measured condition; a human or a later pass judges)
    """
    ex = receipt.get("execution") or {}
    if ex.get("rolled_back"):
        return "rejected"
    if ex.get("healed"):
        return "proved"
    if ex.get("quarantined"):
        return "bounded"
    if ex.get("proposed"):
        return "synthetic"
    if receipt.get("verdict") == "BOTTOM":
        return "speculative"
    return "empirical"
