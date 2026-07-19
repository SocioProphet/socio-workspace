from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .stale_mirror_flow_harness import run_stale_mirror_flow


class ResultLabelFlowSmokeTest(unittest.TestCase):
    def test_stale_mirror_flow_exposes_result_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_stale_mirror_flow(
                Path(tmpdir),
                stale_generation_gap=3,
                policy_allow_stale=True,
                authority_mode="local_first",
            )
            self.assertEqual(result["result_label"]["surface_state"], "remote_metadata_only")
            self.assertEqual(result["result_label"]["freshness_class"], "bounded_stale")

    def test_tombstone_flow_exposes_result_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_tombstone_propagation_flow(
                Path(tmpdir),
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
            )
            self.assertEqual(result["result_label"]["surface_state"], "tombstoned")
            self.assertEqual(result["result_label"]["reconcile_state"], "resolved")

    def test_authority_flow_exposes_result_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_authority_transition_flow(
                Path(tmpdir),
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            )
            self.assertEqual(result["result_label"]["surface_state"], "authority_transition_applied")
            self.assertEqual(result["result_label"]["authority_state"], "remote_authoritative")


if __name__ == "__main__":
    unittest.main()
