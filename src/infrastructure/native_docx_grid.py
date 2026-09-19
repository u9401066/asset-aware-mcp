"""Resolve verified Word table paths and atomically preserve unrelated XML/parts."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_docx_grid import DocxGridResize, NativeDocxTableGridEdit
from src.infrastructure.native_docx_grid_model import W, WordGrid, one
from src.infrastructure.native_docx_grid_mutations import apply
from src.infrastructure.native_docx_structure import (
    DEPENDENCIES,
    body_of,
    canonical,
    field_depths,
)
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from src.infrastructure.native_ooxml import xml_bytes

if TYPE_CHECKING:
    from lxml import etree


def locate(root: etree._Element, chain: list[dict[str, Any]]) -> etree._Element:
    if not chain or len(chain) > 32:
        raise ValueError("Invalid DOCX table ancestry")
    parent = body_of(root)
    table = None
    for i, meta in enumerate(chain):
        if (
            meta.get("source_part") != MAIN_PART
            or meta.get("source_element") != "w:tbl"
        ):
            raise ValueError("DOCX table is not in a supported extracted story")
        if i:
            assert table is not None
            coordinates = str(meta.get("parent_cell", "")).split(":")
            if len(coordinates) != 2 or any(
                not value.isdecimal() for value in coordinates
            ):
                raise ValueError("Invalid DOCX parent-cell locator")
            row, column = map(int, coordinates)
            outer = WordGrid.read(table)
            region = outer.at(row, column)
            if region.column != column:
                raise ValueError(
                    "DOCX parent-cell locator points inside horizontal coverage"
                )
            parent = region.cells[row - region.row]
        elif "sdt_index" in meta:
            index = meta["sdt_index"]
            controls = parent.findall(W + "sdt")
            if type(index) is not int or not 0 <= index < len(controls):
                raise ValueError("DOCX table content-control locator does not resolve")
            content = one(controls[index], "sdtContent")
            if content is None:
                raise ValueError("DOCX table control has no unambiguous content")
            parent = content
        index = meta.get("table_index")
        tables = parent.findall(W + "tbl")
        if type(index) is not int or not 0 <= index < len(tables):
            raise ValueError("DOCX table locator does not resolve")
        table = tables[index]
        if (
            not i
            and "source_order" in meta
            and list(parent).index(table) != meta["source_order"]
        ):
            raise ValueError("DOCX table source order does not resolve")
    assert table is not None
    return table


def read_table(data: bytes, chain: list[dict[str, Any]]) -> dict[str, Any]:
    package = checked_docx(data)
    return WordGrid.read(locate(package.xml(MAIN_PART), chain)).record()


def _guard(
    root: etree._Element, table: etree._Element, request: NativeDocxTableGridEdit
) -> None:
    for ancestor in table.iterancestors():
        if ancestor.tag == W + "sdt":
            pr = one(ancestor, "sdtPr")
            if pr is not None and any(
                node.tag in {W + "dataBinding", W + "docPartObj"}
                or (node.tag == W + "lock" and node.get(W + "val") != "unlocked")
                for node in pr
            ):
                raise ValueError(
                    "Bound or locked content control cannot be structurally edited"
                )
    if all(isinstance(edit, DocxGridResize) for edit in request.edits):
        return
    protected = (
        DEPENDENCIES
        - {"drawing", "pict", "object", "footnoteReference", "endnoteReference"}
    ) | {
        "tcPrChange",
        "trPrChange",
        "tblPrChange",
        "tblGridChange",
        "cellIns",
        "cellDel",
        "cellMerge",
    }
    if any(node.tag in {W + name for name in protected} for node in table.iter()):
        raise ValueError(
            "DOCX table has range/field/revision dependencies requiring coordinated editing"
        )
    body = body_of(root)
    owner = table
    while owner.getparent() is not body:
        parent = owner.getparent()
        if parent is None:
            raise ValueError("DOCX table is not in the document body")
        owner = parent
    if field_depths(body)[list(body).index(owner)]:
        raise ValueError("DOCX table lies inside a field spanning body blocks")


def edit_table(
    data: bytes, chain: list[dict[str, Any]], request: NativeDocxTableGridEdit
) -> tuple[bytes, NativeEditResult]:
    package = checked_docx(data, for_edit=True)
    root = package.xml(MAIN_PART)
    table = locate(root, chain)
    _guard(root, table, request)
    original = deepcopy(table)
    grid = WordGrid.read(table)
    before = [len(grid.rows), len(grid.columns)]
    receipts = []
    inserted = 0
    for edit in request.edits:
        receipt = apply(grid, edit)
        inserted += int(receipt.get("inserted_cells", 0))
        if inserted > 10_000:
            raise ValueError("DOCX batch exceeds 10,000 inserted cells")
        grid = WordGrid.read(table)
        receipts.append({"request": edit.model_dump(), **receipt})
    body_of(root)
    expected = canonical(table)
    changed = expected != canonical(original)
    updated = package.replace({MAIN_PART: xml_bytes(root)}) if changed else data
    after = checked_docx(updated, for_edit=True)
    restored_root = after.xml(MAIN_PART)
    actual = locate(restored_root, chain)
    WordGrid.read(actual)
    if canonical(actual) != expected:
        raise ValueError("DOCX serialized table differs from the planned grid")
    parent = actual.getparent()
    assert parent is not None
    parent.replace(actual, deepcopy(original))
    if canonical(restored_root) != canonical(package.xml(MAIN_PART)):
        raise ValueError("DOCX grid edit changed XML outside the target table")
    if after.parts.keys() != package.parts.keys() or any(
        after.parts[name] != content
        for name, content in package.parts.items()
        if name != MAIN_PART
    ):
        raise ValueError("DOCX grid edit changed unrelated package parts")
    record = grid.record()
    if len(json.dumps(record, ensure_ascii=False).encode()) > 16 * 1024 * 1024:
        raise ValueError("DOCX table readback exceeds the 16 MiB limit")
    result = NativeEditResult(
        changed_parts=[MAIN_PART] if changed else [],
        preserved_parts=len(package.parts) - int(changed),
        changes=[
            {
                "operation": "update_docx_table_grid",
                "reference": request.reference.model_dump(),
                "before_rows_columns": before,
                "after_rows_columns": [len(grid.rows), len(grid.columns)],
                "edits": receipts,
            }
        ],
        checks=[
            "source_revision",
            "block_reference_binding",
            "bounded_grid_and_merge_topology",
            "explicit_merge_content_policy",
            "inserted_cells_readback",
            "serialized_table_readback",
            "unchanged_xml_outside_table",
            "exact_package_inventory",
            "untouched_part_bytes",
        ],
        review_required=[
            "semantic_accuracy",
            "rendered_layout",
            "page_flow",
            "inherited_formatting",
            "repeated_headers",
            "unmodeled_table_dependencies",
        ],
    )
    if len(result.model_dump_json().encode()) > 16 * 1024 * 1024:
        raise ValueError("DOCX table receipt exceeds the 16 MiB limit")
    return updated, result
