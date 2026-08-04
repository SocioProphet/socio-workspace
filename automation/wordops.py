"""WordOps incident router — route escalation-class decisions to the Matrix ChatOps fabric.

WordOps (`prophet-platform/docs/WORDOPS_*`) is the estate's Matrix-native ChatOps agent with a
governed Incident -> Containment flow: a private incident room, a capability-lease broker,
autonomy classes A0-A4, an OPA lease policy, an MCP gateway, the gbrg containment engine, and an
executions ledger. Its governing rule: *only a room-safe summary + receipt_hash returns to the
room; the warrant lives in the ledger/graph, not pasted in.*

This maps a self-heal escalation onto that fabric. Escalation-class decisions become room-safe
incident records the WordOps case-kernel (`apps/matrix-qes-operator`) drains — routing alerts
out of the log-void into an operator's room. The self-heal action maps to an autonomy class:

    quarantine       -> A4  (urgent containment / sever, via the gbrg engine)
    escalate_human   -> A0  (human-in-the-loop; open an incident room, no autonomous action)

Only escalation-class decisions produce incidents; a healed/proposed decision does not open a
room. The record carries the receipt hash + Crystal Atlas claim ref, NOT the raw detail — the
warrant is referenced, discoverable via Sherlock, never pasted. Actual room creation / lease /
containment is the WordOps fabric's job (credentialed, deploy-time); this is the produce side.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from automation.durable_queue import DurableQueue, state_dir
from automation.envelope import ulid

# Decisions that a human / containment must SEE — the alerts that were landing in the void.
ESCALATION_ACTIONS = {"escalate_human", "quarantine"}

# self-heal action -> WordOps autonomy class + severity.
_AUTONOMY = {"quarantine": "A4", "escalate_human": "A0"}
_SEVERITY = {"quarantine": "high", "escalate_human": "warning"}


def _rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_incident(receipt: dict, *, claim_ref: Optional[str] = None) -> dict:
    """A room-safe WordOps incident from a decision receipt (references the warrant, never pastes it)."""
    action = str(receipt.get("action", "unknown"))
    subject = (receipt.get("address") or {}).get("iri", "system://unknown")
    receipt_hash = receipt.get("content_sha256") or ""
    return {
        "incident_id": receipt.get("message_id") or ulid(),
        "trace_id": receipt.get("trace_id"),
        "subject": subject,
        "action": action,
        "verdict": receipt.get("verdict"),
        "epistemic_level": receipt.get("epistemic_level"),
        "severity": _SEVERITY.get(action, "warning"),
        "autonomy_class": _AUTONOMY.get(action, "A0"),
        # the warrant lives in the ledger / Crystal Atlas graph, referenced by hash, not pasted:
        "receipt_hash": receipt_hash,
        "claim_ref": claim_ref or receipt.get("message_id"),
        "summary": f"self-heal {action} on {subject}: {receipt.get('verdict')} "
                   f"(receipt {receipt_hash[:23]})",
        "created_at": receipt.get("decided_at") or _rfc3339(),
    }


def route(receipt: dict, *, claim_ref: Optional[str] = None,
          sink: Optional[DurableQueue] = None) -> Optional[dict]:
    """Record a WordOps incident for an escalation-class decision; None for anything else."""
    if receipt.get("action") not in ESCALATION_ACTIONS:
        return None
    incident = to_incident(receipt, claim_ref=claim_ref)
    (sink if sink is not None else DurableQueue(state_dir() / "wordops-incidents")).put(incident)
    return incident
