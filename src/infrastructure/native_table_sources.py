"""Keep pivot/consolidation source identities explicit during Table column edits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.native_grid_source_ranges import GridSourceResolver
from src.infrastructure.native_grid_structured import rewrite_structured_formula
from src.infrastructure.native_grid_xml import address, tag
from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_spreadsheet_reader import NS, _decode_text, _encode_text

if TYPE_CHECKING:
    from src.domain.native_grid_tables import GridTableChange
    from src.infrastructure.native_grid_table_state import GridTableState
    from src.infrastructure.native_grid_xml import Rectangle
    from src.infrastructure.native_table_cells import TableCellWriter
    from src.infrastructure.native_workbook_plan import WorkbookPlan


def update_sources(
    plan: WorkbookPlan,
    states: list[GridTableState],
    state: GridTableState,
    writer: TableCellWriter,
    changes: list[GridTableChange],
    *,
    affected_bounds: Rectangle | None = None,
) -> list[str]:
    resolver = GridSourceResolver(plan, states)
    affected = set()
    count = 0
    for part, root in plan.roots.items():
        for source in root.xpath(".//s:worksheetSource | .//s:dataRef", namespaces=NS):
            count += 1
            if count > 4096:
                raise ValueError("Table source inspection budget exceeded")
            owner = source.get("sheet")
            rid = source.get(f"{{{DOC_REL_NS}}}id")
            if rid:
                relation = plan.book.package.relationships(part).get(rid)
                if relation is None:
                    raise ValueError("Table source relationship is missing")
                if not relation[1]:
                    continue
                matched = [
                    s["name"]
                    for s in plan.book.entries
                    if s["key"]["part"] == relation[1]
                ]
                if len(matched) != 1 or (
                    owner is not None and owner.casefold() != matched[0].casefold()
                ):
                    raise ValueError("Table source has ambiguous worksheet identity")
                owner = matched[0]
            name = source.get("name")
            if name is not None:
                updated, replaced = rewrite_structured_formula(
                    _decode_text(name), changes
                )
                if replaced:
                    source.set("name", _encode_text(updated))
                expression = updated
            else:
                expression = source.get("ref", "")
            resolved = resolver.resolve(expression, owner)
            if resolved is None or resolved.sheet.casefold() != writer.sheet.casefold():
                continue
            if not resolved.bounds.overlaps(affected_bounds or state.bounds):
                continue
            if source.tag == tag("worksheetSource"):
                header = resolved.bounds.first_row
                for col in range(
                    resolved.bounds.first_column, resolved.bounds.last_column + 1
                ):
                    change = writer.changed.get(address(header, col))
                    if change and any(
                        change["before"].get(key) != change["after"].get(key)
                        for key in ("kind", "value")
                    ):
                        raise ValueError(
                            "Pivot source header changes require coordinated cache field identities"
                        )
            if root.tag == tag("pivotCacheDefinition"):
                root.set("invalid", "1")
                root.set("refreshOnLoad", "1")
                affected.add(part)
    return sorted(affected)
