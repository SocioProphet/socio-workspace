from __future__ import annotations

from pathlib import Path
from typing import Any

from .planner_surface import planner_outcome_from_runtime_surface, planner_outcomes_from_runtime_surface_matrix
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .reconcile_matrix_harness import run_reconcile_matrix
from .result_plan import serving_decision_from_planner_outcome, serving_decisions_from_planner_matrix
from .result_surface import outcome_from_flow_result, outcomes_from_reconcile_matrix
from .stale_mirror_flow_harness import run_stale_mirror_flow


def run_result_serving_pipeline(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    stale_flow = run_stale_mirror_flow(
        root / "stale_mirror",
        stale_generation_gap=3,
        policy_allow_stale=True,
        authority_mode="local_first",
    )
    tombstone_flow = run_tombstone_propagation_flow(
        root / "tombstone",
        signed_tombstone=True,
        local_dirty=False,
        authority_mode="provider_first",
    )
    authority_flow = run_authority_transition_flow(
        root / "authority_transition",
        current_authority="local",
        requested_authority="remote",
        quorum_granted=True,
    )
    matrix = run_reconcile_matrix(root / "reconcile_matrix")

    stale_surface = outcome_from_flow_result("stale_mirror", stale_flow)
    tombstone_surface = outcome_from_flow_result("tombstone", tombstone_flow)
    authority_surface = outcome_from_flow_result("authority_transition", authority_flow)
    matrix_surfaces = outcomes_from_reconcile_matrix(matrix)

    stale_planner = planner_outcome_from_runtime_surface(stale_surface)
    tombstone_planner = planner_outcome_from_runtime_surface(tombstone_surface)
    authority_planner = planner_outcome_from_runtime_surface(authority_surface)
    matrix_planners = planner_outcomes_from_runtime_surface_matrix(matrix_surfaces)

    stale_plan = serving_decision_from_planner_outcome(stale_planner)
    tombstone_plan = serving_decision_from_planner_outcome(tombstone_planner)
    authority_plan = serving_decision_from_planner_outcome(authority_planner)
    matrix_plans = serving_decisions_from_planner_matrix(matrix_planners)

    return {
        "stale_mirror": stale_plan.to_dict(),
        "tombstone": tombstone_plan.to_dict(),
        "authority_transition": authority_plan.to_dict(),
        "reconcile_matrix": matrix_plans,
    }
