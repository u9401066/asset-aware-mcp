"""Worksheet ranges, merge anchors and relative rule origins for grid editing."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import cell_position
from src.infrastructure.native_grid_cells import GridCellWriter, order_cells
from src.infrastructure.native_grid_formulas import translate_shared_formula
from src.infrastructure.native_grid_xml import Rectangle, address, cell_map, shift_cell
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform


def plan_merges(
    root: etree._Element, transform: GridTransform
) -> list[tuple[etree._Element, Rectangle, Rectangle | None, etree._Element | None]]:
    result = []
    cells = cell_map(root)
    bounds_seen: list[Rectangle] = []
    for node in root.findall("s:mergeCells/s:mergeCell", NS):
        bounds = Rectangle.parse(node.get("ref", ""))
        if len(bounds_seen) >= 4096:
            raise ValueError("Merged ranges exceed the native grid inspection budget")
        if any(bounds.overlaps(other) for other in bounds_seen):
            raise ValueError("Overlapping merged ranges are ambiguous")
        bounds_seen.append(bounds)
        moved = bounds.shift(transform)
        anchor = None
        if (
            moved is not None
            and shift_cell(bounds.anchor, transform) is None
            and (transform.edit.merged_anchor or "preserve") == "preserve"
            and bounds.anchor in cells
        ):
            anchor = deepcopy(cells[bounds.anchor])
            anchor.set("r", moved.anchor)
        result.append((node, bounds, moved, anchor))
    return result


def apply_merges(
    root: etree._Element,
    plans: list[
        tuple[etree._Element, Rectangle, Rectangle | None, etree._Element | None]
    ],
) -> list[dict[str, Any]]:
    changes = []
    writer = GridCellWriter(root)
    for node, before, after, anchor in plans:
        if anchor is not None:
            writer.put(anchor)
        if after is None or after.anchor == address(after.last_row, after.last_column):
            node.getparent().remove(node)
        else:
            node.set("ref", after.text)
        if before != after:
            changes.append(
                {
                    "before": before.text,
                    "after": after.text if after else None,
                    "anchor_preserved": anchor is not None,
                    "remains_merged": after is not None and ":" in after.text,
                }
            )
    for parent in root.findall("s:mergeCells", NS):
        count = len(parent.findall("s:mergeCell", NS))
        if count:
            parent.set("count", str(count))
        else:
            root.remove(parent)
    order_cells(root)
    return changes


def shift_ranges(root: etree._Element, transform: GridTransform) -> dict[str, int]:
    changed: dict[str, int] = {}
    # Relative rule formulas are stored against the first sqref origin. If that
    # origin is deleted, first copy them to the surviving original cell; the
    # global formula stage then performs the structural coordinate transform.
    for name in (
        "conditionalFormatting",
        "dataValidation",
        "protectedRange",
        "ignoredError",
        "hyperlink",
    ):
        attribute = "ref" if name == "hyperlink" else "sqref"
        for node in list(root.findall(f".//s:{name}", NS)):
            value = node.get(attribute, "")
            old = [Rectangle.parse(item) for item in value.split()]
            if not old:
                raise ValueError("Worksheet range metadata is missing coordinates")
            moved = [(bounds, bounds.shift(transform, clip=True)) for bounds in old]
            surviving = [
                (before, after) for before, after in moved if after is not None
            ]
            if not surviving:
                node.getparent().remove(node)
                changed[name] = changed.get(name, 0) + 1
                continue
            if name in {"conditionalFormatting", "dataValidation"}:
                before, after = surviving[0]
                assert after is not None
                row, col = after.first_row, after.first_column
                if transform.edit.operation == "delete":
                    if transform.edit.axis == "row" and row >= transform.edit.at:
                        row += transform.edit.count
                    elif transform.edit.axis == "column" and col >= transform.edit.at:
                        col += transform.edit.count
                else:
                    row, col = before.first_row, before.first_column
                dr, dc = row - old[0].first_row, col - old[0].first_column
                if dr or dc:
                    for formula in node.xpath(
                        ".//s:formula | .//s:formula1 | .//s:formula2", namespaces=NS
                    ):
                        formula.text = translate_shared_formula(
                            formula.text or "", dr, dc
                        )
                    for threshold in node.findall(".//s:cfvo", NS):
                        if threshold.get("type") == "formula":
                            threshold.set(
                                "val",
                                translate_shared_formula(
                                    threshold.get("val", ""), dr, dc
                                ),
                            )
            updated = " ".join(
                after.text for _, after in surviving if after is not None
            )
            if updated != value:
                node.set(attribute, updated)
                changed[name] = changed.get(name, 0) + 1
    for container in root.findall(".//s:dataValidations", NS):
        count = len(container.findall("s:dataValidation", NS))
        if count:
            container.set("count", str(count))
        else:
            container.getparent().remove(container)
    for name in ("hyperlinks", "protectedRanges", "ignoredErrors"):
        for container in root.findall(f".//s:{name}", NS):
            if not len(container):
                container.getparent().remove(container)
    return changed


def update_dimension(root: etree._Element) -> None:
    dimension = root.find("s:dimension", NS)
    if dimension is None:
        return  # The optional dimension need not be invented.
    points = [cell_position(location) for location in cell_map(root)]
    for node in root.findall("s:mergeCells/s:mergeCell", NS):
        bounds = Rectangle.parse(node.get("ref", ""))
        points.extend(
            [
                (bounds.first_row, bounds.first_column),
                (bounds.last_row, bounds.last_column),
            ]
        )
    if not points:
        dimension.set("ref", "A1")
        return
    rows, cols = zip(*points, strict=True)
    dimension.set("ref", Rectangle(min(rows), min(cols), max(rows), max(cols)).text)
