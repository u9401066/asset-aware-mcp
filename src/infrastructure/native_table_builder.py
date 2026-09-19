"""Allocate a native Table definition, relationship and worksheet registration."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_grid_table_state import GridTableState
from src.infrastructure.native_grid_xml import Rectangle, tag
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    SHEET_NS,
    TYPE_NS,
    relationships_path,
)
from src.infrastructure.native_spreadsheet_reader import NS, _encode_text
from src.infrastructure.native_table_create_checks import TABLE_TYPE

if TYPE_CHECKING:
    from src.domain.native_table_create import NativeTableCreate
    from src.infrastructure.native_workbook_plan import WorkbookPlan


def build_table(
    plan: WorkbookPlan, request: NativeTableCreate, bounds: Rectangle, ids: set[int]
) -> GridTableState:
    types = plan.roots["[Content_Types].xml"]
    reserved = (
        set(plan.book.package.parts)
        | set(plan.roots)
        | {node.get("PartName", "").lstrip("/") for node in types}
    )
    base = posixpath.dirname(plan.book.workbook_path)
    number = 1
    while (part := posixpath.join(base, "tables", f"table{number}.xml")) in reserved:
        number += 1
    identity = 1
    while identity in ids:
        identity += 1
    rel_path = relationships_path(request.worksheet.part)
    if rel_path in plan.book.package.parts:
        rels = plan.part(rel_path)
    else:
        rels = etree.Element(f"{{{REL_NS}}}Relationships", nsmap={None: REL_NS})
        plan.roots[rel_path] = rels
    existing = {node.get("Id") for node in rels}
    number = 1
    while (rid := f"rId{number}") in existing:
        number += 1
    etree.SubElement(
        rels,
        f"{{{REL_NS}}}Relationship",
        Id=rid,
        Type=f"{DOC_REL_NS}/table",
        Target=posixpath.relpath(
            part, posixpath.dirname(request.worksheet.part) or "."
        ),
    )
    etree.SubElement(
        types, f"{{{TYPE_NS}}}Override", PartName="/" + part, ContentType=TABLE_TYPE
    )
    root = etree.Element(
        tag("table"),
        nsmap={None: SHEET_NS},
        id=str(identity),
        name=request.name,
        displayName=request.name,
        ref=bounds.text,
        headerRowCount=str(int(request.header_row)),
        totalsRowCount=str(int(request.totals_row)),
        totalsRowShown=str(int(request.totals_row)),
    )
    plan.roots[part] = root
    if request.autofilter:
        filtered = Rectangle(
            bounds.first_row,
            bounds.first_column,
            bounds.last_row - int(request.totals_row),
            bounds.last_column,
        )
        etree.SubElement(root, tag("autoFilter"), ref=filtered.text)
    columns = etree.SubElement(
        root, tag("tableColumns"), count=str(len(request.columns))
    )
    for index, column in enumerate(request.columns, 1):
        etree.SubElement(
            columns, tag("tableColumn"), id=str(index), name=_encode_text(column.name)
        )
    style = request.style
    node = etree.SubElement(
        root,
        tag("tableStyleInfo"),
        showFirstColumn=str(int(style.show_first_column)),
        showLastColumn=str(int(style.show_last_column)),
        showRowStripes=str(int(style.show_row_stripes)),
        showColumnStripes=str(int(style.show_column_stripes)),
    )
    if style.name is not None:
        node.set("name", style.name)
    sheet = plan.roots[request.worksheet.part]
    container = sheet.find("s:tableParts", NS)
    if container is None:
        container = etree.Element(tag("tableParts"))
        # tableParts follows drawings/controls/webPublishItems, before extLst.
        position = next(
            (i for i, node in enumerate(sheet) if node.tag == tag("extLst")), len(sheet)
        )
        sheet.insert(position, container)
    registry = etree.SubElement(
        container, tag("tablePart"), {f"{{{DOC_REL_NS}}}id": rid}
    )
    container.set("count", str(len(container)))
    return GridTableState(part, request.worksheet.part, rid, registry, root)
