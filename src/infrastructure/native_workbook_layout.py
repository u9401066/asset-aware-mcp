"""Revision-independent layout patch and complete mechanical read-back."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_layout import LayoutTransform
from src.infrastructure.native_grid_integrity import check_grid_package
from src.infrastructure.native_grid_metadata import clear_chart_caches
from src.infrastructure.native_grid_objects import GridObjects
from src.infrastructure.native_grid_references import clear_formula_caches
from src.infrastructure.native_grid_xml import cell_map, tag
from src.infrastructure.native_layout_xml import (
    check_layout_features,
    dimensions,
    resize_columns,
    resize_rows,
)
from src.infrastructure.native_workbook_package import NativeWorkbookPackage
from src.infrastructure.native_workbook_plan import WorkbookPlan

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_layout import NativeLayoutUpdate
    from src.domain.native_workbook import NativeWorksheetKey


def read_layout(data: bytes, key: NativeWorksheetKey) -> dict[str, Any]:
    book = NativeWorkbookPackage(data)
    sheet = book.match(key)
    return {
        "representation": "native-worksheet-layout-v1",
        "worksheet": sheet,
        "layout": dimensions(book.package.xml(key.part)),
        "review_boundary": "Stored dimensions only. Automatic height, font substitution, object geometry, clipping and formula results require Agent review of a new rendition.",
    }


def _cells(roots: dict[str, etree._Element]) -> dict[str, dict[str, bytes]]:
    return {
        part: {
            address: etree.tostring(cell, method="c14n", exclusive=True)
            for address, cell in cell_map(root).items()
        }
        for part, root in roots.items()
        if root.tag == tag("worksheet")
    }


def update_layout(
    data: bytes, request: NativeLayoutUpdate
) -> tuple[bytes, NativeEditResult]:
    plan = WorkbookPlan(data)
    plan.book.match(request.worksheet)
    root = plan.roots[request.worksheet.part]
    check_layout_features(root, request)
    original = deepcopy(plan.roots)
    clear_formula_caches(original)
    expected_cells = _cells(original)
    objects = GridObjects(plan, request.worksheet.part, request)
    before = dimensions(root)
    receipts = []
    for edit in request.edits:
        transform = LayoutTransform(edit)
        geometry = objects.before(transform)
        if edit.axis == "row":
            resize_rows(root, edit)
        else:
            resize_columns(root, edit)
        receipts.append(
            {
                "edit": edit.model_dump(exclude_none=True),
                "objects": objects.apply(transform, geometry),
            }
        )
    after = dimensions(root)
    caches = clear_formula_caches(plan.roots)
    chart_caches = clear_chart_caches(plan.roots)
    if _cells(plan.roots) != expected_cells:
        raise ValueError("Layout edit changed cell coordinates, payloads or formatting")
    updated, result = plan.finish(
        {
            "operation": "update_worksheet_layout",
            "worksheet": request.worksheet.model_dump(),
            "before": before,
            "after": after,
            "edits": receipts,
            "cleared_formula_values": caches,
            "cleared_chart_caches": chart_caches,
        }
    )
    check_grid_package(plan, updated, result)
    if read_layout(updated, request.worksheet)["layout"] != after:
        raise ValueError("Serialized worksheet dimensions failed read-back")
    result.checks.extend(
        [
            "layout_dimensions_read_back",
            "all_cell_coordinates_payloads_and_styles_preserved_except_formula_caches",
        ]
    )
    result.repairs.append("layout_sensitive_formula_and_chart_caches_invalidated")
    result.review_required.append(
        "automatic_row_heights_font_metrics_clipping_and_object_geometry"
    )
    return updated, result
