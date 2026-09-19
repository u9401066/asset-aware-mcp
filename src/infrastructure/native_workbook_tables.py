"""Read native table identities and complete definitions without enabling edits."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_ooxml import DOC_REL_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_package import WORKSHEET_REL

if TYPE_CHECKING:
    from src.infrastructure.native_workbook_package import NativeWorkbookPackage


def table_inventory(book: NativeWorkbookPackage) -> list[dict[str, Any]]:
    result = []
    for sheet in book.entries:
        if sheet["kind"] != WORKSHEET_REL:
            continue
        part = sheet["key"]["part"]
        root = book.package.xml(part)
        relations = (
            book.package.relationships(part)
            if relationships_path(part) in book.package.parts
            else {}
        )
        for node in root.findall("s:tableParts/s:tablePart", NS):
            rid = node.get(f"{{{DOC_REL_NS}}}id", "")
            kind, target = relations.get(rid, ("", ""))
            if kind != f"{DOC_REL_NS}/table" or not target:
                raise ValueError("Native Table inventory has an invalid relationship")
            table = book.package.xml(target)
            raw = book.package.parts[target]
            result.append(
                {
                    "worksheet": sheet["key"],
                    "relationship_id": rid,
                    "part": target,
                    "attributes": dict(table.attrib),
                    "columns": [
                        dict(col.attrib)
                        for col in table.findall("s:tableColumns/s:tableColumn", NS)
                    ],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "xml": etree.tostring(table, encoding="unicode"),
                    "xml_scope": "Complete parsed table XML; sha256 pins the original package part bytes.",
                }
            )
            if len(result) > 1024:
                raise ValueError("Native Table inventory exceeds the inspection budget")
    return result
