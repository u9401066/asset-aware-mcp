"""Native grid CRUD preserves literal strings, XML, styles, merges and frame scale."""

from copy import deepcopy

import pytest

from src.domain.native_pptx import NativePptxShapeLocator
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_pptx_grid import canonical
from src.infrastructure.native_pptx_package import NS, NativePptxPackage
from tests.native_pptx_grid_helpers import edit, grid_fixture, reference, table, texts
from tests.native_workbook_helpers import _replace


@pytest.mark.parametrize("axis", ["row", "column"])
@pytest.mark.parametrize("index", [0, 1, 3])
def test_insert_and_delete_recover_existing_cells_and_style(axis, index):
    data, ref, _ = grid_fixture(merge=None)
    before = NativePptxPackage(data)
    updated, checks = edit(
        data,
        ref,
        {"op": "insert", "axis": axis, "index": index, "sizes": [321000, 456000]},
        {"op": "delete", "axis": axis, "index": index, "count": 2},
    )
    assert texts(updated) == texts(data)
    after = NativePptxPackage(updated)
    locator = NativePptxShapeLocator(**ref["locator"])
    assert canonical(before.locate(locator)) == canonical(after.locate(locator))
    assert checks.changes[0]["inserted_cells"] == 6
    for part, content in before.parts.items():
        if part != locator.part:
            assert after.parts[part] == content


@pytest.mark.parametrize("axis", ["row", "column"])
def test_insertion_inside_rectangle_expands_merge_then_deletion_shrinks(axis):
    data, ref, _ = grid_fixture(merge="rectangle")
    updated, _ = edit(
        data, ref, {"op": "insert", "axis": axis, "index": 1, "sizes": [123000]}
    )
    target = table(updated)
    assert (target.cell(0, 0).span_height, target.cell(0, 0).span_width) == (
        (3, 2) if axis == "row" else (2, 3)
    )
    assert target.cell(0, 0).text == "樣本 & 結果"
    restored, _ = edit(
        updated,
        reference(updated, NativePptxShapeLocator(**ref["locator"])),
        {"op": "delete", "axis": axis, "index": 1, "count": 1},
    )
    assert texts(restored) == texts(data)
    assert table(restored).cell(0, 0).span_height == 2
    assert table(restored).cell(0, 0).span_width == 2


@pytest.mark.parametrize("axis", ["row", "column"])
def test_deleting_rectangle_anchor_promotes_original_text_and_format(axis):
    data, ref, _ = grid_fixture(merge="rectangle")
    updated, result = edit(
        data, ref, {"op": "delete", "axis": axis, "index": 0, "count": 1}
    )
    target = table(updated)
    assert target.cell(0, 0).text == "樣本 & 結果"
    assert str(target.cell(0, 0).fill.fore_color.rgb) == "204060"
    assert target.cell(0, 0).margin_left == 10000
    assert target.cell(0, 0).span_height == (1 if axis == "row" else 2)
    assert target.cell(0, 0).span_width == (2 if axis == "row" else 1)
    assert result.changes[0]["promoted_merge_anchors"] == 1


def test_single_remaining_merged_cell_becomes_visible_normal_cell():
    data, ref, _ = grid_fixture()
    updated, _ = edit(
        data, ref, {"op": "delete", "axis": "column", "index": 0, "count": 1}
    )
    assert not table(updated).cell(0, 0).is_merge_origin
    assert not table(updated).cell(0, 0).is_spanned
    assert texts(updated) == [
        ["樣本 & 結果", "Value"],
        ["007", "-0.50\nmg/L"],
        ["12", "=SUM(A1:A2)"],
    ]


def test_complete_merge_deletion_and_sequential_indices():
    data, ref, _ = grid_fixture(merge="rectangle")
    updated, result = edit(
        data,
        ref,
        {"op": "delete", "axis": "row", "index": 0, "count": 2},
        {
            "op": "insert",
            "axis": "row",
            "index": 1,
            "sizes": [250000],
            "cells": [
                [{"paragraphs": [[{"text": t}]]} for t in ["A103", "000", "−1.20"]]
            ],
        },
        {"op": "resize", "axis": "column", "index": 1, "sizes": [900000, 2600000]},
    )
    assert texts(updated) == [["A102", "12", "=SUM(A1:A2)"], ["A103", "000", "−1.20"]]
    assert [c.width for c in table(updated).columns] == [1500000, 900000, 2600000]
    assert result.changes[0]["after_rows_columns"] == [2, 3]


def test_resize_preserves_frame_scale_rotation_unknown_xml_and_cell_format():
    from lxml import etree

    data, ref, _ = grid_fixture()
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    node = package.locate(locator)
    transform = node.find("p:xfrm", NS)
    transform.set("rot", "2700000")
    transform.find("a:ext", NS).set("cx", "10000000")
    cell = node.find(".//a:tr/a:tc", NS)
    extension = etree.SubElement(cell, f"{{{NS['a']}}}extLst")
    etree.SubElement(extension, "{urn:custom}keep", value="unchanged")
    original_cell = deepcopy(cell)
    data = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    updated, _ = edit(
        data,
        reference(data, locator),
        {"op": "resize", "axis": "column", "index": 0, "sizes": [2500000]},
    )
    new = NativePptxPackage(updated).locate(locator)
    assert new.find("p:xfrm", NS).get("rot") == "2700000"
    assert new.find("p:xfrm/a:ext", NS).get("cx") == "12000000"
    assert etree.tostring(
        new.find(".//a:tr/a:tc", NS), method="c14n", exclusive=True
    ) == etree.tostring(original_cell, method="c14n", exclusive=True)


@pytest.mark.parametrize("region,grouped", [("notes", False), ("slide", True)])
def test_grid_edits_use_existing_notes_and_group_locators(region, grouped):
    data, ref, _ = grid_fixture(region=region, grouped=grouped)
    updated, _ = edit(
        data, ref, {"op": "insert", "axis": "row", "index": 3, "sizes": [450000]}
    )
    node = NativePptxPackage(updated).locate(NativePptxShapeLocator(**ref["locator"]))
    assert len(node.findall(".//a:tbl/a:tr", NS)) == 4
