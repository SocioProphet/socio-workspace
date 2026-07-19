from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .result_view import ResultViewModel


@dataclass(frozen=True)
class ResultCardSpec:
    flow_name: str
    card_kind: str
    header: str
    subheader: str
    sections: list[str]
    chips: list[str]
    primary_action: str
    content_mode: str
    tone: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def card_from_view(view: ResultViewModel) -> ResultCardSpec:
    if view.container == "alert_strip":
        return ResultCardSpec(
            flow_name=view.flow_name,
            card_kind="alert_card",
            header=view.title,
            subheader=view.subtitle,
            sections=view.body,
            chips=view.chips,
            primary_action=view.primary_action,
            content_mode="hidden",
            tone=view.emphasis,
        )

    if not view.show_content and view.show_metadata:
        return ResultCardSpec(
            flow_name=view.flow_name,
            card_kind="metadata_card",
            header=view.title,
            subheader=view.subtitle,
            sections=view.body,
            chips=view.chips,
            primary_action=view.primary_action,
            content_mode="metadata_only",
            tone=view.emphasis,
        )

    return ResultCardSpec(
        flow_name=view.flow_name,
        card_kind="content_card",
        header=view.title,
        subheader=view.subtitle,
        sections=view.body,
        chips=view.chips,
        primary_action=view.primary_action,
        content_mode="full",
        tone=view.emphasis,
    )


def cards_from_view_matrix(view_matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for flow_name, payload in view_matrix.items():
        view = ResultViewModel(
            flow_name=flow_name,
            container=payload["container"],
            emphasis=payload["emphasis"],
            title=payload["title"],
            subtitle=payload["subtitle"],
            body=list(payload["body"]),
            chips=list(payload["chips"]),
            primary_action=payload["primary_action"],
            show_content=bool(payload["show_content"]),
            show_metadata=bool(payload["show_metadata"]),
        )
        cards[flow_name] = card_from_view(view).to_dict()
    return cards
