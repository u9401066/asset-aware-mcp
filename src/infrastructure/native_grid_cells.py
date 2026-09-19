"""Relocate original row/cell XML while preserving native payload and formatting."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_asset_models import cell_position
from src.infrastructure.native_grid_xml import (
    MAX_GRID_CELLS,
    address,
    cell_map,
    shift_cell,
    tag,
)
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform

ROW_FORMAT = {
    "s",
    "customFormat",
    "ht",
    "hidden",
    "customHeight",
    "outlineLevel",
    "collapsed",
    "thickTop",
    "thickBot",
    "ph",
}


def _template_index(transform: GridTransform) -> int | None:
    edit = transform.edit
    policy = edit.inherit_format or "before"
    if edit.operation != "insert" or policy == "none":
        return None
    return edit.at - 1 if policy == "before" else edit.at


def shift_columns(root: etree._Element, transform: GridTransform) -> None:
    if transform.edit.axis != "column":
        return
    containers = root.findall("s:cols", NS)
    if len(containers) > 1:
        raise ValueError("Multiple column format containers are ambiguous")
    if not containers:
        return
    container = containers[0]
    before: dict[int, dict[str, str]] = {}
    for node in container:
        if not isinstance(node.tag, str):
            continue
        if node.tag != tag("col") or len(node):
            raise ValueError("Unsupported column format structure")
        first, last = int(node.get("min", "0")), int(node.get("max", "0"))
        if not 1 <= first <= last <= 16_384:
            raise ValueError("Invalid column format bounds")
        attrs = {
            key: value
            for key, value in node.attrib.items()
            if key not in {"min", "max"}
        }
        for index in range(first, last + 1):
            if index in before:
                raise ValueError("Overlapping column format definitions")
            before[index] = attrs
    after = {}
    for index, attrs in before.items():
        moved = transform.point(index)
        if moved is not None:
            after[moved] = attrs
    template = before.get(_template_index(transform) or 0)
    if template is not None:
        for index in range(transform.edit.at, transform.edit.at + transform.edit.count):
            after[index] = template
    nodes: list[etree._Element] = []
    previous = 0
    previous_attrs = None
    for index, attrs in sorted(after.items()):
        if nodes and index == previous + 1 and attrs == previous_attrs:
            nodes[-1].set("max", str(index))
        else:
            nodes.append(
                etree.Element(tag("col"), min=str(index), max=str(index), **attrs)
            )
        previous, previous_attrs = index, attrs
    container[:] = nodes + [node for node in container if not isinstance(node.tag, str)]
    if not len(container):
        root.remove(container)


def shift_cells(root: etree._Element, transform: GridTransform) -> dict[str, int]:
    before = cell_map(root)
    data = root.find("s:sheetData", NS)
    assert data is not None
    rows = {int(row.get("r", "0")): row for row in data.findall("s:row", NS)}
    template_index = _template_index(transform)
    template = deepcopy(rows.get(template_index)) if template_index in rows else None
    # Cell style overrides and row/column defaults are distinct: copy only the
    # override, keeping inserted cells empty and without metadata/value payload.
    styles = (
        {
            cell_position(location)[0]: cell.get("s")
            for location, cell in before.items()
            if cell_position(location)[1] == template_index
            and cell.get("s") is not None
        }
        if transform.edit.axis == "column"
        else {}
    )
    moved_count = deleted_count = inserted_count = 0
    for location, cell in before.items():
        moved = shift_cell(location, transform)
        if moved is None:
            cell.getparent().remove(cell)
            deleted_count += 1
        elif moved != location:
            cell.set("r", moved)
            moved_count += 1
    if transform.edit.axis == "row":
        for index, row in rows.items():
            moved_row = transform.point(index)
            if moved_row is None:
                data.remove(row)
            else:
                row.set("r", str(moved_row))
        if template is not None:
            attrs = {
                key: value
                for key, value in template.attrib.items()
                if key in ROW_FORMAT
            }
            formats = [
                (cell_position(cell.get("r", ""))[1], cell.get("s"))
                for cell in template.findall("s:c", NS)
                if cell.get("s") is not None
            ]
            if len(before) + len(formats) * transform.edit.count > MAX_GRID_CELLS:
                raise ValueError("Inherited cell formats exceed the native grid budget")
            if attrs or formats:
                for index in range(
                    transform.edit.at, transform.edit.at + transform.edit.count
                ):
                    new = etree.SubElement(data, tag("row"), r=str(index), **attrs)
                    for column, style in formats:
                        assert style is not None
                        etree.SubElement(
                            new, tag("c"), r=address(index, column), s=style
                        )
                        inserted_count += 1
    else:
        if len(before) + len(styles) * transform.edit.count > MAX_GRID_CELLS:
            raise ValueError("Inherited cell formats exceed the native grid budget")
        for index, style in styles.items():
            assert style is not None
            for col in range(
                transform.edit.at, transform.edit.at + transform.edit.count
            ):
                etree.SubElement(rows[index], tag("c"), r=address(index, col), s=style)
                inserted_count += 1
    order_cells(root)
    return {
        "moved_cells": moved_count,
        "deleted_cells": deleted_count,
        "inserted_formatted_cells": inserted_count,
    }


def order_cells(root: etree._Element) -> None:
    data = root.find("s:sheetData", NS)
    assert data is not None
    for row in data.findall("s:row", NS):
        cells = sorted(
            row.findall("s:c", NS), key=lambda cell: cell_position(cell.get("r", ""))[1]
        )
        row[:] = cells + [node for node in row if node.tag != tag("c")]
        if row.get("spans") is not None:
            if cells:
                first = cell_position(cells[0].get("r", ""))[1]
                last = cell_position(cells[-1].get("r", ""))[1]
                row.set("spans", f"{first}:{last}")
            else:
                row.attrib.pop("spans")
    data[:] = sorted(
        data.findall("s:row", NS), key=lambda row: int(row.get("r", "0"))
    ) + [node for node in data if node.tag != tag("row")]
    cell_map(root)


def set_cell(root: etree._Element, value: etree._Element) -> None:
    GridCellWriter(root).put(value)


class GridCellWriter:
    """Reuse one validated coordinate index for bounded generated cell payloads."""

    def __init__(self, root: etree._Element):
        self.cells = cell_map(root)
        data = root.find("s:sheetData", NS)
        assert data is not None
        self.data = data
        self.rows = {int(row.get("r", "0")): row for row in data.findall("s:row", NS)}

    def put(self, value: etree._Element) -> None:
        location = value.get("r", "")
        number = cell_position(location)[0]
        existing = self.cells.get(location)
        if existing is not None:
            if len(existing) or set(existing.attrib) - {"r", "s"}:
                raise ValueError(
                    "Generated/preserved cell would overwrite another cell payload"
                )
            existing.getparent().replace(existing, value)
        else:
            if len(self.cells) >= MAX_GRID_CELLS:
                raise ValueError("Generated cells exceed the native grid budget")
            row = self.rows.get(number)
            if row is None:
                row = etree.SubElement(self.data, tag("row"), r=str(number))
                self.rows[number] = row
            row.append(value)
        self.cells[location] = value

    def empty(self, location: str) -> etree._Element:
        node = etree.Element(tag("c"), r=location)
        existing = self.cells.get(location)
        if existing is not None and existing.get("s") is not None:
            node.set("s", existing.get("s", ""))
        return node
