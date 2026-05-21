"""
Session-quarantine protocol.

Every agent/runtime lifecycle event must attach to a known session DAG node
or enter the orphan event queue.  After TTL expiry without reconciliation,
the event is quarantined and an OrphanEventReceipt is emitted.

Flow
----
event_received(event)
  → session known  → append to session DAG node
  → session unknown → append to orphan_event_queue

reconcile()
  → tries to match orphan events to sessions via
    conversation_id / parent_id / workspace_id / task_id
  → matched  → attach to session, mark recovered
  → unmatched after TTL → quarantine + emit OrphanEventReceipt
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SessionDAGNode:
    """A node in a session's event DAG."""
    session_id: str
    events: List[dict] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)


@dataclass
class OrphanEntry:
    """An event waiting for reconciliation."""
    event_id: str
    event: dict
    received_at: str
    reconciled: bool = False
    recovered_session_id: Optional[str] = None


@dataclass
class EvidenceRef:
    """A reference to evidence without including the full payload."""
    ref_id: str
    event_id: str
    kind: str
    hint: str  # e.g. "conversation_id=abc123"

    def to_dict(self) -> dict:
        return {
            "ref_id": self.ref_id,
            "event_id": self.event_id,
            "kind": self.kind,
            "hint": self.hint,
        }


@dataclass
class OrphanEventReceipt:
    """
    SourceOS-compatible receipt for a quarantined or recovered orphan event.

    Compatible with SourceOS receipt conventions (SessionReceipt shape).
    Evidence refs reference payload metadata without dumping full context.
    """
    receipt_id: str
    event_id: str
    status: str  # "quarantined" | "recovered"
    quarantined_at: str
    ttl_seconds: int
    reconciliation_attempts: int
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    recovered_session_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "event_id": self.event_id,
            "status": self.status,
            "quarantined_at": self.quarantined_at,
            "ttl_seconds": self.ttl_seconds,
            "reconciliation_attempts": self.reconciliation_attempts,
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "recovered_session_id": self.recovered_session_id,
        }


# ---------------------------------------------------------------------------
# Core protocol
# ---------------------------------------------------------------------------

# Keys used for reconciliation attempts
_RECONCILE_KEYS = ("conversation_id", "parent_id", "workspace_id", "task_id")

DEFAULT_TTL_SECONDS = 300


