"""Visibility defaults, missing dimensions and failed geometry changes stay explicit."""

import pytest
from lxml import etree

from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_grid import NativeWorkbookGrid
from tests.native_grid_drawing_helpers import SHEET_PART, drawing_workbook
from tests.native_workbook_helpers import _parts, _replace
from tests.unit.test_native_worksheet_layout import fixture, layout, request


def test_new_dimension_row_does_not_unhide_a_default_hidden_row():
    source = fixture()
    root = etree.fromstring(_parts(source)[SHEET_PART])
    root.find("s:sheetFormatPr", NS).set("zeroHeight", "1")
    source = _replace(source, {SHEET_PART: etree.tostring(root)})
    data, _ = NativeWorkbookGrid().update_layout(
        source,
        request(
            {"axis": "row", "at": 50, "height_points": 35},
            {"axis": "row", "at": 51, "hidden": False},
        ),
    )
    rows = {r["r"]: r for r in layout(data)["rows"]}
    assert rows["50"]["hidden"] == "1" and rows["50"]["ht"] == "35"
    assert rows["51"]["hidden"] == "0" and "ht" not in rows["51"]
    assert layout(data)["defaults"]["zeroHeight"] == "1"


def test_reset_missing_intervals_creates_no_dimension_records():
    data, _ = NativeWorkbookGrid().update_layout(
        fixture(),
        request(
            {"axis": "column", "at": 10, "count": 4, "reset_size": True},
            {"axis": "row", "at": 50, "reset_size": True},
        ),
    )
    assert len(layout(data)["columns"]) == 1
    assert not any(r["r"] == "50" for r in layout(data)["rows"])


def test_new_column_intervals_can_be_reset_without_losing_existing_styles():
    source = fixture()
    data, _ = NativeWorkbookGrid().update_layout(
        source,
        request(
            {"axis": "column", "at": 4, "count": 5, "width_ooxml": 40},
            {"axis": "column", "at": 7, "reset_size": True},
        ),
    )
    cols = layout(data)["columns"]
    assert [(c["min"], c["max"]) for c in cols] == [
        ("1", "3"),
        ("4", "5"),
        ("6", "6"),
        ("8", "8"),
    ]
    assert cols[1]["style"] == cols[0]["style"]
    assert all("style" not in c for c in cols[2:])


@pytest.mark.parametrize("value", ["nan", "-1", "256", "bad"])
def test_malformed_stored_dimensions_fail_even_without_drawing_objects(value):
    source = fixture()
    root = etree.fromstring(_parts(source)[SHEET_PART])
    root.find("s:cols/s:col", NS).set("width", value)
    with pytest.raises(ValueError, match="dimension"):
        NativeWorkbookGrid().update_layout(
            _replace(source, {SHEET_PART: etree.tostring(root)}),
            request({"axis": "row", "at": 1, "height_points": 35}),
        )


def test_collapsed_object_requires_explicit_preserve_size_policy():
    source = drawing_workbook()
    edit = {"axis": "row", "at": 2, "count": 2, "hidden": True}
    with pytest.raises(ValueError, match="collapse"):
        NativeWorkbookGrid().update_layout(source, request(edit))
    _, result = NativeWorkbookGrid().update_layout(
        source, request({**edit, "collapsed_objects": "preserve_size"})
    )
    drawings = result.changes[0]["edits"][0]["objects"]["drawings"]
    assert any(
        record["collapse_preserved"]
        for records in drawings.values()
        for record in records
    )


def test_nondefault_font_needs_caller_calibration_for_column_anchor_geometry():
    source = drawing_workbook()
    root = etree.fromstring(_parts(source)["xl/styles.xml"])
    root.find("s:fonts/s:font/s:name", NS).set("val", "Arial")
    source = _replace(source, {"xl/styles.xml": etree.tostring(root)})
    edit = {"axis": "column", "at": 1, "width_ooxml": 25}
    with pytest.raises(ValueError, match="column_digit_width"):
        NativeWorkbookGrid().update_layout(source, request(edit))
    _, result = NativeWorkbookGrid().update_layout(
        source, request(edit, column_digit_width=7, default_column_pixels=64)
    )
    assert (
        result.changes[0]["edits"][0]["objects"]["metrics"]["before"]["font_basis"]
        == "caller_digit_width"
    )


def test_new_rows_between_existing_and_far_beyond_used_range_keep_order():
    source = fixture()
    data, _ = NativeWorkbookGrid().update_layout(
        source,
        request(
            {"axis": "row", "at": 3, "count": 8, "height_points": 20},
            {"axis": "row", "at": 1_000_000, "count": 20, "height_points": 30},
        ),
    )
    rows = layout(data)["rows"]
    indices = [int(row["r"]) for row in rows]
    assert indices == sorted(set(indices))
    assert set(range(3, 11)) | set(range(1_000_000, 1_000_020)) <= set(indices)
    assert all(row["ht"] == "30" for row in rows if int(row["r"]) >= 1_000_000)
