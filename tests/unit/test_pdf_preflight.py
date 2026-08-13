"""Regression tests for safe PDF preflight and document-facade routing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf as fitz
import pytest

from src.domain.pdf_preflight import PDFPreflightError
from src.infrastructure.pymupdf_preflight import PyMuPDFPreflightInspector


def _write_fixture_pdf(tmp_path: Path) -> Path:
    image_path = tmp_path / "preflight-image.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 240, 240), False)
    pixmap.clear_with(180)
    pixmap.save(image_path)

    pdf_path = tmp_path / "preflight.pdf"
    document = fitz.open()

    native = document.new_page(width=300, height=400)
    native.insert_textbox(
        fitz.Rect(20, 20, 280, 180),
        " ".join(["Native searchable text supports reliable extraction."] * 10),
        fontsize=10,
    )

    sparse = document.new_page(width=300, height=400)
    sparse.insert_text((20, 40), "Short")

    image = document.new_page(width=300, height=400)
    image.insert_image(
        fitz.Rect(40, 80, 260, 300),
        filename=str(image_path),
        keep_proportion=False,
    )

    scanned = document.new_page(width=300, height=400)
    scanned.insert_image(
        scanned.rect,
        filename=str(image_path),
        keep_proportion=False,
    )

    hybrid = document.new_page(width=300, height=400)
    hybrid.insert_textbox(
        fitz.Rect(20, 20, 280, 150),
        " ".join(["Hybrid page keeps native text and a visual asset."] * 8),
        fontsize=9,
    )
    hybrid.insert_image(
        fitz.Rect(30, 180, 270, 360),
        filename=str(image_path),
        keep_proportion=False,
    )
    hybrid.set_rotation(90)

    document.save(pdf_path)
    document.close()
    return pdf_path


def test_preflight_emits_stable_provenance_locators_and_all_page_routes(
    tmp_path: Path,
) -> None:
    pdf_path = _write_fixture_pdf(tmp_path)

    report = PyMuPDFPreflightInspector(timeout_seconds=0).inspect(pdf_path)

    assert report.schema_version == "pdf-preflight-v1"
    assert report.status == "ok"
    assert report.source.sha256 == hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    assert report.coordinate_system.origin == "top-left"
    assert report.coordinate_system.page_number_base == 1
    assert report.coordinate_system.rotation_basis == "unrotated-cropbox"
    assert [page.locator.page_number for page in report.pages] == [1, 2, 3, 4, 5]
    assert [page.classification for page in report.pages] == [
        "native",
        "sparse",
        "image",
        "scanned",
        "hybrid",
    ]
    assert report.classification_counts.model_dump() == {
        "native": 1,
        "sparse": 1,
        "image": 1,
        "scanned": 1,
        "hybrid": 1,
    }
    assert report.pages[3].ocr_reasons == [
        "no_text",
        "image_dominant",
        "suspected_scanned_page",
    ]
    assert report.pages[4].ocr_recommended is False
    assert report.pages[4].recommended_engine == "docling"
    assert report.pages[4].locator.page_bbox == (0.0, 0.0, 300.0, 400.0)
    assert report.pages[4].locator.rotation_degrees == 90
    assert report.ocr_pages == [2, 3, 4]
    assert report.recommended_engine == "docling"


def test_blank_page_stays_sparse_without_wasting_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    page = PyMuPDFPreflightInspector(timeout_seconds=0).inspect(pdf_path).pages[0]

    assert page.classification == "sparse"
    assert page.metrics.text_characters == 0
    assert page.ocr_recommended is False
    assert page.ocr_reasons == []
    assert page.recommended_engine == "pymupdf"


def test_preflight_process_boundary_returns_validated_schema(tmp_path: Path) -> None:
    pdf_path = tmp_path / "isolated.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((40, 60), "Process isolated PDF preflight smoke test")
    document.save(pdf_path)
    document.close()

    report = PyMuPDFPreflightInspector(timeout_seconds=10).inspect(pdf_path)

    assert report.status == "ok"
    assert report.page_count == 1
    assert report.pages[0].locator.page_number == 1


def test_preflight_rejects_non_pdf_and_file_over_limit(tmp_path: Path) -> None:
    invalid = tmp_path / "not.pdf"
    invalid.write_bytes(b"not a pdf")

    with pytest.raises(PDFPreflightError) as invalid_error:
        PyMuPDFPreflightInspector(timeout_seconds=0).inspect(invalid)
    assert invalid_error.value.code == "invalid_pdf"

    pdf_path = _write_fixture_pdf(tmp_path)
    with pytest.raises(PDFPreflightError) as size_error:
        PyMuPDFPreflightInspector(
            timeout_seconds=0,
            max_file_bytes=pdf_path.stat().st_size - 1,
        ).inspect(pdf_path)
    assert size_error.value.code == "file_too_large"


async def test_document_preflight_op_returns_schema_without_new_public_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.tools import document_tools

    expected = {"schema_version": "pdf-preflight-v1", "status": "ok"}

    class _StubService:
        async def inspect(self, pdf_path: str) -> object:
            assert pdf_path == "paper.pdf"

            class _Result:
                @staticmethod
                def model_dump(*, mode: str) -> dict[str, str]:
                    assert mode == "json"
                    return expected

            return _Result()

    monkeypatch.setattr(document_tools, "pdf_preflight_service", _StubService())

    result = await document_tools.document(op="preflight", pdf_path="paper.pdf")

    assert result == expected


async def test_document_preflight_op_returns_stable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.tools import document_tools

    class _FailingService:
        async def inspect(self, pdf_path: str) -> object:
            raise PDFPreflightError("timeout", f"Timed out inspecting {pdf_path}")

    monkeypatch.setattr(document_tools, "pdf_preflight_service", _FailingService())

    result = await document_tools.document(op="preflight", pdf_path="paper.pdf")

    assert result == {
        "schema_version": "pdf-preflight-v1",
        "status": "error",
        "error_code": "timeout",
        "message": "Timed out inspecting paper.pdf",
    }


async def test_document_preflight_rejects_batch_file_paths_without_inspection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preflight is singular and must never silently inspect only batch item 0."""
    from src.presentation.tools import document_tools

    class _FailIfCalled:
        async def inspect(self, _pdf_path: str) -> object:
            raise AssertionError("preflight service must not inspect a batch fallback")

    monkeypatch.setattr(document_tools, "pdf_preflight_service", _FailIfCalled())

    result = await document_tools.document(
        op="preflight",
        file_paths=["first.pdf", "second.pdf"],
    )

    assert "accepts only pdf_path" in result
    assert "file_paths is a batch-ingest parameter" in result
