"""Inspect OpenFormula resource references without evaluating spreadsheet values."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.infrastructure.native_odf_package import NS
from src.infrastructure.native_workbook_render_source import RESOURCE_FUNCTIONS

if TYPE_CHECKING:
    from lxml import etree

FUNCTION = re.compile(r"(?<![\w.])([A-Za-z_][A-Za-z_0-9.]*)\s*\(")
ERROR = re.compile(r"#(?:REF!|VALUE!|NULL!|DIV/0!|NAME\?|NUM!|N/A)(?![A-Za-z_0-9])")


def _quoted(text: str, start: int) -> tuple[int, str]:
    quote = text[start]
    index, value = start + 1, []
    while index < len(text):
        if text[index] == quote:
            if index + 1 < len(text) and text[index + 1] == quote:
                value.append(quote)
                index += 2
                continue
            return index + 1, "".join(value)
        value.append(text[index])
        index += 1
    raise ValueError("Unterminated ODS formula/reference quote")


def check_reference(text: str) -> None:
    """External OpenFormula references have a # outside quoted document/sheet names."""
    index = 0
    while index < len(text):
        if text[index] == "'":
            index, _ = _quoted(text, index)
        elif text[index] == "#":
            if error := ERROR.match(text, index):
                index = error.end()
            else:
                raise ValueError(
                    "External ODS references need a resource-aware preview"
                )
        else:
            index += 1


def check_formula(text: str, node: etree._Element, *, qualified: bool) -> None:
    if len(text) > 65_536:
        raise ValueError("ODS preview formula exceeds its inspection budget")
    if qualified and not text.startswith("="):
        prefix, separator, expression = text.partition(":")
        if not separator or node.nsmap.get(prefix) != NS["of"]:
            raise ValueError("ODS preview requires a known OpenFormula namespace")
        text = expression
    if qualified and not text.startswith("="):
        raise ValueError("ODS OpenFormula expression must begin with equals")
    visible, index = list(text), 0
    while index < len(text):
        start = index
        if text[index] == '"':
            index, _ = _quoted(text, index)
        elif text[index] == "[":
            index += 1
            while index < len(text) and text[index] != "]":
                if text[index] == "'":
                    index, _ = _quoted(text, index)
                elif text[index] == "[":
                    raise ValueError("Nested ODS formula reference")
                else:
                    index += 1
            if index == len(text):
                raise ValueError("Unterminated ODS formula reference")
            check_reference(text[start + 1 : index])
            index += 1
        elif text[index] in "']":
            raise ValueError("Ambiguous ODS formula reference syntax")
        else:
            index += 1
            continue
        visible[start:index] = " " * (index - start)
    masked = "".join(visible)
    for match in FUNCTION.finditer(masked):
        name = match[1].upper()
        if "." in name:
            if not name.startswith(("COM.MICROSOFT.", "ORG.OPENOFFICE.")):
                raise ValueError("ODS add-in formulas need a resource-aware preview")
            name = name.removeprefix("COM.MICROSOFT.").removeprefix("ORG.OPENOFFICE.")
        if name in RESOURCE_FUNCTIONS:
            raise ValueError(
                "Resource-loading ODS formulas need a resource-aware preview"
            )
        if name == "INDIRECT":
            start = match.end()
            while start < len(text) and text[start].isspace():
                start += 1
            if start >= len(text) or text[start] != '"':
                raise ValueError("Dynamic ODS INDIRECT needs a resource-aware preview")
            end, reference = _quoted(text, start)
            remainder = text[end:].lstrip()
            if not remainder.startswith((";", ")")):
                raise ValueError("Dynamic ODS INDIRECT needs a resource-aware preview")
            check_reference(reference)
            if re.search(r"(?:^|[\s\[])[A-Za-z][A-Za-z0-9+.-]*:", reference):
                raise ValueError("External ODS INDIRECT needs a resource-aware preview")
