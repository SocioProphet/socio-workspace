from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..checkpoints import CheckpointStore
from ..events import EventSink
from ..types import ConnectorCheckpoint, EvidenceEvent


@dataclass(frozen=True)
class ConnectorContext:
    connector_id: str
    dataset_ref: str
    policy_bundle_ref: str
    actor_ref: str
    workspace_ref: str


class ConnectorExecutor:
    def __init__(self, context: ConnectorContext, checkpoints: CheckpointStore, events: EventSink) -> None:
        self.context = context
        self.checkpoints = checkpoints
        self.events = events

    def restore_checkpoint(self) -> ConnectorCheckpoint | None:
        return self.checkpoints.load(self.context.connector_id, self.context.dataset_ref)

    def emit(self, event_type: str, correlation_id: str, payload: dict[str, Any]) -> None:
        self.events.emit(
            EvidenceEvent(
                event_id=f"{self.context.connector_id}:{correlation_id}:{event_type}",
                event_type=event_type,
                occurred_at=payload.get("occurred_at", ""),
                actor_ref=self.context.actor_ref,
                workspace_ref=self.context.workspace_ref,
                dataset_ref=self.context.dataset_ref,
                policy_bundle_ref=self.context.policy_bundle_ref,
                correlation_id=correlation_id,
                payload=payload,
            )
        )

    def scan(self) -> Iterable[dict[str, Any]]:
        raise NotImplementedError

    def apply(self) -> None:
        raise NotImplementedError
