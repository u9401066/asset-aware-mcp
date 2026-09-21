"""Independent native objects and rendered pixels prove annotation edits stay scoped."""

from __future__ import annotations

import hashlib
import io

import pikepdf
import pymupdf
import pytest

from src.domain.native_pdf_annotations import (
    PdfAnnotationReference,
    PdfAnnotationsUpdate,
)
from src.infrastructure.native_pdf_annotation_edits import edit_annotations
from src.infrastructure.native_pdf_annotations import decompose_annotations
from src.infrastructure.native_pdf_graph import graph_digest
from tests.native_pdf_helpers import build_pdf, page_reference, pixels, rewrite


def reference(data, text="Keep annotation 0"):
    record = next(r for r in decompose_annotations(data) if r["contents"] == text)
    return PdfAnnotationReference.model_validate(
        {
            "asset_id": "file_" + "a" * 32,
            "revision": hashlib.sha256(data).hexdigest(),
            "locator": record["locator"],
            "value_sha256": graph_digest(record),
        }
    ).model_dump()


def update(data, edits):
    return edit_annotations(data, PdfAnnotationsUpdate.model_validate({"edits": edits}))


def body_pixels(data):
    with pymupdf.open(stream=data, filetype="pdf") as document:
        return [p.get_pixmap(annots=False).samples for p in document]


def test_metadata_preserves_foreign_appearance_and_native_page_content():
    source = build_pdf(forms=True, links=True, labels=True)
    changed, report = update(
        source,
        [
            {
                "op": "update",
                "reference": reference(source),
                "metadata": {
                    "contents": "VERIFIED 批註 007 µg -0.50 mg/L",
                    "author": "user",
                },
            }
        ],
    )
    assert pixels(source) == pixels(changed)
    assert body_pixels(source) == body_pixels(changed)
    assert report.changes[0]["after"]["contents"] == "VERIFIED 批註 007 µg -0.50 mg/L"
    with (
        pikepdf.Pdf.open(io.BytesIO(source)) as old,
        pikepdf.Pdf.open(io.BytesIO(changed)) as new,
    ):
        assert (
            old.pages[0].obj.Annots[0].AP.N.read_raw_bytes()
            == new.pages[0].obj.Annots[0].AP.N.read_raw_bytes()
        )

        def streams(page):
            value = page.obj.Contents
            parts = [value] if isinstance(value, pikepdf.Stream) else list(value)
            return [part.read_raw_bytes() for part in parts]

        assert [streams(p) for p in old.pages] == [streams(p) for p in new.pages]
    no_change, receipt = update(
        changed,
        [
            {
                "op": "update",
                "reference": reference(changed, "VERIFIED 批註 007 µg -0.50 mg/L"),
                "metadata": {"contents": "VERIFIED 批註 007 µg -0.50 mg/L"},
            }
        ],
    )
    assert no_change == changed and not receipt.changes
    assert "unchanged_native_graph_no_serialization" in receipt.checks


@pytest.mark.parametrize("page_index", [0, 1, 2])
def test_create_visible_freetext_then_replace_appearance_then_delete(page_index):
    source = build_pdf(forms=True, links=True, labels=True)
    created, report = update(
        source,
        [
            {
                "op": "create",
                "page_reference": page_reference(source, page_index).model_dump(),
                "appearance": {
                    "kind": "FreeText",
                    "rect": [0.1, 0.4, 0.8, 0.6],
                    "text": "Created 批註 007 µg",
                },
                "metadata": {"author": "user"},
            }
        ],
    )
    assert body_pixels(created) == body_pixels(source)
    assert pixels(created)[page_index] != pixels(source)[page_index]
    assert report.changes[0]["after"]["contents"] == "Created 批註 007 µg"
    edited, report = update(
        created,
        [
            {
                "op": "update",
                "reference": reference(created, "Created 批註 007 µg"),
                "replace_appearance": {
                    "kind": "FreeText",
                    "rect": [0.15, 0.4, 0.85, 0.7],
                    "text": "Corrected 批註 -0.50 mg/L",
                    "font_size": 18.0,
                },
            }
        ],
    )
    assert body_pixels(edited) == body_pixels(source)
    assert report.changes[0]["after"]["contents"] == "Corrected 批註 -0.50 mg/L"
    deleted, report = update(
        edited,
        [
            {
                "op": "delete",
                "reference": reference(edited, "Corrected 批註 -0.50 mg/L"),
                "scope": "annotation_and_owned_popup",
            }
        ],
    )
    assert pixels(deleted) == pixels(source)
    assert len(decompose_annotations(deleted)) == len(decompose_annotations(source))
    assert report.changes[0]["secure_erasure"] is False


def test_delete_note_and_owned_popup_preserves_other_notes():
    source = build_pdf()
    changed, report = update(
        source,
        [
            {
                "op": "delete",
                "reference": reference(source),
                "scope": "annotation_and_owned_popup",
            }
        ],
    )
    records = decompose_annotations(changed)
    assert len(records) == 4
    assert report.changes[0]["operation"] == "delete_annotation"
    assert not any(r["locator"]["page"]["page_index"] == 0 for r in records)
    assert body_pixels(changed) == body_pixels(source)
    assert pixels(changed)[1:] == pixels(source)[1:]


