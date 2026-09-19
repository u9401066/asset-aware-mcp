"""Word grid transformations retaining surviving native XML nodes."""

from __future__ import annotations

from copy import deepcopy

from lxml import etree

from src.domain.native_docx_grid import (
    DocxGridDelete,
    DocxGridEdit,
    DocxGridInsert,
    DocxGridMerge,
    DocxGridResize,
    DocxGridSplit,
)
from src.domain.native_docx_structure import NativeDocxCell, NativeDocxTable
from src.infrastructure.native_docx_builder import build_blocks
from src.infrastructure.native_docx_grid_model import (
    TR_ORDER,
    Region,
    W,
    WordGrid,
    blank_like,
    blocks,
    empty,
    one,
    prop,
    set_value,
)
from src.infrastructure.native_docx_structure_checks import check_blocks


def _new_cells(
    edit: DocxGridInsert, rows: int, columns: int
) -> list[list[etree._Element]]:
    typed = edit.cells or [
        [NativeDocxCell() for _ in range(columns)] for _ in range(rows)
    ]
    if len(typed) != rows or any(len(row) != columns for row in typed):
        raise ValueError("Inserted DOCX cells must match the inserted rectangle")
    request = NativeDocxTable(column_widths_twips=[1] * columns, cells=typed)
    table = build_blocks([request])[0]
    check_blocks([table], [request])
    result = [row.findall(W + "tc") for row in table.findall(W + "tr")]
    for row in result:
        for cell in row:
            pr = one(cell, "tcPr")
            assert pr is not None
            width = one(pr, "tcW")
            if width is not None:
                pr.remove(width)
    return result


def _check_covered(edit: DocxGridInsert, row: int, column: int) -> None:
    if edit.cells and edit.cells[row][column] != NativeDocxCell():
        raise ValueError(
            "Inserted omitted/merged coverage must have default empty cells"
        )


def insert(grid: WordGrid, edit: DocxGridInsert) -> int:
    count, index = len(edit.sizes_twips), edit.index
    rows, columns = len(grid.rows), len(grid.columns)
    length = rows if edit.axis == "row" else columns
    if not index <= length or length + count > 100:
        raise ValueError("DOCX insertion exceeds grid bounds")
    new = _new_cells(
        edit,
        count if edit.axis == "row" else rows,
        columns if edit.axis == "row" else count,
    )
    if edit.axis == "row":
        for region in grid.regions:
            if region.row >= index:
                region.row += count
            elif region.bottom > index:
                offset = index - region.row
                for i in range(count):
                    for column in range(region.column, region.right):
                        _check_covered(edit, i, column)
                region.cells[offset:offset] = [
                    blank_like(region.cells[0]) for _ in range(count)
                ]
                region.row_span += count
                region.changed = True
        inserted_rows = []
        for i, height in enumerate(edit.sizes_twips):
            row = etree.Element(W + "tr")
            set_value(
                prop(row, "trPr"),
                "trHeight",
                {"val": str(height), "hRule": "atLeast"},
                TR_ORDER,
            )
            inserted_rows.append(row)
            for column in range(columns):
                if not any(
                    x.row <= index + i < x.bottom and x.column <= column < x.right
                    for x in grid.regions
                ):
                    grid.regions.append(
                        Region(index + i, column, 1, 1, [new[i][column]])
                    )
        grid.rows[index:index] = inserted_rows
        grid.omissions[index:index] = [(0, 0)] * count
    else:
        for region in grid.regions:
            if region.column >= index:
                region.column += count
            elif region.right > index:
                for row in range(region.row, region.bottom):
                    for i in range(count):
                        _check_covered(edit, row, i)
                region.col_span += count
                region.changed = True
        for row, (before, after) in enumerate(grid.omissions):
            if index < before:
                grid.omissions[row] = before + count, after
                omitted = True
            elif index > columns - after:
                grid.omissions[row] = before, after + count
                omitted = True
            else:
                omitted = False
            for i in range(count):
                if omitted:
                    _check_covered(edit, row, i)
                elif not any(
                    x.row <= row < x.bottom and x.column <= index + i < x.right
                    for x in grid.regions
                ):
                    grid.regions.append(Region(row, index + i, 1, 1, [new[row][i]]))
        grid.columns[index:index] = [
            etree.Element(W + "gridCol", {W + "w": str(width)})
            for width in edit.sizes_twips
        ]
    return len(new) * len(new[0])


