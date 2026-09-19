"""Patch dimension attributes while retaining cell payloads and interval metadata."""

from __future__ import annotations

from bisect import bisect_right
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_grid_metadata import UNMODELED
from src.infrastructure.native_grid_xml import cell_map, tag
from src.infrastructure.native_ooxml import SHEET_NS
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from src.domain.native_layout import NativeLayoutEdit, NativeLayoutUpdate


def _size(value: str, maximum: str) -> None:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Malformed worksheet dimension") from exc
    if not number.is_finite() or not 0 <= number <= Decimal(maximum):
        raise ValueError("Worksheet dimension exceeds supported bounds")


def dimensions(root: etree._Element) -> dict[str, Any]:
    if root.tag != tag("worksheet"):
        raise ValueError("Layout operations require an ordinary worksheet")
    cell_map(root)
    for name in ("sheetFormatPr", "cols", "sheetProtection"):
        if len(root.findall("s:" + name, NS)) > 1:
            raise ValueError("Ambiguous worksheet layout container")
    defaults = root.find("s:sheetFormatPr", NS)
    if defaults is not None:
        for key, maximum in (("defaultRowHeight", "409.5"), ("defaultColWidth", "255")):
            if key in defaults.attrib:
                _size(defaults.attrib[key], maximum)
    rows = root.findall("s:sheetData/s:row", NS)
    for row in rows:
        if "ht" in row.attrib:
            _size(row.attrib["ht"], "409.5")
    cols = root.find("s:cols", NS)
    columns = []
    occupied: set[int] = set()
    for node in cols if cols is not None else []:
        if not isinstance(node.tag, str):
            continue
        if node.tag != tag("col") or len(node):
            raise ValueError("Unsupported native column interval payload")
        first, last = int(node.get("min", "0")), int(node.get("max", "0"))
        if not 1 <= first <= last <= 16_384:
            raise ValueError("Invalid worksheet column interval")
        interval = set(range(first, last + 1))
        if occupied & interval:
            raise ValueError("Overlapping worksheet column intervals")
        occupied |= interval
        if "width" in node.attrib:
            _size(node.attrib["width"], "255")
        columns.append(dict(node.attrib))
    protection = root.find("s:sheetProtection", NS)
    return {
        "defaults": dict(defaults.attrib) if defaults is not None else {},
        "rows": [dict(row.attrib) for row in rows],
        "columns": columns,
        "protection": dict(protection.attrib) if protection is not None else None,
        "units": {
            "height": "points",
            "width": "raw OOXML column width including padding",
        },
    }


def check_layout_features(root: etree._Element, request: NativeLayoutUpdate) -> None:
    dimensions(root)
    protection = root.find("s:sheetProtection", NS)
    if protection is not None and protection.get("sheet", "0") not in {"0", "false"}:
        for axis in {edit.axis for edit in request.edits}:
            key = "formatRows" if axis == "row" else "formatColumns"
            if protection.get(key, "1") not in {"0", "false"}:
                raise ValueError(
                    "Protected worksheet does not permit this axis formatting"
                )
    unmodeled = {tag(name) for name in UNMODELED}
    for node in root.iter():
        if isinstance(node.tag, str) and node.tag in unmodeled:
            raise ValueError("Unmodeled worksheet layout requires a dedicated workflow")
    if any(
        isinstance(node.tag, str) and etree.QName(node).namespace != SHEET_NS
        for node in root
    ):
        raise ValueError("Foreign worksheet layout needs explicit geometry handling")


def _attributes(attrs: dict[str, str], edit: NativeLayoutEdit) -> dict[str, str]:
    result = dict(attrs)
    field, custom = (
        ("ht", "customHeight") if edit.axis == "row" else ("width", "customWidth")
    )
    size = edit.height_points if edit.axis == "row" else edit.width_ooxml
    if edit.reset_size:
        result.pop(field, None)
        result.pop(custom, None)
    elif size is not None:
        result[field] = format(Decimal(str(size)).normalize(), "f")
        result[custom] = "1"
    if edit.axis == "column" and (edit.reset_size or size is not None):
        result.pop("bestFit", None)
    if edit.hidden is not None:
        result["hidden"] = "1" if edit.hidden else "0"
    return result


def resize_rows(root: etree._Element, edit: NativeLayoutEdit) -> None:
    data = root.find("s:sheetData", NS)
    assert data is not None
    rows = {int(row.attrib["r"]): row for row in data.findall("s:row", NS)}
    existing = sorted(rows)
    for number in range(edit.at, edit.at + edit.count):
        row = rows.get(number)
        attrs = dict(row.attrib) if row is not None else {"r": str(number)}
        changed = _attributes(attrs, edit)
        if changed == attrs:
            continue
        if row is None:
            defaults = root.find("s:sheetFormatPr", NS)
            if (
                edit.hidden is None
                and defaults is not None
                and defaults.get("zeroHeight") in {"1", "true"}
            ):
                # Creating a row record would otherwise make a default-hidden row visible.
                changed["hidden"] = "1"
            row = etree.Element(tag("row"))
            successor = bisect_right(existing, number)
            if successor == len(existing):
                data.append(row)
            else:
                rows[existing[successor]].addprevious(row)
            rows[number] = row
        row.attrib.clear()
        row.attrib.update(changed)


def resize_columns(root: etree._Element, edit: NativeLayoutEdit) -> None:
    cols = root.find("s:cols", NS)
    first, last = edit.at, edit.at + edit.count - 1
    uncovered = set(range(first, last + 1))
    if cols is None:
        cols = etree.Element(tag("cols"))
        data = root.find("s:sheetData", NS)
        assert data is not None
        root.insert(root.index(data), cols)
    for node in list(cols):
        if node.tag != tag("col"):
            continue
        left, right = int(node.attrib["min"]), int(node.attrib["max"])
        start, end = max(left, first), min(right, last)
        if start > end:
            continue
        uncovered.difference_update(range(start, end + 1))
        original = {
            key: value
            for key, value in node.attrib.items()
            if key not in {"min", "max"}
        }
        changed = _attributes(original, edit)
        if changed == original:
            continue
        index = cols.index(node)
        for a, b, attrs in (
            (left, start - 1, original),
            (start, end, changed),
            (end + 1, right, original),
        ):
            if a <= b and attrs:
                replacement = deepcopy(node)
                replacement.attrib.clear()
                replacement.attrib.update({"min": str(a), "max": str(b), **attrs})
                cols.insert(index, replacement)
                index += 1
        cols.remove(node)
    attrs = _attributes({}, edit)
    # Only newly assigned dimensions/visibility need records for absent columns.
    while uncovered and attrs:
        start = end = min(uncovered)
        uncovered.remove(start)
        while end + 1 in uncovered:
            end += 1
            uncovered.remove(end)
        node = etree.Element(tag("col"), min=str(start), max=str(end), **attrs)
        following = next(
            (
                item
                for item in cols
                if item.tag == tag("col") and int(item.attrib["min"]) > start
            ),
            None,
        )
        if following is None:
            cols.append(node)
        else:
            cols.insert(cols.index(following), node)
    if not len(cols) and not cols.attrib and not cols.text:
        root.remove(cols)
