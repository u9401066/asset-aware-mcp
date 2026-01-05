"""
Integration Tests for ETL Pipeline

Tests the complete document ingestion flow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.document_service import DocumentService
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.pdf_extractor import PyMuPDFExtractor


class TestDocumentServiceIntegration:
    """Integration tests for DocumentService."""

    @pytest.fixture
    def service(self, temp_dir: Path) -> DocumentService:
        """Create DocumentService with real implementations."""
        repository = FileStorage(base_dir=temp_dir)
        pdf_extractor = PyMuPDFExtractor()

        return DocumentService(
            repository=repository,
            pdf_extractor=pdf_extractor,
            knowledge_graph=None,  # Skip LightRAG for unit tests
        )

    @pytest.mark.asyncio
    async def test_ingest_nonexistent_file(self, service: DocumentService):
        """Test ingesting a non-existent file."""
        results = await service.ingest(["nonexistent.pdf"])

        assert len(results) == 1
        assert not results[0].success
        assert "not found" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_ingest_non_pdf_file(self, service: DocumentService, temp_dir: Path):
        """Test ingesting a non-PDF file."""
        # Create a text file
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("This is not a PDF")

        results = await service.ingest([str(txt_file)])

        assert len(results) == 1
        assert not results[0].success
        assert "not a pdf" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_list_empty_documents(self, service: DocumentService):
        """Test listing documents when none exist."""
        documents = await service.list_documents()

        assert documents == []

    @pytest.mark.asyncio
    async def test_get_manifest_nonexistent(self, service: DocumentService):
        """Test getting manifest for non-existent document."""
        manifest = await service.get_manifest("doc_nonexistent_abc123")

        assert manifest is None


class TestPDFExtractorIntegration:
    """Integration tests for PDF extractor (requires actual PDF)."""

    @pytest.fixture
    def extractor(self) -> PyMuPDFExtractor:
        """Create PDF extractor."""
        return PyMuPDFExtractor()

    def test_extract_nonexistent_pdf(self, extractor: PyMuPDFExtractor):
        """Test extracting from non-existent PDF raises error."""
        with pytest.raises(RuntimeError):  # PyMuPDF raises RuntimeError
            extractor.extract_text(Path("nonexistent.pdf"))
