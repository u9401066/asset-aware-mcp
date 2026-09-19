"""Independent relocation and serialized package preservation checks."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_grid_table_state import table_states
from src.infrastructure.native_grid_xml import cell_map, shift_cell, tag
from src.infrastructure.native_workbook_plan import WorkbookPlan

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_grid import GridTransform


def relocation_snapshot(
    root: etree._Element, transform: GridTransform
) -> dict[str, bytes]:
    result = {}
    for address, cell in cell_map(root).items():
        moved = shift_cell(address, transform)
        if moved is not None:
            expected = deepcopy(cell)
            expected.set("r", moved)
            result[moved] = etree.tostring(expected, method="c14n", exclusive=True)
    return result


def check_relocated_cells(root: etree._Element, expected: dict[str, bytes]) -> None:
    cells = cell_map(root)
    for address, payload in expected.items():
        if (
            address not in cells
            or etree.tostring(cells[address], method="c14n", exclusive=True) != payload
        ):
            raise ValueError(
                "Native grid relocation changed a surviving cell payload or format"
            )


def check_grid_package(
    plan: WorkbookPlan, data: bytes, result: NativeEditResult
) -> None:
    checked = WorkbookPlan(data)
    for part, expected in plan.roots.items():
        actual = checked.part(part)
        if etree.tostring(actual, method="c14n") != etree.tostring(
            expected, method="c14n"
        ):
            raise ValueError(
                "Serialized native grid package failed exact XML read-back"
            )
        if actual.tag == tag("worksheet"):
            cell_map(actual)
    table_states(checked)  # Recheck column identity/range/relationship coherence.
    for part, original in plan.book.package.parts.items():
        if (
            part not in result.changed_parts
            and checked.book.package.parts.get(part) != original
        ):
            raise ValueError("Native grid changed an unmodified package part")
    result.checks.extend(
        [
            "surviving_cell_payloads_and_styles_preserved_during_relocation",
            "complete_grid_xml_read_back",
            "table_column_identities_and_ranges_read_back",
        ]
    )
