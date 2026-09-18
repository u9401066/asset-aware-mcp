"""Lossless shape XML with explicit local structure for agent interpretation."""

from __future__ import annotations

import hashlib
from typing import Any

from lxml import etree

from src.infrastructure.native_pptx_package import A_NS, NS, shape_identity


def _xml(node: etree._Element | None) -> str | None:
    return (
        etree.tostring(node, encoding="unicode", with_tail=False)
        if node is not None
        else None
    )


def paragraphs(body: etree._Element) -> list[dict[str, Any]]:
    result = []
    for index, paragraph in enumerate(body.findall("a:p", NS)):
        children = []
        run_index = 0
        for child in paragraph:
            kind = (
                etree.QName(child).localname
                if isinstance(child.tag, str)
                else "comment"
            )
            if kind not in {"r", "fld", "br"} or not child.tag.startswith(
                f"{{{A_NS}}}"
            ):
                continue
            text = child.findtext("a:t", "", NS) if kind != "br" else "\n"
            item: dict[str, Any] = {"kind": kind, "text": text, "xml": _xml(child)}
            if kind == "r":
                item["run"] = run_index
                item["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                run_index += 1
            children.append(item)
        result.append(
            {
                "paragraph": index,
                "properties_xml": _xml(paragraph.find("a:pPr", NS)),
                "items": children,
            }
        )
    return result


def _table(table: etree._Element) -> dict[str, Any]:
    rows = []
    for row_index, row in enumerate(table.findall("a:tr", NS)):
        cells = []
        for column, cell in enumerate(row.findall("a:tc", NS)):
            body = cell.find("a:txBody", NS)
            cells.append(
                {
                    "row": row_index,
                    "column": column,
                    "attributes": dict(cell.attrib),
                    "properties_xml": _xml(cell.find("a:tcPr", NS)),
                    "paragraphs": paragraphs(body) if body is not None else [],
                }
            )
        rows.append({"row": row_index, "attributes": dict(row.attrib), "cells": cells})
    return {
        "rows": rows,
        "grid_xml": _xml(table.find("a:tblGrid", NS)),
        "properties_xml": _xml(table.find("a:tblPr", NS)),
    }


def shape_record(
    locator: dict[str, str], shape: etree._Element, parents: list[str]
) -> dict[str, Any]:
    identity = shape_identity(shape)
    body = shape.find("p:txBody", NS)
    table = shape.find("a:graphic/a:graphicData/a:tbl", NS)
    transforms = shape.xpath(
        "./p:spPr/a:xfrm | ./p:grpSpPr/a:xfrm | ./p:xfrm", namespaces=NS
    )
    result: dict[str, Any] = {
        "locator": locator,
        "kind": etree.QName(shape).localname,
        "name": identity.get("name", ""),
        "description": identity.get("descr", ""),
        "group_path": parents,
        "transform_xml": [_xml(transform) for transform in transforms],
        "coordinate_scope": "local_EMU; inherited transforms and visual bounds not computed",
        "xml": _xml(shape),
        "paragraphs": paragraphs(body) if body is not None else [],
    }
    if table is not None:
        result["table"] = _table(table)
    return result


def text_body(
    shape: etree._Element, row: int | None, column: int | None
) -> etree._Element:
    if row is None:
        body = shape.find("p:txBody", NS)
    else:
        table = shape.find("a:graphic/a:graphicData/a:tbl", NS)
        if table is None or column is None:
            raise ValueError("Presentation target is not a table cell")
        rows = table.findall("a:tr", NS)
        if row >= len(rows):
            raise ValueError("Presentation table row is outside the existing structure")
        cells = rows[row].findall("a:tc", NS)
        if column >= len(cells):
            raise ValueError(
                "Presentation table column is outside the existing structure"
            )
        cell = cells[column]
        if cell.get("hMerge") in {"true", "1"} or cell.get("vMerge") in {"true", "1"}:
            raise ValueError("Edit the anchor of a merged presentation table cell")
        body = cell.find("a:txBody", NS)
    if body is None:
        raise ValueError("Presentation target has no directly editable text body")
    return body
