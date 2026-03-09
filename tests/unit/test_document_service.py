"""Unit tests for DocumentService CRUD and PDF→DOCX conversion helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

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
async def test_delete_document_adds_kg_warning() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True
    knowledge_graph = MagicMock()
    knowledge_graph.is_available = True

    service = DocumentService(
        repository=repository,
        pdf_extractor=MagicMock(),
        knowledge_graph=knowledge_graph,
    )

    result = await service.delete_document("doc_123")

    assert result["success"] is True
    assert result["warnings"]
    assert "Knowledge graph entries were not removed" in result["warnings"][0]


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
