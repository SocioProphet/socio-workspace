from __future__ import annotations

import unittest

from .reconcile import (
    decide_authority_transition,
    decide_stale_mirror_action,
    decide_tombstone_action,
)


class ReconcileDeepSmokeTest(unittest.TestCase):
    def test_unsigned_tombstone_is_rejected(self) -> None:
        decision = decide_tombstone_action(
            signed_tombstone=False,
            local_dirty=False,
            authority_mode="provider_first",
        )
        self.assertEqual(decision.action, "reject_tombstone")
        self.assertEqual(decision.reason, "unsigned_tombstone")

    def test_signed_tombstone_with_local_dirty_requires_manual_reconcile(self) -> None:
        decision = decide_tombstone_action(
            signed_tombstone=True,
            local_dirty=True,
            authority_mode="local_first",
        )
        self.assertEqual(decision.action, "manual_reconcile")
        self.assertEqual(decision.reason, "local_dirty_remote_tombstone")

    def test_stale_mirror_blocked_without_policy_allowance(self) -> None:
        decision = decide_stale_mirror_action(
            stale_generation_gap=3,
            policy_allow_stale=False,
            authority_mode="local_first",
        )
        self.assertEqual(decision.action, "block_stale_mirror")
        self.assertEqual(decision.reason, "stale_not_allowed")

    def test_local_first_with_stale_allowed_becomes_metadata_only(self) -> None:
        decision = decide_stale_mirror_action(
            stale_generation_gap=2,
            policy_allow_stale=True,
            authority_mode="local_first",
        )
        self.assertEqual(decision.action, "metadata_only")
        self.assertEqual(decision.reason, "stale_mirror_local_first")

    def test_authority_transition_requires_quorum(self) -> None:
        decision = decide_authority_transition(
            current_authority="local",
            requested_authority="remote",
            quorum_granted=False,
        )
        self.assertEqual(decision.action, "manual_reconcile")
        self.assertEqual(decision.reason, "quorum_required_for_authority_transition")

    def test_authority_transition_with_quorum_promotes(self) -> None:
        decision = decide_authority_transition(
            current_authority="local",
            requested_authority="remote",
            quorum_granted=True,
        )
        self.assertEqual(decision.action, "promote_authority")
        self.assertEqual(decision.authoritative_side, "remote")


if __name__ == "__main__":
    unittest.main()
