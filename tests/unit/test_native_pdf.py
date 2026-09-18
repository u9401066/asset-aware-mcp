"""Native page CRUD preserves mixed content and rejects unresolved dependencies."""

from __future__ import annotations

import io

import pikepdf
import pymupdf
import pytest

from src.domain.native_pdf import NativePdfCreate, NativePdfInsert, NativePdfPageEdit
from src.infrastructure.native_pdf import NativePdf
from tests.native_pdf_helpers import build_pdf, page_reference, pixels, rewrite


@pytest.mark.parametrize("feature", ["plain", "links", "forms", "labels"])
def test_native_pdf_reorder_with_document_features(feature):
    data = build_pdf(**({feature: True} if feature != "plain" else {}))
    adapter = NativePdf()
    refs = [page_reference(data, i) for i in (2, 0, 1)]
    changed, checks = adapter.reorder(data, refs)
    assert pixels(changed) == [pixels(data)[i] for i in (2, 0, 1)]
    assert checks.preserved_parts == 3
    with pymupdf.open(stream=changed, filetype="pdf") as pdf:
        assert pdf.embfile_get("original.txt") == b"exact attachment\n"
        assert pdf.metadata["title"] == "Preserve this metadata"
        if feature == "links":
            assert pdf[1].get_links()[0]["page"] == 2
            assert pdf.get_toc()[0][2] == 3
        if feature == "forms":
            assert next(pdf[1].widgets()).field_value == "preserved value"
    if feature == "labels":
        before = adapter.inspect(data)["pages"]
        assert [p["label"] for p in adapter.inspect(changed)["pages"]] == [
            before[i]["label"] for i in (2, 0, 1)
        ]


@pytest.mark.parametrize("forms", [False, True])
def test_pdf_create_by_copying_complete_pages_and_blank(forms):
    data = build_pdf(forms=forms, labels=True)
    refs = [page_reference(data, i) for i in range(3)]
    request = NativePdfCreate.model_validate(
        {
            "name": "composed.pdf",
            "pages": [{"reference": r.model_dump()} for r in refs] + [{"blank": {}}],
        }
    )
    copied, checks = NativePdf().create(
        request, {f"{refs[0].asset_id}:{refs[0].revision}": data}
    )
    assert pixels(copied)[:3] == pixels(data)
    assert len(checks.changes) == 4
    assert NativePdf().inspect(copied)["pages"][-1]["label"] == "4"
    assert checks.changes[-1]["source_reference"] == refs[-1].model_dump()
    with pymupdf.open(stream=copied, filetype="pdf") as pdf:
        assert pdf.metadata["title"] == ""
        if forms:
            assert next(pdf[0].widgets()).field_value == "preserved value"


def test_pdf_insert_delete_and_geometry_roundtrip():
    data = build_pdf()
    adapter = NativePdf()
    inserted, _ = adapter.insert(
        data,
        NativePdfInsert.model_validate(
            {"position": 1, "pages": [{"blank": {"width": 400, "height": 500}}]}
        ),
        {},
    )
    assert len(adapter.inspect(inserted)["pages"]) == 4
    deleted, _ = adapter.delete(inserted, [page_reference(inserted, 1)])
    assert pixels(deleted) == pixels(data)
    changed, report = adapter.edit(
        deleted,
        [
            NativePdfPageEdit(
                reference=page_reference(deleted, 0),
                rotation=90,
                crop_box=[10, 20, 390, 480],
            )
        ],
    )
    assert pixels(changed)[1:] == pixels(data)[1:]
    page = adapter.inspect(changed)["pages"][0]
    assert page["rotation"] == 90 and page["crop_box"] == [10, 20, 390, 480]
    assert report.preserved_parts == 2


@pytest.mark.parametrize("operation", ["delete", "copy"])
def test_pdf_rejects_dangling_link_destinations(operation):
    data = build_pdf(links=True)
    adapter = NativePdf()
    with pytest.raises(ValueError, match="unselected page"):
        if operation == "delete":
            adapter.delete(data, [page_reference(data, 1)])
        else:
            ref = page_reference(data, 0)
            request = NativePdfCreate.model_validate(
                {"name": "partial.pdf", "pages": [{"reference": ref.model_dump()}]}
            )
            adapter.create(request, {f"{ref.asset_id}:{ref.revision}": data})


@pytest.mark.parametrize(
    "kind", ["stale", "duplicate", "empty", "all_pages", "incomplete_reorder", "crop"]
)
def test_pdf_rejects_invalid_mutations(kind):
    data = build_pdf()
    adapter = NativePdf()
    ref = page_reference(data, 0)
    with pytest.raises(ValueError):
        if kind == "stale":
            adapter.delete(data, [ref.model_copy(update={"value_sha256": "0" * 64})])
        elif kind == "duplicate":
            adapter.delete(data, [ref, ref])
        elif kind == "empty":
            adapter.delete(data, [])
        elif kind == "all_pages":
            adapter.delete(data, [page_reference(data, i) for i in range(3)])
        elif kind == "incomplete_reorder":
            adapter.reorder(data, [ref])
        else:
            adapter.edit(
                data, [NativePdfPageEdit(reference=ref, crop_box=[-10, 0, 400, 500])]
            )


def test_pdf_rejects_signatures_and_xfa():
    data = build_pdf()
    for change in [
        lambda p: setattr(p.Root, "Perms", pikepdf.Dictionary()),
        lambda p: setattr(
            p.Root, "AcroForm", pikepdf.Dictionary(XFA=p.make_stream(b"<xfa/>"))
        ),
    ]:
        protected = rewrite(data, change)
        with pytest.raises(ValueError, match=r"Signed|XFA"):
            NativePdf().delete(protected, [page_reference(protected, 2)])


def test_pdf_rejects_encryption_without_silent_removal():
    with pikepdf.Pdf.open(io.BytesIO(build_pdf())) as pdf:
        output = io.BytesIO()
        pdf.save(output, encryption=pikepdf.Encryption(owner="owner", user=""))
    with pytest.raises(ValueError, match="Encrypted"):
        NativePdf().inspect(output.getvalue())