def delete(grid: WordGrid, edit: DocxGridDelete) -> int:
    index, end = edit.index, edit.index + edit.count
    length = len(grid.rows) if edit.axis == "row" else len(grid.columns)
    if end > length or edit.count >= length:
        raise ValueError("DOCX deletion exceeds grid or removes its last axis")
    promoted = 0
    survivors = []
    for region in grid.regions:
        start = region.row if edit.axis == "row" else region.column
        stop = region.bottom if edit.axis == "row" else region.right
        removed = max(0, min(stop, end) - max(start, index))
        if removed == stop - start:
            continue
        new_start = start - min(edit.count, max(0, start - index))
        if edit.axis == "row":
            retained = [
                cell
                for i, cell in enumerate(region.cells, start)
                if not index <= i < end
            ]
            if index <= start < end:
                # Promote content with its paragraph/run/nested-table XML; keep
                # the surviving continuation's native cell formatting.
                target = retained[0]
                if not empty(target):
                    raise ValueError(
                        "Cannot promote merge anchor over hidden continuation content"
                    )
                for child in blocks(target):
                    target.remove(child)
                target.extend(deepcopy(child) for child in blocks(region.cells[0]))
                promoted += 1
            region.cells = retained
            region.row, region.row_span = new_start, region.row_span - removed
        else:
            region.column, region.col_span = new_start, region.col_span - removed
        if removed:
            region.changed = True
        survivors.append(region)
    grid.regions = survivors
    if edit.axis == "row":
        del grid.rows[index:end]
        del grid.omissions[index:end]
    else:
        columns = len(grid.columns)
        grid.omissions = [
            (
                before - max(0, min(before, end) - index),
                after - max(0, end - max(index, columns - after)),
            )
            for before, after in grid.omissions
        ]
        del grid.columns[index:end]
    return promoted


def resize(grid: WordGrid, edit: DocxGridResize) -> None:
    items = grid.rows if edit.axis == "row" else grid.columns
    if edit.index + len(edit.sizes_twips) > len(items):
        raise ValueError("DOCX resize exceeds grid")
    for item, size in zip(items[edit.index :], edit.sizes_twips, strict=False):
        if edit.axis == "row":
            set_value(
                prop(item, "trPr"),
                "trHeight",
                {"val": str(size), "hRule": "atLeast"},
                TR_ORDER,
            )
        else:
            item.set(W + "w", str(size))


def merge(grid: WordGrid, edit: DocxGridMerge) -> int:
    selected = {
        grid.at(row, column)
        for row in range(edit.row, edit.end_row + 1)
        for column in range(edit.column, edit.end_column + 1)
    }
    for region in selected:
        if not (
            edit.row <= region.row
            and edit.column <= region.column
            and region.bottom <= edit.end_row + 1
            and region.right <= edit.end_column + 1
        ):
            raise ValueError(
                "DOCX merge must include every intersected merge completely"
            )
    if len(selected) == 1:
        return 0
    anchor = grid.at(edit.row, edit.column).cells[0]
    physical = sorted(
        (region.row + i, region.column, cell)
        for region in selected
        for i, cell in enumerate(region.cells)
    )
    moved = 0
    for _, _, cell in physical:
        if cell is anchor or empty(cell):
            continue
        if edit.content_policy == "require_empty":
            raise ValueError("DOCX merge would discard nonempty cell content")
        values = blocks(cell)
        moved += len(values)
        anchor.extend(values)
    if anchor[-1].tag != W + "p":
        etree.SubElement(anchor, W + "p")
    cells = [anchor]
    for row in range(edit.row + 1, edit.end_row + 1):
        cells.append(
            blank_like(
                grid.at(row, edit.column).cells[row - grid.at(row, edit.column).row]
            )
        )
    grid.regions = [region for region in grid.regions if region not in selected]
    grid.regions.append(
        Region(
            edit.row,
            edit.column,
            edit.end_row - edit.row + 1,
            edit.end_column - edit.column + 1,
            cells,
            True,
        )
    )
    return moved


def split(grid: WordGrid, edit: DocxGridSplit) -> None:
    region = grid.at(edit.row, edit.column)
    if (region.row, region.column) != (edit.row, edit.column):
        raise ValueError("DOCX split requires the merge anchor")
    if region.row_span == region.col_span == 1:
        return
    if any(not empty(cell) for cell in region.cells[1:]):
        raise ValueError(
            "DOCX split cannot guess the role of hidden continuation content"
        )
    grid.regions.remove(region)
    for row in range(region.row, region.bottom):
        for column in range(region.column, region.right):
            cell = (
                region.cells[row - region.row]
                if column == region.column
                else blank_like(region.cells[row - region.row])
            )
            grid.regions.append(Region(row, column, 1, 1, [cell], True))


def apply(grid: WordGrid, edit: DocxGridEdit) -> dict[str, int | str]:
    receipt: dict[str, int | str] = {"op": edit.op}
    if isinstance(edit, DocxGridInsert):
        receipt["inserted_cells"] = insert(grid, edit)
    elif isinstance(edit, DocxGridDelete):
        receipt["promoted_merge_anchors"] = delete(grid, edit)
    elif isinstance(edit, DocxGridResize):
        resize(grid, edit)
    elif isinstance(edit, DocxGridMerge):
        receipt["moved_blocks"] = merge(grid, edit)
    else:
        split(grid, edit)
    grid.write(fixed_widths=getattr(edit, "axis", None) == "column")
    return receipt
