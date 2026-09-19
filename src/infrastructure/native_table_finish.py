"""Read back a complete private Table patch before repository publication."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_grid_integrity import check_relocated_cells
from src.infrastructure.native_grid_table_state import table_states
from src.infrastructure.native_workbook_plan import WorkbookPlan

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.infrastructure.native_table_cells import TableCellWriter


def finish_table(
    plan: WorkbookPlan, worksheet: str, writer: TableCellWriter, change: dict[str, Any]
) -> tuple[bytes, NativeEditResult]:
    updated, result = plan.finish(change)
    checked = WorkbookPlan(updated)
    table_states(checked)
    for part, expected in plan.roots.items():
        if etree.tostring(checked.part(part), method="c14n") != etree.tostring(
            expected, method="c14n"
        ):
            raise ValueError("Native Table package failed exact XML readback")
    check_relocated_cells(checked.roots[worksheet], writer.expected)
    for part, payload in plan.book.package.parts.items():
        if (
            part not in result.changed_parts
            and checked.book.package.parts.get(part) != payload
        ):
            raise ValueError("Native Table edit changed an untouched package part")
    result.checks.extend(
        [
            "exact_table_and_column_preconditions_checked",
            "table_cells_and_run_formats_read_back",
            "complete_table_package_xml_read_back",
        ]
    )
    result.repairs.append("table_reference_and_calculation_caches_updated")
    return updated, result
