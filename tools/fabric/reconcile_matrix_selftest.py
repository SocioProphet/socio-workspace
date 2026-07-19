from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .reconcile_matrix_harness import run_reconcile_matrix


class ReconcileMatrixSmokeTest(unittest.TestCase):
    def test_reconcile_matrix_combines_tombstone_stale_and_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_reconcile_matrix(Path(tmpdir))
            self.assertIn("tombstone", result)
            self.assertIn("stale_mirror", result)
            self.assertIn("authority_transition", result)
            self.assertEqual(result["direct_decisions"]["tombstone"]["action"], "apply_tombstone")
            self.assertEqual(result["direct_decisions"]["stale_mirror"]["action"], "metadata_only")
            self.assertEqual(result["direct_decisions"]["authority_transition"]["action"], "promote_authority")
            self.assertGreaterEqual(result["tombstone"]["event_count"], 2)
            self.assertGreaterEqual(result["stale_mirror"]["event_count"], 2)
            self.assertGreaterEqual(result["authority_transition"]["event_count"], 2)


if __name__ == "__main__":
    unittest.main()
