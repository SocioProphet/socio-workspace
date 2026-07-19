from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .checkpoints import CheckpointStore
from .replay_harness import run_repeated_drive_executor
from .types import ConnectorCheckpoint


class ReplayAndIdempotenceSmokeTest(unittest.TestCase):
    def test_repeated_drive_executor_runs_keep_checkpoint_and_emit_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_repeated_drive_executor(Path(tmpdir), runs=2)
            self.assertEqual(result["runs"], 2)
            self.assertIsNotNone(result["checkpoint"])
            self.assertEqual(result["checkpoint"]["connector_id"], "drive")
            self.assertEqual(result["checkpoint"]["last_applied_change_id"], "drive-scan-demo")
            self.assertEqual(result["event_count"], 2)

    def test_checkpoint_roundtrip_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CheckpointStore(Path(tmpdir))
            checkpoint = ConnectorCheckpoint(
                checkpoint_id="ckpt-demo",
                connector_id="drive",
                dataset_ref="ds/demo",
                cursor_or_marker="cursor-1",
                last_successful_scan_at="2026-04-16T00:00:00Z",
                last_applied_change_id="change-1",
                integrity_digest="demo",
                executor_version="v1",
                created_at="2026-04-16T00:00:00Z",
                updated_at="2026-04-16T00:00:00Z",
            )
            store.save(checkpoint)
            loaded = store.load("drive", "ds/demo")
            self.assertEqual(loaded, checkpoint)


if __name__ == "__main__":
    unittest.main()
