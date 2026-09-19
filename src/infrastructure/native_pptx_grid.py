"""Atomic table grid edits with immutable reference and package read-back checks."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_assets import NativeEditResult
from src.domain.native_pptx import shape_representation_sha256
from src.domain.native_pptx_grid import NativePptxGridMerge, NativePptxGridSplit
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_pptx_grid_merges import merge_cells, split_cells
from src.infrastructure.native_pptx_grid_model import TableGrid, sizes
from src.infrastructure.native_pptx_grid_mutations import apply_grid_edit
from src.infrastructure.native_pptx_package import NS, NativePptxPackage
from src.infrastructure.native_pptx_records import shape_record

if TYPE_CHECKING:
    from src.domain.native_pptx_grid import NativePptxTableGridEdit


def canonical(node: etree._Element) -> bytes:
    return bytes(etree.tostring(node, method="c14n"))


def _extent(shape: etree._Element) -> etree._Element:
    values = shape.findall("p:xfrm/a:ext", NS)
    if len(values) != 1:
        raise ValueError("Table requires one explicit local frame extent")
    sizes(values, "cx")
    sizes(values, "cy")
    return values[0]


def _verify(
    before: NativePptxPackage,
    updated: bytes,
    request: NativePptxTableGridEdit,
    original: etree._Element,
    expected: bytes,
) -> None:
    after = NativePptxPackage(updated)
    reference = request.reference
    list(after.shapes())
    actual = after.locate(reference.locator)
    TableGrid.read(actual)
    if canonical(actual) != expected:
        raise ValueError("Table grid read-back differs from planned shape")
    parent = actual.getparent()
    assert parent is not None
    parent.replace(actual, deepcopy(original))
    part = reference.locator.part
    if canonical(before.xml(part)) != canonical(after.roots[part]):
        raise ValueError("Presentation changed outside requested table shape")
    if set(after.parts) != set(before.parts) or any(
        after.parts[name] != content
        for name, content in before.parts.items()
        if name != part
    ):
        raise ValueError("Table grid edit changed unrelated package members")


def edit_table_grid(
    data: bytes, request: NativePptxTableGridEdit
) -> tuple[bytes, NativeEditResult]:
    package = NativePptxPackage(data)
    package.check_editable()
    reference = request.reference
    found = [
        (node, parents)
        for locator, node, parents in package.shapes()
        if locator == reference.locator.model_dump()
    ]
    if len(found) != 1:
        raise ValueError("Table grid reference does not resolve")
    shape, parents = found[0]
    if (
        shape_representation_sha256(
            shape_record(reference.locator.model_dump(), shape, parents)
        )
        != reference.value_sha256
    ):
        raise ValueError("Stale table shape representation")
    original = deepcopy(shape)
    grid = TableGrid.read(shape)
    old_totals = sum(sizes(grid.columns, "w")), sum(sizes(grid.rows, "h"))
    extent = _extent(shape)
    old_extents = int(extent.get("cx")), int(extent.get("cy"))
    inserted = promoted = 0
    merged = split = paragraphs_moved = 0
    before_dimensions = len(grid.rows), len(grid.columns)
    for edit in request.edits:
        if isinstance(edit, NativePptxGridMerge):
            paragraphs_moved += merge_cells(grid, edit)
            merged += 1
        elif isinstance(edit, NativePptxGridSplit):
            split_cells(grid, edit)
            split += 1
        else:
            count, moved = apply_grid_edit(grid, edit)
            inserted += count
            promoted += moved
        if inserted > 10_000:
            raise ValueError("Grid edit batch exceeds 10,000 inserted cells")
        grid.write()
        grid = TableGrid.read(shape)
    totals = sum(sizes(grid.columns, "w")), sum(sizes(grid.rows, "h"))
    for axis, initial, old, total in zip(
        ("cx", "cy"), old_extents, old_totals, totals, strict=True
    ):
        value = (initial * total + old // 2) // old
        if not 1 <= value <= 100_000_000:
            raise ValueError("Resized table frame exceeds bounded EMU extent")
        extent.set(axis, str(value))
    expected = canonical(shape)
    part = reference.locator.part
    updated = package.replace({part: xml_bytes(package.roots[part])})
    _verify(package, updated, request, original, expected)
    return updated, NativeEditResult(
        changed_parts=[part],
        preserved_parts=len(package.parts) - 1,
        changes=[
            {
                "operation": "edit_table_grid",
                "locator": reference.locator.model_dump(),
                "before_rows_columns": list(before_dimensions),
                "after_rows_columns": [len(grid.rows), len(grid.columns)],
                "edit_count": len(request.edits),
                "inserted_cells": inserted,
                "promoted_merge_anchors": promoted,
                "merged_regions": merged,
                "split_regions": split,
                "migrated_paragraphs": paragraphs_moved,
            }
        ],
        checks=[
            "shape_reference_hash",
            "bounded_grid_and_merge_topology",
            "explicit_merge_content_policy",
            "requested_cell_creation_read_back",
            "scaled_frame_extent",
            "serialized_shape_read_back",
            "unchanged_xml_outside_table",
            "exact_package_inventory",
            "untouched_part_bytes",
        ],
        review_required=[
            "semantic_accuracy",
            "rendered_layout",
            "text_overflow",
            "inherited_formatting",
            "unmodeled_table_dependencies",
        ],
    )
