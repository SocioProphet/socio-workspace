from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .result_render import RenderBlock


@dataclass(frozen=True)
class ResultViewModel:
    flow_name: str
    container: str
    emphasis: str
    title: str
    subtitle: str
    body: list[str]
    chips: list[str]
    primary_action: str
    show_content: bool
    show_metadata: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def view_from_render_block(block: RenderBlock) -> ResultViewModel:
    if block.variant == "banner":
        return ResultViewModel(
            flow_name=block.flow_name,
            container="alert_strip",
            emphasis=block.status_tone,
            title=block.headline,
            subtitle=block.subheadline,
            body=block.body_lines,
            chips=block.badges,
            primary_action=block.affordances[0] if block.affordances else "none",
            show_content=False,
            show_metadata=False,
        )

    if block.status_tone == "warning":
        return ResultViewModel(
            flow_name=block.flow_name,
            container="detail_card",
            emphasis="warning",
            title=block.headline,
            subtitle=block.subheadline,
            body=block.body_lines,
            chips=block.badges,
            primary_action=block.affordances[0] if block.affordances else "none",
            show_content=False,
            show_metadata=True,
        )

    if block.status_tone == "info":
        return ResultViewModel(
            flow_name=block.flow_name,
            container="detail_card",
            emphasis="info",
            title=block.headline,
            subtitle=block.subheadline,
            body=block.body_lines,
            chips=block.badges,
            primary_action=block.affordances[0] if block.affordances else "none",
            show_content=False,
            show_metadata=True,
        )

    return ResultViewModel(
        flow_name=block.flow_name,
        container="detail_card",
        emphasis="normal",
        title=block.headline,
        subtitle=block.subheadline,
        body=block.body_lines,
        chips=block.badges,
        primary_action=block.affordances[0] if block.affordances else "none",
        show_content=True,
        show_metadata=True,
    )


def views_from_render_matrix(render_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    views: dict[str, dict[str, Any]] = {}
    for flow_name, payload in render_matrix.items():
        block = RenderBlock(
            flow_name=flow_name,
            variant=payload["variant"],
            status_tone=payload["status_tone"],
            headline=payload["headline"],
            subheadline=payload["subheadline"],
            body_lines=list(payload["body_lines"]),
            badges=list(payload["badges"]),
            affordances=list(payload["affordances"]),
        )
        views[flow_name] = view_from_render_block(block).to_dict()
    return views
