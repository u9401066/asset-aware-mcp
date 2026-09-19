"""Native sheet CRUD through explicit OOXML patches, without workbook resaving."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_workbook import (
    NativeWorksheetInsert,
    NativeWorksheetKey,
    NativeWorksheetRename,
)
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    SHEET_NS,
    TYPE_NS,
    relationships_path,
)
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_package import (
    WORKSHEET_REL,
    WORKSHEET_TYPE,
    NativeWorkbookPackage,
)
from src.infrastructure.native_workbook_plan import WorkbookPlan
from src.infrastructure.native_workbook_references import NativeWorkbookReferences
from src.infrastructure.native_workbook_tables import table_inventory

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult


class NativeWorkbookStructure:
    def read(self, data: bytes, *, references: bool = False) -> dict[str, Any]:
        book = NativeWorkbookPackage(data)
        result: dict[str, Any] = {
            "representation": "native-workbook-structure-v1",
            "workbook_part": book.workbook_path,
            "worksheets": book.entries,
            "defined_names": [
                {"attributes": dict(n.attrib), "formula": n.text or ""}
                for n in book.workbook.findall("s:definedNames/s:definedName", NS)
            ],
            "views": [
                dict(n.attrib)
                for n in book.workbook.findall("s:bookViews/s:workbookView", NS)
            ],
            "custom_views": [
                dict(n.attrib)
                for n in book.workbook.findall(
                    "s:customWorkbookViews/s:customWorkbookView", NS
                )
            ],
            "cell_read_operation": "read_cell",
            "tables": table_inventory(book),
        }
        if references:
            result["references"] = [
                field.record()
                for field in NativeWorkbookReferences(book, book.active_parts()).fields
            ]
            result["reference_scope"] = (
                "Explicit formula/name/chart/validation/conditional-format/hyperlink/pivot fields; dynamic strings and external workbooks require Agent review."
            )
        return result

    def add(
        self, data: bytes, request: NativeWorksheetInsert, allow_3d: bool = False
    ) -> tuple[bytes, NativeEditResult]:
        plan = WorkbookPlan(data)
        book = plan.book
        if (
            request.index > len(book.entries)
            or len(book.entries) + len(request.names) > 256
        ):
            raise ValueError(
                "Worksheet insertion index or count exceeds workbook bounds"
            )
        if {item["name"].casefold() for item in book.entries} & {
            name.casefold() for name in request.names
        }:
            raise ValueError("Worksheet name already exists ignoring case")
        next_id = max(int(item["key"]["sheet_id"]) for item in book.entries) + 1
        rels, types = plan.roots[plan.rel_path], plan.roots["[Content_Types].xml"]
        base = posixpath.dirname(book.workbook_path)
        existing_rids = {node.get("Id") for node in rels}
        inserted = []
        for offset, name in enumerate(request.names):
            number = 1
            while (
                part := posixpath.join(base, "worksheets", f"sheet{number}.xml")
            ) in book.package.parts or part in plan.roots:
                number += 1
            key = NativeWorksheetKey(sheet_id=str(next_id + offset), part=part)
            number = 1
            while (rid := f"rId{number}") in existing_rids:
                number += 1
            existing_rids.add(rid)
            node = etree.Element(
                f"{{{SHEET_NS}}}sheet", name=name, sheetId=key.sheet_id
            )
            node.set(f"{{{DOC_REL_NS}}}id", rid)
            book.nodes[key.sheet_id] = node
            root = etree.Element(f"{{{SHEET_NS}}}worksheet", nsmap={None: SHEET_NS})
            etree.SubElement(root, f"{{{SHEET_NS}}}sheetData")
            plan.roots[part] = root
            etree.SubElement(
                rels,
                f"{{{REL_NS}}}Relationship",
                Id=rid,
                Type=WORKSHEET_REL,
                Target=posixpath.relpath(part, base or "."),
            )
            etree.SubElement(
                types,
                f"{{{TYPE_NS}}}Override",
                PartName="/" + part,
                ContentType=WORKSHEET_TYPE,
            )
            inserted.append(
                {
                    "key": key.model_dump(),
                    "name": name,
                    "state": "visible",
                    "kind": WORKSHEET_REL,
                }
            )
        plan.after[request.index : request.index] = inserted
        membership = plan.refs.check_membership(book.entries, plan.after, allow_3d)
        return plan.finish(
            {
                "operation": "add_worksheets",
                "inserted": inserted,
                "index": request.index,
                "changed_3d_memberships": membership,
            }
        )

    def rename(
        self, data: bytes, request: NativeWorksheetRename
    ) -> tuple[bytes, NativeEditResult]:
        plan = WorkbookPlan(data)
        target = plan.book.match(request.key)
        if any(
            item["name"].casefold() == request.name.casefold()
            and item["key"] != target["key"]
            for item in plan.after
        ):
            raise ValueError("Worksheet name already exists ignoring case")
        changes = plan.refs.rename(target["name"], request.name)
        plan.book.nodes[request.key.sheet_id].set("name", request.name)
        plan.after[target["index"]]["name"] = request.name
        return plan.finish(
            {
                "operation": "rename_worksheet",
                "key": request.key.model_dump(),
                "old_name": target["name"],
                "new_name": request.name,
                "rewritten_references": changes,
            }
        )

    def reorder(
        self, data: bytes, keys: list[NativeWorksheetKey], allow_3d: bool = False
    ) -> tuple[bytes, NativeEditResult]:
        plan = WorkbookPlan(data)
        if len(keys) != len(plan.after) or len({key.sheet_id for key in keys}) != len(
            keys
        ):
            raise ValueError(
                "Worksheet order must contain all current keys exactly once"
            )
        plan.after = [plan.book.match(key) for key in keys]
        membership = plan.refs.check_membership(plan.book.entries, plan.after, allow_3d)
        return plan.finish(
            {
                "operation": "reorder_worksheets",
                "order": [key.model_dump() for key in keys],
                "changed_3d_memberships": membership,
            }
        )

    def delete(
        self, data: bytes, keys: list[NativeWorksheetKey]
    ) -> tuple[bytes, NativeEditResult]:
        if not 1 <= len(keys) <= 32 or len({key.sheet_id for key in keys}) != len(keys):
            raise ValueError("Delete requires 1..32 distinct worksheet keys")
        removed = {key.sheet_id for key in keys}
        plan = WorkbookPlan(data, removed)
        entries = [plan.book.match(key) for key in keys]
        tables: set[str] = set()
        for entry in entries:
            part = entry["key"]["part"]
            if relationships_path(part) in plan.book.package.parts:
                for kind, target in plan.book.package.relationships(part).values():
                    if kind == f"{DOC_REL_NS}/table" and target:
                        table = plan.book.package.xml(target)
                        tables.update(
                            table.get(key, "").casefold()
                            for key in ("name", "displayName")
                            if table.get(key)
                        )
        plan.refs.check_delete(plan.book.entries, removed, tables)
        rids = {item["relationship_id"] for item in entries}
        rels = plan.roots[plan.rel_path]
        for node in list(rels):
            if node.get("Id") in rids:
                rels.remove(node)
        return plan.finish(
            {
                "operation": "delete_worksheets",
                "keys": [key.model_dump() for key in keys],
                "detached_parts_retained": True,
                "secure_erasure": False,
            }
        )
