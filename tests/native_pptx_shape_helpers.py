"""Shared native shape CRUD requests and independently read revision references."""

from __future__ import annotations

import hashlib

from src.application.native_pptx_operations import attach_pptx_evidence
from src.domain.native_pptx import NativePptxReference, NativePptxShapeCreate
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_pptx_package import NativePptxPackage


def addition(data, *, region="slide", grouped=False):
    package = NativePptxPackage(data)
    slide = package.slides[0]
    part = next(part for kind, part in package.slide_regions(slide) if kind == region)
    container = {**slide, "part": part, "region": region}
    if grouped:
        group = next(
            record
            for record in NativePresentation().iter_shapes(data)
            if record["kind"] == "grpSp" and record["locator"]["part"] == part
        )
        container["group_shape_id"] = group["locator"]["shape_id"]
    return NativePptxShapeCreate.model_validate(
        {
            "container": container,
            "textbox": {
                "left": 100000,
                "top": 200000,
                "width": 1000000,
                "height": 500000,
                "paragraphs": [
                    [
                        {"text": "新增 µ", "bold": True, "font_size_pt": 24},
                        {"text": " preserved", "italic": True},
                    ],
                    [{"text": "Second paragraph"}],
                ],
            },
        }
    )


def reference(data, record, *, asset_id="file_" + "a" * 32):
    attach_pptx_evidence(record, asset_id, hashlib.sha256(data).hexdigest())
    return NativePptxReference.model_validate(record["evidence"])
