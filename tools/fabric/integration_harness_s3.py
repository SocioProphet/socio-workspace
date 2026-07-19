from __future__ import annotations

from pathlib import Path
from typing import Any

from .connectors.s3 import S3Executor
from .integration_common import run_mount_and_connector_flow


def run_mount_and_s3_flow(root: Path) -> dict[str, Any]:
    return run_mount_and_connector_flow(
        root,
        executor_cls=S3Executor,
        connector_id="s3",
        dataset_ref="ds/demo-s3",
        mount_name="demo-s3",
        capacity_bytes=2048,
    )
