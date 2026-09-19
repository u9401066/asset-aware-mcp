"""Relocate legacy note/control anchors without rebuilding their VML payloads."""

from __future__ import annotations

import re
from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from src.domain.native_asset_models import cell_position
from src.domain.native_grid_geometry import GridPoint, relocate_axis
from src.infrastructure.native_grid_metrics import EMU_PER_PIXEL
from src.infrastructure.native_grid_xml import address, shift_cell

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid_geometry import (
        GeometryTransform,
        GridAxisMetrics,
        GridPlacement,
    )

VML = "urn:schemas-microsoft-com:vml"
EXCEL = "urn:schemas-microsoft-com:office:excel"
VNS = {"v": VML, "x": EXCEL}
UNITS = {"pt": 12700, "px": EMU_PER_PIXEL, "in": 914400, "cm": 360000, "mm": 36000}
LENGTH = re.compile(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(pt|px|in|cm|mm)\s*", re.I)


def _field(data: etree._Element, name: str) -> etree._Element:
    values = data.findall(f"{{{EXCEL}}}{name}")
    if len(values) != 1:
        raise ValueError("Missing or ambiguous VML object locator")
    return values[0]


def note_location(data: etree._Element) -> str | None:
    if data.get("ObjectType") != "Note":
        return None
    return address(
        int(_field(data, "Row").text or "") + 1,
        int(_field(data, "Column").text or "") + 1,
    )


def _enabled(data: etree._Element, name: str) -> bool:
    nodes = data.findall(f"{{{EXCEL}}}{name}")
    if not nodes:
        return False
    value = (nodes[0].text or "").strip().casefold()
    if len(nodes) != 1 or value not in {"", "true", "false", "t", "f", "1", "0"}:
        raise ValueError("Ambiguous VML positioning policy")
    return value in {"", "true", "t", "1"}


def _style(shape: etree._Element, placement: GridPlacement, axis: str) -> None:
    coordinate, extent = (
        ("margin-top", "height") if axis == "row" else ("margin-left", "width")
    )
    edits = {}
    if placement.new_position != placement.old_position:
        edits[coordinate] = (placement.old_position, placement.new_position)
    if placement.new_extent != placement.old_extent:
        edits[extent] = (placement.old_extent, placement.new_extent)
    if not edits:
        return
    chunks = shape.get("style", "").split(";")
    found = set()
    for index, chunk in enumerate(chunks):
        key, separator, value = chunk.partition(":")
        name = key.strip().casefold()
        if name not in edits or not separator:
            continue
        match = LENGTH.fullmatch(value)
        if name in found or not match:
            raise ValueError("Unsupported or duplicate VML geometry style")
        found.add(name)
        old, new = edits[name]
        size, unit = Decimal(match[1]), match[2].lower()
        if name == coordinate:
            size += Decimal(new - old) / UNITS[unit]
        elif old:
            size *= Decimal(new) / old
        else:
            raise ValueError("Collapsed VML style needs explicit size reconciliation")
        chunks[index] = key + ":" + format(size, "f") + unit
    for name in edits.keys() - found:
        chunks.append(name + ":" + format(Decimal(edits[name][1]) / 12700, "f") + "pt")
    shape.set("style", ";".join(chunks))


def _geometry(
    shape: etree._Element,
    data: etree._Element,
    transform: GeometryTransform,
    before: GridAxisMetrics,
    after: GridAxisMetrics,
) -> dict[str, Any]:
    node = _field(data, "Anchor")
    values = [int(value.strip()) for value in (node.text or "").split(",")]
    if len(values) != 8:
        raise ValueError("VML anchor must contain eight pixel coordinates")
    offset = 2 if transform.edit.axis == "row" else 0
    start = GridPoint(values[offset], values[offset + 1] * EMU_PER_PIXEL)
    end = GridPoint(values[offset + 4], values[offset + 5] * EMU_PER_PIXEL)
    move, resize = _enabled(data, "MoveWithCells"), _enabled(data, "SizeWithCells")
    if resize and not move:
        raise ValueError(
            "VML resize without move requires a dedicated positioning policy"
        )
    mode: Literal["twoCell", "oneCell", "absolute"] = (
        "twoCell" if resize else "oneCell" if move else "absolute"
    )
    placed = relocate_axis(start, end, before, after, transform, mode=mode)
    if any(point.offset % EMU_PER_PIXEL for point in (placed.start, placed.end)):
        raise ValueError("VML relocation cannot represent fractional pixel offsets")
    values[offset : offset + 2] = [
        placed.start.index,
        placed.start.offset // EMU_PER_PIXEL,
    ]
    values[offset + 4 : offset + 6] = [
        placed.end.index,
        placed.end.offset // EMU_PER_PIXEL,
    ]
    if (start, end) != (placed.start, placed.end):
        node.text = ", ".join(map(str, values))
    _style(shape, placed, transform.edit.axis)
    return {"shape_id": shape.get("id"), "mode": mode, **asdict(placed)}


def shift_vml(
    root: etree._Element,
    transform: GeometryTransform,
    before: GridAxisMetrics,
    after: GridAxisMetrics,
) -> list[dict[str, Any]]:
    shapes = root.findall("v:shape", VNS)
    if root.findall("v:group", VNS):
        raise ValueError(
            "Grouped legacy drawing geometry requires a dedicated workflow"
        )
    ids = [shape.get("id", "") for shape in shapes]
    if len(shapes) > 10_000 or len(ids) != len(set(ids)) or "" in ids:
        raise ValueError("Duplicate VML identities or object budget exceeded")
    changes = []
    for shape in shapes:
        clients = shape.findall("x:ClientData", VNS)
        if len(clients) != 1:
            raise ValueError(
                "Worksheet VML object requires one cell positioning record"
            )
        data = clients[0]
        location = note_location(data)
        moved = shift_cell(location, transform) if location is not None else None
        if location is not None and moved is None:
            root.remove(shape)
            changes.append({"shape_id": shape.get("id"), "deleted_note": location})
            continue
        if moved is not None and moved != location:
            row, column = cell_position(moved)
            _field(data, "Row").text = str(row - 1)
            _field(data, "Column").text = str(column - 1)
        geometry = _geometry(shape, data, transform, before, after)
        changes.append({"before_cell": location, "after_cell": moved, **geometry})
    return changes
