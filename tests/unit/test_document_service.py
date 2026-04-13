"""Unit tests for DocumentService CRUD and PDF→DOCX conversion helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.document_service import DocumentService


@pytest.mark.asyncio
async def test_delete_document_success() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True

    service = DocumentService(repository=repository, pdf_extractor=MagicMock())

    result = await service.delete_document("doc_123")

    assert result == {
        "success": True,
        "doc_id": "doc_123",
        "filename": "paper.pdf",
        "warnings": [],
    }


@pytest.mark.asyncio
async def test_delete_document_removes_kg_entries() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True
    knowledge_graph = MagicMock()
    knowledge_graph.is_available = True
    knowledge_graph.delete_document = AsyncMock(
        return_value={"status": "success", "message": "deleted"}
    )

    service = DocumentService(
        repository=repository,
        pdf_extractor=MagicMock(),
        knowledge_graph=knowledge_graph,
    )

    result = await service.delete_document("doc_123")

    assert result["success"] is True
    assert result["warnings"] == []
    assert result["knowledge_graph_status"] == "success"
    knowledge_graph.delete_document.assert_awaited_once_with("doc_123")


@pytest.mark.asyncio
async def test_delete_document_warns_when_kg_delete_fails() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True
    knowledge_graph = MagicMock()
    knowledge_graph.is_available = True
    knowledge_graph.delete_document = AsyncMock(side_effect=RuntimeError("boom"))

    service = DocumentService(
        repository=repository,
        pdf_extractor=MagicMock(),
        knowledge_graph=knowledge_graph,
    )

    result = await service.delete_document("doc_123")

    assert result["success"] is True
    assert result["warnings"]
    assert "Knowledge graph deletion failed" in result["warnings"][0]


@pytest.mark.asyncio
async def test_convert_pdf_to_docx_rejects_fidelity_mode() -> None:
    service = DocumentService(repository=MagicMock(), pdf_extractor=MagicMock())

    result = await service.convert_pdf_to_docx("doc_123", mode="fidelity")

    assert result["success"] is False
    assert "content mode only" in result["error"]


@pytest.mark.asyncio
async def test_convert_pdf_to_docx_success(monkeypatch, tmp_path: Path) -> None:
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path
    repository.load_markdown.return_value = "# Title\n\nHello world"
    repository.load_manifest.return_value = MagicMock(
        title="Paper Title",
        assets=MagicMock(figures=[], tables=[MagicMock()]),
    )

    service = DocumentService(repository=repository, pdf_extractor=MagicMock())

    captured: dict[str, object] = {}

    def fake_build(markdown, manifest, output_path):
        captured["markdown"] = markdown
        captured["output_path"] = output_path

    monkeypatch.setattr(service, "_build_docx_from_markdown", fake_build)

    result = await service.convert_pdf_to_docx("doc_123")

    assert result == {
        "success": True,
        "doc_id": "doc_123",
        "output_path": str(tmp_path / "converted_from_pdf.docx"),
        "mode": "content",
        "figures_embedded": 0,
        "tables_found": 1,
    }
    assert captured["markdown"] == "# Title\n\nHello world"
    assert captured["output_path"] == tmp_path / "converted_from_pdf.docx"


@pytest.mark.asyncio
async def test_convert_pdf_to_pptx_rejects_fidelity_mode() -> None:
    service = DocumentService(repository=MagicMock(), pdf_extractor=MagicMock())

    result = await service.convert_pdf_to_pptx("doc_123", mode="fidelity")

    assert result["success"] is False
    assert "content mode only" in result["error"]


@pytest.mark.asyncio
async def test_convert_pdf_to_pptx_success(monkeypatch, tmp_path: Path) -> None:
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path
    repository.load_markdown.return_value = "# Slide 1\n\n- bullet"
    repository.load_manifest.return_value = MagicMock(
        title="Deck Title",
        filename="slides.pdf",
        assets=MagicMock(
            figures=[MagicMock(path=tmp_path / "fig1.png", caption="Cap")]
        ),
    )

    service = DocumentService(repository=repository, pdf_extractor=MagicMock())

    captured: dict[str, object] = {}

    def fake_build(markdown, manifest, output_path):
        captured["markdown"] = markdown
        captured["output_path"] = output_path
        return {"total_slides": 3, "figure_slides": 1}

    monkeypatch.setattr(service, "_build_pptx_from_markdown", fake_build)

    result = await service.convert_pdf_to_pptx("doc_123")

    assert result == {
        "success": True,
        "doc_id": "doc_123",
        "output_path": str(tmp_path / "converted_from_pdf.pptx"),
        "mode": "content",
        "slides_created": 3,
        "figure_slides": 1,
    }
    assert captured["markdown"] == "# Slide 1\n\n- bullet"
    assert captured["output_path"] == tmp_path / "converted_from_pdf.pptx"


@pytest.mark.asyncio
async def test_ingest_reports_progress_callback(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path / "doc_test"
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()
    extractor.extract_text.return_value = "# Title\n\nHello"
    extractor.get_page_count.return_value = 1
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    progress_events: list[tuple[int, int, str, str]] = []

    async def progress_callback(
        step: int, total: int, phase: str, message: str
    ) -> None:
        progress_events.append((step, total, phase, message))

    results = await service.ingest([str(pdf_path)], progress_callback=progress_callback)

    assert len(results) == 1
    assert results[0].success is True
    assert progress_events
    assert progress_events[-1][0] == progress_events[-1][1]
    assert progress_events[-1][2] == "Completed"


@pytest.mark.asyncio
async def test_ingest_overwrites_stale_original_pdf_copy(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fresh")
    doc_dir = tmp_path / "doc_fixed"
    doc_dir.mkdir()
    (doc_dir / "original.pdf").write_bytes(b"%PDF-1.4 stale")

    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()
    extractor.extract_text.return_value = "# Title\n\nHello"
    extractor.get_page_count.return_value = 1
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "src.application.document_service.DocId.generate",
        lambda *_args: MagicMock(value="doc_fixed"),
    )

    results = await service.ingest([str(pdf_path)])

    assert results[0].success is True
    assert (doc_dir / "original.pdf").read_bytes() == b"%PDF-1.4 fresh"
