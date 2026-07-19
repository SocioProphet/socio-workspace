from __future__ import annotations

from html import escape

from .result_preview import ResultPreview


def html_from_preview(preview: ResultPreview) -> str:
    classes = [
        "result-preview",
        preview.layout,
        f"tone-{preview.visual_tone}",
        f"visibility-{preview.visibility}",
    ]
    chips = "".join(
        f'<li class="chip">{escape(chip)}</li>' for chip in preview.chips
    )
    lines = "".join(
        f'<li class="summary-line">{escape(line)}</li>' for line in preview.summary_lines
    )
    action = escape(preview.action_label)
    return (
        f'<article class="{" ".join(classes)}" data-flow="{escape(preview.flow_name)}">'
        f'<header><h2>{escape(preview.title)}</h2><p>{escape(preview.subtitle)}</p></header>'
        f'<ul class="summary">{lines}</ul>'
        f'<ul class="chips">{chips}</ul>'
        f'<footer><button>{action}</button></footer>'
        '</article>'
    )



def html_from_preview_matrix(preview_matrix: dict[str, dict[str, object]]) -> str:
    items: list[str] = []
    for flow_name, payload in preview_matrix.items():
        preview = ResultPreview(
            flow_name=flow_name,
            layout=str(payload["layout"]),
            title=str(payload["title"]),
            subtitle=str(payload["subtitle"]),
            summary_lines=list(payload["summary_lines"]),
            chips=list(payload["chips"]),
            action_label=str(payload["action_label"]),
            visual_tone=str(payload["visual_tone"]),
            visibility=str(payload["visibility"]),
        )
        items.append(html_from_preview(preview))
    return '<section class="result-preview-grid">' + "".join(items) + '</section>'
