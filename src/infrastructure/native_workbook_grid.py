"""Private original-package native worksheet row/column CRUD orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.native_grid import GridTransform
from src.infrastructure.native_grid_cells import shift_cells, shift_columns
from src.infrastructure.native_grid_filters import shift_filters
from src.infrastructure.native_grid_integrity import (
    check_grid_package,
    check_relocated_cells,
    relocation_snapshot,
)
from src.infrastructure.native_grid_metadata import (
    check_grid_features,
    clear_chart_caches,
    repair_outline_levels,
    shift_cell_watches,
    shift_pivot_locations,
)
from src.infrastructure.native_grid_named_sources import GridNamedSources
from src.infrastructure.native_grid_objects import GridObjects
from src.infrastructure.native_grid_ranges import (
    apply_merges,
    plan_merges,
    shift_ranges,
    update_dimension,
)
from src.infrastructure.native_grid_references import (
    GridReferences,
    clear_formula_caches,
)
from src.infrastructure.native_grid_shared import (
    expand_shared_formulas,
    shift_formula_blocks,
)
from src.infrastructure.native_grid_tables import GridTables
from src.infrastructure.native_grid_views import shift_breaks, shift_views
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_workbook_plan import WorkbookPlan

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_grid import NativeGridUpdate


class NativeWorkbookGrid:
    def update(
        self, data: bytes, request: NativeGridUpdate
    ) -> tuple[bytes, NativeEditResult]:
        plan = WorkbookPlan(data)
        target = plan.book.match(request.worksheet)
        root = plan.roots[request.worksheet.part]
        check_grid_features(root)
        objects = GridObjects(plan, request.worksheet.part, request)
        tables = GridTables(plan)
        expanded = sum(
            expand_shared_formulas(sheet)
            for sheet in plan.roots.values()
            if sheet.tag == tag("worksheet")
        )
        receipts = []
        for edit in request.edits:
            transform = GridTransform(edit)
            before_geometry = objects.before(transform)
            blocks = shift_formula_blocks(root, transform)
            ranges = shift_ranges(root, transform)
            refs = GridReferences(plan.book, plan.roots)
            named = GridNamedSources(plan, tables.states)
            sources = refs.shift_sources(target["name"], transform)
            pivots = shift_pivot_locations(plan, request.worksheet.part, transform)
            tables.prepare(request.worksheet.part, transform)
            merges = plan_merges(root, transform)
            expected = relocation_snapshot(root, transform)
            shift_columns(root, transform)
            cells = shift_cells(root, transform)
            check_relocated_cells(root, expected)
            apply_merges(root, merges)
            shift_views(root, transform)
            shift_breaks(root, transform)
            shift_filters(root, transform)
            watches = shift_cell_watches(root, transform)
            drawings = objects.apply(transform, before_geometry)
            structured = tables.rewrite_references()
            references = refs.rewrite(target["name"], transform)
            receipts.append(
                {
                    "edit": edit.model_dump(exclude_none=True),
                    "cells": cells,
                    "formula_blocks": blocks,
                    "ranges": ranges,
                    "source_ranges": sources,
                    "pivot_locations": pivots,
                    "cell_watches": watches,
                    "objects": drawings,
                    "structured_references": structured,
                    "references": references,
                    "tables": tables.finish_cells(),
                    "invalidated_named_source_caches": named.finish(
                        target["name"], transform
                    ),
                }
            )
        caches = clear_formula_caches(plan.roots)
        chart_caches = clear_chart_caches(plan.roots)
        repair_outline_levels(root)
        update_dimension(root)
        change: dict[str, Any] = {
            "operation": "update_worksheet_grid",
            "worksheet": request.worksheet.model_dump(),
            "edits": receipts,
            "expanded_shared_formulas": expanded,
            "cleared_formula_values": caches,
            "cleared_remaining_chart_caches": chart_caches,
            "generated_table_cells": tables.generated,
        }
        updated, result = plan.finish(change)
        check_grid_package(plan, updated, result)
        result.repairs.extend(
            [
                "grid_coordinates_and_dependencies_relocated",
                "stale_formula_and_chart_caches_invalidated",
                "worksheet_bounds_and_outline_levels_recomputed",
            ]
        )
        result.review_required.append(
            "drawing_font_metrics_auto_row_height_and_geometry"
        )
        return updated, result
