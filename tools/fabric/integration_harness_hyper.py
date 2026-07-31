from __future__ import annotations

from pathlib import Path
from typing import Any

from .connectors.hyper import HyperExecutor
from .integration_common import run_mount_and_connector_flow


def run_mount_and_hyper_flow(root: Path) -> dict[str, Any]:
    return run_mount_and_connector_flow(
        root,
        executor_cls=HyperExecutor,
        connector_id="hyper",
        dataset_ref="ds/demo-hyper",
        mount_name="demo-hyper",
        capacity_bytes=4096,
    )
