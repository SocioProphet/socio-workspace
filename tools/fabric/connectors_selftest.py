from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .checkpoints import CheckpointStore
from .connectors.base import ConnectorContext
from .connectors.drive import DriveExecutor
from .connectors.hyper import HyperExecutor
from .connectors.rsync import RsyncExecutor
from .connectors.s3 import S3Executor
from .events import EventSink


class ConnectorSmokeTest(unittest.TestCase):
    def test_all_connector_executors_emit_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            checkpoints = CheckpointStore(root / "ckpt")
            events = EventSink(root / "events.ndjson")

            executors = [
                DriveExecutor,
                RsyncExecutor,
                S3Executor,
                HyperExecutor,
            ]
            for executor_cls in executors:
                context = ConnectorContext(
                    connector_id=executor_cls.__name__.lower(),
                    dataset_ref="ds/demo",
                    policy_bundle_ref="policy/default",
                    actor_ref="tester",
                    workspace_ref="ws/demo",
                )
                executor = executor_cls(context, checkpoints, events)
                executor.apply()
                self.assertIsNotNone(checkpoints.load(context.connector_id, context.dataset_ref))

            lines = events.path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 4)


if __name__ == "__main__":
    unittest.main()
