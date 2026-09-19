"""Validate Table membership and names before introducing native structures."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.infrastructure.native_grid_xml import Rectangle, tag
from src.infrastructure.native_ooxml import DOC_REL_NS, TYPE_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS, _decode_text
from src.infrastructure.native_workbook_package import WORKSHEET_REL

if TYPE_CHECKING:
    from src.domain.native_table_create import NativeTableCreate
    from src.infrastructure.native_grid_table_state import GridTableState
    from src.infrastructure.native_workbook_plan import WorkbookPlan

TABLE_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"


def check_creation(
    plan: WorkbookPlan, request: NativeTableCreate, states: list[GridTableState]
) -> Rectangle:
    owner = plan.book.match(request.worksheet)
    if owner["kind"] != WORKSHEET_REL:
        raise ValueError("Native Tables require a worksheet")
    bounds = Rectangle.parse(request.ref)
    if bounds.text != request.ref:
        raise ValueError("Table ref must be a canonical uppercase A1 range")
    if bounds.last_column - bounds.first_column + 1 != len(request.columns):
        raise ValueError("Table range width must match its columns")
    if bounds.last_row - bounds.first_row < int(request.header_row) + int(
        request.totals_row
    ):
        raise ValueError("A new Table needs at least one data row")
    root = plan.roots[request.worksheet.part]
    if root.find("s:sheetProtection", NS) is not None:
        raise ValueError("Protected worksheets require an explicit unlock workflow")
    if any(
        s.worksheet == request.worksheet.part and s.bounds.overlaps(bounds)
        for s in states
    ):
        raise ValueError("New Table overlaps an existing Table")
    for node in root.xpath("s:mergeCells/s:mergeCell | s:autoFilter", namespaces=NS):
        if Rectangle.parse(node.get("ref", "")).overlaps(bounds):
            raise ValueError(
                "New Table overlaps merged cells or a worksheet AutoFilter"
            )
    for formula in root.findall("s:sheetData/s:row/s:c/s:f", NS):
        if formula.get("t") not in {None, "normal"}:
            ref = formula.get("ref", formula.getparent().get("r", ""))
            if Rectangle.parse(ref).overlaps(bounds):
                raise ValueError(
                    "New Table overlaps a shared/array/data-table formula range"
                )
    containers = root.findall("s:tableParts", NS)
    if len(containers) > 1 or any(
        set(c.attrib) - {"count"}
        or any(n.tag != tag("tablePart") for n in c)
        or int(c.get("count", str(len(c)))) != len(c)
        for c in containers
    ):
        raise ValueError("Ambiguous worksheet Table registry")
    check_style(plan, request.style.name)
    return bounds


def reserved_tables(plan: WorkbookPlan, name: str) -> set[int]:
    names = {
        _decode_text(node.get("name", "")).casefold()
        for node in plan.book.workbook.findall("s:definedNames/s:definedName", NS)
    }
    paths = {
        node.get("PartName", "").lstrip("/")
        for node in plan.roots["[Content_Types].xml"]
        if node.tag == f"{{{TYPE_NS}}}Override"
        and node.get("ContentType") == TABLE_TYPE
    }
    # Include active nonstandard part paths even if their content type was omitted.
    for entry in plan.book.entries:
        part = entry["key"]["part"]
        if relationships_path(part) in plan.book.package.parts:
            paths.update(
                target
                for kind, target in plan.book.package.relationships(part).values()
                if kind == f"{DOC_REL_NS}/table"
            )
    ids = set()
    if len(paths) > 1024:
        raise ValueError("Native Table definitions exceed the inspection budget")
    for part in sorted(paths):
        root = plan.book.package.xml(part)
        identity = int(root.get("id", "0"))
        if (
            root.tag != tag("table")
            or not 1 <= identity <= 4_294_967_295
            or identity in ids
        ):
            raise ValueError("Invalid or duplicate native Table IDs")
        ids.add(identity)
        names.update(
            _decode_text(root.get(key, "")).casefold()
            for key in ("name", "displayName")
        )
    if name.casefold() in names:
        raise ValueError("Table name conflicts with an existing Table or defined name")
    return ids


def check_style(plan: WorkbookPlan, name: str | None) -> None:
    if name is None:
        return
    match = re.fullmatch(r"TableStyle(Light|Medium|Dark)([1-9][0-9]?)", name)
    if match and int(match[2]) <= {"Light": 21, "Medium": 28, "Dark": 11}[match[1]]:
        return
    for kind, part in plan.book.package.relationships(plan.book.workbook_path).values():
        if kind == f"{DOC_REL_NS}/styles" and part:
            for node in plan.book.package.xml(part).findall(
                "s:tableStyles/s:tableStyle", NS
            ):
                if node.get("name") == name and node.get("table", "1") in {"1", "true"}:
                    return
    raise ValueError("Table style must be a built-in or existing workbook Table style")
