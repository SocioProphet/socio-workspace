"""Tests for automation/session_quarantine.py."""

import pytest

from automation.session_quarantine import (
    DEFAULT_TTL_SECONDS,
    EvidenceRef,
    OrphanEntry,
    OrphanEventReceipt,
    SessionDAGNode,
    SessionQuarantineProtocol,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(**kwargs) -> dict:
    """Return a minimal lifecycle event, overridable via kwargs."""
    base = {
        "event_id": "evt-001",
        "session_id": "ses-001",
        "conversation_id": "conv-abc",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestKnownSessionEvent:
    """Acceptance: known-session event is attached to the session DAG."""

    def test_known_session_returns_attached(self):
        proto = SessionQuarantineProtocol()
        proto.register_session("ses-001")

        result = proto.event_received(_make_event(event_id="evt-001", session_id="ses-001"))

        assert result == "attached"

    def test_event_appears_in_dag_node(self):
        proto = SessionQuarantineProtocol()
        proto.register_session("ses-001")
        proto.event_received(_make_event(event_id="evt-001", session_id="ses-001"))

        node = proto.get_session("ses-001")
        assert node is not None
        assert len(node.events) == 1
        assert node.events[0]["event_id"] == "evt-001"

    def test_multiple_events_accumulate_in_dag(self):
        proto = SessionQuarantineProtocol()
        proto.register_session("ses-a")

        for i in range(3):
            proto.event_received({"event_id": f"evt-{i}", "session_id": "ses-a"})

        assert len(proto.get_session("ses-a").events) == 3


class TestUnknownSessionEvent:
    """Acceptance: unknown-session event enters the orphan queue."""

    def test_unknown_session_returns_orphaned(self):
        proto = SessionQuarantineProtocol()

        result = proto.event_received(_make_event(session_id="ses-missing"))

        assert result == "orphaned"

    def test_orphan_appears_in_queue(self):
        proto = SessionQuarantineProtocol()
        proto.event_received(_make_event(event_id="evt-002", session_id="ses-missing"))

        orphans = proto.get_orphan_queue()
        assert len(orphans) == 1
        assert orphans[0].event_id == "evt-002"

    def test_event_without_session_id_is_orphaned(self):
        proto = SessionQuarantineProtocol()
        result = proto.event_received({"event_id": "evt-nosess", "payload": "data"})

        assert result == "orphaned"
        assert len(proto.get_orphan_queue()) == 1

    def test_multiple_sessions_mixed_events(self):
        proto = SessionQuarantineProtocol()
        proto.register_session("ses-a")
        proto.register_session("ses-b")

        proto.event_received({"event_id": "e1", "session_id": "ses-a"})
        proto.event_received({"event_id": "e2", "session_id": "ses-b"})
        proto.event_received({"event_id": "e3", "session_id": "ses-unknown"})

        assert len(proto.get_session("ses-a").events) == 1
        assert len(proto.get_session("ses-b").events) == 1
        assert len(proto.get_orphan_queue()) == 1


class TestTTLExpiry:
    """Acceptance: events not reconciled within TTL are quarantined with a receipt."""

    def test_ttl_zero_quarantines_immediately(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(_make_event(event_id="evt-ttl", session_id="ses-missing"))

        proto.reconcile()

        assert len(proto.get_orphan_queue()) == 0

    def test_quarantine_emits_receipt(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(_make_event(event_id="evt-ttl", session_id="ses-missing"))

        proto.reconcile()

        receipts = proto.get_receipts()
        assert len(receipts) == 1
        assert receipts[0].status == "quarantined"
        assert receipts[0].event_id == "evt-ttl"

    def test_high_ttl_does_not_quarantine(self):
        proto = SessionQuarantineProtocol(ttl_seconds=DEFAULT_TTL_SECONDS)
        proto.event_received(_make_event(event_id="evt-keep", session_id="ses-missing"))

        proto.reconcile()

        # Still in queue, not yet quarantined
        assert len(proto.get_orphan_queue()) == 1
        assert len(proto.get_receipts()) == 0

    def test_receipt_records_ttl(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(_make_event(event_id="evt-ttl2", session_id="ses-x"))
        proto.reconcile()

        receipt = proto.get_receipts()[0]
        assert receipt.ttl_seconds == 0


class TestRecoveredEvent:
    """Acceptance: reconciled events attach correctly to sessions with recovered receipts."""

    def test_reconcile_via_conversation_id(self):
        proto = SessionQuarantineProtocol(ttl_seconds=300)
        proto.register_session("ses-recover")
        # Seed the session with an event sharing conversation_id
        proto._sessions["ses-recover"].events.append(
            {"event_id": "seed-0", "conversation_id": "conv-xyz"}
        )

        # Orphan event with matching conversation_id
        proto.event_received(
            _make_event(event_id="evt-rec", session_id="ses-unknown", conversation_id="conv-xyz")
        )
        proto.reconcile()

        assert len(proto.get_orphan_queue()) == 0
        node = proto.get_session("ses-recover")
        assert any(e["event_id"] == "evt-rec" for e in node.events)

    def test_reconcile_emits_recovered_receipt(self):
        proto = SessionQuarantineProtocol(ttl_seconds=300)
        proto.register_session("ses-r2")
        proto._sessions["ses-r2"].events.append(
            {"event_id": "s0", "workspace_id": "ws-999"}
        )

        proto.event_received(
            {"event_id": "evt-ws", "session_id": "ses-gone", "workspace_id": "ws-999"}
        )
        proto.reconcile()

        receipts = proto.get_receipts()
        recovered = [r for r in receipts if r.status == "recovered"]
        assert len(recovered) == 1
        assert recovered[0].event_id == "evt-ws"
        assert recovered[0].recovered_session_id == "ses-r2"

    def test_reconcile_via_task_id(self):
        proto = SessionQuarantineProtocol(ttl_seconds=300)
        proto.register_session("ses-task")
        proto._sessions["ses-task"].events.append(
            {"event_id": "s-task", "task_id": "task-42"}
        )

        proto.event_received(
            {"event_id": "evt-task", "session_id": "ses-nope", "task_id": "task-42"}
        )
        proto.reconcile()

        node = proto.get_session("ses-task")
        assert any(e["event_id"] == "evt-task" for e in node.events)

    def test_reconcile_via_parent_id(self):
        proto = SessionQuarantineProtocol(ttl_seconds=300)
        proto.register_session("ses-parent")
        proto._sessions["ses-parent"].events.append(
            {"event_id": "s-par", "parent_id": "par-7"}
        )

        proto.event_received(
            {"event_id": "evt-par", "session_id": "ses-nope", "parent_id": "par-7"}
        )
        proto.reconcile()

        node = proto.get_session("ses-parent")
        assert any(e["event_id"] == "evt-par" for e in node.events)


class TestEvidenceReferences:
    """Acceptance: quarantined events emit receipts with evidenceRefs."""

    def test_evidence_refs_present_for_conversation_id(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(
            {
                "event_id": "evt-evid",
                "session_id": "ses-missing",
                "conversation_id": "conv-evid",
            }
        )
        proto.reconcile()

        receipt = proto.get_receipts()[0]
        assert len(receipt.evidence_refs) >= 1
        kinds = [r.kind for r in receipt.evidence_refs]
        assert "conversation_id" in kinds

    def test_evidence_refs_include_workspace_and_task(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(
            {
                "event_id": "evt-multi",
                "session_id": "ses-x",
                "workspace_id": "ws-abc",
                "task_id": "t-99",
            }
        )
        proto.reconcile()

        receipt = proto.get_receipts()[0]
        kinds = [r.kind for r in receipt.evidence_refs]
        assert "workspace_id" in kinds
        assert "task_id" in kinds

    def test_evidence_refs_hint_is_concise(self):
        """Evidence refs must reference metadata, not dump full payload."""
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(
            {
                "event_id": "evt-hint",
                "session_id": "ses-y",
                "conversation_id": "conv-hint",
                "large_field": "x" * 10_000,
            }
        )
        proto.reconcile()

        receipt = proto.get_receipts()[0]
        for ref in receipt.evidence_refs:
            # Hint must not contain the large payload
            assert len(ref.hint) < 200

    def test_no_evidence_refs_when_no_reconcile_keys(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received({"event_id": "evt-bare", "session_id": "ses-z"})
        proto.reconcile()

        receipt = proto.get_receipts()[0]
        assert receipt.evidence_refs == []


class TestReceiptSerialization:
    """Verify OrphanEventReceipt.to_dict() produces correct output."""

    def test_to_dict_structure(self):
        proto = SessionQuarantineProtocol(ttl_seconds=0)
        proto.event_received(
            {"event_id": "evt-serial", "session_id": "ses-s", "task_id": "task-7"}
        )
        proto.reconcile()

        d = proto.get_receipts()[0].to_dict()

        assert d["status"] == "quarantined"
        assert d["event_id"] == "evt-serial"
        assert d["ttl_seconds"] == 0
        assert isinstance(d["evidence_refs"], list)
        assert d["recovered_session_id"] is None

    def test_recovered_receipt_to_dict_has_session(self):
        proto = SessionQuarantineProtocol(ttl_seconds=300)
        proto.register_session("ses-ser")
        proto._sessions["ses-ser"].events.append(
            {"event_id": "sx", "conversation_id": "conv-ser"}
        )
        proto.event_received(
            {"event_id": "evt-ser", "session_id": "s-gone", "conversation_id": "conv-ser"}
        )
        proto.reconcile()

        receipts = [r for r in proto.get_receipts() if r.status == "recovered"]
        assert len(receipts) == 1
        d = receipts[0].to_dict()
        assert d["recovered_session_id"] == "ses-ser"
        assert isinstance(d["receipt_id"], str) and len(d["receipt_id"]) > 0
