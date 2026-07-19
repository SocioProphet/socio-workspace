from __future__ import annotations

from html import escape

from .result_html import html_from_preview, html_from_preview_matrix
from .result_preview import ResultPreview


_BASE_STYLE = """
body { font-family: system-ui, sans-serif; margin: 24px; }
header.page-header { margin-bottom: 20px; }
section.result-preview-grid { display: grid; gap: 16px; }
article.result-preview { border: 1px solid #ccc; border-radius: 10px; padding: 16px; }
article.inline_alert { border-left: 6px solid #b00020; }
article.metadata_panel { border-left: 6px solid #d97706; }
article.content_panel { border-left: 6px solid #2563eb; }
ul.summary, ul.chips { padding-left: 20px; }
button { padding: 6px 12px; }
""".strip()


def page_from_preview(title: str, preview: ResultPreview) -> str:
    body = html_from_preview(preview)
    return (
        "<!doctype html>"
        "<html><head>"
        f"<title>{escape(title)}</title>"
        f"<style>{_BASE_STYLE}</style>"
        "</head><body>"
        f'<header class="page-header"><h1>{escape(title)}</h1></header>'
        f"{body}"
        "</body></html>"
    )



def page_from_preview_matrix(title: str, preview_matrix: dict[str, dict[str, object]]) -> str:
    body = html_from_preview_matrix(preview_matrix)
    return (
        "<!doctype html>"
        "<html><head>"
        f"<title>{escape(title)}</title>"
        f"<style>{_BASE_STYLE}</style>"
        "</head><body>"
        f'<header class="page-header"><h1>{escape(title)}</h1></header>'
        f"{body}"
        "</body></html>"
    )
