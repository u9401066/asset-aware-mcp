"""Annotation identity is page/revision scoped; markup comments are not body text."""

from __future__ import annotations

import io

import pikepdf
import pymupdf
import pytest
from PIL import Image

from src.domain.native_pdf_annotations import (
    PdfAnnotationAppearance,
    PdfAnnotationLocator,
)
from src.infrastructure.native_pdf_annotation_factory import appearance_pdf
from src.infrastructure.native_pdf_annotations import (
    decompose_annotations,
    inspect_annotations,
    read_annotation,
)
from src.infrastructure.native_pdf_package import NativePdfPackage
from tests.native_pdf_helpers import build_pdf, rewrite


def test_complete_annotation_catalog_includes_popup_and_widget():
    source = build_pdf(forms=True, links=True)
    listing = inspect_annotations(source)
    records = decompose_annotations(source)
    assert listing["annotation_count"] == len(records) == 8
    assert {r["subtype"] for r in records} == {"/Text", "/Popup", "/Widget", "/Link"}
    note = next(r for r in records if r["contents"] == "Keep annotation 0")
    locator = PdfAnnotationLocator.model_validate(note["locator"])
    assert read_annotation(source, locator) == note
    assert note["relations"]["Popup"]
    assert note["native_graph"]["objects"]
    with pytest.raises(ValueError, match="locator"):
        read_annotation(source, locator.model_copy(update={"object_id": 9999}))


def test_direct_annotation_and_duplicate_names_remain_distinguishable():
    def add(pdf):
        page = pdf.pages[0]
        page.obj.Annots.append(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Annot,
                Subtype=pikepdf.Name.Text,
                Rect=pikepdf.Array([10, 20, 30, 40]),
                NM=pikepdf.String("duplicate"),
                Contents=pikepdf.String("直接批註 007 µg"),
            )
        )
        page.obj.Annots[0].NM = pikepdf.String("duplicate")

    source = rewrite(build_pdf(), add)
    records = decompose_annotations(source)
    direct = next(r for r in records if r["contents"] == "直接批註 007 µg")
    assert direct["locator"]["object_id"] == 0
    assert len([r for r in records if r["name"] == "duplicate"]) == 2


@pytest.mark.parametrize(
    "kind",
    [
        "Text",
        "FreeText",
        "Highlight",
        "Underline",
        "StrikeOut",
        "Squiggly",
        "Square",
        "Circle",
        "Line",
        "PolyLine",
        "Polygon",
        "Ink",
    ],
)
@pytest.mark.parametrize("page_index", [0, 1, 2])
def test_factory_native_geometry_and_actual_appearances(kind, page_index):
    geometry = {
        "Text": {"point": [0.2, 0.2]},
        "FreeText": {"rect": [0.1, 0.1, 0.8, 0.4], "text": "批註 007 µg <literal>"},
        "Square": {"rect": [0.1, 0.1, 0.8, 0.4]},
        "Circle": {"rect": [0.1, 0.1, 0.8, 0.4]},
        "Line": {"vertices": [[0.1, 0.1], [0.8, 0.4]]},
        "PolyLine": {"vertices": [[0.1, 0.1], [0.8, 0.4]]},
        "Polygon": {"vertices": [[0.1, 0.1], [0.8, 0.4], [0.2, 0.4]]},
        "Ink": {"strokes": [[[0.1, 0.1], [0.8, 0.4]]]},
    }.get(kind, {"quads": [[0.1, 0.1, 0.8, 0.1, 0.1, 0.2, 0.8, 0.2]]})
    spec = PdfAnnotationAppearance.model_validate({"kind": kind, **geometry})
    with NativePdfPackage(build_pdf()) as package:
        result = appearance_pdf(package.pdf.pages[page_index], spec)
    with pymupdf.open(stream=result, filetype="pdf") as document:
        page = document[0]
        annotation = next(page.annots())
        assert annotation.type[1] == kind
        assert page.get_pixmap().samples != page.get_pixmap(annots=False).samples
        if kind == "FreeText":
            assert annotation.info["content"] == geometry["text"]
            assert "批註" in annotation.get_text()
        if kind in {"Square", "Circle", "FreeText"}:
            rect = annotation.rect * page.rotation_matrix
            fractions = [
                rect.x0 / page.rect.width,
                rect.y0 / page.rect.height,
                rect.x1 / page.rect.width,
                rect.y1 / page.rect.height,
            ]
            assert fractions == pytest.approx(geometry["rect"], abs=0.01)
    with pikepdf.Pdf.open(io.BytesIO(result)) as generated:
        assert generated.pages[0].obj.Annots[0].AP.N.read_bytes()


@pytest.mark.parametrize(
    "spec",
    [
        {"kind": "Text", "point": [0.1, 0.2], "text": "unused"},
        {"kind": "FreeText", "rect": [0.8, 0.2, 0.1, 0.4]},
        {"kind": "Line", "vertices": [[0.1, 0.2]]},
        {"kind": "Highlight", "quads": [[-0.1] * 8]},
        {"kind": "Text", "point": [float("nan"), 0.2]},
    ],
)
def test_typed_geometry_rejects_ignored_fields_and_invalid_positions(spec):
    with pytest.raises(ValueError):
        PdfAnnotationAppearance.model_validate(spec)


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("unit", [1, 2])
def test_display_geometry_with_nonzero_origins_inherited_rotation_and_user_units(
    angle, unit
):
    def modify(pdf):
        page = pdf.pages[0]
        page.obj.MediaBox = pikepdf.Array([20, 30, 420, 530])
        page.obj.CropBox = pikepdf.Array([40, 50, 400, 510])
        page.obj.UserUnit = unit
        page.obj.Parent.Rotate = angle
        if "/Rotate" in page.obj:
            del page.obj.Rotate

    source = rewrite(build_pdf(), modify)
    spec = PdfAnnotationAppearance.model_validate(
        {"kind": "Square", "rect": [0.1, 0.2, 0.8, 0.7]}
    )
    with NativePdfPackage(source) as package:
        generated = appearance_pdf(package.pdf.pages[0], spec)
    record = next(
        r for r in decompose_annotations(generated) if r["subtype"] == "/Square"
    )
    assert record["display_geometry"]["rect"] == pytest.approx(
        [0.1, 0.2, 0.8, 0.7], abs=0.01
    )
    with pymupdf.open(stream=generated, filetype="pdf") as document:
        pix = document[0].get_pixmap()
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        positions = [
            i
            for i, color in enumerate(image.get_flattened_data())
            if color[0] > 150 and color[1] < 100 and color[2] < 100
        ]
        xs, ys = [i % pix.width for i in positions], [i // pix.width for i in positions]
        actual = [
            min(xs) / pix.width,
            min(ys) / pix.height,
            (max(xs) + 1) / pix.width,
            (max(ys) + 1) / pix.height,
        ]
        assert actual == pytest.approx([0.1, 0.2, 0.8, 0.7], abs=0.01)


def test_invalid_relation_is_reported_without_fabricating_a_target():
    source = rewrite(
        build_pdf(), lambda pdf: setattr(pdf.pages[0].obj.Annots[0], "IRT", 17)
    )
    record = next(
        r for r in decompose_annotations(source) if r["contents"] == "Keep annotation 0"
    )
    assert record["relations"]["IRT"] == []
    assert record["unresolved_relations"] == ["IRT"]
