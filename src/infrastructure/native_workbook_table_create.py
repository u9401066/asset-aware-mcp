"""Create a native editable Table while preserving source cells and package parts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.native_grid_tables import GridTableChange
from src.domain.native_table_edit import NativeTableColumnEdit
from src.infrastructure.native_grid_cells import order_cells
from src.infrastructure.native_grid_metadata import clear_chart_caches
from src.infrastructure.native_grid_ranges import update_dimension
from src.infrastructure.native_grid_references import clear_formula_caches
from src.infrastructure.native_grid_structured import rewrite_structured_formula
from src.infrastructure.native_grid_table_state import table_states
from src.infrastructure.native_grid_xml import address
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_table_builder import build_table
from src.infrastructure.native_table_cells import TableCellWriter
from src.infrastructure.native_table_columns import update_calculated, update_totals
from src.infrastructure.native_table_create_checks import (
    check_creation,
    reserved_tables,
)
from src.infrastructure.native_table_finish import finish_table
from src.infrastructure.native_table_sources import update_sources
from src.infrastructure.native_workbook_plan import WorkbookPlan

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_table_create import NativeTableCreate


class NativeWorkbookTableCreate:
    def create(
        self, data: bytes, request: NativeTableCreate
    ) -> tuple[bytes, NativeEditResult]:
        plan = WorkbookPlan(data)
        states = table_states(plan)
        bounds = check_creation(plan, request, states)
        ids = reserved_tables(plan, request.name)
        owner = plan.book.match(request.worksheet)
        writer = TableCellWriter(plan, request.worksheet.part, owner["name"])
        for position, column in enumerate(request.columns, bounds.first_column):
            if request.header_row:
                location = address(bounds.first_row, position)
                current = writer.value(location)
                if current["kind"] == "blank" and request.header_policy == "fill_blank":
                    writer.write(location, "string", column.name)
                elif current["kind"] != "string" or current["value"] != column.name:
                    raise ValueError(
                        "Table header must match its exact column name; fill_blank only fills blank cells"
                    )
            if (
                request.totals_row
                and writer.value(address(bounds.last_row, position))["kind"] != "blank"
            ):
                raise ValueError(
                    "A new Table totals row must be blank; existing data cannot become totals implicitly"
                )
        state = build_table(plan, request, bounds, ids)
        names = [GridTableChange(state.name, state.columns, state.columns)]
        for offset, (column, node) in enumerate(
            zip(
                request.columns,
                state.root.findall("s:tableColumns/s:tableColumn", NS),
                strict=True,
            )
        ):
            if column.calculated is None and column.totals is None:
                continue
            for formula in (
                column.calculated.formula if column.calculated else None,
                column.totals.value
                if column.totals and column.totals.kind == "formula"
                else None,
            ):
                if formula is not None:
                    rewrite_structured_formula(formula, names, table_context=state.name)
            edit = NativeTableColumnEdit(
                column_id=offset + 1,
                expected_name=column.name,
                calculated=column.calculated,
                totals=column.totals,
            )
            update_calculated(state, node, bounds.first_column + offset, edit, writer)
            update_totals(state, node, bounds.first_column + offset, edit, writer)
        sources = update_sources(plan, [*states, state], state, writer, names)
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
                "operation": "add_workbook_table",
                "request": request.model_dump(),
                "created_table": {
                    "worksheet": request.worksheet.model_dump(),
                    "part": state.part,
                    "relationship_id": state.rid,
                    "id": state.root.get("id"),
                    "name": state.name,
                    "ref": bounds.text,
                },
                "cells": writer.changed,
                "invalidated_pivot_caches": sources,
                "formula_caches_removed": caches,
                "chart_caches_removed": charts,
            },
        )
