"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

# ============================================================================
# Docx Tools
# ============================================================================


class TestPDFValidation:
    """Tests for PDF validation in document_service."""

    async def test_invalid_pdf_header(self, temp_dir: Path) -> None:
        """Document service rejects files without %PDF- header."""
        from src.application.document_service import DocumentService

        fake_pdf = temp_dir / "fake.pdf"
        fake_pdf.write_bytes(b"NOT A PDF FILE CONTENT")

        mock_repo = MagicMock()
        mock_extractor = MagicMock()
        service = DocumentService(repository=mock_repo, pdf_extractor=mock_extractor)

        result = await service._ingest_single(str(fake_pdf))
        assert not result.success
        assert "PDF" in result.error or "header" in result.error

    async def test_valid_pdf_header(self, temp_dir: Path) -> None:
        """Document service accepts files with %PDF- header."""
        from src.application.document_service import DocumentService

        valid_pdf = temp_dir / "valid.pdf"
        # Minimal valid-header PDF (extraction will fail but header passes)
        valid_pdf.write_bytes(b"%PDF-1.4 minimal content")

        mock_repo = MagicMock()
        mock_repo.save_markdown.return_value = temp_dir / "content.md"
        mock_repo.get_doc_dir.return_value = temp_dir
        mock_extractor = MagicMock()
        mock_extractor.extract_text.side_effect = Exception("Not a real PDF")

        service = DocumentService(repository=mock_repo, pdf_extractor=mock_extractor)

        result = await service._ingest_single(str(valid_pdf))
        # Header passed, but extraction fails — error should be about extraction, not header
        assert not result.success
        assert "header" not in (result.error or "").lower()
