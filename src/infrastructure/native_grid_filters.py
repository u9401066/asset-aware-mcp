"""Filter/sort ranges and relative column IDs through worksheet grid edits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.native_grid_xml import Rectangle
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform


def shift_filters(root: etree._Element, transform: GridTransform) -> int:
    count = 0
    for node in list(root.findall(".//s:autoFilter", NS)):
        before = Rectangle.parse(node.get("ref", ""))
        after = before.shift(transform, clip=True)
        if after is None:
            node.getparent().remove(node)
            count += 1
            continue
        if after != before:
            node.set("ref", after.text)
            count += 1
        seen = set()
        for column in list(node.findall("s:filterColumn", NS)):
            index = int(column.get("colId", "-1"))
            if (
                not 0 <= index <= before.last_column - before.first_column
                or index in seen
            ):
                raise ValueError("Invalid or duplicate filter column index")
            seen.add(index)
            if transform.edit.axis == "column":
                moved = transform.point(before.first_column + index)
                if moved is None:
                    node.remove(column)
                else:
                    column.set("colId", str(moved - after.first_column))
    for node in list(root.findall(".//s:sortState", NS)):
        before = Rectangle.parse(node.get("ref", ""))
        after = before.shift(transform, clip=True)
        if after is None:
            node.getparent().remove(node)
            count += 1
            continue
        if after != before:
            node.set("ref", after.text)
            count += 1
        for condition in list(node.findall("s:sortCondition", NS)):
            value = Rectangle.parse(condition.get("ref", "")).shift(
                transform, clip=True
            )
            if value is None:
                node.remove(condition)
            else:
                condition.set("ref", value.text)
        if not node.findall("s:sortCondition", NS):
            node.getparent().remove(node)
    return count
