from __future__ import annotations

import unittest

from .reconcile import decide_reconcile_action


class ReconcileDecisionSmokeTest(unittest.TestCase):
    def test_local_dirty_and_remote_delete_forces_manual_reconcile(self) -> None:
        decision = decide_reconcile_action(
            local_dirty=True,
            remote_delete=True,
            remote_newer=False,
            authority_mode="local_first",
        )
        self.assertEqual(decision.action, "manual_reconcile")
        self.assertEqual(decision.reason, "local_dirty_remote_delete")

    def test_local_first_remote_newer_without_stale_allowance_requires_manual(self) -> None:
        decision = decide_reconcile_action(
            local_dirty=False,
            remote_delete=False,
            remote_newer=True,
            authority_mode="local_first",
            policy_allow_stale=False,
        )
        self.assertEqual(decision.action, "manual_reconcile")
        self.assertEqual(decision.authoritative_side, "local")

    def test_provider_first_defaults_remote_wins(self) -> None:
        decision = decide_reconcile_action(
            local_dirty=False,
            remote_delete=False,
            remote_newer=False,
            authority_mode="provider_first",
        )
        self.assertEqual(decision.action, "remote_wins")
        self.assertEqual(decision.authoritative_side, "remote")

    def test_hybrid_with_change_requires_explicit_resolution(self) -> None:
        decision = decide_reconcile_action(
            local_dirty=False,
            remote_delete=False,
            remote_newer=True,
            authority_mode="hybrid",
        )
        self.assertEqual(decision.action, "manual_reconcile")
        self.assertEqual(decision.reason, "hybrid_requires_explicit_resolution")


if __name__ == "__main__":
    unittest.main()
