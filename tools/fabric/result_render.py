from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .result_interface import ResultInterfaceView


@dataclass(frozen=True)
class RenderBlock:
    flow_name: str
    variant: str
    status_tone: str
    headline: str
    subheadline: str
    body_lines: list[str]
    badges: list[str]
    affordances: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def render_block_from_interface(view: ResultInterfaceView) -> RenderBlock:
    if view.display_state == "hidden":
        return RenderBlock(
            flow_name=view.flow_name,
            variant="banner",
            status_tone="critical",
            headline=view.headline,
            subheadline="Result is hidden from the surface.",
            body_lines=[view.detail],
            badges=view.badges,
            affordances=[view.next_action],
        )

    if view.display_state == "metadata_only":
        return RenderBlock(
            flow_name=view.flow_name,
            variant="card",
            status_tone="warning",
            headline=view.headline,
            subheadline="Only metadata is available.",
            body_lines=[view.detail],
            badges=view.badges,
            affordances=[view.next_action],
        )

    if view.display_state == "pending_refresh":
        return RenderBlock(
            flow_name=view.flow_name,
            variant="card",
            status_tone="info",
            headline=view.headline,
            subheadline="Serving is deferred until refresh.",
            body_lines=[view.detail],
            badges=view.badges,
            affordances=[view.next_action],
        )

    if view.display_state == "blocked":
        return RenderBlock(
            flow_name=view.flow_name,
            variant="banner",
            status_tone="critical",
            headline=view.headline,
            subheadline="Manual resolution is required.",
            body_lines=[view.detail],
            badges=view.badges,
            affordances=[view.next_action],
        )

    if view.display_state == "annotated":
        return RenderBlock(
            flow_name=view.flow_name,
            variant="card",
            status_tone="warning",
            headline=view.headline,
            subheadline="Serving with visible annotations.",
            body_lines=[view.detail],
            badges=view.badges,
            affordances=[view.next_action],
        )

    return RenderBlock(
        flow_name=view.flow_name,
        variant="card",
        status_tone="normal",
        headline=view.headline,
        subheadline="Serving normally.",
        body_lines=[view.detail],
        badges=view.badges,
        affordances=[view.next_action],
    )


def render_blocks_from_interface_matrix(interface_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    for flow_name, payload in interface_matrix.items():
        view = ResultInterfaceView(
            flow_name=flow_name,
            display_state=payload["display_state"],
            headline=payload["headline"],
            detail=payload["detail"],
            badges=list(payload["badges"]),
            content_visible=bool(payload["content_visible"]),
            metadata_visible=bool(payload["metadata_visible"]),
            next_action=payload["next_action"],
        )
        blocks[flow_name] = render_block_from_interface(view).to_dict()
    return blocks
