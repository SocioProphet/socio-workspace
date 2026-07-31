from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .result_card import ResultCardSpec


@dataclass(frozen=True)
class ResultPreview:
    flow_name: str
    layout: str
    title: str
    subtitle: str
    summary_lines: list[str]
    chips: list[str]
    action_label: str
    visual_tone: str
    visibility: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preview_from_card(card: ResultCardSpec) -> ResultPreview:
    if card.card_kind == "alert_card":
        return ResultPreview(
            flow_name=card.flow_name,
            layout="inline_alert",
            title=card.header,
            subtitle=card.subheader,
            summary_lines=card.sections,
            chips=card.chips,
            action_label=card.primary_action,
            visual_tone=card.tone,
            visibility="hidden",
        )

    if card.card_kind == "metadata_card":
        return ResultPreview(
            flow_name=card.flow_name,
            layout="metadata_panel",
            title=card.header,
            subtitle=card.subheader,
            summary_lines=card.sections,
            chips=card.chips,
            action_label=card.primary_action,
            visual_tone=card.tone,
            visibility="metadata_only",
        )

    return ResultPreview(
        flow_name=card.flow_name,
        layout="content_panel",
        title=card.header,
        subtitle=card.subheader,
        summary_lines=card.sections,
        chips=card.chips,
        action_label=card.primary_action,
        visual_tone=card.tone,
        visibility="full",
    )


def previews_from_card_matrix(card_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    previews: dict[str, dict[str, Any]] = {}
    for flow_name, payload in card_matrix.items():
        card = ResultCardSpec(
            flow_name=flow_name,
            card_kind=payload["card_kind"],
            header=payload["header"],
            subheader=payload["subheader"],
            sections=list(payload["sections"]),
            chips=list(payload["chips"]),
            primary_action=payload["primary_action"],
            content_mode=payload["content_mode"],
            tone=payload["tone"],
        )
        previews[flow_name] = preview_from_card(card).to_dict()
    return previews
