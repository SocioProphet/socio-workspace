from __future__ import annotations

import unittest

from .conflict_harness import classify_conflict


class ConflictPathSmokeTest(unittest.TestCase):
    def test_local_dirty_and_remote_delete_requires_manual_reconcile(self) -> None:
        self.assertEqual(
            classify_conflict(local_dirty=True, remote_delete=True, authority_mode="local_first"),
            "manual_reconcile",
        )

    def test_authority_modes_choose_expected_default(self) -> None:
        self.assertEqual(classify_conflict(False, False, authority_mode="local_first"), "local_wins")
        self.assertEqual(classify_conflict(False, False, authority_mode="provider_first"), "remote_wins")


if __name__ == "__main__":
    unittest.main()
