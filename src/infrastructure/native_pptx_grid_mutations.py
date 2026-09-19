"""Transform grid nodes and merged rectangles without rebuilding existing cells."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_pptx_table import (
    NativePptxTableCellCreate,
    NativePptxTableCreate,
)
from src.infrastructure.native_pptx_grid_model import new_node, rectangle_flags
from src.infrastructure.native_pptx_package import A_NS, NS
from src.infrastructure.native_pptx_table_builder import build_table
from src.infrastructure.native_pptx_table_checks import verify_table

if TYPE_CHECKING:
    from src.domain.native_pptx_grid import GridAxisEdit, NativePptxGridInsert
    from src.infrastructure.native_pptx_grid_model import Rectangle, TableGrid


def _insert_cells(
    grid: TableGrid, edit: NativePptxGridInsert
) -> tuple[list[list[etree._Element]], list[list[NativePptxTableCellCreate]]]:
    rows = len(edit.sizes) if edit.axis == "row" else len(grid.rows)
    columns = len(edit.sizes) if edit.axis == "column" else len(grid.columns)
    cells = (
        edit.cells
        if edit.cells is not None
        else [
            [NativePptxTableCellCreate() for _ in range(columns)] for _ in range(rows)
        ]
    )
    if len(cells) != rows or any(len(row) != columns for row in cells):
        raise ValueError("Inserted cells must match the new row-major grid slice")
    request = NativePptxTableCreate(
        left=0, top=0, column_widths=[1] * columns, row_heights=[1] * rows, cells=cells
    )
    shape = build_table(request)
    verify_table(shape, request)
    return [
        row.findall("a:tc", NS) for row in shape.findall(".//a:tbl/a:tr", NS)
    ], cells


def _promotion_safe(cell: etree._Element) -> None:
    if (
        any((node.text or "") for node in cell.findall(".//a:t", NS))
        or cell.findall(".//a:fld", NS)
        or cell.findall(".//a:br", NS)
        or cell.findall(".//a:hlinkClick", NS)
        or cell.findall(".//a:hlinkMouseOver", NS)
        or cell.findall(".//a:extLst", NS)
        or cell.get("id") is not None
        or any(
            isinstance(node.tag, str)
            and (
                etree.QName(node).namespace != A_NS
                or any(key.startswith("{" + NS["r"] + "}") for key in node.attrib)
            )
            for node in cell.iter()
        )
    ):
        raise ValueError(
            "Anchor promotion would discard hidden cell content or identity"
        )


def _remap_merges(
    grid: TableGrid,
    old: list[tuple[Rectangle, etree._Element]],
    mapping: list[int | None],
    axis: str,
) -> int:
    result, promoted = [], 0
    for (r, c, end_r, end_c), anchor in old:
        start, end = (r, end_r) if axis == "row" else (c, end_c)
        remaining = [
            mapping[i] for i in range(start, end + 1) if mapping[i] is not None
        ]
        if not remaining:
            continue
        low, high = remaining[0], remaining[-1]
        assert low is not None and high is not None
        rectangle = (low, c, high, end_c) if axis == "row" else (r, low, end_r, high)
        nr, nc, er, ec = rectangle
        if mapping[start] is None:
            _promotion_safe(grid.cells[nr][nc])
            grid.cells[nr][nc] = anchor
            promoted += 1
        if (nr, nc) != (er, ec):
            result.append(rectangle)
    grid.merges = result
    return promoted


def apply_grid_edit(grid: TableGrid, edit: GridAxisEdit) -> tuple[int, int]:
    nodes = grid.rows if edit.axis == "row" else grid.columns
    attribute = "h" if edit.axis == "row" else "w"
    count = edit.count if edit.op == "delete" else len(edit.sizes)
    n, index = len(nodes), edit.index
    if index > n or (edit.op != "insert" and index + count > n):
        raise ValueError("Grid edit is outside the current row/column range")
    if edit.op == "resize":
        for node, size in zip(nodes[index : index + count], edit.sizes, strict=True):
            node.set(attribute, str(size))
        return 0, 0
    if not 1 <= n + (count if edit.op == "insert" else -count) <= 100:
        raise ValueError("Grid edit must retain 1..100 rows and columns")
    old = [(rect, grid.cells[rect[0]][rect[1]]) for rect in grid.merges]
    inserted = {}
    mapping: list[int | None]
    if edit.op == "insert":
        cells, requests = _insert_cells(grid, edit)
        inserted = {
            id(cell): request
            for row, supplied in zip(cells, requests, strict=True)
            for cell, request in zip(row, supplied, strict=True)
        }
        additions = [
            new_node("tr" if edit.axis == "row" else "gridCol", attribute, size)
            for size in edit.sizes
        ]
        nodes[index:index] = additions
        if edit.axis == "row":
            grid.cells[index:index] = cells
        else:
            for row, added in zip(grid.cells, cells, strict=True):
                row[index:index] = added
        mapping = [i if i < index else i + count for i in range(n)]
    else:
        del nodes[index : index + count]
        if edit.axis == "row":
            del grid.cells[index : index + count]
        else:
            for row in grid.cells:
                del row[index : index + count]
        mapping = [
            i if i < index else (None if i < index + count else i - count)
            for i in range(n)
        ]
    promoted = _remap_merges(grid, old, mapping, edit.axis)
    flags = rectangle_flags(grid.merges)
    empty = NativePptxTableCellCreate()
    for r, row in enumerate(grid.cells):
        for c, cell in enumerate(row):
            value = flags.get((r, c), {})
            if (
                (value.get("hMerge") or value.get("vMerge"))
                and id(cell) in inserted
                and inserted[id(cell)] != empty
            ):
                raise ValueError("Inserted covered cells must be default/empty")
    return len(inserted), promoted
