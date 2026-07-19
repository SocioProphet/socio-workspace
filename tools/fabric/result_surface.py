from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VisibleRuntimeOutcome:
    flow_name: str
    surface_state: str
    freshness_class: str
    authority_state: str
    reconcile_state: str
    operator_message: str
    event_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def outcome_from_flow_result(flow_name: str, flow_result: dict[str, Any]) -> VisibleRuntimeOutcome:
    label = flow_result["result_label"]
    return VisibleRuntimeOutcome(
        flow_name=flow_name,
        surface_state=label["surface_state"],
        freshness_class=label["freshness_class"],
        authority_state=label["authority_state"],
        reconcile_state=label["reconcile_state"],
        operator_message=label["operator_message"],
        event_count=int(flow_result.get("event_count", 0)),
    )


def outcomes_from_reconcile_matrix(matrix_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "tombstone": outcome_from_flow_result("tombstone", matrix_result["tombstone"]).to_dict(),
        "stale_mirror": outcome_from_flow_result("stale_mirror", matrix_result["stale_mirror"]).to_dict(),
        "authority_transition": outcome_from_flow_result("authority_transition", matrix_result["authority_transition"]).to_dict(),
    }
