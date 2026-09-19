"""Word physical cells, omitted positions and rectangular merge regions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from lxml import etree

from src.infrastructure.native_docx_workspace import WORD_NS

W = "{" + WORD_NS + "}"
TC_ORDER = [
    "cnfStyle",
    "tcW",
    "gridSpan",
    "hMerge",
    "vMerge",
    "tcBorders",
    "shd",
    "noWrap",
    "tcMar",
    "textDirection",
    "tcFitText",
    "vAlign",
    "hideMark",
    "headers",
    "cellIns",
    "cellDel",
    "cellMerge",
    "tcPrChange",
]
TR_ORDER = [
    "cnfStyle",
    "divId",
    "gridBefore",
    "gridAfter",
    "wBefore",
    "wAfter",
    "cantSplit",
    "trHeight",
    "tblHeader",
    "tblCellSpacing",
    "jc",
    "hidden",
    "ins",
    "del",
    "trPrChange",
]
TBL_ORDER = [
    "tblStyle",
    "tblpPr",
    "tblOverlap",
    "bidiVisual",
    "tblStyleRowBandSize",
    "tblStyleColBandSize",
    "tblW",
    "jc",
    "tblCellSpacing",
    "tblInd",
    "tblBorders",
    "shd",
    "tblLayout",
    "tblCellMar",
    "tblLook",
    "tblCaption",
    "tblDescription",
    "tblPrChange",
]


def one(parent: etree._Element, name: str) -> etree._Element | None:
    nodes = parent.findall(W + name)
    if len(nodes) > 1:
        raise ValueError(f"Ambiguous Word {name} properties")
    return nodes[0] if nodes else None


def prop(parent: etree._Element, name: str) -> etree._Element:
    node = one(parent, name)
    if node is None:
        node = etree.Element(W + name)
        parent.insert(0, node)
    return node


def set_value(
    parent: etree._Element, name: str, attrs: dict[str, str], order: list[str]
) -> None:
    node = one(parent, name)
    if node is None:
        node = etree.Element(W + name)
        after = {W + item for item in order[order.index(name) + 1 :]}
        position = next(
            (i for i, child in enumerate(parent) if child.tag in after), len(parent)
        )
        parent.insert(position, node)
    for key, value in attrs.items():
        node.set(W + key, value)


def integer(
    node: etree._Element | None, attr: str, default: int, minimum: int = 0
) -> int:
    raw = node.get(W + attr) if node is not None else None
    try:
        value = int(raw) if raw is not None else default
    except ValueError as exc:
        raise ValueError("Invalid Word grid integer") from exc
    if not minimum <= value <= 31680:
        raise ValueError("Word grid integer exceeds bounds")
    return value


def omission(row: etree._Element, side: str) -> int:
    pr = one(row, "trPr")
    return integer(one(pr, side) if pr is not None else None, "val", 0)


def header(row: etree._Element) -> bool:
    pr = one(row, "trPr")
    node = one(pr, "tblHeader") if pr is not None else None
    return node is not None and node.get(W + "val", "true") not in {"0", "false", "off"}


def blocks(cell: etree._Element) -> list[etree._Element]:
    return [child for child in cell if child.tag != W + "tcPr"]


def empty(cell: etree._Element) -> bool:
    """Only ordinary empty paragraphs can be deliberately discarded by a merge."""
    for child in blocks(cell):
        if child.tag != W + "p":
            return False
        for node in child:
            if node.tag == W + "pPr":
                continue
            if node.tag != W + "r" or any(
                item.tag not in {W + "rPr", W + "t"}
                or (item.tag == W + "t" and item.text)
                for item in node
            ):
                return False
    return True


def blank_like(cell: etree._Element) -> etree._Element:
    result = etree.Element(W + "tc")
    pr = one(cell, "tcPr")
    if pr is not None:
        result.append(deepcopy(pr))
    etree.SubElement(result, W + "p")
    return result


def text_projection(cell: etree._Element) -> str:
    """Expose literal Word text tokens, retaining paragraph/tab/break boundaries."""
    paragraphs = []
    for paragraph in cell.iter(W + "p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == W + "t":
                parts.append(node.text or "")
            elif node.tag == W + "tab":
                parts.append("\t")
            elif node.tag in {W + "br", W + "cr"}:
                parts.append("\n")
        paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


@dataclass(eq=False)
class Region:
    row: int
    column: int
    row_span: int
    col_span: int
    cells: list[etree._Element]
    changed: bool = False

    @property
    def bottom(self) -> int:
        return self.row + self.row_span

    @property
    def right(self) -> int:
        return self.column + self.col_span


@dataclass
class WordGrid:
    table: etree._Element
    grid: etree._Element
    columns: list[etree._Element]
    rows: list[etree._Element]
    regions: list[Region]
    omissions: list[tuple[int, int]]

    @classmethod
    def read(cls, table: etree._Element) -> WordGrid:
        if table.tag != W + "tbl" or any(
            node.tag not in {W + "tblPr", W + "tblGrid", W + "tr"} for node in table
        ):
            raise ValueError(
                "DOCX table has unsupported direct wrappers or range markers"
            )
        grid = one(table, "tblGrid")
        one(table, "tblPr")
        if grid is None or any(node.tag != W + "gridCol" for node in grid):
            raise ValueError("DOCX table needs one explicit unambiguous grid")
        rows, columns = table.findall(W + "tr"), list(grid)
        if not 1 <= len(rows) <= 100 or not 1 <= len(columns) <= 100:
            raise ValueError("DOCX table dimensions must be within 1..100")
        regions: list[Region] = []
        omissions = []
        previous: dict[tuple[int, int], Region] = {}
        for r, row in enumerate(rows):
            one(row, "trPr")
            if any(
                child.tag not in {W + "tblPrEx", W + "trPr", W + "tc"} for child in row
            ):
                raise ValueError("DOCX row has unsupported wrappers or range markers")
            before, after = omission(row, "gridBefore"), omission(row, "gridAfter")
            omissions.append((before, after))
            position = before
            current = {}
            cells = row.findall(W + "tc")
            if not cells:
                raise ValueError("DOCX row has no physical cells")
            for cell in cells:
                pr = one(cell, "tcPr")
                span = integer(
                    one(pr, "gridSpan") if pr is not None else None, "val", 1, 1
                )
                if pr is not None and one(pr, "hMerge") is not None:
                    raise ValueError(
                        "Legacy horizontal merges require an explicit conversion"
                    )
                merge = one(pr, "vMerge") if pr is not None else None
                state = merge.get(W + "val", "continue") if merge is not None else None
                if state not in {None, "restart", "continue"}:
                    raise ValueError("Unknown vertical merge state")
                contents = blocks(cell)
                if not contents or contents[-1].tag != W + "p":
                    raise ValueError("DOCX cell must end with a paragraph")
                if position + span > len(columns):
                    raise ValueError("DOCX cell exceeds declared layout grid")
                key = position, span
                if state == "continue":
                    region = previous.get(key)
                    if region is None:
                        raise ValueError(
                            "Orphan or mismatched vertical merge continuation"
                        )
                    region.row_span += 1
                    region.cells.append(cell)
                else:
                    region = Region(r, position, 1, span, [cell])
                    regions.append(region)
                if state is not None:
                    current[key] = region
                position += span
            if position + after != len(columns):
                raise ValueError(
                    "DOCX row coverage and omissions differ from declared grid"
                )
            previous = current
        result = cls(table, grid, columns, rows, regions, omissions)
        result.validate()
        return result

    def validate(self) -> None:
        if not 1 <= len(self.rows) <= 100 or not 1 <= len(self.columns) <= 100:
            raise ValueError("DOCX grid dimensions exceed bounds")
        coverage: set[tuple[int, int]] = set()
        for region in self.regions:
            if (
                region.row < 0
                or region.column < 0
                or region.row_span < 1
                or region.col_span < 1
                or region.bottom > len(self.rows)
                or region.right > len(self.columns)
                or len(region.cells) != region.row_span
            ):
                raise ValueError("Invalid Word merge bounds")
            flags = {header(self.rows[r]) for r in range(region.row, region.bottom)}
            if len(flags) > 1:
                raise ValueError("DOCX merge crosses repeated-header/body boundary")
            for row in range(region.row, region.bottom):
                before, after = self.omissions[row]
                for column in range(region.column, region.right):
                    if (row, column) in coverage or not before <= column < len(
                        self.columns
                    ) - after:
                        raise ValueError("Overlapping Word merge or omitted position")
                    coverage.add((row, column))
        expected = {
            (r, c)
            for r, (before, after) in enumerate(self.omissions)
            for c in range(before, len(self.columns) - after)
        }
        if coverage != expected or any(
            before + after >= len(self.columns) for before, after in self.omissions
        ):
            raise ValueError("Word grid contains an uncovered cell or empty row")

    def at(self, row: int, column: int) -> Region:
        for region in self.regions:
            if (
                region.row <= row < region.bottom
                and region.column <= column < region.right
            ):
                return region
        raise ValueError("Position is outside the table or omitted from this row")

    def widths(self) -> list[int]:
        values = [integer(node, "w", -1, 1) for node in self.columns]
        if sum(values) > 31680:
            raise ValueError("DOCX table width exceeds 31,680 twips")
        return values

    def write(self, *, fixed_widths: bool = False) -> None:
        self.validate()
        widths = self.widths() if fixed_widths else []
        if fixed_widths:
            pr = prop(self.table, "tblPr")
            set_value(pr, "tblW", {"w": str(sum(widths)), "type": "dxa"}, TBL_ORDER)
            set_value(pr, "tblLayout", {"type": "fixed"}, TBL_ORDER)
        for child in list(self.grid):
            self.grid.remove(child)
        self.grid.extend(self.columns)
        for row in self.table.findall(W + "tr"):
            self.table.remove(row)
        self.table.extend(self.rows)
        for r, row in enumerate(self.rows):
            for cell in row.findall(W + "tc"):
                row.remove(cell)
            for name, value in zip(
                ("gridBefore", "gridAfter"), self.omissions[r], strict=True
            ):
                if value != omission(row, name):
                    set_value(prop(row, "trPr"), name, {"val": str(value)}, TR_ORDER)
            if fixed_widths:
                before, after = self.omissions[r]
                for name, count, width in (
                    ("wBefore", before, sum(widths[:before])),
                    ("wAfter", after, sum(widths[len(widths) - after :])),
                ):
                    row_pr = one(row, "trPr")
                    if count or (row_pr is not None and one(row_pr, name) is not None):
                        set_value(
                            prop(row, "trPr"),
                            name,
                            {"w": str(width), "type": "dxa"},
                            TR_ORDER,
                        )
            for region in sorted(
                (x for x in self.regions if x.row <= r < x.bottom),
                key=lambda x: x.column,
            ):
                cell = region.cells[r - region.row]
                if region.changed:
                    pr = prop(cell, "tcPr")
                    for name, geometry_value in (
                        (
                            "gridSpan",
                            str(region.col_span) if region.col_span > 1 else None,
                        ),
                        (
                            "vMerge",
                            ("restart" if r == region.row else "continue")
                            if region.row_span > 1
                            else None,
                        ),
                    ):
                        node = one(pr, name)
                        if geometry_value is None:
                            if node is not None:
                                pr.remove(node)
                        else:
                            set_value(pr, name, {"val": geometry_value}, TC_ORDER)
                if fixed_widths:
                    set_value(
                        prop(cell, "tcPr"),
                        "tcW",
                        {
                            "w": str(sum(widths[region.column : region.right])),
                            "type": "dxa",
                        },
                        TC_ORDER,
                    )
                row.append(cell)

    def record(self) -> dict[str, Any]:
        return {
            "schema": "native-docx-table-grid-v1",
            "rows": len(self.rows),
            "columns": len(self.columns),
            "column_widths_twips": [
                integer(node, "w", 0) if node.get(W + "w") is not None else None
                for node in self.columns
            ],
            "row_heights": [
                [
                    {
                        "value_twips": integer(node, "val", 0),
                        "rule": node.get(W + "hRule", "auto"),
                    }
                    for node in row.findall(W + "trPr/" + W + "trHeight")
                ]
                for row in self.rows
            ],
            "text_projection": "Literal w:t, tab and break tokens with paragraph boundaries; no field evaluation or visibility verdict. Inspect native_xml and actual rendering.",
            "row_omissions": [{"before": a, "after": b} for a, b in self.omissions],
            "repeat_header_rows": [r for r, row in enumerate(self.rows) if header(row)],
            "regions": [
                {
                    "row": x.row,
                    "column": x.column,
                    "row_span": x.row_span,
                    "col_span": x.col_span,
                    "physical_cells": [
                        {"row": x.row + i, "text": text_projection(cell)}
                        for i, cell in enumerate(x.cells)
                    ],
                }
                for x in self.regions
            ],
            "native_xml": etree.tostring(
                self.table, encoding="unicode", with_tail=False
            ),
        }
