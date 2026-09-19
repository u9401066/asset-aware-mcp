"""Validate indirect pivot/consolidation source identities across one grid edit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.native_grid_source_ranges import GridSourceResolver
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_spreadsheet_reader import NS, _decode_text

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform
    from src.infrastructure.native_grid_source_ranges import GridSourceRange
    from src.infrastructure.native_grid_table_state import GridTableState
    from src.infrastructure.native_workbook_plan import WorkbookPlan


class GridNamedSources:
    def __init__(self, plan: WorkbookPlan, states: list[GridTableState]):
        self.plan, self.states = plan, states
        resolver = GridSourceResolver(plan, states)
        self.sources: list[
            tuple[str, etree._Element, str | None, GridSourceRange | None]
        ] = []
        for part, root in plan.roots.items():
            for source in root.xpath(
                ".//s:worksheetSource[@name] | .//s:dataRef[@name]", namespaces=NS
            ):
                owner = source.get("sheet")
                rid = source.get(f"{{{DOC_REL_NS}}}id")
                if rid:
                    relation = plan.book.package.relationships(part).get(rid)
                    if relation is None:
                        raise ValueError("Named source relationship is missing")
                    if not relation[1]:
                        continue
                    matched = [
                        entry["name"]
                        for entry in plan.book.entries
                        if entry["key"]["part"] == relation[1]
                    ]
                    if len(matched) != 1 or (
                        owner is not None and owner.casefold() != matched[0].casefold()
                    ):
                        raise ValueError(
                            "Named source relationship has ambiguous worksheet identity"
                        )
                    owner = matched[0]
                resolved = resolver.resolve(_decode_text(source.get("name", "")), owner)
                self.sources.append((part, source, owner, resolved))
                if len(self.sources) > 4096:
                    raise ValueError("Named source inspection budget exceeded")

    def finish(self, target: str, transform: GridTransform) -> list[str]:
        resolver = GridSourceResolver(self.plan, self.states)
        changed = set()
        for part, source, owner, before in self.sources:
            if before is None or before.sheet.casefold() != target.casefold():
                continue
            after = resolver.resolve(_decode_text(source.get("name", "")), owner)
            if after is None or before.sheet.casefold() != after.sheet.casefold():
                raise ValueError("Grid edit changes named source worksheet identity")
            if source.tag == tag("worksheetSource"):
                old, new = before.bounds, after.bounds
                if (
                    old.last_column - old.first_column
                    != new.last_column - new.first_column
                ):
                    raise ValueError(
                        "Named pivot source column changes require matching cache field identities"
                    )
                if (
                    transform.edit.axis == "row"
                    and transform.point(old.first_row) is None
                ):
                    raise ValueError(
                        "Named pivot header deletion requires matching cache field identities"
                    )
                root = self.plan.roots[part]
                if root.tag == tag("pivotCacheDefinition"):
                    root.set("invalid", "1")
                    root.set("refreshOnLoad", "1")
                    changed.add(part)
        return sorted(changed)
