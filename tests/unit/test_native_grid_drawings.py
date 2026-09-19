"""Drawing anchors, transforms and embedded media survive structural grid edits."""

from copy import deepcopy

import pytest
from lxml import etree

from src.infrastructure.native_grid_drawings import NS, XDR, shift_drawing
from src.infrastructure.native_grid_metrics import EMU_PER_PIXEL
from tests.native_grid_drawing_helpers import (
    DRAWING_PART,
    apply_drawing_grid,
    drawing_plan,
    drawing_workbook,
)
from tests.native_workbook_helpers import _parts, _replace


def pictures(data):
    root = etree.fromstring(_parts(data)[DRAWING_PART])
    return [node for node in root if node.find("xdr:pic", NS) is not None]


def image_geometry(node):
    offset = node.find("xdr:pic/xdr:spPr/a:xfrm/a:off", NS)
    extent = node.find("xdr:pic/xdr:spPr/a:xfrm/a:ext", NS)
    return tuple(int(offset.get(key)) for key in ("x", "y")) + tuple(
        int(extent.get(key)) for key in ("cx", "cy")
    )


def test_insert_inside_image_resizes_only_two_cell_object_and_preserves_media():
    source = drawing_workbook()
    data, result, _, _ = apply_drawing_grid(source)
    geometries = [image_geometry(node) for node in pictures(data)]
    assert geometries == [
        tuple(value * EMU_PER_PIXEL for value in (69, 23, 64, height))
        for height in (80, 40, 40)
    ]
    before, after = _parts(source), _parts(data)
    for part in before:
        if part not in result.changed_parts:
            assert after[part] == before[part]
    assert "xl/media/image1.png" not in result.changed_parts
    chart = etree.fromstring(after[DRAWING_PART]).find(".//xdr:graphicFrame", NS)
    assert dict(chart.find("xdr:xfrm/a:ext", NS).attrib) == {"cx": "0", "cy": "0"}
    assert before["xl/charts/chart1.xml"] == after["xl/charts/chart1.xml"]


def test_insert_before_image_moves_cell_objects_but_reanchors_fixed_picture():
    data, _, _, _ = apply_drawing_grid(drawing_workbook(), at=1)
    nodes = pictures(data)
    assert [image_geometry(node)[1] // EMU_PER_PIXEL for node in nodes] == [43, 43, 23]
    assert [image_geometry(node)[3] // EMU_PER_PIXEL for node in nodes] == [40, 40, 40]
    assert nodes[2].find("xdr:from/xdr:row", NS).text == "1"
    assert nodes[2].find("xdr:from/xdr:rowOff", NS).text == str(3 * EMU_PER_PIXEL)


def test_column_insertion_preserves_fixed_coordinates_and_grows_crossing_image():
    # At B2+5px a 64px image ends inside column C; inserted column C grows it.
    data, _, _, _ = apply_drawing_grid(drawing_workbook(), axis="column", at=3)
    assert [image_geometry(node)[2] // EMU_PER_PIXEL for node in pictures(data)] == [
        128,
        64,
        64,
    ]


def test_deleted_anchor_cells_keep_visible_size_with_explicit_receipt():
    data, result, _, _ = apply_drawing_grid(
        drawing_workbook(), at=2, operation="delete", count=2
    )
    assert image_geometry(pictures(data)[0])[1:] == (
        20 * EMU_PER_PIXEL,
        64 * EMU_PER_PIXEL,
        40 * EMU_PER_PIXEL,
    )
    changes = result.changes[0]["objects"]
    assert changes[0]["collapse_preserved"] is True
    with pytest.raises(ValueError, match="collapse"):
        apply_drawing_grid(
            drawing_workbook(),
            at=2,
            operation="delete",
            count=2,
            collapsed_objects="reject",
        )


def test_explicit_one_cell_and_absolute_anchors_keep_their_extents():
    source = drawing_workbook()
    root = etree.fromstring(_parts(source)[DRAWING_PART])
    anchor = root[0]
    anchor.tag = f"{{{XDR}}}oneCellAnchor"
    anchor.attrib.clear()
    anchor.remove(anchor.find("xdr:to", NS))
    anchor.insert(
        1,
        etree.Element(
            f"{{{XDR}}}ext", cx=str(64 * EMU_PER_PIXEL), cy=str(40 * EMU_PER_PIXEL)
        ),
    )
    fixed = root[1]
    fixed.tag = f"{{{XDR}}}absoluteAnchor"
    fixed.attrib.clear()
    fixed.remove(fixed.find("xdr:from", NS))
    fixed.remove(fixed.find("xdr:to", NS))
    fixed.insert(0, etree.Element(f"{{{XDR}}}pos", x="100", y="200"))
    fixed.insert(1, etree.Element(f"{{{XDR}}}ext", cx="300", cy="400"))
    expected_fixed = etree.tostring(fixed)
    data, _, _, _ = apply_drawing_grid(
        _replace(source, {DRAWING_PART: etree.tostring(root)}), at=1
    )
    nodes = pictures(data)
    assert image_geometry(nodes[0])[1] == 43 * EMU_PER_PIXEL
    assert nodes[0].find("xdr:ext", NS).get("cy") == str(40 * EMU_PER_PIXEL)
    assert etree.tostring(nodes[1]) == expected_fixed


@pytest.mark.parametrize(
    "kind", ["duplicate_id", "unknown_anchor", "unknown_behavior", "missing_marker"]
)
def test_ambiguous_drawing_geometry_is_rejected(kind):
    plan, transform, before, after = drawing_plan(drawing_workbook())
    root = deepcopy(plan.roots[DRAWING_PART])
    if kind == "duplicate_id":
        nodes = root.findall(".//xdr:cNvPr", NS)
        nodes[1].set("id", nodes[0].get("id"))
    elif kind == "unknown_anchor":
        root[0].tag = f"{{{XDR}}}unknown"
    elif kind == "unknown_behavior":
        root[0].set("editAs", "unknown")
    else:
        marker = root[0].find("xdr:from", NS)
        marker.remove(marker.find("xdr:row", NS))
    with pytest.raises(ValueError):
        shift_drawing(root, transform, before, after)
