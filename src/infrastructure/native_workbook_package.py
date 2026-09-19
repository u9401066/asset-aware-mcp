"""Worksheet identity and active package graphs for structure-preserving edits."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_workbook import NativeWorksheetKey
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    SHEET_NS,
    TYPE_NS,
    relationships_path,
)
from src.infrastructure.native_spreadsheet_reader import NS, NativeSpreadsheetReader

if TYPE_CHECKING:
    from collections.abc import Iterator

WORKSHEET_REL = f"{DOC_REL_NS}/worksheet"
CHARTSHEET_REL = f"{DOC_REL_NS}/chartsheet"
WORKSHEET_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
)


class NativeWorkbookPackage(NativeSpreadsheetReader):
    def __init__(self, data: bytes):
        super().__init__(data)
        lists = self.workbook.findall("s:sheets", NS)
        if len(lists) != 1 or any(
            isinstance(n.tag, str) and n.tag != f"{{{SHEET_NS}}}sheet" for n in lists[0]
        ):
            raise ValueError("Ambiguous workbook sheet registry")
        self.sheet_list = lists[0]
        self.nodes: dict[str, etree._Element] = {}
        self.entries: list[dict[str, Any]] = []
        paths, names = set(), set()
        for index, node in enumerate(self.sheet_list.findall("s:sheet", NS)):
            name = node.get("name", "")
            info = self.sheets[name]
            try:
                key = NativeWorksheetKey(
                    sheet_id=str(int(info["sheet_id"])), part=info["part"]
                )
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid workbook sheetId") from exc
            if (
                key.sheet_id in self.nodes
                or key.part in paths
                or name.casefold() in names
            ):
                raise ValueError("Duplicate workbook sheet identity, part or name")
            state = node.get("state", "visible")
            if state not in {"visible", "hidden", "veryHidden"}:
                raise ValueError("Invalid worksheet visibility state")
            if key.part not in self.package.parts:
                raise ValueError("Missing native worksheet part")
            self.nodes[key.sheet_id] = node
            paths.add(key.part)
            names.add(name.casefold())
            self.entries.append(
                {
                    "index": index,
                    "key": key.model_dump(),
                    "name": name,
                    "kind": info["kind"],
                    "state": state,
                    "relationship_id": node.get(f"{{{DOC_REL_NS}}}id"),
                    "attributes": dict(node.attrib),
                }
            )

    def match(self, key: NativeWorksheetKey) -> dict[str, Any]:
        matches = [item for item in self.entries if item["key"] == key.model_dump()]
        if len(matches) != 1:
            raise ValueError(
                "Worksheet key does not match this exact workbook revision"
            )
        return matches[0]

    def active_parts(self, excluded_sheet_ids: set[str] | None = None) -> set[str]:
        excluded_sheet_ids = excluded_sheet_ids or set()
        skip = {
            item["relationship_id"]
            for item in self.entries
            if item["key"]["sheet_id"] in excluded_sheet_ids
        }
        active, pending = set(), [""]
        while pending:
            owner = pending.pop()
            if owner in active:
                continue
            active.add(owner)
            if relationships_path(owner) not in self.package.parts:
                continue
            for rid, (_kind, target) in self.package.relationships(owner).items():
                if owner == self.workbook_path and rid in skip:
                    continue
                if target:
                    if target not in self.package.parts:
                        raise ValueError("Dangling workbook package relationship")
                    pending.append(target)
        return active - {""}

    def xml_parts(self, active: set[str]) -> Iterator[tuple[str, etree._Element]]:
        types = self.package.xml("[Content_Types].xml")
        xml = {
            item.get("PartName", "").lstrip("/")
            for item in types
            if item.tag == f"{{{TYPE_NS}}}Override"
            and item.get("ContentType", "").endswith("xml")
        }
        xml.update(item["key"]["part"] for item in self.entries)
        for path in sorted(active):
            if path in xml or path.endswith((".xml", ".vml")):
                yield (
                    path,
                    self.workbook
                    if path == self.workbook_path
                    else self.package.xml(path),
                )

    def check_editable(self) -> None:
        if self.workbook.find("s:workbookProtection", NS) is not None:
            raise ValueError(
                "Protected workbook structure requires an explicit unlock workflow"
            )
        if len(self.entries) > 256:
            raise ValueError("Workbook sheet structure exceeds the 256-sheet budget")
        if any(
            item["kind"] not in {WORKSHEET_REL, CHARTSHEET_REL} for item in self.entries
        ):
            raise ValueError(
                "Macro/dialog/unknown sheets require a dedicated structural workflow"
            )
        if (
            self.workbook.find("s:extLst", NS) is not None
            or self.workbook.find("s:fileSharing", NS) is not None
        ):
            raise ValueError(
                "Workbook extension/shared-revision structures require a dedicated workflow"
            )
        if any(
            isinstance(node.tag, str) and etree.QName(node).namespace != SHEET_NS
            for node in self.workbook
        ):
            raise ValueError("Foreign workbook structure requires a dedicated workflow")
        types = self.package.xml("[Content_Types].xml")
        blocked = (
            "digital-signature",
            "vbaproject",
            "revisionlog",
            "revisionheader",
            "activex",
        )
        if any(
            any(value in item.get("ContentType", "").lower() for value in blocked)
            for item in types
        ):
            raise ValueError(
                "Signed, macro, ActiveX or revision workbooks require a dedicated structural workflow"
            )
        for path in self.package.parts:
            if path.endswith(".rels"):
                for item in self.package.xml(path):
                    if any(value in item.get("Type", "").lower() for value in blocked):
                        raise ValueError(
                            "Signed, macro, ActiveX or revision relationships block sheet structure changes"
                        )
        self.active_parts()  # Validate the active graph before planning a mutation.
