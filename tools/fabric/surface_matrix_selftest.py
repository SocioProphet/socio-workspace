from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from .cli import cmd_show_planner_surface, cmd_show_surface
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .reconcile_matrix_harness import run_reconcile_matrix
from .result_surface import outcome_from_flow_result, outcomes_from_reconcile_matrix
from .stale_mirror_flow_harness import run_stale_mirror_flow


class SurfaceMatrixSmokeTest(unittest.TestCase):
    def test_runtime_surface_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stale = run_stale_mirror_flow(
                Path(tmpdir) / "stale",
                stale_generation_gap=3,
                policy_allow_stale=True,
                authority_mode="local_first",
            )
            tombstone = run_tombstone_propagation_flow(
                Path(tmpdir) / "tombstone",
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
            )
            authority = run_authority_transition_flow(
                Path(tmpdir) / "authority",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            )
            matrix = run_reconcile_matrix(Path(tmpdir) / "matrix")

            self.assertEqual(outcome_from_flow_result("stale_mirror", stale).surface_state, "remote_metadata_only")
            self.assertEqual(outcome_from_flow_result("tombstone", tombstone).surface_state, "tombstoned")
            self.assertEqual(outcome_from_flow_result("authority_transition", authority).surface_state, "authority_transition_applied")
            surfaces = outcomes_from_reconcile_matrix(matrix)
            self.assertEqual(surfaces["stale_mirror"]["surface_state"], "remote_metadata_only")
            self.assertEqual(surfaces["tombstone"]["surface_state"], "tombstoned")
            self.assertEqual(surfaces["authority_transition"]["surface_state"], "authority_transition_applied")

    def test_cli_surface_and_planner_surface_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cases = [
                argparse.Namespace(
                    kind="stale_mirror",
                    root=str(Path(tmpdir) / "stale"),
                    stale_generation_gap=3,
                    policy_allow_stale=True,
                    signed_tombstone=False,
                    local_dirty=False,
                    authority_mode="local_first",
                    current_authority="local",
                    requested_authority="remote",
                    quorum_granted=False,
                ),
                argparse.Namespace(
                    kind="tombstone",
                    root=str(Path(tmpdir) / "tombstone"),
                    stale_generation_gap=3,
                    policy_allow_stale=False,
                    signed_tombstone=True,
                    local_dirty=False,
                    authority_mode="provider_first",
                    current_authority="local",
                    requested_authority="remote",
                    quorum_granted=False,
                ),
                argparse.Namespace(
                    kind="authority_transition",
                    root=str(Path(tmpdir) / "authority"),
                    stale_generation_gap=3,
                    policy_allow_stale=False,
                    signed_tombstone=False,
                    local_dirty=False,
                    authority_mode="local_first",
                    current_authority="local",
                    requested_authority="remote",
                    quorum_granted=True,
                ),
                argparse.Namespace(
                    kind="reconcile_matrix",
                    root=str(Path(tmpdir) / "matrix"),
                    stale_generation_gap=3,
                    policy_allow_stale=True,
                    signed_tombstone=True,
                    local_dirty=False,
                    authority_mode="provider_first",
                    current_authority="local",
                    requested_authority="remote",
                    quorum_granted=True,
                ),
            ]
            for ns in cases:
                self.assertEqual(cmd_show_surface(ns), 0)
                self.assertEqual(cmd_show_planner_surface(ns), 0)


if __name__ == "__main__":
    unittest.main()