class SessionQuarantineProtocol:
    """Enforce session-DAG attachment for every lifecycle event.

    Parameters
    ----------
    ttl_seconds:
        Time-to-live (seconds) for orphan events before they are quarantined.
        Defaults to :data:`DEFAULT_TTL_SECONDS`.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds

        # session_id → DAG node
        self._sessions: Dict[str, SessionDAGNode] = {}

        # event_id → OrphanEntry
        self._orphan_queue: Dict[str, OrphanEntry] = {}

        # All emitted receipts (quarantined and recovered)
        self._receipts: List[OrphanEventReceipt] = []

        # Reconciliation attempt count per event_id
        self._reconcile_counts: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def register_session(self, session_id: str) -> SessionDAGNode:
        """Register a new known session and return its DAG node."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionDAGNode(session_id=session_id)
            logger.info("Session registered: %s", session_id)
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[SessionDAGNode]:
        """Return the DAG node for *session_id*, or ``None`` if unknown."""
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Event ingress
    # ------------------------------------------------------------------

    def event_received(self, event: dict) -> str:
        """Process an incoming lifecycle event.

        Returns
        -------
        ``"attached"``
            The event was immediately attached to a known session DAG node.
        ``"orphaned"``
            No matching session was found; the event was added to the orphan queue.
        """
        session_id = event.get("session_id", "")
        event_id = event.get("event_id") or str(uuid.uuid4())

        # Ensure the event carries a stable id
        if "event_id" not in event:
            event = dict(event, event_id=event_id)

        if session_id and session_id in self._sessions:
            self._attach_to_session(session_id, event)
            return "attached"

        self._enqueue_orphan(event_id, event)
        return "orphaned"

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    def reconcile(self) -> None:
        """Attempt reconciliation of all currently queued orphan events.

        For each unreconciled orphan:

        - tries to find a matching session via *conversation_id*, *parent_id*,
          *workspace_id*, or *task_id*
        - if matched: attaches the event, marks it recovered, and emits a receipt
        - if TTL exceeded without a match: quarantines the event and emits a receipt
        """
        now = datetime.now(timezone.utc)
        to_quarantine = []

        for entry in list(self._orphan_queue.values()):
            if entry.reconciled:
                continue

            self._reconcile_counts[entry.event_id] = (
                self._reconcile_counts.get(entry.event_id, 0) + 1
            )

            matched_session = self._find_matching_session(entry.event)
            if matched_session:
                self._attach_to_session(matched_session, entry.event)
                entry.reconciled = True
                entry.recovered_session_id = matched_session
                self._emit_receipt(entry, status="recovered")
                logger.info(
                    "Orphan event %s recovered → session %s",
                    entry.event_id,
                    matched_session,
                )
                continue

            received_dt = datetime.fromisoformat(entry.received_at)
            # Make received_dt timezone-aware if it isn't already
            if received_dt.tzinfo is None:
                received_dt = received_dt.replace(tzinfo=timezone.utc)
            age_seconds = (now - received_dt).total_seconds()
            if age_seconds >= self.ttl_seconds:
                to_quarantine.append(entry)

        for entry in to_quarantine:
            self._quarantine(entry)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_orphan_queue(self) -> List[OrphanEntry]:
        """Return pending (unreconciled) orphan entries."""
        return [e for e in self._orphan_queue.values() if not e.reconciled]

    def get_receipts(self) -> List[OrphanEventReceipt]:
        """Return all emitted receipts (quarantined and recovered)."""
        return list(self._receipts)

    def get_sessions(self) -> Dict[str, SessionDAGNode]:
        """Return all registered session DAG nodes."""
        return dict(self._sessions)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _attach_to_session(self, session_id: str, event: dict) -> None:
        node = self._sessions[session_id]
        node.events.append(event)
        logger.debug(
            "Event %s attached to session %s (total events: %d)",
            event.get("event_id", "?"),
            session_id,
            len(node.events),
        )

    def _enqueue_orphan(self, event_id: str, event: dict) -> None:
        entry = OrphanEntry(
            event_id=event_id,
            event=event,
            received_at=_now_iso(),
        )
        self._orphan_queue[event_id] = entry
        logger.info("Orphan event queued: event_id=%s", event_id)

    def _find_matching_session(self, event: dict) -> Optional[str]:
        """Return a session_id if the event can be reconciled, else ``None``."""
        for key in _RECONCILE_KEYS:
            value = event.get(key)
            if not value:
                continue
            for session_id, node in self._sessions.items():
                # Check whether any existing event on the session shares the key
                for session_event in node.events:
                    if session_event.get(key) == value:
                        return session_id
        return None

    def _quarantine(self, entry: OrphanEntry) -> None:
        """Quarantine an irreconcilable orphan and emit a receipt."""
        entry.reconciled = True  # remove from active queue
        self._emit_receipt(entry, status="quarantined")
        logger.warning(
            "Event quarantined: event_id=%s (attempts=%d)",
            entry.event_id,
            self._reconcile_counts.get(entry.event_id, 0),
        )

    def _emit_receipt(self, entry: OrphanEntry, status: str) -> None:
        evidence_refs = self._build_evidence_refs(entry)
        receipt = OrphanEventReceipt(
            receipt_id=str(uuid.uuid4()),
            event_id=entry.event_id,
            status=status,
            quarantined_at=_now_iso(),
            ttl_seconds=self.ttl_seconds,
            reconciliation_attempts=self._reconcile_counts.get(entry.event_id, 0),
            evidence_refs=evidence_refs,
            recovered_session_id=entry.recovered_session_id,
        )
        self._receipts.append(receipt)

    def _build_evidence_refs(self, entry: OrphanEntry) -> List[EvidenceRef]:
        """Build evidence refs that reference payload metadata without dumping full context."""
        refs = []
        for key in _RECONCILE_KEYS:
            value = entry.event.get(key)
            if value:
                refs.append(
                    EvidenceRef(
                        ref_id=str(uuid.uuid4()),
                        event_id=entry.event_id,
                        kind=key,
                        hint=f"{key}={value}",
                    )
                )
        return refs
