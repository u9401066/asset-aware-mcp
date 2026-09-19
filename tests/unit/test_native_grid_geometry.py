"""Drawing policies preserve measured placement with explicit font/default metrics."""

import pytest
from lxml import etree

from src.domain.native_grid import GridTransform, NativeGridEdit, NativeGridUpdate
from src.domain.native_grid_geometry import GridAxisMetrics, GridPoint, relocate_axis
from src.infrastructure.native_grid_metrics import EMU_PER_PIXEL, GridMetrics
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_plan import WorkbookPlan
from tests.native_grid_helpers import table_workbook


def request(**kwargs):
    return NativeGridUpdate(
        worksheet={"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
        edits=[{"axis": "row", "operation": "insert", "at": 2}],
        **kwargs,
    )


def transform(at=2, operation="insert", count=1, **kwargs):
    return GridTransform(
        NativeGridEdit(axis="row", operation=operation, at=at, count=count, **kwargs)
    )


def test_actual_stored_column_width_and_row_height_match_source_pixel_dimensions():
    plan = WorkbookPlan(table_workbook())
    root = plan.roots["xl/worksheets/sheet1.xml"]
    before = xml_bytes(root)
    factory = GridMetrics(plan, request())
    columns, col_info = factory.axis(root, "column")
    rows, row_info = factory.axis(root, "row")
    assert columns.prefix(3) == 3 * 131 * EMU_PER_PIXEL  # XlsxWriter width 18.
    assert columns.prefix(4) == (3 * 131 + 64) * EMU_PER_PIXEL
    assert rows.prefix(3) == (20 + 20 + 32) * EMU_PER_PIXEL
    assert rows.prefix(4) == (20 + 20 + 32 + 20) * EMU_PER_PIXEL
    assert (
        col_info["digit_width_pixels"] == 7 and col_info["default_column_pixels"] == 64
    )
    assert row_info["default_points"] == "15"
    assert xml_bytes(root) == before


def test_unknown_normal_font_requires_explicit_column_calibration():
    plan = WorkbookPlan(table_workbook())
    plan.roots["xl/styles.xml"].find("s:fonts/s:font/s:name", NS).set("val", "Arial")
    root = plan.roots["xl/worksheets/sheet1.xml"]
    with pytest.raises(ValueError, match="column_digit_width"):
        GridMetrics(plan, request()).axis(root, "column")
    with pytest.raises(ValueError, match="default_column_pixels"):
        GridMetrics(plan, request(column_digit_width=8)).axis(root, "column")
    metrics, info = GridMetrics(
        plan, request(column_digit_width=8, default_column_pixels=73)
    ).axis(root, "column")
    assert metrics.default_size == 73 * EMU_PER_PIXEL
    assert info["font_basis"] == "caller_digit_width"
    root.remove(root.find("s:sheetFormatPr", NS))
    with pytest.raises(ValueError, match="default_row_height_points"):
        GridMetrics(plan, request()).axis(root, "row")
    assert (
        GridMetrics(plan, request(default_row_height_points=18.0))
        .axis(root, "row")[0]
        .default_size
        == 24 * EMU_PER_PIXEL
    )


def test_hidden_defaults_and_explicit_dimensions_are_preserved():
    plan = WorkbookPlan(table_workbook())
    root = plan.roots["xl/worksheets/sheet1.xml"]
    root.find("s:sheetFormatPr", NS).set("zeroHeight", "1")
    root.find('s:sheetData/s:row[@r="3"]', NS).set("hidden", "1")
    rows, _ = GridMetrics(plan, request()).axis(root, "row")
    assert rows.default_size == 0
    assert rows.prefix(1) == 0  # No stored row 1.
    assert rows.prefix(2) == 20 * EMU_PER_PIXEL  # Explicit visible header.
    assert rows.prefix(3) == rows.prefix(2)  # Explicit hidden row.
    root.find("s:cols/s:col", NS).set("hidden", "1")
    columns, _ = GridMetrics(plan, request()).axis(root, "column")
    assert columns.prefix(3) == 0 and columns.prefix(4) == 64 * EMU_PER_PIXEL


def test_stored_default_column_width_uses_ooxml_width_units():
    plan = WorkbookPlan(table_workbook())
    root = plan.roots["xl/worksheets/sheet1.xml"]
    root.find("s:sheetFormatPr", NS).set("defaultColWidth", "9.140625")
    columns, info = GridMetrics(plan, request()).axis(root, "column")
    assert columns.default_size == 64 * EMU_PER_PIXEL
    assert info["basis"] == "stored_default_column_width"


def test_sparse_metrics_normalize_hidden_cells_and_do_not_iterate_a_million_rows():
    metrics = GridAxisMetrics(1_048_576, 20, ((1, 0), (2, 40), (900_000, 30)))
    assert metrics.prefix(3) == 60
    assert metrics.locate(20) == GridPoint(2, 0)
    assert metrics.absolute(GridPoint(900_001, 5)) == 900_001 * 20 + 10 + 5
    assert metrics.locate(metrics.prefix(metrics.limit)) == GridPoint(
        metrics.limit - 1, 20
    )
    for location in (0, 19, 20, 21, 59, 60, 900_001 * 20 + 13):
        assert metrics.absolute(metrics.locate(location)) == location


@pytest.mark.parametrize(
    "mode,expected_extent", [("twoCell", 85), ("oneCell", 65), ("absolute", 65)]
)
def test_insertion_inside_object_honors_move_resize_policy(mode, expected_extent):
    metrics = GridAxisMetrics(1_048_576, 20)
    result = relocate_axis(
        GridPoint(0, 5), GridPoint(3, 10), metrics, metrics, transform(), mode=mode
    )
    assert result.new_position == result.old_position == 5
    assert result.new_extent == expected_extent
    assert result.old_extent == 65


def test_insertion_before_object_moves_only_cell_anchored_objects():
    metrics = GridAxisMetrics(1_048_576, 20)
    for mode in ("oneCell", "twoCell", "absolute"):
        result = relocate_axis(
            GridPoint(1, 5),
            GridPoint(4, 10),
            metrics,
            metrics,
            transform(at=1),
            mode=mode,
        )
        assert result.new_position == (25 if mode == "absolute" else 45)
        assert result.new_extent == 65


def test_deleted_object_interval_has_explicit_preserve_size_or_reject_policy():
    metrics = GridAxisMetrics(1_048_576, 20)
    result = relocate_axis(
        GridPoint(1, 5),
        GridPoint(2, 10),
        metrics,
        metrics,
        transform(operation="delete", count=2),
        mode="twoCell",
    )
    assert result.collapse_preserved and result.new_extent == 25
    assert result.start == GridPoint(1, 0) and result.end == GridPoint(2, 5)
    with pytest.raises(ValueError, match="collapse"):
        relocate_axis(
            GridPoint(1, 5),
            GridPoint(2, 10),
            metrics,
            metrics,
            transform(operation="delete", count=2, collapsed_objects="reject"),
            mode="twoCell",
        )


def test_absolute_anchor_reconstruction_uses_changed_row_dimensions():
    before = GridAxisMetrics(1_048_576, 20, ((0, 40), (1, 0), (2, 30)))
    after = GridAxisMetrics(1_048_576, 20, ((0, 40), (1, 40), (2, 0), (3, 30)))
    result = relocate_axis(
        GridPoint(0, 5),
        GridPoint(3, 10),
        before,
        after,
        transform(at=1),
        mode="absolute",
    )
    assert result.start == GridPoint(0, 5) and result.end == GridPoint(3, 0)
    assert result.old_position == result.new_position == 5
    assert result.old_extent == result.new_extent == 75


def test_invalid_metrics_and_nonfinite_native_dimensions_fail():
    with pytest.raises(ValueError, match="duplicate"):
        GridAxisMetrics(16_384, 20, ((0, 10), (0, 20)))
    plan = WorkbookPlan(table_workbook())
    root = plan.roots["xl/worksheets/sheet1.xml"]
    root.find("s:cols/s:col", NS).set("width", "NaN")
    with pytest.raises(ValueError, match="dimension"):
        GridMetrics(plan, request()).axis(root, "column")
    row = etree.SubElement(root.find("s:sheetData", NS), tag("row"), r="3")
    row.set("ht", "10")
    with pytest.raises(ValueError, match="Duplicate"):
        GridMetrics(plan, request()).axis(root, "row")
