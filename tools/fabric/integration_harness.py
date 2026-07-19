from __future__ import annotations

from pathlib import Path
from typing import Any

from .connectors.drive import DriveExecutor
from .integration_common import run_mount_and_connector_flow


def run_mount_and_drive_flow(root: Path) -> dict[str, Any]:
    return run_mount_and_connector_flow(
        root,
        executor_cls=DriveExecutor,
        connector_id="drive",
        dataset_ref="ds/demo",
        mount_name="demo",
        capacity_bytes=1024,
    )
