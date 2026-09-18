"""Native spreadsheet reads and scoped cell edits with explicit preservation checks."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

from src.domain.native_assets import (
    cell_position,
)
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    SHEET_NS,
    NativeOOXMLPackage,
)

if TYPE_CHECKING:
    from lxml import etree

NS = {"s": SHEET_NS}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
ESCAPED_CHARACTER = re.compile(r"_x([0-9A-Fa-f]{4})_")


def _decode_text(value: str) -> str:
    # ST_Xstring escapes are UTF-16 code units. Substitute only once so an
    # escaped underscore in _x005F_x0041_ stays the literal text _x0041_.
    decoded = ESCAPED_CHARACTER.sub(lambda match: chr(int(match[1], 16)), value)
    try:
        return decoded.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    except UnicodeError as exc:
        raise ValueError("Invalid UTF-16 escape in spreadsheet text") from exc


def _encode_text(value: str) -> str:
    return re.sub(r"_(?=x[0-9A-Fa-f]{4}_)", "_x005F_", value).replace("\r", "_x000D_")


def _tag(name: str) -> str:
    return f"{{{SHEET_NS}}}{name}"


def _contains(bounds: str, address: str) -> bool:
    pieces = bounds.replace("$", "").split(":")
    if len(pieces) not in {1, 2}:
        raise ValueError("Unsupported worksheet range")
    first, last = cell_position(pieces[0]), cell_position(pieces[-1])
    row, col = cell_position(address)
    return first[0] <= row <= last[0] and first[1] <= col <= last[1]


class NativeSpreadsheetReader:
    def __init__(self, data: bytes):
        self.package = NativeOOXMLPackage(data)
        self.workbook_path = self.package.workbook_path()
        self.workbook = self.package.xml(self.workbook_path)
        self.rels = self.package.relationships(self.workbook_path)
        self.sheets: dict[str, dict[str, str]] = {}
        for sheet in self.workbook.findall("s:sheets/s:sheet", NS):
            name, identity = sheet.get("name"), sheet.get("sheetId")
            rid = sheet.get(f"{{{DOC_REL_NS}}}id", "")
            kind, path = self.rels.get(rid, ("", ""))
            if not name or not identity or not path or name in self.sheets:
                raise ValueError("Invalid or ambiguous worksheet identity")
            self.sheets[name] = {"sheet_id": identity, "part": path, "kind": kind}
        if not self.sheets:
            raise ValueError("Workbook contains no sheets")
        self.shared_strings: list[etree._Element] = []
        self.shared_string_path: str | None = None
        for kind, path in self.rels.values():
            if kind == f"{DOC_REL_NS}/sharedStrings":
                if self.shared_string_path is not None:
                    raise ValueError("Ambiguous shared-string relationships")
                self.shared_string_path = path
                self.shared_strings = self.package.xml(path).findall("s:si", NS)

    def _sheet(self, name: str) -> etree._Element:
        if name not in self.sheets:
            raise ValueError(f"Unknown worksheet: {name}")
        info = self.sheets[name]
        if info["kind"] != f"{DOC_REL_NS}/worksheet":
            raise ValueError("Chart/dialog sheets do not expose cell operations")
        root = self.package.xml(info["part"])
        if root.tag != _tag("worksheet") or root.find("s:sheetData", NS) is None:
            raise ValueError("Invalid worksheet structure")
        rows: set[int] = set()
        cells: set[str] = set()
        for row in root.findall("s:sheetData/s:row", NS):
            number = int(row.get("r", "0"))
            if not 1 <= number <= 1_048_576 or number in rows:
                raise ValueError("Invalid or duplicate worksheet row coordinate")
            rows.add(number)
            for cell in row.findall("s:c", NS):
                address = cell.get("r", "")
                if cell_position(address)[0] != number or address in cells:
                    raise ValueError("Cell locator disagrees with its worksheet row")
                cells.add(address)
        return root

    def _value(self, cell: etree._Element | None) -> dict[str, Any]:
        if cell is None:
            return {"kind": "blank", "value": None, "style_index": None}
        kind = cell.get("t", "n")
        raw = cell.findtext("s:v", namespaces=NS)
        style = cell.get("s")
        formula = cell.find("s:f", NS)
        if formula is not None:
            return {
                "kind": "formula",
                "value": "=" + formula.text if formula.text else None,
                "formula_resolved": bool(formula.text),
                "cached_value": raw,
                "cached_value_verified": False,
                "formula_attributes": dict(formula.attrib),
                "style_index": style,
            }
        if kind in {"s", "inlineStr"}:
            return self._string_value(cell, kind, raw, style)
        if kind == "b":
            if raw not in {"0", "1"}:
                raise ValueError("Invalid Boolean cell")
            return {"kind": "boolean", "value": raw == "1", "style_index": style}
        if kind == "n" and raw is not None:
            try:
                number = float(raw)
            except ValueError as exc:
                raise ValueError("Invalid numeric cell") from exc
            if not math.isfinite(number):
                raise ValueError("Nonfinite numeric cell")
            return {
                "kind": "number",
                "value": number,
                "raw_value": raw,
                "style_index": style,
            }
        return {
            "kind": "blank" if raw is None else kind,
            "value": raw,
            "style_index": style,
        }

    def read_cell(self, sheet: str, address: str) -> dict[str, Any]:
        cell_position(address)
        root = self._sheet(sheet)
        matches = root.xpath(
            "./s:sheetData/s:row/s:c[@r=$address]", namespaces=NS, address=address
        )
        return {
            "sheet": sheet,
            "cell": address,
            "locator": {**self.sheets[sheet], "cell": address},
            **self._value(matches[0] if matches else None),
        }

    def inspect(
        self, *, sheet: str | None = None, offset: int = 0, limit: int = 200
    ) -> dict[str, Any]:
        if offset < 0 or not 1 <= limit <= 1000:
            raise ValueError("Require offset >= 0 and limit between 1 and 1000")
        selected = [sheet] if sheet else list(self.sheets)
        cells = []
        count = 0
        for name in selected:
            if name not in self.sheets:
                raise ValueError(f"Unknown worksheet: {name}")
            if self.sheets[name]["kind"] != f"{DOC_REL_NS}/worksheet":
                continue
            root = self._sheet(name)
            seen: set[str] = set()
            for cell in root.findall("s:sheetData/s:row/s:c", NS):
                address = cell.get("r", "")
                cell_position(address)
                if address in seen:
                    raise ValueError("Duplicate worksheet cell address")
                seen.add(address)
                if offset <= count < offset + limit:
                    cells.append(
                        {
                            "sheet": name,
                            "cell": address,
                            "locator": {**self.sheets[name], "cell": address},
                            **self._value(cell),
                        }
                    )
                count += 1
        return {
            "sheets": [{"name": name, **info} for name, info in self.sheets.items()],
            "cells": cells,
            "matched_count": count,
            "next_offset": offset + limit if offset + limit < count else None,
            "formula_evaluation": "not_performed",
            "rendered_layout": "agent_review_required",
        }

    def _string_value(
        self, cell: etree._Element, kind: str, raw: str | None, style: str | None
    ) -> dict[str, Any]:
        if kind == "s":
            try:
                index = int(raw or "")
            except ValueError as exc:
                raise ValueError("Invalid shared-string index") from exc
            if index < 0 or index >= len(self.shared_strings):
                raise ValueError("Missing shared-string item")
            text_root = self.shared_strings[index]
        else:
            text_root = cell.find("s:is", NS)
            if text_root is None:
                raise ValueError("Missing inline string")
        text = "".join(
            text_root.xpath("./s:t/text() | ./s:r/s:t/text()", namespaces=NS)
        )
        return {
            "kind": "string",
            "value": _decode_text(text),
            "rich_text": bool(text_root.findall("s:r", NS)),
            "style_index": style,
        }
