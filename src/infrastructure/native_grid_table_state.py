"""Exact active worksheet/table identities and native table column metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.native_grid_tables import GridTableChange, GridTableColumn
from src.infrastructure.native_grid_xml import Rectangle, tag
from src.infrastructure.native_ooxml import DOC_REL_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS, _decode_text
from src.infrastructure.native_workbook_package import WORKSHEET_REL

if TYPE_CHECKING:
    from lxml import etree

    from src.infrastructure.native_workbook_plan import WorkbookPlan


@dataclass
class GridTableState:
    part: str
    worksheet: str
    rid: str
    registry: etree._Element
    root: etree._Element
    deleted: bool = False

    @property
    def name(self) -> str:
        return str(self.root.get("displayName", ""))

    @property
    def bounds(self) -> Rectangle:
        return Rectangle.parse(self.root.get("ref", ""))

    @property
    def headers(self) -> int:
        return int(self.root.get("headerRowCount", "1"))

    @property
    def totals(self) -> int:
        return int(self.root.get("totalsRowCount", "0"))

    @property
    def columns(self) -> tuple[GridTableColumn, ...]:
        return tuple(
            GridTableColumn(
                int(node.get("id", "0")), _decode_text(node.get("name", ""))
            )
            for node in self.root.findall("s:tableColumns/s:tableColumn", NS)
        )

    def validate(self) -> None:
        bounds = self.bounds
        if (
            self.root.tag != tag("table")
            or self.headers not in {0, 1}
            or self.totals not in {0, 1}
        ):
            raise ValueError("Unsupported native table header/totals structure")
        if bounds.last_row - bounds.first_row + 1 < self.headers + self.totals:
            raise ValueError(
                "Native table range is smaller than its header/totals rows"
            )
        if (
            len(self.root.findall("s:tableColumns", NS)) != 1
            or len(self.columns) != bounds.last_column - bounds.first_column + 1
        ):
            raise ValueError("Native table columns disagree with its range")
        GridTableChange(self.name, self.columns, self.columns)


def table_states(plan: WorkbookPlan) -> list[GridTableState]:
    states: list[GridTableState] = []
    parts, names = set(), set()
    for entry in plan.book.entries:
        if entry["kind"] != WORKSHEET_REL:
            continue
        part = entry["key"]["part"]
        root = plan.roots[part]
        relations = (
            plan.book.package.relationships(part)
            if relationships_path(part) in plan.book.package.parts
            else {}
        )
        seen_rids = set()
        for node in root.findall("s:tableParts/s:tablePart", NS):
            rid = node.get(f"{{{DOC_REL_NS}}}id", "")
            kind, target = relations.get(rid, ("", ""))
            if (
                rid in seen_rids
                or target in parts
                or kind != f"{DOC_REL_NS}/table"
                or not target
            ):
                raise ValueError(
                    "Ambiguous native table relationship or worksheet ownership"
                )
            seen_rids.add(rid)
            state = GridTableState(target, part, rid, node, plan.roots[target])
            state.validate()
            if state.name.casefold() in names:
                raise ValueError("Duplicate native table names are ambiguous")
            if any(
                previous.worksheet == part and previous.bounds.overlaps(state.bounds)
                for previous in states
            ):
                raise ValueError("Overlapping native tables are ambiguous")
            parts.add(target)
            names.add(state.name.casefold())
            states.append(state)
            if len(states) > 1024:
                raise ValueError("Native tables exceed the grid inspection budget")
        referenced = {
            rid for rid, (kind, _) in relations.items() if kind == f"{DOC_REL_NS}/table"
        }
        if seen_rids != referenced:
            raise ValueError("Unregistered native table relationships are ambiguous")
    return states
