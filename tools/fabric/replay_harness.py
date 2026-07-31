from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .checkpoints import CheckpointStore
from .connectors.base import ConnectorContext
from .connectors.drive import DriveExecutor
from .events import EventSink


def run_repeated_drive_executor(root: Path, runs: int = 2) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    checkpoints = CheckpointStore(root / "checkpoints")
    events = EventSink(root / "events.ndjson")

    executor = DriveExecutor(
        ConnectorContext(
            connector_id="drive",
            dataset_ref="ds/demo",
            policy_bundle_ref="policy/default",
            actor_ref="tester",
            workspace_ref="ws/demo",
        ),
        checkpoints,
        events,
    )

    for _ in range(runs):
        executor.apply()

    checkpoint = checkpoints.load("drive", "ds/demo")
    event_lines = (root / "events.ndjson").read_text(encoding="utf-8").strip().splitlines()

    return {
        "runs": runs,
        "checkpoint": asdict(checkpoint) if checkpoint else None,
        "event_count": len([line for line in event_lines if line]),
        "last_event": event_lines[-1] if event_lines else None,
    }
