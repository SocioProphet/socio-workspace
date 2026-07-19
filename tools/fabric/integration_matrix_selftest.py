from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .connectors.drive import DriveExecutor
from .connectors.hyper import HyperExecutor
from .connectors.s3 import S3Executor
from .integration_common import run_mount_and_connector_flow


class IntegrationMatrixSmokeTest(unittest.TestCase):
    def test_drive_s3_hyper_share_one_harness(self) -> None:
        cases = [
            (DriveExecutor, "drive", "ds/demo-drive", "demo-drive", 1024),
            (S3Executor, "s3", "ds/demo-s3", "demo-s3", 2048),
            (HyperExecutor, "hyper", "ds/demo-hyper", "demo-hyper", 4096),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, (executor_cls, connector_id, dataset_ref, mount_name, capacity_bytes) in enumerate(cases):
                root = Path(tmpdir) / f"case-{idx}"
                result = run_mount_and_connector_flow(
                    root,
                    executor_cls=executor_cls,
                    connector_id=connector_id,
                    dataset_ref=dataset_ref,
                    mount_name=mount_name,
                    capacity_bytes=capacity_bytes,
                )
                self.assertIsNotNone(result["mount_registration"])
                self.assertIsNotNone(result["registry_entry"])
                self.assertIsNotNone(result["checkpoint"])
                self.assertGreaterEqual(result["event_count"], 2)
                self.assertEqual(result["checkpoint"]["connector_id"], connector_id)
                self.assertEqual(result["registry_entry"]["workspace_ref"], "ws/demo")


if __name__ == "__main__":
    unittest.main()
