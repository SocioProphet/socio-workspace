from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .result_plan import ResultServingDecision


@dataclass(frozen=True)
class ResultInterfaceView:
    flow_name: str
    display_state: str
    headline: str
    detail: str
    badges: list[str]
    content_visible: bool
    metadata_visible: bool
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def interface_from_serving_decision(decision: ResultServingDecision) -> ResultInterfaceView:
    if decision.serve_mode == "omit":
        return ResultInterfaceView(
            flow_name=decision.flow_name,
            display_state="hidden",
            headline="Content omitted",
            detail=decision.message,
            badges=decision.badges,
            content_visible=False,
            metadata_visible=False,
            next_action=decision.required_actions[0] if decision.required_actions else "none",
        )

    if decision.serve_mode == "metadata_only":
        return ResultInterfaceView(
            flow_name=decision.flow_name,
            display_state="metadata_only",
            headline="Metadata only",
            detail=decision.message,
            badges=decision.badges,
            content_visible=False,
            metadata_visible=True,
            next_action=decision.required_actions[0] if decision.required_actions else "none",
        )

    if decision.serve_mode == "defer_until_refresh":
        return ResultInterfaceView(
            flow_name=decision.flow_name,
            display_state="pending_refresh",
            headline="Refresh required",
            detail=decision.message,
            badges=decision.badges,
            content_visible=False,
            metadata_visible=True,
            next_action=decision.required_actions[0] if decision.required_actions else "none",
        )

    if decision.serve_mode == "blocked":
        return ResultInterfaceView(
            flow_name=decision.flow_name,
            display_state="blocked",
            headline="Manual resolution required",
            detail=decision.message,
            badges=decision.badges,
            content_visible=False,
            metadata_visible=True,
            next_action=decision.required_actions[0] if decision.required_actions else "none",
        )

    if decision.serve_mode == "serve_with_annotation":
        return ResultInterfaceView(
            flow_name=decision.flow_name,
            display_state="annotated",
            headline="Serving with annotation",
            detail=decision.message,
            badges=decision.badges,
            content_visible=True,
            metadata_visible=True,
            next_action=decision.required_actions[0] if decision.required_actions else "none",
        )

    return ResultInterfaceView(
        flow_name=decision.flow_name,
        display_state="visible",
        headline="Serving normally",
        detail=decision.message,
        badges=decision.badges,
        content_visible=decision.include_content,
        metadata_visible=decision.include_metadata,
        next_action=decision.required_actions[0] if decision.required_actions else "none",
    )


def interfaces_from_serving_matrix(serving_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    views: dict[str, dict[str, Any]] = {}
    for flow_name, payload in serving_matrix.items():
        decision = ResultServingDecision(
            flow_name=flow_name,
            serve_mode=payload["serve_mode"],
            include_content=bool(payload["include_content"]),
            include_metadata=bool(payload["include_metadata"]),
            badges=list(payload["badges"]),
            required_actions=list(payload["required_actions"]),
            message=payload["message"],
        )
        views[flow_name] = interface_from_serving_decision(decision).to_dict()
    return views
