"""Bounded ODF paragraph whitespace and literal display serialization."""

from __future__ import annotations

import re

from lxml import etree

from src.domain.native_ods import MAX_ODS_TEXT
from src.infrastructure.native_odf_package import NS, q


def paragraph_text(root: etree._Element) -> str:
    pieces: list[str] = []
    size = 0
    pending = False

    def append(text: str, *, explicit: bool = False) -> None:
        nonlocal size, pending
        segments = [text] if explicit else re.split(r"([ \t\r\n]+)", text)
        for piece in segments:
            if not piece:
                continue
            if not explicit and re.fullmatch(r"[ \t\r\n]+", piece):
                pending = True
                continue
            if pending and pieces:
                pieces.append(" ")
                size += 1
            pending = False
            size += len(piece)
            if size > MAX_ODS_TEXT:
                raise ValueError("ODS paragraph exceeds text budget")
            pieces.append(piece)

    def walk(node: etree._Element) -> None:
        append(node.text or "")
        for child in node:
            if child.tag == q("text", "s"):
                raw = child.get(q("text", "c"), "1")
                if (
                    not re.fullmatch(r"[0-9]{1,6}", raw)
                    or not 1 <= int(raw) <= MAX_ODS_TEXT
                ):
                    raise ValueError("Invalid or excessive ODS explicit space count")
                append(" " * int(raw), explicit=True)
            elif child.tag in {q("text", "tab"), q("text", "line-break")}:
                append("\t" if child.tag == q("text", "tab") else "\n", explicit=True)
            elif child.tag == q("text", "ruby"):
                base = child.find(q("text", "ruby-base"))
                if base is not None:
                    walk(base)
            elif (
                isinstance(child.tag, str)
                and child.tag.startswith("{" + NS["text"] + "}")
                and child.tag not in {q("text", "note-body"), q("text", "ruby-text")}
            ):
                walk(child)
            append(child.tail or "")

    walk(root)
    return "".join(pieces)


def display_paragraph(value: str) -> etree._Element:
    """Explicit whitespace protects leading/trailing spaces and literal newlines."""
    paragraph = etree.Element(q("text", "p"))
    last: etree._Element | None = None
    for piece in re.split(r"( +|\t|\n|\r)", value):
        if not piece:
            continue
        if piece.startswith(" "):
            last = etree.SubElement(paragraph, q("text", "s"))
            last.set(q("text", "c"), str(len(piece)))
        elif piece in {"\t", "\n", "\r"}:
            last = etree.SubElement(
                paragraph, q("text", "tab" if piece == "\t" else "line-break")
            )
        elif last is None:
            paragraph.text = (paragraph.text or "") + piece
        else:
            last.tail = (last.tail or "") + piece
    return paragraph
