from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .connectors.drive import DriveExecutor
from .connectors.hyper import HyperExecutor
from .connectors.s3 import S3Executor
from .integration_common import run_mount_and_connector_flow


class ReplayMatrixSmokeTest(unittest.TestCase):
    def test_shared_harness_repeats_cleanly_for_drive_s3_hyper(self) -> None:
        cases = [
            (DriveExecutor, "drive", "ds/replay-drive", "replay-drive", 1024),
            (S3Executor, "s3", "ds/replay-s3", "replay-s3", 2048),
            (HyperExecutor, "hyper", "ds/replay-hyper", "replay-hyper", 4096),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, (executor_cls, connector_id, dataset_ref, mount_name, capacity_bytes) in enumerate(cases):
                root = Path(tmpdir) / f"case-{idx}"
                first = run_mount_and_connector_flow(
                    root,
                    executor_cls=executor_cls,
                    connector_id=connector_id,
                    dataset_ref=dataset_ref,
                    mount_name=mount_name,
                    capacity_bytes=capacity_bytes,
                )
                second = run_mount_and_connector_flow(
                    root,
                    executor_cls=executor_cls,
                    connector_id=connector_id,
                    dataset_ref=dataset_ref,
                    mount_name=mount_name,
                    capacity_bytes=capacity_bytes,
                )
                self.assertIsNotNone(first["checkpoint"])
                self.assertIsNotNone(second["checkpoint"])
                self.assertEqual(second["checkpoint"]["connector_id"], connector_id)
                self.assertGreaterEqual(second["event_count"], first["event_count"])


if __name__ == "__main__":
    unittest.main()
