"""Corrupt writers, orphan forms, opaque dependencies and bounded execution."""

from __future__ import annotations

import io
import json
import multiprocessing
import os

import pikepdf
import pytest

from src.domain.native_pdf import NativePdfCreate, NativePdfInsert
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_pdf_process import ProcessNativePdf
from tests.native_pdf_helpers import build_pdf, page_reference, rewrite


@pytest.mark.parametrize("target", ["page", "metadata", "attachment"])
def test_pdf_writer_corruption_fails_before_revision(target, monkeypatch):
    from src.infrastructure import native_pdf_checks

    data = build_pdf()
    save = native_pdf_checks.save_pdf

    def corrupt(pdf, version=""):
        original = save(pdf, version)

        def alter(p):
            if target == "page":
                p.pages[0].obj.Contents = p.make_stream(b"BT /F 12 Tf (tampered) Tj ET")
            elif target == "metadata":
                p.docinfo.Title = "tampered"
            else:
                p.attachments["original.txt"] = b"tampered attachment"

        return rewrite(original, alter)

    monkeypatch.setattr(native_pdf_checks, "save_pdf", corrupt)
    with pytest.raises(ValueError, match=r"graph changed|properties changed"):
        NativePdf().reorder(data, [page_reference(data, i) for i in (2, 0, 1)])


def test_orphan_copied_form_is_rejected_even_with_widget_appearance(monkeypatch):
    original = pikepdf.Pdf.add_pages_from
    data = build_pdf(forms=True)
    refs = [page_reference(data, i) for i in range(3)]

    def orphan(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        self.Root.AcroForm.Fields = pikepdf.Array()
        return result

    monkeypatch.setattr(pikepdf.Pdf, "add_pages_from", orphan)
    request = NativePdfCreate.model_validate(
        {"name": "orphan.pdf", "pages": [{"reference": r.model_dump()} for r in refs]}
    )
    with pytest.raises(ValueError, match="missing, detached or changed"):
        NativePdf().create(request, {f"{refs[0].asset_id}:{refs[0].revision}": data})


def test_annotation_cycle_repair_is_required_and_reported(monkeypatch):
    from src.infrastructure import native_pdf_copy

    data = build_pdf(forms=True)
    ref = page_reference(data, 0)
    request = NativePdfCreate.model_validate(
        {"name": "forms.pdf", "pages": [{"reference": ref.model_dump()}]}
    )
    sources = {f"{ref.asset_id}:{ref.revision}": data}
    _, checks = NativePdf().create(request, sources)
    assert "relinked_copied_annotation_backreferences" in checks.repairs
    monkeypatch.setattr(native_pdf_copy, "repair_annotation_links", lambda *args: False)
    with pytest.raises(ValueError, match="source object graph"):
        NativePdf().create(request, sources)


def test_conflicting_field_copy_fails_without_renaming():
    data = build_pdf(forms=True)
    ref = page_reference(data, 0)
    request = NativePdfInsert.model_validate(
        {"position": 0, "pages": [{"reference": ref.model_dump()}]}
    )
    with pytest.raises(ValueError, match="rename fields"):
        NativePdf().insert(data, request, {f"{ref.asset_id}:{ref.revision}": data})


@pytest.mark.parametrize("key", ["StructTreeRoot", "OCProperties"])
def test_copy_rejects_unmodeled_document_integration(key):
    data = rewrite(build_pdf(), lambda p: setattr(p.Root, key, pikepdf.Dictionary()))
    ref = page_reference(data, 0)
    request = NativePdfCreate.model_validate(
        {"name": "unsupported.pdf", "pages": [{"reference": ref.model_dump()}]}
    )
    with pytest.raises(ValueError, match="document-level"):
        NativePdf().create(request, {f"{ref.asset_id}:{ref.revision}": data})


@pytest.mark.parametrize(
    "limit", ["MAX_GRAPH_NODES", "MAX_GRAPH_BYTES", "MAX_GRAPH_DEPTH"]
)
def test_graph_limits_fail_closed(limit, monkeypatch):
    from src.infrastructure import native_pdf_graph

    data = build_pdf()
    ref = page_reference(data, 0)
    monkeypatch.setattr(native_pdf_graph, limit, 1)
    with pytest.raises(ValueError, match="limit"):
        NativePdf().read_page(data, ref.locator)


def test_worker_timeout_and_parser_failure_do_not_leave_children():
    data = build_pdf()
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(ValueError, match="time limit"):
        ProcessNativePdf(timeout=0.000001).inspect(data)
    assert {p.pid for p in multiprocessing.active_children()} == before
    with pytest.raises(ValueError, match="failed"):
        ProcessNativePdf().inspect(b"not a PDF")
    assert {p.pid for p in multiprocessing.active_children()} == before


def _exit_worker(connection, operation, arguments):
    os._exit(12)


def test_worker_crash_is_a_bounded_error(monkeypatch):
    from src.infrastructure import native_pdf_process

    before = {p.pid for p in multiprocessing.active_children()}
    monkeypatch.setattr(native_pdf_process, "_worker", _exit_worker)
    with pytest.raises(ValueError, match="without a result"):
        ProcessNativePdf().inspect(build_pdf())
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_image_limit_returns_metadata_and_explicit_failure(monkeypatch):
    from src.presentation import native_pdf_response

    monkeypatch.setattr(
        native_pdf_response, "image_exceeds_response_limit", lambda _: True
    )
    result = native_pdf_response.native_pdf_image_response(
        {"success": True, "asset_id": "file_test", "image_png": b"png"}
    )
    assert len(result) == 1 and result[0].type == "text"
    payload = json.loads(result[0].text)
    assert not payload["success"] and payload["image_omitted"]
    assert payload["asset_id"] == "file_test" and "image_png" not in payload


def test_password_protection_is_not_silently_bypassed():
    with pikepdf.Pdf.open(io.BytesIO(build_pdf())) as pdf:
        output = io.BytesIO()
        pdf.save(output, encryption=pikepdf.Encryption(owner="owner", user="secret"))
    with pytest.raises(ValueError):
        NativePdf().inspect(output.getvalue())
