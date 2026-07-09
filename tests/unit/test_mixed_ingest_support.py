"""Unit tests for mixed-format (PDF + DOCX/DOC/ODT/ODS) batch ingestion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities import IngestResult
from src.presentation.tools.mixed_ingest_support import (
    build_mixed_ingest_handler,
    classify_document_path,
    format_counts,
    is_mixed_or_non_pdf_batch,
)


class TestClassifyDocumentPath:
    def test_classifies_pdf(self) -> None:
        assert classify_document_path("/papers/study.pdf") == "pdf"
        assert classify_document_path("/papers/STUDY.PDF") == "pdf"

    def test_classifies_docx_family(self) -> None:
        assert classify_document_path("/reports/summary.docx") == "docx"
        assert classify_document_path("/reports/legacy.doc") == "docx"
        assert classify_document_path("/reports/legacy.odt") == "docx"
        assert classify_document_path("/reports/legacy.ods") == "docx"

    def test_classifies_unknown_extension_as_unsupported(self) -> None:
        assert classify_document_path("/notes/readme.txt") == "unsupported"
        assert classify_document_path("/data/archive") == "unsupported"


class TestIsMixedOrNonPdfBatch:
    def test_all_pdf_batch_is_not_mixed(self) -> None:
        assert is_mixed_or_non_pdf_batch(["a.pdf", "b.pdf"]) is False

    def test_any_docx_makes_batch_mixed(self) -> None:
        assert is_mixed_or_non_pdf_batch(["a.pdf", "b.docx"]) is True

    def test_any_unsupported_makes_batch_mixed(self) -> None:
        assert is_mixed_or_non_pdf_batch(["a.pdf", "b.txt"]) is True

    def test_all_docx_batch_is_mixed(self) -> None:
        assert is_mixed_or_non_pdf_batch(["a.docx", "b.doc"]) is True


def test_format_counts_tallies_each_classification() -> None:
    counts = format_counts(["a.pdf", "b.pdf", "c.docx", "d.txt"])
    assert counts == {"pdf": 2, "docx": 1, "unsupported": 1}


class TestBuildMixedIngestHandler:
    @pytest.mark.asyncio
    async def test_routes_each_file_to_its_engine_and_reports_progress(self) -> None:
        document_service = MagicMock()
        document_service.ingest = AsyncMock(
            return_value=[
                IngestResult(
                    doc_id="doc_pdf_1",
                    filename="study.pdf",
                    success=True,
                    backend="docling",
                )
            ]
        )
        docx_service = MagicMock()
        docx_service.ingest_docx = AsyncMock(
            return_value={"success": True, "doc_id": "docx_summary_1"}
        )
        reporter = MagicMock()
        reporter.report = AsyncMock()

        handler = build_mixed_ingest_handler(
            ["/papers/study.pdf", "/reports/summary.docx"],
            document_service=document_service,
            docx_service=docx_service,
        )
        result = await handler(reporter)

        assert result["success"] is True
        assert result["total"] == 2
        assert result["succeeded"] == 2
        assert result["failed"] == 0
        assert not result["failed_files"]
        docs_by_format = {doc["format"]: doc for doc in result["documents"]}
        assert docs_by_format["pdf"]["doc_id"] == "doc_pdf_1"
        assert docs_by_format["pdf"]["backend"] == "docling"
        assert docs_by_format["docx"]["doc_id"] == "docx_summary_1"
        assert docs_by_format["docx"]["backend"] == "docx"
        document_service.ingest.assert_awaited_once()
        docx_service.ingest_docx.assert_awaited_once_with("/reports/summary.docx")
        assert reporter.report.await_count == 2

    @pytest.mark.asyncio
    async def test_one_bad_file_does_not_abort_the_batch(self) -> None:
        """A failing/unsupported file must not prevent the rest from ingesting."""
        document_service = MagicMock()
        document_service.ingest = AsyncMock(
            return_value=[
                IngestResult(
                    doc_id="doc_pdf_1",
                    filename="good.pdf",
                    success=True,
                    backend="pymupdf",
                )
            ]
        )
        docx_service = MagicMock()
        docx_service.ingest_docx = AsyncMock(
            return_value={"success": False, "error": "corrupt docx"}
        )
        reporter = MagicMock()
        reporter.report = AsyncMock()

        handler = build_mixed_ingest_handler(
            ["/papers/good.pdf", "/reports/broken.docx", "/notes/readme.txt"],
            document_service=document_service,
            docx_service=docx_service,
        )
        result = await handler(reporter)

        # The batch job itself always completes; failures are per-file. The
        # caller (JobService._process_conversion_job) decides whether
        # `failed_files` should mark the whole job FAILED; this handler's
        # own contract is just "never raise, always report every outcome".
        assert result["success"] is True
        assert len(result["documents"]) == 1
        assert result["documents"][0]["doc_id"] == "doc_pdf_1"
        assert len(result["failed_files"]) == 2
        failed_by_file = {
            item["file"]: item["error"] for item in result["failed_files"]
        }
        assert failed_by_file["/reports/broken.docx"] == "corrupt docx"
        assert "Unsupported file type" in failed_by_file["/notes/readme.txt"]

    @pytest.mark.asyncio
    async def test_unexpected_exception_is_isolated_per_file(self) -> None:
        """An unhandled exception from an ingester must not crash the job."""
        document_service = MagicMock()
        document_service.ingest = AsyncMock(side_effect=RuntimeError("boom"))
        docx_service = MagicMock()
        reporter = MagicMock()
        reporter.report = AsyncMock()

        handler = build_mixed_ingest_handler(
            ["/papers/study.pdf"],
            document_service=document_service,
            docx_service=docx_service,
        )
        result = await handler(reporter)

        assert result["success"] is True
        assert result["failed_files"] == [
            {"file": "/papers/study.pdf", "error": "boom"}
        ]
