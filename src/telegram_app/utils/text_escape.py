from __future__ import annotations

import html
from telegram.helpers import escape_markdown


def esc_html(x: object | None) -> str:
    """Escape seguro para textos enviados con parse_mode=HTML."""
    return html.escape("" if x is None else str(x))


def esc_md(x: object | None, *, version: int = 2) -> str:
    """Escape seguro para textos enviados con parse_mode=Markdown/MarkdownV2."""
    return escape_markdown("" if x is None else str(x), version=version)
