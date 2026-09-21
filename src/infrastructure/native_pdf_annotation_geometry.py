"""Describe native annotation geometry in the same displayed fractions used by edits."""

from __future__ import annotations

from typing import Any

import pikepdf
import pymupdf


def display_transforms(
    data: bytes, page_indices: set[int]
) -> dict[int, dict[str, Any]]:
    with pymupdf.open(stream=data, filetype="pdf") as document:
        if document.is_repaired:
            raise ValueError("Annotation geometry reader required PDF repair")
        result = {}
        for index in sorted(page_indices):
            page = document[index]
            if page.rect.is_empty or page.rect.is_infinite:
                raise ValueError("Annotation geometry has invalid page bounds")
            angle = page.rotation
            displayed = page.rect
            page.set_rotation(0)
            width, height = page.rect.width, page.rect.height
            rotation = pymupdf.Matrix(
                {
                    0: (1, 0, 0, 1, 0, 0),
                    90: (0, 1, -1, 0, height, 0),
                    180: (-1, 0, 0, -1, width, height),
                    270: (0, -1, 1, 0, 0, width),
                }[angle]
            )
            result[index] = {
                "width": displayed.width,
                "height": displayed.height,
                "matrix": list(page.transformation_matrix * rotation),
            }
            page.set_rotation(angle)
        return result


def display_geometry(
    annotation: pikepdf.Object, transform: dict[str, Any]
) -> dict[str, Any]:
    matrix = pymupdf.Matrix(transform["matrix"])

    def points(values: Any) -> list[float] | None:
        if not isinstance(values, pikepdf.Array) or len(values) % 2:
            return None
        positions = []
        for index in range(0, len(values), 2):
            value = (
                pymupdf.Point(float(values[index]), float(values[index + 1])) * matrix
            )
            positions.extend(
                [value.x / transform["width"], value.y / transform["height"]]
            )
        return positions

    result: dict[str, Any] = {
        "coordinate_system": "displayed CropBox fractions, top-left, after rotation; values outside 0..1 are not clipped",
        "page_width_points": transform["width"],
        "page_height_points": transform["height"],
    }
    rectangle = points(annotation.get("/Rect"))
    if rectangle is not None and len(rectangle) == 4:
        result["rect"] = [
            min(rectangle[0], rectangle[2]),
            min(rectangle[1], rectangle[3]),
            max(rectangle[0], rectangle[2]),
            max(rectangle[1], rectangle[3]),
        ]
    for native, key in (
        ("/QuadPoints", "quad_points"),
        ("/Vertices", "vertices"),
        ("/L", "line"),
    ):
        if native in annotation:
            result[key] = points(annotation[native])
    if "/InkList" in annotation and isinstance(annotation.InkList, pikepdf.Array):
        result["strokes"] = [points(stroke) for stroke in annotation.InkList]
    return result
