from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from .cli import cmd_show_result_plan
from .planner_surface import planner_outcome_from_runtime_surface, planner_outcomes_from_runtime_surface_matrix
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .reconcile_matrix_harness import run_reconcile_matrix
from .result_plan import serving_decision_from_planner_outcome, serving_decisions_from_planner_matrix
from .result_serving_harness import run_result_serving_pipeline
from .result_surface import outcome_from_flow_result, outcomes_from_reconcile_matrix
from .stale_mirror_flow_harness import run_stale_mirror_flow


class ServingMatrixSmokeTest(unittest.TestCase):
    def test_direct_and_pipeline_serving_layers(self) -> None:
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
            pipeline = run_result_serving_pipeline(Path(tmpdir) / "pipeline")

            stale_plan = serving_decision_from_planner_outcome(
                planner_outcome_from_runtime_surface(outcome_from_flow_result("stale_mirror", stale))
            )
            tombstone_plan = serving_decision_from_planner_outcome(
                planner_outcome_from_runtime_surface(outcome_from_flow_result("tombstone", tombstone))
            )
            authority_plan = serving_decision_from_planner_outcome(
                planner_outcome_from_runtime_surface(outcome_from_flow_result("authority_transition", authority))
            )
            matrix_plans = serving_decisions_from_planner_matrix(
                planner_outcomes_from_runtime_surface_matrix(outcomes_from_reconcile_matrix(matrix))
            )

            self.assertEqual(stale_plan.serve_mode, "metadata_only")
            self.assertEqual(tombstone_plan.serve_mode, "omit")
            self.assertEqual(authority_plan.serve_mode, "defer_until_refresh")
            self.assertEqual(matrix_plans["stale_mirror"]["serve_mode"], "metadata_only")
            self.assertEqual(matrix_plans["tombstone"]["serve_mode"], "omit")
            self.assertEqual(matrix_plans["authority_transition"]["serve_mode"], "defer_until_refresh")
            self.assertEqual(pipeline["stale_mirror"]["serve_mode"], "metadata_only")
            self.assertEqual(pipeline["tombstone"]["serve_mode"], "omit")
            self.assertEqual(pipeline["authority_transition"]["serve_mode"], "defer_until_refresh")

    def test_cli_show_result_plan_matrix(self) -> None:
        cases = [
            argparse.Namespace(
                kind="stale_mirror",
                root=None,
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
                root=None,
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
                root=None,
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
                root=None,
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
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, ns in enumerate(cases):
                ns.root = str(Path(tmpdir) / f"case-{idx}")
                rc = cmd_show_result_plan(ns)
                self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
