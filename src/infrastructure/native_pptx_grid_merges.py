"""Merge/split existing cells with explicit content handling and intact paragraph XML."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_pptx_package import A_NS, NS

if TYPE_CHECKING:
    from src.domain.native_pptx_grid import NativePptxGridMerge, NativePptxGridSplit
    from src.infrastructure.native_pptx_grid_model import Rectangle, TableGrid


def _body(cell: etree._Element) -> etree._Element | None:
    bodies = cell.findall("a:txBody", NS)
    if len(bodies) > 1:
        raise ValueError("Ambiguous table cell text bodies")
    if not bodies:
        return None
    body = bodies[0]
    allowed = {f"{{{A_NS}}}{name}" for name in ("bodyPr", "lstStyle", "p")}
    if (
        (body.text or "").strip()
        or any((child.tail or "").strip() for child in body)
        or any(
            isinstance(child.tag, str) and child.tag not in allowed for child in body
        )
        or len(body.findall("a:bodyPr", NS)) != 1
        or len(body.findall("a:lstStyle", NS)) > 1
        or not body.findall("a:p", NS)
    ):
        raise ValueError("Unsupported table text-body structure for merge")
    return body


def has_content(body: etree._Element | None) -> bool:
    if body is None:
        return False
    for paragraph in body.findall("a:p", NS):
        if paragraph.attrib or any(
            isinstance(child.tag, str)
            and child.tag not in {f"{{{A_NS}}}{n}" for n in ("pPr", "r", "endParaRPr")}
            for child in paragraph
        ):
            return True
        if any(
            run.attrib
            or any(child.tag not in {f"{{{A_NS}}}rPr", f"{{{A_NS}}}t"} for child in run)
            for run in paragraph.findall("a:r", NS)
        ):
            return True
        for node in paragraph.iter():
            if not isinstance(node.tag, str):
                continue
            name = etree.QName(node)
            if (
                name.namespace != A_NS
                or (name.localname != "t" and (node.text or "").strip())
                or (node.tail or "").strip()
                or any(key.startswith("{" + NS["r"] + "}") for key in node.attrib)
                or name.localname
                in {"fld", "br", "tab", "hlinkClick", "hlinkMouseOver", "extLst"}
                or (name.localname == "t" and (node.text or ""))
            ):
                return True
    return False


def _overlaps(left: Rectangle, right: Rectangle) -> bool:
    return not (
        left[2] < right[0]
        or right[2] < left[0]
        or left[3] < right[1]
        or right[3] < left[1]
    )


def _contains(outer: Rectangle, inner: Rectangle) -> bool:
    return (
        outer[0] <= inner[0] <= inner[2] <= outer[2]
        and outer[1] <= inner[1] <= inner[3] <= outer[3]
    )


def _move_paragraphs(anchor: etree._Element, sources: list[etree._Element]) -> int:
    if not sources:
        return 0
    target = _body(anchor)
    if target is None:
        target = etree.Element(f"{{{A_NS}}}txBody")
        etree.SubElement(target, f"{{{A_NS}}}bodyPr")
        etree.SubElement(target, f"{{{A_NS}}}lstStyle")
        anchor.insert(0, target)
    count = 0
    expected = [_paragraph_xml(p) for p in target.findall("a:p", NS)]
    for body in sources:
        paragraphs = body.findall("a:p", NS)
        expected.extend(_paragraph_xml(p) for p in paragraphs)
        for paragraph in paragraphs:
            target.append(paragraph)
        etree.SubElement(body, f"{{{A_NS}}}p")
        count += len(paragraphs)
    if [_paragraph_xml(p) for p in target.findall("a:p", NS)] != expected:
        raise ValueError("Merged paragraph XML changed during migration")
    return count


def _paragraph_xml(paragraph: etree._Element) -> bytes:
    return bytes(
        etree.tostring(paragraph, method="c14n", exclusive=True, with_tail=False)
    )


def merge_cells(grid: TableGrid, edit: NativePptxGridMerge) -> int:
    rectangle = edit.row, edit.column, edit.end_row, edit.end_column
    if edit.end_row >= len(grid.rows) or edit.end_column >= len(grid.columns):
        raise ValueError("Merge rectangle is outside the current table grid")
    if any(
        _overlaps(rectangle, old) and not _contains(rectangle, old)
        for old in grid.merges
    ):
        raise ValueError("Partial merge intersection; split the existing merge first")
    sources = []
    anchor = grid.cells[edit.row][edit.column]
    _body(anchor)
    for r in range(edit.row, edit.end_row + 1):
        for c in range(edit.column, edit.end_column + 1):
            if (r, c) == (edit.row, edit.column):
                continue
            body = _body(grid.cells[r][c])
            if has_content(body):
                if edit.content_policy == "require_empty":
                    raise ValueError(
                        "Merge would hide non-anchor cell content; use append_paragraphs explicitly"
                    )
                assert body is not None
                sources.append(body)
    moved = _move_paragraphs(anchor, sources)
    grid.merges = [old for old in grid.merges if not _contains(rectangle, old)] + [
        rectangle
    ]
    return moved


def split_cells(grid: TableGrid, edit: NativePptxGridSplit) -> None:
    selected = [r for r in grid.merges if r[:2] == (edit.row, edit.column)]
    if len(selected) != 1:
        raise ValueError("Split requires an existing table merge origin")
    grid.merges.remove(selected[0])
