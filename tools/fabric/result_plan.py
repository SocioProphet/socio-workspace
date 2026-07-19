from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .planner_surface import PlannerVisibleOutcome


@dataclass(frozen=True)
class ResultServingDecision:
    flow_name: str
    serve_mode: str
    include_content: bool
    include_metadata: bool
    badges: list[str]
    required_actions: list[str]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def serving_decision_from_planner_outcome(outcome: PlannerVisibleOutcome) -> ResultServingDecision:
    if outcome.planner_mode == "hide_from_results":
        return ResultServingDecision(
            flow_name=outcome.flow_name,
            serve_mode="omit",
            include_content=False,
            include_metadata=False,
            badges=[outcome.badge],
            required_actions=[outcome.operator_action],
            message=outcome.message,
        )

    if outcome.planner_mode == "metadata_only":
        return ResultServingDecision(
            flow_name=outcome.flow_name,
            serve_mode="metadata_only",
            include_content=False,
            include_metadata=True,
            badges=[outcome.badge, outcome.freshness_hint],
            required_actions=[outcome.operator_action],
            message=outcome.message,
        )

    if outcome.planner_mode == "serve_with_stale_badge":
        return ResultServingDecision(
            flow_name=outcome.flow_name,
            serve_mode="serve_with_annotation",
            include_content=True,
            include_metadata=True,
            badges=[outcome.badge, outcome.freshness_hint],
            required_actions=[outcome.operator_action],
            message=outcome.message,
        )

    if outcome.planner_mode == "refresh_and_retry":
        return ResultServingDecision(
            flow_name=outcome.flow_name,
            serve_mode="defer_until_refresh",
            include_content=False,
            include_metadata=True,
            badges=[outcome.badge],
            required_actions=[outcome.operator_action],
            message=outcome.message,
        )

    if outcome.planner_mode == "block_until_manual_resolution":
        return ResultServingDecision(
            flow_name=outcome.flow_name,
            serve_mode="blocked",
            include_content=False,
            include_metadata=True,
            badges=[outcome.badge],
            required_actions=[outcome.operator_action],
            message=outcome.message,
        )

    return ResultServingDecision(
        flow_name=outcome.flow_name,
        serve_mode="serve_normally",
        include_content=True,
        include_metadata=True,
        badges=[outcome.badge],
        required_actions=[],
        message=outcome.message,
    )


def serving_decision_from_planner_dict(flow_name: str, outcome: dict[str, Any]) -> ResultServingDecision:
    planner = PlannerVisibleOutcome(
        flow_name=flow_name,
        planner_mode=outcome["planner_mode"],
        badge=outcome["badge"],
        freshness_hint=outcome["freshness_hint"],
        authority_hint=outcome["authority_hint"],
        operator_action=outcome["operator_action"],
        message=outcome["message"],
    )
    return serving_decision_from_planner_outcome(planner)


def serving_decisions_from_planner_matrix(planner_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: serving_decision_from_planner_dict(name, outcome).to_dict()
        for name, outcome in planner_matrix.items()
    }