def test_all_batch_references_are_validated_before_any_mutation():
    source = build_pdf()
    page = page_reference(source, 0).model_dump()
    changed, _ = update(
        source,
        [
            {
                "op": "create",
                "page_reference": page,
                "appearance": {"kind": "Square", "rect": [0.1, 0.5, 0.2, 0.6]},
            }
            for _ in range(2)
        ],
    )
    assert len(decompose_annotations(changed)) > len(decompose_annotations(source))
    assert body_pixels(changed) == body_pixels(source)


@pytest.mark.parametrize(
    "kind",
    [
        "stale",
        "locked",
        "foreign_dependency",
        "reply",
        "shared",
        "signature",
        "rich_text",
    ],
)
def test_edits_reject_unapproved_scope_or_stale_evidence(kind):
    def modify(pdf):
        a = pdf.pages[0].obj.Annots[0]
        if kind == "locked":
            a.F = 128
        if kind == "foreign_dependency":
            pdf.Root.CustomAnnotationPointer = a
        if kind == "reply":
            pdf.pages[1].obj.Annots[0].IRT = a
        if kind == "shared":
            pdf.pages[1].obj.Annots.append(a)
        if kind == "signature":
            pdf.Root.Perms = pikepdf.Dictionary()
        if kind == "rich_text":
            a.RC = pikepdf.String("<p>Keep <b>format</b></p>")

    source = rewrite(build_pdf(), modify)
    ref = reference(source)
    if kind == "stale":
        ref["value_sha256"] = "0" * 64
    edit = {"op": "delete", "reference": ref, "scope": "annotation_and_owned_popup"}
    if kind == "rich_text":
        edit = {
            "op": "update",
            "reference": ref,
            "metadata": {"contents": "lost format"},
        }
    with pytest.raises(ValueError):
        update(source, [edit])


def test_reply_thread_deletion_requires_all_explicit_references():
    source = rewrite(
        build_pdf(),
        lambda pdf: setattr(
            pdf.pages[1].obj.Annots[0], "IRT", pdf.pages[0].obj.Annots[0]
        ),
    )
    changed, _ = update(
        source,
        [
            {
                "op": "delete",
                "reference": reference(source, text),
                "scope": "annotation_and_owned_popup",
            }
            for text in ("Keep annotation 0", "Keep annotation 1")
        ],
    )
    assert len(decompose_annotations(changed)) == 2


def test_freetext_content_cannot_be_changed_without_a_new_appearance():
    source = build_pdf()
    created, _ = update(
        source,
        [
            {
                "op": "create",
                "page_reference": page_reference(source, 0).model_dump(),
                "appearance": {
                    "kind": "FreeText",
                    "rect": [0.1, 0.3, 0.8, 0.5],
                    "text": "KEEP",
                },
            }
        ],
    )
    with pytest.raises(ValueError, match="appearance"):
        update(
            created,
            [
                {
                    "op": "update",
                    "reference": reference(created, "KEEP"),
                    "metadata": {"contents": "WRONG"},
                }
            ],
        )


def test_deletion_handles_indirect_annotation_arrays():
    source = rewrite(
        build_pdf(),
        lambda pdf: setattr(
            pdf.pages[0].obj, "Annots", pdf.make_indirect(pdf.pages[0].obj.Annots)
        ),
    )
    changed, _ = update(
        source,
        [
            {
                "op": "delete",
                "reference": reference(source),
                "scope": "annotation_and_owned_popup",
            }
        ],
    )
    assert len(decompose_annotations(changed)) == 4


def test_deletion_rejects_annotation_array_reused_outside_the_page():
    def modify(pdf):
        value = pdf.make_indirect(pdf.pages[0].obj.Annots)
        pdf.pages[0].obj.Annots = value
        pdf.Root.CustomArray = value

    source = rewrite(build_pdf(), modify)
    with pytest.raises(ValueError, match="dependency"):
        update(
            source,
            [
                {
                    "op": "delete",
                    "reference": reference(source),
                    "scope": "annotation_and_owned_popup",
                }
            ],
        )


def test_direct_annotation_update_receipt_follows_deleted_slots():
    def modify(pdf):
        pdf.pages[0].obj.Annots.append(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Annot,
                Subtype=pikepdf.Name.Text,
                Contents=pikepdf.String("DIRECT"),
                Rect=pikepdf.Array([10, 20, 30, 40]),
            )
        )

    source = rewrite(build_pdf(), modify)
    changed, report = update(
        source,
        [
            {
                "op": "delete",
                "reference": reference(source),
                "scope": "annotation_and_owned_popup",
            },
            {
                "op": "update",
                "reference": reference(source, "DIRECT"),
                "metadata": {"contents": "DIRECT UPDATED"},
            },
        ],
    )
    current = next(
        r for r in decompose_annotations(changed) if r["contents"] == "DIRECT UPDATED"
    )
    assert current["locator"]["annotation_index"] == 0
    assert report.changes[1]["after"] == current


