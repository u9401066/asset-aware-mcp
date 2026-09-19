"""One private native Table metadata/cell/reference patch with exact readback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.native_grid_tables import GridTableChange, GridTableColumn
from src.infrastructure.native_grid_cells import order_cells
from src.infrastructure.native_grid_metadata import clear_chart_caches
from src.infrastructure.native_grid_ranges import update_dimension
from src.infrastructure.native_grid_references import clear_formula_caches
from src.infrastructure.native_grid_structured import rewrite_structured_formula
from src.infrastructure.native_grid_tables import GridTables
from src.infrastructure.native_ooxml import DOC_REL_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_table_cells import TableCellWriter
from src.infrastructure.native_table_columns import (
    rename_header,
    update_calculated,
    update_totals,
)
from src.infrastructure.native_table_finish import finish_table
from src.infrastructure.native_table_sources import update_sources
from src.infrastructure.native_workbook_plan import WorkbookPlan

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_table_edit import NativeTableUpdate


class NativeWorkbookTableEdit:
    def update(
        self, data: bytes, request: NativeTableUpdate
    ) -> tuple[bytes, NativeEditResult]:
        plan = WorkbookPlan(data)
        owner = plan.book.match(request.worksheet)
        if plan.roots[request.worksheet.part].find("s:sheetProtection", NS) is not None:
            raise ValueError("Protected worksheets require an explicit unlock workflow")
        tables = GridTables(plan)
        matches = [
            s
            for s in tables.states
            if s.part == request.part and s.worksheet == request.worksheet.part
        ]
        if len(matches) != 1:
            raise ValueError("Table part is not active in the exact selected worksheet")
        state = matches[0]
        if state.root.get("ref") != request.expected_ref:
            raise ValueError("Stale native Table expected_ref")
        relations = (
            plan.book.package.relationships(state.worksheet)
            if relationships_path(state.worksheet) in plan.book.package.parts
            else {}
        )
        if (
            state.root.get("tableType", "worksheet") != "worksheet"
            or state.root.find(".//s:xmlColumnPr", NS) is not None
            or state.root.find(".//s:extLst", NS) is not None
            or any(kind == f"{DOC_REL_NS}/queryTable" for kind, _ in relations.values())
            or any(
                node.get("queryTableFieldId") or node.get("uniqueName")
                for node in state.root.findall("s:tableColumns/s:tableColumn", NS)
            )
        ):
            raise ValueError(
                "Mapped/query/extended Table edits require coordinated source field identities"
            )
        edits = {edit.column_id: edit for edit in request.columns}
        before = state.columns
        if not edits.keys() <= {col.identity for col in before}:
            raise ValueError("Table edit names an unknown column ID")
        after = []
        for col in before:
            edit = edits.get(col.identity)
            if edit and edit.expected_name != col.name:
                raise ValueError("Stale Table column expected_name")
            after.append(
                GridTableColumn(
                    col.identity,
                    edit.name if edit and edit.name is not None else col.name,
                )
            )
        change = GridTableChange(state.name, before, tuple(after))
        aliases = set(
            {
                name.casefold(): name
                for name in (state.name, state.root.get("name", ""))
                if name
            }.values()
        )
        changes = [
            GridTableChange(alias, before, tuple(after)) for alias in sorted(aliases)
        ]
        writer = TableCellWriter(plan, state.worksheet, owner["name"])
        nodes = state.root.findall("s:tableColumns/s:tableColumn", NS)
        for position, (col, node) in enumerate(
            zip(before, nodes, strict=True), state.bounds.first_column
        ):
            if col.identity in edits:
                rename_header(state, node, position, edits[col.identity], writer)
        references = (
            tables.rewrite_references(changes) if change.before != change.after else {}
        )
        # New formulas are expressed in the final column names; identity mappings
        # validate known selectors without rewriting them back into old names.
        final_names = [
            GridTableChange(alias, tuple(after), tuple(after))
            for alias in sorted(aliases)
        ]
        for position, (col, node) in enumerate(
            zip(before, nodes, strict=True), state.bounds.first_column
        ):
            edit = edits.get(col.identity)
            if edit is None:
                continue
            formulas = [
                edit.calculated.formula if edit.calculated else None,
                edit.totals.value
                if edit.totals and edit.totals.kind == "formula"
                else None,
            ]
            for formula in formulas:
                if formula is not None:
                    rewrite_structured_formula(
                        formula, final_names, table_context=state.name
                    )
            update_calculated(state, node, position, edit, writer)
            update_totals(state, node, position, edit, writer)
        sources = update_sources(plan, tables.states, state, writer, changes)
        caches = clear_formula_caches(plan.roots)
        charts = clear_chart_caches(plan.roots)
        order_cells(writer.root)
        update_dimension(writer.root)
        state.validate()
        return finish_table(
            plan,
            state.worksheet,
            writer,
            {
                "operation": "update_workbook_table",
                "request": request.model_dump(),
                "cells": writer.changed,
                "structured_references": references,
                "invalidated_pivot_caches": sources,
                "formula_caches_removed": caches,
                "chart_caches_removed": charts,
            },
        )
