from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .result_surface import VisibleRuntimeOutcome


@dataclass(frozen=True)
class PlannerVisibleOutcome:
    flow_name: str
    planner_mode: str
    badge: str
    freshness_hint: str
    authority_hint: str
    operator_action: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def planner_outcome_from_runtime_surface(surface: VisibleRuntimeOutcome) -> PlannerVisibleOutcome:
    if surface.surface_state == "tombstoned":
        return PlannerVisibleOutcome(
            flow_name=surface.flow_name,
            planner_mode="hide_from_results",
            badge="tombstoned",
            freshness_hint=surface.freshness_class,
            authority_hint=surface.authority_state,
            operator_action="no_read",
            message="Content is tombstoned and should be hidden from result surfaces.",
        )

    if surface.surface_state == "remote_metadata_only":
        return PlannerVisibleOutcome(
            flow_name=surface.flow_name,
            planner_mode="metadata_only",
            badge="stale-mirror",
            freshness_hint=surface.freshness_class,
            authority_hint=surface.authority_state,
            operator_action="offer_hydration_if_policy_allows",
            message="Only metadata should be surfaced because the mirror is stale under local-first policy.",
        )

    if surface.surface_state == "stale_mirror":
        return PlannerVisibleOutcome(
            flow_name=surface.flow_name,
            planner_mode="serve_with_stale_badge",
            badge="stale-mirror",
            freshness_hint=surface.freshness_class,
            authority_hint=surface.authority_state,
            operator_action="annotate_staleness",
            message="Serve results with a stale badge and clear freshness annotation.",
        )

    if surface.surface_state == "authority_transition_applied":
        return PlannerVisibleOutcome(
            flow_name=surface.flow_name,
            planner_mode="refresh_and_retry",
            badge="authority-shift",
            freshness_hint=surface.freshness_class,
            authority_hint=surface.authority_state,
            operator_action="refresh_indexes_and_retry",
            message="Authority changed; refresh dependent state before serving results.",
        )

    if surface.reconcile_state == "manual_reconcile_required":
        return PlannerVisibleOutcome(
            flow_name=surface.flow_name,
            planner_mode="block_until_manual_resolution",
            badge="manual-reconcile",
            freshness_hint=surface.freshness_class,
            authority_hint=surface.authority_state,
            operator_action="manual_resolution",
            message="Manual reconcile is required before serving this surface.",
        )

    return PlannerVisibleOutcome(
        flow_name=surface.flow_name,
        planner_mode="serve_normally",
        badge="normal",
        freshness_hint=surface.freshness_class,
        authority_hint=surface.authority_state,
        operator_action="none",
        message="Surface can be served normally.",
    )


def planner_outcome_from_surface_dict(flow_name: str, surface: dict[str, Any]) -> PlannerVisibleOutcome:
    runtime = VisibleRuntimeOutcome(
        flow_name=flow_name,
        surface_state=surface["surface_state"],
        freshness_class=surface["freshness_class"],
        authority_state=surface["authority_state"],
        reconcile_state=surface["reconcile_state"],
        operator_message=surface["operator_message"],
        event_count=int(surface.get("event_count", 0)),
    )
    return planner_outcome_from_runtime_surface(runtime)


def planner_outcomes_from_runtime_surface_matrix(surface_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: planner_outcome_from_surface_dict(name, surface).to_dict()
        for name, surface in surface_matrix.items()
    }