def test_inverse_check_detects_accidental_page_stream_mutation(monkeypatch):
    import src.infrastructure.native_pdf_annotation_edits as module

    original = module._metadata

    def corrupt(annotation, metadata):
        original(annotation, metadata)
        annotation.P.Contents[0].write(b"% unintended body replacement\n")

    monkeypatch.setattr(module, "_metadata", corrupt)
    source = build_pdf()
    digest = hashlib.sha256(source).hexdigest()
    with pytest.raises(ValueError, match="outside the explicit"):
        update(
            source,
            [
                {
                    "op": "update",
                    "reference": reference(source),
                    "metadata": {"author": "user"},
                }
            ],
        )
    assert hashlib.sha256(source).hexdigest() == digest


def test_metadata_changes_preserve_independently_authored_native_appearance():
    def custom(pdf):
        annotation = pdf.pages[0].obj.Annots[0]
        stream = pdf.make_stream(b"0.2 0.5 0.8 rg 0 0 18 18 re f\n")
        stream.Type = pikepdf.Name.XObject
        stream.Subtype = pikepdf.Name.Form
        stream.BBox = pikepdf.Array([0, 0, 18, 18])
        stream.Resources = pikepdf.Dictionary()
        annotation.AP = pikepdf.Dictionary(N=stream)
        annotation.CustomMetadata = pikepdf.String("untouched")

    source = rewrite(build_pdf(), custom)
    changed, _ = update(
        source,
        [
            {
                "op": "update",
                "reference": reference(source),
                "metadata": {"subject": "review"},
            }
        ],
    )
    assert pixels(changed) == pixels(source)
    with pikepdf.Pdf.open(io.BytesIO(changed)) as pdf:
        annotation = pdf.pages[0].obj.Annots[0]
        assert str(annotation.CustomMetadata) == "untouched"
        assert annotation.AP.N.read_bytes() == b"0.2 0.5 0.8 rg 0 0 18 18 re f\n"


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_annotation_array_indirection_and_untouched_pages_are_preserved(operation):
    def modify(pdf):
        for page in pdf.pages:
            page.obj.Annots = pdf.make_indirect(page.obj.Annots)

    source = rewrite(build_pdf(), modify)
    edit = {"op": operation, "reference": reference(source)}
    if operation == "create":
        edit = {
            "op": "create",
            "page_reference": page_reference(source, 0).model_dump(),
            "appearance": {"kind": "Text", "point": [0.1, 0.5]},
        }
    elif operation == "update":
        edit["metadata"] = {"author": "user"}
    else:
        edit["scope"] = "annotation_and_owned_popup"
    changed, _ = update(source, [edit])
    with pikepdf.Pdf.open(io.BytesIO(changed)) as pdf:
        assert all(p.obj.Annots.is_indirect for p in pdf.pages)
    assert pixels(changed)[1:] == pixels(source)[1:]


def test_creation_does_not_detach_an_externally_shared_annotation_array():
    def modify(pdf):
        value = pdf.make_indirect(pdf.pages[0].obj.Annots)
        pdf.pages[0].obj.Annots = value
        pdf.Root.CustomArray = value

    source = rewrite(build_pdf(), modify)
    with pytest.raises(ValueError, match="dependency"):
        update(
            source,
            [
                {
                    "op": "create",
                    "page_reference": page_reference(source, 0).model_dump(),
                    "appearance": {"kind": "Text", "point": [0.1, 0.5]},
                }
            ],
        )


def test_parent_comment_update_keeps_cross_page_reply_links():
    source = rewrite(
        build_pdf(),
        lambda pdf: setattr(
            pdf.pages[1].obj.Annots[0], "IRT", pdf.pages[0].obj.Annots[0]
        ),
    )
    changed, _ = update(
        source,
        [
            {
                "op": "update",
                "reference": reference(source),
                "metadata": {"contents": "UPDATED PARENT"},
            }
        ],
    )
    assert pixels(changed) == pixels(source)
    with pikepdf.Pdf.open(io.BytesIO(changed)) as pdf:
        assert (
            pdf.pages[1].obj.Annots[0].IRT.objgen == pdf.pages[0].obj.Annots[0].objgen
        )
        assert str(pdf.pages[1].obj.Annots[0].IRT.Contents) == "UPDATED PARENT"


def test_owned_popup_lock_is_respected_during_parent_deletion():
    source = rewrite(
        build_pdf(), lambda pdf: setattr(pdf.pages[0].obj.Annots[0].Popup, "F", 128)
    )
    with pytest.raises(ValueError, match="locked owned"):
        update(
            source,
            [
                {
                    "op": "delete",
                    "reference": reference(source),
                    "scope": "annotation_and_owned_popup",
                }
            ],
        )
