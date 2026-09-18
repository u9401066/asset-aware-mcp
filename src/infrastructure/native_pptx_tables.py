"""Insert native tables into existing shape trees with independently checked grids."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.native_assets import NativeEditResult
from src.domain.native_pptx_table import (
    NativePptxTableAddition,
    validate_table_additions,
)
from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_pptx_package import A_NS, NativePptxPackage
from src.infrastructure.native_pptx_shape_edit import _append_shape, _finish
from src.infrastructure.native_pptx_table_builder import build_table
from src.infrastructure.native_pptx_table_checks import verify_table


def add_tables(
    data: bytes, items: list[NativePptxTableAddition]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(items) <= 100:
        raise ValueError("Table additions require 1..100 tables")
    validate_table_additions(items)
    package = NativePptxPackage(data)
    package.check_editable()
    list(package.shapes())
    style_id = destination_table_style(package)
    changes = [
        _append_shape(
            package, item, build_table(item.table, style_id), name=item.table.name
        )
        for item in items
    ]
    updated, checks = _finish(package, changes, False)
    checked = NativePptxPackage(updated)
    for item, change, report in zip(items, changes, checks.changes, strict=True):
        verify_table(checked.locate(change.locator), item.table, style_id)
        report.update(
            operation="add_table",
            table_style_id=style_id,
            rows=len(item.table.row_heights),
            columns=len(item.table.column_widths),
        )
    checks.checks.append("requested_table_grid_text_formatting_and_merges")
    return updated, checks


def destination_table_style(package: NativePptxPackage) -> str | None:
    targets = [
        path
        for kind, path in package.relationships(package.main_part).values()
        if kind == f"{DOC_REL_NS}/tableStyles"
    ]
    if not targets:
        return None
    if len(targets) != 1 or targets[0] not in package.parts:
        raise ValueError("Presentation table styles need one internal relationship")
    root = package.xml(targets[0])
    identity = root.get("def", "")
    if root.tag != f"{{{A_NS}}}tblStyleLst" or not re.fullmatch(
        r"\{[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\}", identity
    ):
        raise ValueError("Invalid destination table style default")
    return str(identity)
