"""Native selection, frozen pane, and manual print-break coordinate repairs."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from src.infrastructure.native_grid_xml import Rectangle, shift_cell, tag
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform

PANES = {
    "topLeft": (False, False),
    "topRight": (True, False),
    "bottomLeft": (False, True),
    "bottomRight": (True, True),
}


def shift_views(root: etree._Element, transform: GridTransform) -> None:
    for view in root.xpath(".//s:sheetView | .//s:customSheetView", namespaces=NS):
        if view.get("topLeftCell") is not None:
            moved = shift_cell(view.get("topLeftCell", ""), transform, clamp=True)
            assert moved is not None
            view.set("topLeftCell", moved)
        panes = view.findall("s:pane", NS)
        if len(panes) > 1:
            raise ValueError("Worksheet view contains ambiguous panes")
        if panes:
            _pane(panes[0], view, transform)
        for selection in view.findall("s:selection", NS):
            _selection(selection, transform)


def _pane(pane: etree._Element, view: etree._Element, transform: GridTransform) -> None:
    state = pane.get("state", "split")
    if state not in {"split", "frozen", "frozenSplit"}:
        raise ValueError("Unknown worksheet pane state")
    if pane.get("topLeftCell") is not None:
        moved = shift_cell(pane.get("topLeftCell", ""), transform, clamp=True)
        assert moved is not None
        pane.set("topLeftCell", moved)
    values = {key: float(pane.get(key, "0")) for key in ("xSplit", "ySplit")}
    if any(not math.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("Invalid worksheet pane split")
    if state == "split":
        return  # Pixel/point positions are not frozen row/column counts.
    if any(not value.is_integer() for value in values.values()):
        raise ValueError("Frozen panes require integral row/column counts")
    if values["xSplit"] >= 16_384 or values["ySplit"] >= 1_048_576:
        raise ValueError("Frozen pane leaves no scrollable worksheet cells")
    key = "ySplit" if transform.edit.axis == "row" else "xSplit"
    original = int(values[key])
    if original:
        # A frozen area starts at the sheet edge; inserting at row/column one
        # adds frozen cells too. Its trailing boundary follows surviving cells.
        if transform.edit.operation == "insert":
            count = original + (
                transform.edit.count if transform.edit.at <= original else 0
            )
        else:
            removed = max(
                0,
                min(original, transform.edit.at + transform.edit.count - 1)
                - transform.edit.at
                + 1,
            )
            count = original - removed
        if count >= transform.edit.limit:
            raise ValueError("Grid edit freezes the complete worksheet axis")
        values[key] = float(count)
        if count:
            pane.set(key, str(count))
        else:
            pane.attrib.pop(key, None)
    available_x, available_y = bool(values["xSplit"]), bool(values["ySplit"])

    def mapped(value: str) -> str:
        if value not in PANES:
            raise ValueError("Unknown worksheet pane selection")
        x, y = PANES[value]
        selected = (x and available_x, y and available_y)
        return next(name for name, point in PANES.items() if point == selected)

    original_active = pane.get("activePane", "topLeft")
    if pane.get("activePane") is not None:
        pane.set("activePane", mapped(pane.get("activePane", "")))
    selections = view.findall("s:selection", NS)
    active = pane.get("activePane", "topLeft")
    preferred = [
        node for node in selections if node.get("pane", "topLeft") == original_active
    ]
    # If a pane disappears, keep its active selection and consolidate duplicates.
    grouped: dict[str, list[etree._Element]] = {}
    for selection in selections:
        previous = selection.get("pane", "topLeft")
        updated = mapped(previous)
        selection.set("pane", updated)
        grouped.setdefault(updated, []).append(selection)
    for name, group in grouped.items():
        chosen = (
            next((node for node in preferred if node in group), group[0])
            if name == active
            else group[0]
        )
        for selection in group:
            if selection is not chosen:
                view.remove(selection)
    if not available_x and not available_y:
        view.remove(pane)
        for selection in view.findall("s:selection", NS):
            selection.attrib.pop("pane", None)


def _selection(node: etree._Element, transform: GridTransform) -> None:
    active = shift_cell(node.get("activeCell", "A1"), transform, clamp=True)
    assert active is not None
    ranges = [
        Rectangle.parse(value)
        for value in node.get("sqref", node.get("activeCell", "A1")).split()
    ]
    if not ranges:
        raise ValueError("Empty worksheet selection")
    original_index = int(node.get("activeCellId", "0"))
    if not 0 <= original_index < len(ranges):
        raise ValueError("Active selection index is outside its range list")
    indexed = [
        (index, new)
        for index, old in enumerate(ranges)
        if (new := old.shift(transform, clip=True)) is not None
    ]
    moved = [bounds for _, bounds in indexed]
    if not moved:
        moved = [Rectangle.parse(active)]
    selected = next(
        (
            index
            for index, (old_index, bounds) in enumerate(indexed)
            if old_index == original_index and bounds.contains(active)
        ),
        None,
    )
    if selected is None:
        selected = next(
            (index for index, bounds in enumerate(moved) if bounds.contains(active)),
            None,
        )
    if selected is None:
        selected, active = 0, moved[0].anchor
    node.set("sqref", " ".join(bounds.text for bounds in moved))
    node.set("activeCell", active)
    node.set("activeCellId", str(selected))


def shift_breaks(root: etree._Element, transform: GridTransform) -> None:
    for kind, axis in (("rowBreaks", "row"), ("colBreaks", "column")):
        for container in root.findall(f".//s:{kind}", NS):
            for node in list(container):
                if node.tag != tag("brk"):
                    continue
                if axis == transform.edit.axis:
                    moved = transform.point(int(node.get("id", "-1")) + 1)
                    if moved is None:
                        container.remove(node)
                    else:
                        node.set("id", str(moved - 1))
                else:
                    first, last = (
                        int(node.get("min", "0")),
                        int(node.get("max", str(transform.edit.limit - 1))),
                    )
                    span = transform.span(first + 1, last + 1, clip=True)
                    if span is None:
                        container.remove(node)
                    else:
                        node.set("min", str(span[0] - 1))
                        node.set("max", str(span[1] - 1))
            breaks = container.findall("s:brk", NS)
            if not breaks:
                container.getparent().remove(container)
            else:
                container.set("count", str(len(breaks)))
                container.set(
                    "manualBreakCount",
                    str(sum(node.get("man") in {"1", "true"} for node in breaks)),
                )
