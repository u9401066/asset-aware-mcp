"""Guard unmodeled coordinates and repair derived worksheet metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_grid_references import CHART_NS
from src.infrastructure.native_grid_xml import Rectangle, cell_map, shift_cell, tag
from src.infrastructure.native_ooxml import DOC_REL_NS, SHEET_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform
    from src.infrastructure.native_workbook_plan import WorkbookPlan

UNMODELED = {
    "scenarios",
    "smartTags",
    "oleObjects",
    "controls",
    "webPublishItems",
    "extLst",
}
CHART_CACHES = {
    f"{{{CHART_NS}}}{name}" for name in ("numCache", "strCache", "multiLvlStrCache")
}


def check_grid_features(root: etree._Element) -> None:
    if root.tag != tag("worksheet"):
        raise ValueError("Native grid edits require a worksheet, not a chart sheet")
    if root.find("s:sheetProtection", NS) is not None:
        raise ValueError("Protected worksheets require an explicit unlock workflow")
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        name = etree.QName(node)
        if name.namespace == SHEET_NS and name.localname in UNMODELED:
            raise ValueError(
                f"Worksheet {name.localname} needs a dedicated coordinate workflow"
            )
    if any(
        isinstance(node.tag, str) and etree.QName(node).namespace != SHEET_NS
        for node in root
    ):
        raise ValueError(
            "Foreign worksheet structures require explicit coordinate handling"
        )
    for cell in cell_map(root).values():
        if cell.get("cm") is not None or cell.get("vm") is not None:
            raise ValueError("Cell metadata requires an identity-aware grid workflow")


def shift_cell_watches(root: etree._Element, transform: GridTransform) -> int:
    count = 0
    for container in root.findall("s:cellWatches", NS):
        for node in container.findall("s:cellWatch", NS):
            original = node.get("r", "")
            moved = shift_cell(original, transform)
            if moved is None:
                container.remove(node)
            elif moved != original:
                node.set("r", moved)
            count += int(moved != original)
        if not len(container):
            root.remove(container)
    return count


def shift_pivot_locations(
    plan: WorkbookPlan, worksheet: str, transform: GridTransform
) -> int:
    count = 0
    if relationships_path(worksheet) not in plan.book.package.parts:
        return count
    for kind, part in plan.book.package.relationships(worksheet).values():
        if kind != DOC_REL_NS + "/pivotTable" or not part:
            continue
        root = plan.part(part)
        locations = root.findall("s:location", NS)
        if len(locations) != 1:
            raise ValueError("Pivot table requires one complete result location")
        node = locations[0]
        before = Rectangle.parse(node.get("ref", ""))
        after = before.shift(transform)
        if after is None or (
            after.last_row - after.first_row,
            after.last_column - after.first_column,
        ) != (
            before.last_row - before.first_row,
            before.last_column - before.first_column,
        ):
            raise ValueError(
                "Partial pivot result edits require a pivot-aware workflow"
            )
        if after != before:
            node.set("ref", after.text)
            count += 1
    return count


def repair_outline_levels(root: etree._Element) -> None:
    properties = root.find("s:sheetFormatPr", NS)
    if properties is None:
        return
    for key, path in (
        ("outlineLevelRow", "s:sheetData/s:row"),
        ("outlineLevelCol", "s:cols/s:col"),
    ):
        levels = [int(node.get("outlineLevel", "0")) for node in root.findall(path, NS)]
        if any(not 0 <= value <= 7 for value in levels):
            raise ValueError("Worksheet outline levels must be between zero and seven")
        maximum = max(levels, default=0)
        if maximum or key in properties.attrib:
            properties.set(key, str(maximum))


def clear_chart_caches(roots: dict[str, etree._Element]) -> int:
    count = 0
    for root in roots.values():
        for node in list(root.iter()):
            if node.tag in CHART_CACHES:
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
                    count += 1
    return count
