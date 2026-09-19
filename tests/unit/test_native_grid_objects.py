"""Comment text, author identity and legacy display boxes move as one package edit."""

from copy import deepcopy
from decimal import Decimal

import pytest
from lxml import etree

from src.domain.native_grid import GridTransform, NativeGridUpdate
from src.infrastructure.native_grid_cells import shift_cells, shift_columns
from src.infrastructure.native_grid_objects import GridObjects
from src.infrastructure.native_grid_vml import VNS
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_plan import WorkbookPlan
from tests.native_grid_drawing_helpers import SHEET_PART, drawing_workbook
from tests.native_workbook_helpers import _parts, _replace

COMMENTS = "xl/comments1.xml"
VML_PART = "xl/drawings/vmlDrawing1.vml"


def apply_objects(source, **edit):
    plan = WorkbookPlan(source)
    request = NativeGridUpdate.model_validate(
        {
            "worksheet": {"sheet_id": "1", "part": SHEET_PART},
            "edits": [{"axis": "row", "operation": "insert", "at": 1, **edit}],
        }
    )
    objects = GridObjects(plan, SHEET_PART, request)
    transform = GridTransform(request.edits[0])
    before = objects.before(transform)
    root = plan.roots[SHEET_PART]
    shift_columns(root, transform)
    shift_cells(root, transform)
    changes = objects.apply(transform, before)
    return plan.finish({"operation": "object_integration", "objects": changes})


def nodes(data, part, path, namespaces):
    return etree.fromstring(_parts(data)[part]).findall(path, namespaces)


def style(shape):
    return dict(chunk.split(":", 1) for chunk in shape.get("style").split(";") if chunk)


def test_note_cell_text_author_and_display_position_move_together():
    source = drawing_workbook()
    data, result = apply_objects(source)
    comments = nodes(data, COMMENTS, "s:commentList/s:comment", NS)
    assert [node.get("ref") for node in comments] == ["A2", "B3"]
    originals = nodes(source, COMMENTS, "s:commentList/s:comment", NS)
    for old, new in zip(originals, comments, strict=True):
        restored = deepcopy(new)
        restored.set("ref", old.get("ref"))
        assert etree.tostring(restored) == etree.tostring(old)
    assert _parts(data)["xl/styles.xml"] == _parts(source)["xl/styles.xml"]
    shapes = nodes(data, VML_PART, "v:shape", VNS)
    old_shapes = nodes(source, VML_PART, "v:shape", VNS)
    for old, new in zip(old_shapes, shapes, strict=True):
        assert (
            int(new.find("x:ClientData/x:Row", VNS).text)
            == int(old.find("x:ClientData/x:Row", VNS).text) + 1
        )
        previous, current = style(old), style(new)
        assert (
            Decimal(current["margin-top"].removesuffix("pt"))
            == Decimal(previous["margin-top"].removesuffix("pt")) + 15
        )
        assert current["height"] == previous["height"]
        assert current["visibility"] == previous["visibility"]
        assert etree.tostring(new.find("v:textbox", VNS)) == etree.tostring(
            old.find("v:textbox", VNS)
        )
    assert result.changes[0]["objects"]["metrics"]["before"]["dpi"] == 96


@pytest.mark.parametrize("axis,at,remaining", [("row", 2, "A1"), ("column", 1, "A2")])
def test_deleting_note_cell_removes_only_corresponding_shape(axis, at, remaining):
    source = drawing_workbook()
    data, result = apply_objects(source, axis=axis, operation="delete", at=at)
    comments = nodes(data, COMMENTS, "s:commentList/s:comment", NS)
    assert [node.get("ref") for node in comments] == [remaining]
    shapes = nodes(data, VML_PART, "v:shape", VNS)
    assert len(shapes) == 1
    assert len(nodes(data, VML_PART, "v:shapetype", VNS)) == 1
    assert nodes(data, COMMENTS, "s:authors", NS)[0].xpath("string()") == nodes(
        source, COMMENTS, "s:authors", NS
    )[0].xpath("string()")
    changes = result.changes[0]["objects"]["vml"][VML_PART]
    assert sum("deleted_note" in item for item in changes) == 1


def test_deleting_all_notes_keeps_empty_parts_and_historical_content_is_unchanged():
    source = drawing_workbook()
    data, _ = apply_objects(source, operation="delete", at=1, count=2)
    assert not nodes(data, COMMENTS, "s:commentList/s:comment", NS)
    assert not nodes(data, VML_PART, "v:shape", VNS)
    assert len(nodes(source, COMMENTS, "s:commentList/s:comment", NS)) == 2
    assert (
        _parts(data)["xl/worksheets/_rels/sheet1.xml.rels"]
        == _parts(source)["xl/worksheets/_rels/sheet1.xml.rels"]
    )


def test_fixed_note_box_stays_fixed_while_its_commented_cell_moves():
    source = drawing_workbook()
    root = etree.fromstring(_parts(source)[VML_PART])
    client = root.find("v:shape/x:ClientData", VNS)
    client.remove(client.find("x:MoveWithCells", VNS))
    client.remove(client.find("x:SizeWithCells", VNS))
    before_style = root.find("v:shape", VNS).get("style")
    data, result = apply_objects(_replace(source, {VML_PART: etree.tostring(root)}))
    shape = nodes(data, VML_PART, "v:shape", VNS)[0]
    assert shape.get("style") == before_style
    assert shape.find("x:ClientData/x:Row", VNS).text == "1"
    geometry = result.changes[0]["objects"]["vml"][VML_PART][0]
    assert geometry["old_position"] == geometry["new_position"]
    assert geometry["old_extent"] == geometry["new_extent"]
    # The same absolute end point needs a new offset after the 40px row moves.
    assert shape.find("x:ClientData/x:Anchor", VNS).text == "1, 15, 0, 2, 3, 15, 2, 36"


@pytest.mark.parametrize("kind", ["orphan", "duplicate", "bad_style", "bad_anchor"])
def test_unmatched_or_ambiguous_note_metadata_fails_without_publishing(kind):
    source = drawing_workbook()
    root = etree.fromstring(_parts(source)[VML_PART])
    client = root.find("v:shape/x:ClientData", VNS)
    if kind == "orphan":
        client.find("x:Row", VNS).text = "500"
    elif kind == "duplicate":
        root.append(deepcopy(root.find("v:shape", VNS)))
    elif kind == "bad_style":
        root.find("v:shape", VNS).set("style", "margin-top:calc(10px)")
    else:
        client.find("x:Anchor", VNS).text = "1, 2"
    with pytest.raises(ValueError):
        apply_objects(_replace(source, {VML_PART: etree.tostring(root)}))
    assert len(nodes(source, COMMENTS, "s:commentList/s:comment", NS)) == 2
