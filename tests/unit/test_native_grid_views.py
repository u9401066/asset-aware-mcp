"""Freeze counts and zero-based page breaks remain tied to moved grid cells."""

import pytest
from lxml import etree

from src.domain.native_grid import GridTransform, NativeGridEdit
from src.infrastructure.native_grid_views import shift_breaks, shift_views
from src.infrastructure.native_ooxml import SHEET_NS
from src.infrastructure.native_spreadsheet_reader import NS


def change(operation="insert", at=2, count=1, axis="row"):
    return GridTransform(
        NativeGridEdit(operation=operation, at=at, count=count, axis=axis)
    )


def worksheet(body):
    return etree.fromstring(
        f'<worksheet xmlns="{SHEET_NS}">{body}<sheetData/></worksheet>'
    )


def test_frozen_panes_keep_active_selection_when_one_axis_is_deleted():
    root = worksheet(
        '<sheetViews><sheetView workbookViewId="0" topLeftCell="A3"><pane xSplit="2" ySplit="2" topLeftCell="C3" activePane="topRight" state="frozen"/><selection pane="topRight" activeCell="D1" sqref="D1"/><selection pane="bottomLeft" activeCell="A4" sqref="A4"/><selection pane="bottomRight" activeCell="D4" sqref="D4"/></sheetView></sheetViews>'
    )
    shift_views(root, change(operation="delete", at=1, count=2))
    view = root.find("s:sheetViews/s:sheetView", NS)
    pane = view.find("s:pane", NS)
    assert pane.get("xSplit") == "2" and pane.get("ySplit") is None
    assert pane.get("topLeftCell") == "C1" and pane.get("activePane") == "topRight"
    assert view.get("topLeftCell") == "A1"
    selections = {node.get("pane"): node for node in view.findall("s:selection", NS)}
    assert set(selections) == {"topRight", "topLeft"}
    assert selections["topRight"].get("activeCell") == "D1"
    assert selections["topLeft"].get("activeCell") == "A2"


def test_removing_final_frozen_axis_unfreezes_view_and_keeps_active_cell():
    root = worksheet(
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="2" topLeftCell="A3" activePane="bottomLeft" state="frozen"/><selection pane="topLeft" activeCell="B1" sqref="B1"/><selection pane="bottomLeft" activeCell="D4" sqref="D4"/></sheetView></sheetViews>'
    )
    shift_views(root, change(operation="delete", at=1, count=2))
    view = root.find("s:sheetViews/s:sheetView", NS)
    assert view.find("s:pane", NS) is None
    selections = view.findall("s:selection", NS)
    assert len(selections) == 1 and selections[0].get("pane") is None
    assert selections[0].get("activeCell") == "D2"


@pytest.mark.parametrize("at,expected", [(1, "3"), (2, "3"), (3, "2")])
def test_insertion_within_freeze_adds_cells_but_outside_does_not(at, expected):
    root = worksheet(
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="2" topLeftCell="A3" state="frozen"/></sheetView></sheetViews>'
    )
    shift_views(root, change(at=at))
    assert root.find("s:sheetViews/s:sheetView/s:pane", NS).get("ySplit") == expected


def test_split_positions_are_points_not_rows_and_selection_index_survives():
    root = worksheet(
        '<sheetViews><sheetView workbookViewId="0"><pane xSplit="1155.5" ySplit="800.25" topLeftCell="C4" state="split"/><selection activeCell="A4" activeCellId="1" sqref="A1:A8 A4:A6"/></sheetView></sheetViews>'
    )
    shift_views(root, change())
    pane = root.find("s:sheetViews/s:sheetView/s:pane", NS)
    assert pane.get("xSplit") == "1155.5" and pane.get("ySplit") == "800.25"
    assert pane.get("topLeftCell") == "C5"
    selection = root.find("s:sheetViews/s:sheetView/s:selection", NS)
    assert selection.get("sqref") == "A1:A9 A5:A7"
    assert selection.get("activeCell") == "A5" and selection.get("activeCellId") == "1"


def test_selection_wholly_deleted_uses_valid_surviving_cell():
    root = worksheet(
        '<sheetViews><sheetView workbookViewId="0"><selection activeCell="A2" sqref="A2:A3"/></sheetView></sheetViews>'
    )
    shift_views(root, change(operation="delete", at=2, count=2))
    selection = root.find("s:sheetViews/s:sheetView/s:selection", NS)
    assert dict(selection.attrib) == {
        "activeCell": "A2",
        "sqref": "A2",
        "activeCellId": "0",
    }


def test_page_break_ids_and_cross_axis_extents_follow_zero_based_coordinates():
    root = worksheet(
        '<rowBreaks count="2" manualBreakCount="1"><brk id="2" min="0" max="16383" man="1"/><brk id="5" min="1" max="4"/></rowBreaks><colBreaks count="1" manualBreakCount="1"><brk id="4" min="1" max="6" man="1"/></colBreaks>'
    )
    shift_breaks(root, change(operation="delete", at=3, count=2))
    row = root.find("s:rowBreaks", NS)
    assert row.get("count") == "1" and row.get("manualBreakCount") == "0"
    assert row.find("s:brk", NS).get("id") == "3"
    col = root.find("s:colBreaks/s:brk", NS)
    assert (col.get("min"), col.get("max")) == ("1", "4")
    shift_breaks(root, change(axis="column", at=1))
    assert row.find("s:brk", NS).get("min") == "2"
    assert row.find("s:brk", NS).get("max") == "5"
    assert col.get("id") == "5"


@pytest.mark.parametrize(
    "attribute,value", [("xSplit", "nan"), ("ySplit", "2.5"), ("xSplit", "16384")]
)
def test_invalid_frozen_pane_is_not_silently_coerced(attribute, value):
    root = worksheet(
        f'<sheetViews><sheetView workbookViewId="0"><pane state="frozen" {attribute}="{value}"/></sheetView></sheetViews>'
    )
    with pytest.raises(ValueError):
        shift_views(root, change())
