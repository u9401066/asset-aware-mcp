"""Patch worksheet DrawingML anchors and corresponding top-level transforms."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal

from src.domain.native_grid_geometry import GridPoint, relocate_axis

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid_geometry import (
        GeometryTransform,
        GridAxisMetrics,
        GridPlacement,
    )

XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"xdr": XDR, "a": DRAWING}
PAYLOADS = {
    "sp": "spPr/a:xfrm",
    "pic": "spPr/a:xfrm",
    "cxnSp": "spPr/a:xfrm",
    "grpSp": "grpSpPr/a:xfrm",
    "graphicFrame": "xfrm",
}


def _child(parent: etree._Element, name: str) -> etree._Element:
    children = parent.findall(f"{{{XDR}}}{name}")
    if len(children) != 1:
        raise ValueError("Missing or ambiguous native drawing anchor geometry")
    return children[0]


def _point(node: etree._Element, axis: str) -> GridPoint:
    key = "row" if axis == "row" else "col"
    return GridPoint(
        int(_child(node, key).text or ""), int(_child(node, key + "Off").text or "")
    )


def _write_point(node: etree._Element, axis: str, point: GridPoint) -> None:
    key = "row" if axis == "row" else "col"
    for name, value in ((key, point.index), (key + "Off", point.offset)):
        element = _child(node, name)
        if int(element.text or "") != value:
            element.text = str(value)


def _sync_transform(
    anchor: etree._Element, placement: GridPlacement, axis: str
) -> None:
    payloads = [
        (node, name) for name in PAYLOADS for node in anchor.findall(f"{{{XDR}}}{name}")
    ]
    if len(payloads) != 1:
        raise ValueError("Unsupported or ambiguous DrawingML object payload")
    payload, kind = payloads[0]
    path = "/".join(
        "xdr:" + part if ":" not in part else part for part in PAYLOADS[kind].split("/")
    )
    transforms = payload.findall(path, NS)
    if len(transforms) > 1:
        raise ValueError("Multiple DrawingML object transforms are ambiguous")
    if not transforms:
        return  # The container anchor remains authoritative for inherited transforms.
    transform = transforms[0]
    offset, extent = transform.find("a:off", NS), transform.find("a:ext", NS)
    if (
        kind == "graphicFrame"
        and extent is not None
        and all(int(extent.get(key, "0")) == 0 for key in ("cx", "cy"))
    ):
        return  # Excel chart frames commonly use an intentionally zero placeholder.
    coordinate, size = ("y", "cy") if axis == "row" else ("x", "cx")
    if offset is not None and placement.new_position != placement.old_position:
        offset.set(
            coordinate,
            str(
                int(offset.get(coordinate, ""))
                + placement.new_position
                - placement.old_position
            ),
        )
    if extent is not None and placement.new_extent != placement.old_extent:
        original = int(extent.get(size, ""))
        if placement.old_extent == 0:
            raise ValueError(
                "A collapsed source transform needs explicit visible-size reconciliation"
            )
        extent.set(
            size,
            str(
                (original * placement.new_extent + placement.old_extent // 2)
                // placement.old_extent
            ),
        )


def shift_drawing(
    root: etree._Element,
    transform: GeometryTransform,
    before: GridAxisMetrics,
    after: GridAxisMetrics,
) -> list[dict[str, Any]]:
    if root.tag != f"{{{XDR}}}wsDr":
        raise ValueError("Unsupported worksheet drawing namespace")
    ids = [node.get("id", "") for node in root.findall(".//xdr:cNvPr", NS)]
    if len(ids) > 10_000 or len(set(ids)) != len(ids):
        raise ValueError("Ambiguous drawing IDs or object inspection budget exceeded")
    receipts = []
    for anchor in root:
        if not isinstance(anchor.tag, str):
            continue
        if anchor.tag == f"{{{XDR}}}absoluteAnchor":
            continue
        if anchor.tag not in {f"{{{XDR}}}oneCellAnchor", f"{{{XDR}}}twoCellAnchor"}:
            raise ValueError("Unmodeled DrawingML anchor structure")
        start_node = _child(anchor, "from")
        start = _point(start_node, transform.edit.axis)
        end_node = None
        mode: Literal["twoCell", "oneCell", "absolute"]
        if anchor.tag == f"{{{XDR}}}twoCellAnchor":
            end_node = _child(anchor, "to")
            end = _point(end_node, transform.edit.axis)
            selected = anchor.get("editAs", "twoCell")
            if selected not in {"twoCell", "oneCell", "absolute"}:
                raise ValueError("Unknown DrawingML editAs behavior")
            mode = selected
        else:
            key = "cy" if transform.edit.axis == "row" else "cx"
            extent = int(_child(anchor, "ext").get(key, ""))
            if extent < 0:
                raise ValueError("Drawing extent cannot be negative")
            end = before.locate(before.absolute(start) + extent)
            mode = "oneCell"
        placement = relocate_axis(start, end, before, after, transform, mode=mode)
        _write_point(start_node, transform.edit.axis, placement.start)
        if end_node is not None:
            _write_point(end_node, transform.edit.axis, placement.end)
        _sync_transform(anchor, placement, transform.edit.axis)
        if (
            (start, end) != (placement.start, placement.end)
            or placement.old_position != placement.new_position
            or placement.old_extent != placement.new_extent
        ):
            receipts.append(
                {
                    "shape_ids": [
                        node.get("id") for node in anchor.findall(".//xdr:cNvPr", NS)
                    ],
                    "mode": mode,
                    "axis": transform.edit.axis,
                    "before_start": asdict(start),
                    "before_end": asdict(end),
                    **asdict(placement),
                }
            )
    return receipts
