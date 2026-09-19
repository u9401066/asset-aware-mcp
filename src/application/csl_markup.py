"""Preserve CSL typography without importing arbitrary markup into wiki notes."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

TAGS = frozenset({"div", "span", "i", "em", "b", "strong", "sup", "sub"})
CLASSES = frozenset(
    {
        "csl-entry",
        "csl-bib-body",
        "csl-block",
        "csl-left-margin",
        "csl-right-inline",
        "csl-indent",
    }
)
STYLES = frozenset(
    {
        "font-style:normal;",
        "font-variant:small-caps;",
        "font-variant:normal;",
        "font-weight:normal;",
        "text-decoration:none;",
        "text-decoration:underline;",
    }
)


class _CslMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in TAGS:
            return
        if len(self.stack) >= 100:
            raise ValueError("CSL markup nesting limit")
        safe = ""
        for key, value in attrs:
            if (key == "class" and value in CLASSES) or (
                key == "style" and value in STYLES
            ):
                safe += f' {key}="{html.escape(value or "", quote=True)}"'
        self.parts.append(f"<{tag}{safe}>")
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            raise ValueError("Unbalanced CSL output markup")
        self.stack.pop()
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        escaped = html.escape(data, quote=False)
        escaped = re.sub(r"[\[\]|`*_#]", lambda m: f"&#{ord(m[0])};", escaped)
        self.parts.append(escaped)


def safe_csl_html(value: str) -> str:
    parser = _CslMarkup()
    parser.feed(value)
    parser.close()
    if parser.stack:
        raise ValueError("Unclosed CSL output markup")
    return "".join(parser.parts)


def citation_preview(
    citations: list[dict], bibliography: list[dict], options: dict
) -> bytes:
    """Standalone typography preview; dimensions come from bounded processor options."""
    line_spacing = min(4, max(1, int(options.get("linespacing", 1))))
    entry_spacing = min(4, max(0, int(options.get("entryspacing", 1))))
    indent = (
        "padding-left:2em;text-indent:-2em;" if options.get("hangingindent") else ""
    )
    css = (
        "body{font-family:Georgia,serif;max-width:52rem;margin:3rem auto;padding:0 1.5rem;color:#17202a}"
        f".csl-entry{{line-height:{line_spacing};margin-bottom:{entry_spacing}em;{indent}}}"
        ".csl-left-margin{float:left;min-width:2em;text-indent:0}.csl-right-inline{margin-left:2em;text-indent:0}"
        ".citation{margin:1em 0}.scope{font:0.9rem/1.5 system-ui;color:#465365}"
    )
    citation_html = "\n".join(
        f'<div class="citation"><strong>{html.escape(c["id"])}</strong><br>{c["html"]}</div>'
        for c in citations
    )
    bibliography_html = "\n".join(entry["html"] for entry in bibliography)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
        f"<title>Citation document</title><style>{css}</style></head><body><h1>Citation document</h1>"
        f"{citation_html}<h2>Bibliography</h2>{bibliography_html}"
        '<p class="scope">Rendered by citeproc-js (Frank Bennett) and official CSL styles. '
        "Bibliographic data, source support, printed locators and typography require Agent review.</p>"
        "</body></html>"
    ).encode()
