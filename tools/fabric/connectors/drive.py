from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .base import ConnectorExecutor
from ..types import ConnectorCheckpoint


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DriveExecutor(ConnectorExecutor):
    def scan(self) -> Iterable[dict[str, Any]]:
        checkpoint = self.restore_checkpoint()
        yield {
            "change_id": "drive-scan-demo",
            "source_ref": "drive:file_id:revision_id",
            "operation": "scan",
            "cursor": getattr(checkpoint, "cursor_or_marker", ""),
            "occurred_at": _now(),
        }

    def apply(self) -> None:
        for change in self.scan():
            self.emit("connector.scan.completed", change["change_id"], change)
            checkpoint = ConnectorCheckpoint(
                checkpoint_id="ckpt-drive-demo",
                connector_id=self.context.connector_id,
                dataset_ref=self.context.dataset_ref,
                cursor_or_marker=change["change_id"],
                last_successful_scan_at=change["occurred_at"],
                last_applied_change_id=change["change_id"],
                integrity_digest="demo",
                executor_version="v1",
                created_at=change["occurred_at"],
                updated_at=change["occurred_at"],
            )
            self.checkpoints.save(checkpoint)
