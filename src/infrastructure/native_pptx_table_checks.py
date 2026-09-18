"""Compare newly serialized table grids, text, formatting and merge maps to input."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_pptx_table import (
        NativePptxTableCellCreate,
        NativePptxTableCreate,
    )
from src.infrastructure.native_pptx_package import NS, shape_identity


def equal(actual: Any, expected: Any, detail: str) -> None:
    if actual != expected:
        raise ValueError(f"Table read-back differs from requested {detail}")


def _merge_attributes(
    request: NativePptxTableCreate,
) -> dict[tuple[int, int], dict[str, str]]:
    attributes = {}
    for merge in request.merges:
        height, width = (
            merge.end_row - merge.row + 1,
            merge.end_column - merge.column + 1,
        )
        for row in range(merge.row, merge.end_row + 1):
            for column in range(merge.column, merge.end_column + 1):
                value = {}
                if row == merge.row and height > 1:
                    value["rowSpan"] = str(height)
                if column == merge.column and width > 1:
                    value["gridSpan"] = str(width)
                if row > merge.row:
                    value["vMerge"] = "1"
                if column > merge.column:
                    value["hMerge"] = "1"
                attributes[row, column] = value
    return attributes


def _color(node: etree._Element, path: str) -> str | None:
    color = node.find(path + "/a:srgbClr", NS)
    return color.get("val") if color is not None else None


def _cell(node: etree._Element, request: NativePptxTableCellCreate) -> None:
    props = node.find("a:tcPr", NS)
    equal(
        props.get("anchor"),
        {"top": "t", "middle": "ctr", "bottom": "b"}[request.vertical_anchor],
        "vertical alignment",
    )
    for name in ("marL", "marR", "marT", "marB"):
        equal(props.get(name), str(request.margin), "cell margin")
    equal(
        _color(props, "a:solidFill"),
        request.fill_rgb.upper() if request.fill_rgb else None,
        "cell fill",
    )
    paragraphs = node.findall("a:txBody/a:p", NS)
    equal(len(paragraphs), len(request.paragraphs), "paragraph count")
    for paragraph, expected in zip(paragraphs, request.paragraphs, strict=True):
        equal(
            paragraph.find("a:pPr", NS).get("algn"),
            {"left": "l", "center": "ctr", "right": "r"}[request.alignment],
            "paragraph alignment",
        )
        runs = paragraph.findall("a:r", NS)
        equal(len(runs), len(expected), "run count")
        for run, source in zip(runs, expected, strict=True):
            props = run.find("a:rPr", NS)
            equal(run.findtext("a:t", "", NS), source.text, "literal cell text")
            equal(props.get("b"), str(int(source.bold)), "bold")
            equal(props.get("i"), str(int(source.italic)), "italic")
            equal(props.get("sz"), str(source.font_size_pt * 100), "font size")
            equal(
                _color(props, "a:solidFill"),
                request.text_rgb.upper() if request.text_rgb else None,
                "text color",
            )


def verify_table(
    node: etree._Element, request: NativePptxTableCreate, style_id: str | None = None
) -> None:
    props = shape_identity(node)
    equal(
        (props.get("name"), props.get("descr")),
        (request.name, request.description),
        "name/description",
    )
    transform = node.find("p:xfrm", NS)
    equal(
        dict(transform.find("a:off", NS).attrib),
        {"x": str(request.left), "y": str(request.top)},
        "position",
    )
    equal(
        dict(transform.find("a:ext", NS).attrib),
        {"cx": str(sum(request.column_widths)), "cy": str(sum(request.row_heights))},
        "extent",
    )
    table = node.find("a:graphic/a:graphicData/a:tbl", NS)
    if table is None:
        raise ValueError("Added shape is not a native table")
    equal(
        [int(col.get("w")) for col in table.findall("a:tblGrid/a:gridCol", NS)],
        request.column_widths,
        "column widths",
    )
    rows = table.findall("a:tr", NS)
    equal([int(row.get("h")) for row in rows], request.row_heights, "row heights")
    verify_cells_and_style(table, rows, request, style_id)


def verify_cells_and_style(
    table: etree._Element,
    rows: list[etree._Element],
    request: NativePptxTableCreate,
    style_id: str | None,
) -> None:
    styles = table.find("a:tblPr", NS)
    equal(
        styles.findtext("a:tableStyleId", None, NS), style_id, "destination table style"
    )
    for name, field in [
        ("firstRow", "first_row"),
        ("lastRow", "last_row"),
        ("firstCol", "first_column"),
        ("lastCol", "last_column"),
        ("bandRow", "row_banding"),
        ("bandCol", "column_banding"),
    ]:
        equal(
            styles.get(name, "0") in {"1", "true"},
            getattr(request, field),
            "table style role",
        )
    merged = _merge_attributes(request)
    for row, actual in enumerate(rows):
        cells = actual.findall("a:tc", NS)
        equal(len(cells), len(request.column_widths), "cell grid")
        for column, cell in enumerate(cells):
            expected = merged.get((row, column), {})
            equal(dict(cell.attrib), expected, "merge attributes")
            if expected.get("hMerge") or expected.get("vMerge"):
                equal(cell.findall(".//a:t", NS), [], "covered cell content")
            else:
                _cell(cell, request.cells[row][column])
