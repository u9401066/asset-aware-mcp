"""Coordinate private table edits, generated cells and stable structured references."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_grid_tables import GridTableChange
from src.infrastructure.native_grid_cells import GridCellWriter, order_cells
from src.infrastructure.native_grid_formulas import translate_shared_formula
from src.infrastructure.native_grid_references import formula_fields
from src.infrastructure.native_grid_structured import rewrite_structured_formula
from src.infrastructure.native_grid_table_edit import TableGridEdit
from src.infrastructure.native_grid_table_state import table_states
from src.infrastructure.native_grid_xml import Rectangle, address, tag
from src.infrastructure.native_ooxml import DOC_REL_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS, XML_SPACE, _encode_text

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform
    from src.infrastructure.native_grid_table_state import GridTableState
    from src.infrastructure.native_workbook_plan import WorkbookPlan
    from src.infrastructure.native_workbook_references import WorkbookReferenceField


class GridTables:
    def __init__(self, plan: WorkbookPlan):
        self.plan = plan
        self.states = table_states(plan)
        self.edits: list[TableGridEdit] = []

    def prepare(self, worksheet: str, transform: GridTransform) -> None:
        self.edits = []
        for state in self.states:
            if state.deleted or state.worksheet != worksheet:
                continue
            self._check_bound_structures(state, transform)
            edit = TableGridEdit(state, transform)
            edit.prepare()
            if edit.change.after is None:
                self._detach(state)
            self.edits.append(edit)

    def _check_bound_structures(
        self, state: GridTableState, transform: GridTransform
    ) -> None:
        before = state.bounds
        after = before.shift(transform)
        columns_change = (
            after is None
            or after.last_column - after.first_column
            != before.last_column - before.first_column
        )
        if not columns_change:
            return
        for _, source, _ in self._named_sources(state):
            if source.tag == tag("worksheetSource"):
                raise ValueError(
                    "Pivot table source column changes require coordinated cache field identities"
                )
        relations = (
            self.plan.book.package.relationships(state.worksheet)
            if relationships_path(state.worksheet) in self.plan.book.package.parts
            else {}
        )
        if (
            state.root.get("tableType", "worksheet") != "worksheet"
            or state.root.find(".//s:xmlColumnPr", NS) is not None
            or any(kind == f"{DOC_REL_NS}/queryTable" for kind, _ in relations.values())
        ):
            raise ValueError(
                "Mapped/query table column changes require coordinated source field identities"
            )

    def _detach(self, state: GridTableState) -> None:
        # Retain historical bytes but detach the table registry and relationship.
        for part in self.plan.book.active_parts():
            if relationships_path(part) not in self.plan.book.package.parts:
                continue
            for rid, (_, target) in self.plan.book.package.relationships(part).items():
                if target == state.part and (
                    part != state.worksheet or rid != state.rid
                ):
                    raise ValueError(
                        "Deleted native table has another incoming relationship"
                    )
        if self._named_sources(state):
            raise ValueError("Deleted table is still a pivot/consolidation source")
        parent = state.registry.getparent()
        parent.remove(state.registry)
        remaining = parent.findall("s:tablePart", NS)
        if remaining:
            parent.set("count", str(len(remaining)))
        else:
            parent.getparent().remove(parent)
        relationships = self.plan.part(relationships_path(state.worksheet))
        for node in list(relationships):
            if node.get("Id") == state.rid:
                relationships.remove(node)
        self.plan.roots.pop(state.part)
        state.deleted = True

    def _named_sources(
        self, state: GridTableState
    ) -> list[tuple[str, etree._Element, etree._Element]]:
        found = []
        names = {state.name.casefold(), state.root.get("name", "").casefold()}
        names.discard("")
        for part, root in self.plan.roots.items():
            for source in root.xpath(
                ".//s:worksheetSource | .//s:dataRef", namespaces=NS
            ):
                if source.get("name", "").casefold() not in names:
                    continue
                rid = source.get(f"{{{DOC_REL_NS}}}id")
                if rid:
                    relations = self.plan.book.package.relationships(part)
                    if rid not in relations:
                        raise ValueError("Named source relationship is missing")
                    if not relations[rid][1]:
                        continue
                found.append((part, source, root))
        return found

    def invalidate_named_source_caches(self) -> list[str]:
        changed = set()
        for edit in self.edits:
            if edit.state.deleted:
                continue
            for part, _, root in self._named_sources(edit.state):
                if root.tag == tag("pivotCacheDefinition"):
                    root.set("invalid", "1")
                    root.set("refreshOnLoad", "1")
                    changed.add(part)
        return sorted(changed)

    def context(self, field: WorkbookReferenceField) -> str | None:
        for state in self.states:
            if state.deleted:
                continue
            if state.part == field.part:
                return state.name
            if state.worksheet != field.part:
                continue
            parent = field.node.getparent()
            if (
                parent is not None
                and parent.tag == tag("c")
                and state.bounds.contains(parent.get("r", ""))
            ):
                return state.name
            for ancestor in field.node.iterancestors():
                if ancestor.tag not in {
                    tag("conditionalFormatting"),
                    tag("dataValidation"),
                }:
                    continue
                ranges = [
                    Rectangle.parse(value)
                    for value in ancestor.get("sqref", "").split()
                ]
                if ranges and all(
                    state.bounds.contains(value.anchor)
                    and state.bounds.contains(
                        address(value.last_row, value.last_column)
                    )
                    for value in ranges
                ):
                    return state.name
        return None

    def rewrite_references(self) -> dict[str, int]:
        changes = []
        for edit in self.edits:
            if edit.change.before == edit.change.after:
                continue
            changes.append(edit.change)
            alias = edit.state.root.get("name", "")
            if alias and alias.casefold() != edit.change.name.casefold():
                changes.append(
                    GridTableChange(alias, edit.change.before, edit.change.after)
                )
        if not changes:
            return {}
        plans = []
        total = fields = 0
        for part, root in self.plan.roots.items():
            for field in formula_fields(part, root):
                fields += 1
                total += len(field.text.encode("utf-8"))
                if fields > 20_000 or total > 8 * 1024 * 1024:
                    raise ValueError(
                        "Structured references exceed the inspection budget"
                    )
                value, count = rewrite_structured_formula(
                    field.formula(), changes, table_context=self.context(field)
                )
                if count:
                    if field.kind == "hyperlink_location" and field.text.startswith(
                        "#"
                    ):
                        value = "#" + value
                    plans.append((field, value, count))
        counts: dict[str, int] = {}
        for field, value, count in plans:
            field.set(value)
            counts[field.part] = counts.get(field.part, 0) + count
        return counts

    def finish_cells(self) -> list[dict[str, Any]]:
        writers: dict[str, GridCellWriter] = {}
        for edit in self.edits:
            state = edit.state
            if state.deleted:
                continue
            if state.worksheet not in writers:
                writers[state.worksheet] = GridCellWriter(
                    self.plan.roots[state.worksheet]
                )
            writer = writers[state.worksheet]
            for location, name in edit.headers_to_write:
                cell = writer.empty(location)
                cell.set("t", "inlineStr")
                text = etree.SubElement(etree.SubElement(cell, tag("is")), tag("t"))
                text.set(XML_SPACE, "preserve")
                text.text = _encode_text(name)
                writer.put(cell)
            generated = 0
            first = state.bounds.first_row + state.headers
            for formula, column, delta, rows in edit.calculated:
                if delta:
                    formula.text = translate_shared_formula(
                        formula.text or "", delta, 0
                    )
                for row in rows:
                    cell = writer.empty(address(row, column))
                    node = etree.SubElement(cell, tag("f"))
                    node.text = translate_shared_formula(
                        formula.text or "", row - first, 0
                    )
                    writer.put(cell)
                    generated += 1
            edit.receipt["generated_headers"] = len(edit.headers_to_write)
            edit.receipt["generated_calculated_cells"] = generated
        for part in writers:
            order_cells(self.plan.roots[part])
        return [edit.receipt for edit in self.edits]
