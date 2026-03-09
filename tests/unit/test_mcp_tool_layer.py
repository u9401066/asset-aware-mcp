"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Docx Tools
# ============================================================================


class TestDocxTools:
    """Tests for docx_tools.py MCP functions."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self) -> None:
        """Patch dependencies for isolated testing."""
        self.mock_docx_service = MagicMock()
        self.mock_docx_validator = MagicMock()
        self.mock_dfm_table_bridge = MagicMock()
        self.mock_table_service = MagicMock()

    async def test_ingest_docx_file_not_found(self) -> None:
        """ingest_docx returns error for missing file."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.ingest_docx = AsyncMock(
                return_value={"success": False, "error": "File not found: /bad.docx"}
            )
            from src.presentation.tools.docx_tools import ingest_docx

            result = await ingest_docx("/bad.docx")
            assert "❌" in result
            assert (
                "失敗" in result
                or "not found" in result.lower()
                or "File not found" in result
            )

    async def test_ingest_docx_success(self) -> None:
        """ingest_docx returns formatted summary on success."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.ingest_docx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "docx_test_abc123",
                    "source": "test.docx",
                    "total_blocks": 10,
                    "editable_blocks": 8,
                    "protected_blocks": 2,
                    "assets": 3,
                    "dfm_path": "/data/docx_test_abc123/content.dfm",
                    "integrity": "OK",
                    "block_types": {"paragraph": 6, "table": 2, "heading": 2},
                }
            )
            from src.presentation.tools.docx_tools import ingest_docx

            result = await ingest_docx("/test.docx")
            assert "✅" in result
            assert "docx_test_abc123" in result
            assert "10" in result  # total_blocks

    async def test_get_docx_content_not_found(self) -> None:
        """get_docx_content returns error for unknown doc_id."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.get_dfm = AsyncMock(return_value=None)
            from src.presentation.tools.docx_tools import get_docx_content

            result = await get_docx_content("nonexistent")
            assert "❌" in result

    async def test_get_docx_content_full(self) -> None:
        """get_docx_content returns full DFM when no block_id."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.get_dfm = AsyncMock(return_value="# Test\n\nHello world")
            from src.presentation.tools.docx_tools import get_docx_content

            result = await get_docx_content("doc123")
            assert result == "# Test\n\nHello world"

    async def test_get_docx_content_block(self) -> None:
        """get_docx_content returns specific block as JSON."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.get_block_content = AsyncMock(
                return_value={"id": "p001", "type": "paragraph", "content": "Test"}
            )
            from src.presentation.tools.docx_tools import get_docx_content

            result = await get_docx_content("doc123", block_id="p001")
            parsed = json.loads(result)
            assert parsed["id"] == "p001"

    async def test_save_docx_failure(self) -> None:
        """save_docx returns error on failure."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.save_docx = AsyncMock(
                return_value={"success": False, "error": "IR not found"}
            )
            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx("doc123", "# edited content")
            assert "❌" in result

    async def test_save_docx_success(self) -> None:
        """save_docx returns success with path."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.save_docx = AsyncMock(
                return_value={
                    "success": True,
                    "output_path": "/data/doc123/output.docx",
                    "integrity": "OK",
                }
            )
            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx("doc123", "# content")
            assert "✅" in result
            assert "output.docx" in result

    async def test_list_docx_blocks_not_found(self) -> None:
        """list_docx_blocks returns error for unknown doc."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.list_blocks = AsyncMock(return_value=None)
            from src.presentation.tools.docx_tools import list_docx_blocks

            result = await list_docx_blocks("nonexistent")
            assert "❌" in result

    async def test_list_docx_blocks_empty(self) -> None:
        """list_docx_blocks handles empty doc."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.list_blocks = AsyncMock(return_value=[])
            from src.presentation.tools.docx_tools import list_docx_blocks

            result = await list_docx_blocks("doc123")
            assert "沒有" in result

    async def test_list_docx_blocks_success(self) -> None:
        """list_docx_blocks returns markdown table."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.list_blocks = AsyncMock(
                return_value=[
                    {
                        "id": "p001",
                        "type": "paragraph",
                        "editable": True,
                        "style": "Normal",
                        "preview": "Hello world",
                    },
                    {
                        "id": "t001",
                        "type": "table",
                        "editable": True,
                        "style": "TableGrid",
                        "preview": "Col1 | Col2",
                    },
                ]
            )
            from src.presentation.tools.docx_tools import list_docx_blocks

            result = await list_docx_blocks("doc123")
            assert "p001" in result
            assert "t001" in result
            assert "2 個區塊" in result

    async def test_list_docx_documents_success(self) -> None:
        """list_docx_documents returns markdown summary table."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.list_documents = AsyncMock(
                return_value=[
                    {
                        "doc_id": "docx_123",
                        "filename": "demo.docx",
                        "total_blocks": 7,
                        "has_output_docx": True,
                        "has_output_pdf": False,
                        "updated_at": "2026-02-10T08:00:00",
                    }
                ]
            )
            from src.presentation.tools.docx_tools import list_docx_documents

            result = await list_docx_documents()
            assert "docx_123" in result
            assert "demo.docx" in result
            assert "DOCX Documents" in result

    async def test_delete_docx_success(self) -> None:
        """delete_docx returns formatted summary on success."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.delete_docx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "docx_123",
                    "filename": "demo.docx",
                }
            )
            from src.presentation.tools.docx_tools import delete_docx

            result = await delete_docx("docx_123")
            assert "✅" in result
            assert "demo.docx" in result

    async def test_convert_docx_to_pdf_success(self) -> None:
        """convert_docx_to_pdf returns converted path."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.convert_to_pdf = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "docx_123",
                    "mode": "fidelity",
                    "output_path": "/workspace/output.pdf",
                }
            )
            from src.presentation.tools.docx_tools import convert_docx_to_pdf

            result = await convert_docx_to_pdf("docx_123")
            assert "✅" in result
            assert "output.pdf" in result

    async def test_convert_docx_to_doc_success(self) -> None:
        """convert_docx_to_doc returns converted path."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.convert_to_doc = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "docx_123",
                    "mode": "fidelity",
                    "output_path": "/workspace/output.doc",
                }
            )
            from src.presentation.tools.docx_tools import convert_docx_to_doc

            result = await convert_docx_to_doc("docx_123")
            assert "✅" in result
            assert "output.doc" in result

    async def test_docx_validate_roundtrip_strict(self, tmp_path: Path) -> None:
        """docx_validate_roundtrip forwards strict mode to validator."""
        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch("src.presentation.tools.docx_tools.docx_validator") as mock_validator,
        ):
            doc_dir = tmp_path / "docx_123"
            doc_dir.mkdir()
            (doc_dir / "original.docx").write_bytes(b"docx")

            mock_svc.repository.get_doc_dir.return_value = doc_dir
            mock_svc._load_ir.return_value = {"doc_id": "docx_123"}
            mock_svc.adapter.ir_to_docx.return_value = None

            report = MagicMock()
            report.to_markdown.return_value = "STRICT PASS"
            mock_validator.validate.return_value = report

            from src.presentation.tools.docx_tools import docx_validate_roundtrip

            result = await docx_validate_roundtrip("docx_123", strict=True)

            assert result == "STRICT PASS"
            mock_validator.validate.assert_called_once()
            _, kwargs = mock_validator.validate.call_args
            assert kwargs["strict"] is True


# ============================================================================
# Job Tools
# ============================================================================


class TestJobTools:
    """Tests for job_tools.py MCP functions."""

    async def test_get_job_status_not_found(self) -> None:
        """get_job_status returns error for unknown job."""
        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.get_job = AsyncMock(return_value=None)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_nonexistent")
            assert "❌" in result

    async def test_cancel_job_success(self) -> None:
        """cancel_job returns confirmation."""
        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.cancel_job = AsyncMock(return_value=True)
            from src.presentation.tools.job_tools import cancel_job

            result = await cancel_job("job_123")
            assert "🚫" in result

    async def test_cancel_job_not_found(self) -> None:
        """cancel_job returns error when job not found."""
        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.cancel_job = AsyncMock(return_value=False)
            from src.presentation.tools.job_tools import cancel_job

            result = await cancel_job("job_nonexistent")
            assert "❌" in result


# ============================================================================
# Document Tools
# ============================================================================


class TestDocumentTools:
    """Tests for document_tools.py MCP functions."""

    async def test_list_documents_empty(self) -> None:
        """list_documents returns help message when empty."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.list_documents = AsyncMock(return_value=[])
            from src.presentation.tools.document_tools import list_documents

            result = await list_documents()
            assert "ingest_documents" in result

    async def test_parse_pdf_structure_file_not_found(self) -> None:
        """parse_pdf_structure returns error for missing file."""
        from src.presentation.tools.document_tools import parse_pdf_structure

        result = await parse_pdf_structure("/nonexistent/file.pdf")
        assert "❌" in result

    async def test_search_source_location_no_blocks(self) -> None:
        """search_source_location returns error when blocks.json missing."""
        with patch("src.presentation.tools.document_tools.settings") as mock_settings:
            mock_settings.data_dir = Path("/tmp/nonexistent")  # noqa: S108
            from src.presentation.tools.document_tools import (
                search_source_location,
            )

            result = await search_source_location("doc123", "test query")
            assert "❌" in result

    async def test_delete_document_success(self) -> None:
        """delete_document returns formatted summary on success."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.delete_document = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "doc_123",
                    "filename": "paper.pdf",
                    "warnings": ["kg not removed"],
                }
            )
            from src.presentation.tools.document_tools import delete_document

            result = await delete_document("doc_123")
            assert "✅" in result
            assert "paper.pdf" in result
            assert "warning" in result

    async def test_convert_pdf_to_docx_success(self) -> None:
        """convert_pdf_to_docx returns output summary on success."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.convert_pdf_to_docx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "doc_123",
                    "mode": "content",
                    "output_path": "/workspace/converted.docx",
                    "figures_embedded": 2,
                    "tables_found": 1,
                }
            )
            from src.presentation.tools.document_tools import convert_pdf_to_docx

            result = await convert_pdf_to_docx("doc_123")
            assert "✅" in result
            assert "converted.docx" in result
            assert "figures_embedded" in result


# ============================================================================
# Table Tools
# ============================================================================


class TestTableTools:
    """Tests for table_tools.py MCP functions."""

    async def test_plan_table_schema_requires_question(self) -> None:
        """plan_table schema op requires question."""
        with patch("src.presentation.tools.table_tools.document_service"):
            from src.presentation.tools.table_tools import plan_table

            result = await plan_table("schema", question="")
            assert "❌" in result

    async def test_plan_table_schema_comparison(self) -> None:
        """plan_table suggests comparison intent for comparison keywords."""
        with patch("src.presentation.tools.table_tools.document_service"):
            from src.presentation.tools.table_tools import plan_table

            result = await plan_table("schema", question="比較三種藥物副作用")
            assert "comparison" in result

    async def test_plan_table_templates(self) -> None:
        """plan_table templates lists available templates."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.list_templates.return_value = [
                {
                    "name": "drug_comparison",
                    "title": "Drug Comparison",
                    "description": "Compare drugs",
                    "intent": "comparison",
                    "columns": [{"name": "Drug", "type": "text", "required": True}],
                }
            ]
            from src.presentation.tools.table_tools import plan_table

            result = await plan_table("templates")
            assert "drug_comparison" in result

    async def test_plan_table_unknown_operation(self) -> None:
        """plan_table returns error for unknown operation."""
        from src.presentation.tools.table_tools import plan_table

        result = await plan_table("unknown_op")
        assert "❌" in result

    async def test_table_manage_create_missing_params(self) -> None:
        """table_manage create requires intent, title, columns."""
        from src.presentation.tools.table_tools import table_manage

        result = await table_manage("create", title="Test")
        assert "❌" in result

    async def test_table_manage_list_empty(self) -> None:
        """table_manage list returns help when empty."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.list_tables.return_value = []
            from src.presentation.tools.table_tools import table_manage

            result = await table_manage("list")
            assert "table_manage" in result

    async def test_table_manage_unknown_operation(self) -> None:
        """table_manage returns error for unknown op."""
        from src.presentation.tools.table_tools import table_manage

        result = await table_manage("unknown_op")
        assert "❌" in result

    async def test_table_data_add_rows_missing(self) -> None:
        """table_data add_rows requires rows."""
        from src.presentation.tools.table_tools import table_data

        result = await table_data("add_rows", "tbl_123")
        assert "❌" in result

    async def test_table_data_get_row_missing_index(self) -> None:
        """table_data get_row requires positive row_index."""
        from src.presentation.tools.table_tools import table_data

        result = await table_data("get_row", "tbl_123")
        assert "❌" in result

    async def test_table_cite_add_missing_params(self) -> None:
        """table_cite add requires row_index, column_name, refs."""
        from src.presentation.tools.table_tools import table_cite

        result = await table_cite("add", "tbl_123")
        assert "❌" in result

    async def test_table_history_changes_missing_id(self) -> None:
        """table_history changes requires table_id."""
        from src.presentation.tools.table_tools import table_history

        result = await table_history("changes", "")
        assert "❌" in result

    async def test_table_draft_create_missing_title(self) -> None:
        """table_draft create requires title."""
        from src.presentation.tools.table_tools import table_draft

        result = await table_draft("create")
        assert "❌" in result


# ============================================================================
# Profile Tools
# ============================================================================


class TestProfileTools:
    """Tests for profile_tools.py MCP functions."""

    async def test_list_etl_profiles(self) -> None:
        """list_etl_profiles returns profile list."""
        from src.presentation.tools.profile_tools import list_etl_profiles

        result = await list_etl_profiles()
        assert "profiles" in result
        assert result["count"] >= 1
        assert any(p["name"] == "default" for p in result["profiles"])

    async def test_get_etl_profile_not_found(self) -> None:
        """get_etl_profile returns error for unknown profile."""
        from src.presentation.tools.profile_tools import get_etl_profile

        result = await get_etl_profile("nonexistent_profile")
        assert result["success"] is False
        assert "available" in result

    async def test_get_current_etl_profile(self) -> None:
        """get_current_etl_profile returns current profile info."""
        from src.presentation.tools.profile_tools import get_current_etl_profile

        result = await get_current_etl_profile()
        assert "name" in result


# ============================================================================
# Knowledge Tools
# ============================================================================


class TestKnowledgeTools:
    """Tests for knowledge_tools.py MCP functions."""

    async def test_export_knowledge_graph_disabled(self) -> None:
        """export_knowledge_graph shows error when LightRAG disabled."""
        with patch("src.presentation.tools.knowledge_tools.knowledge_graph", None):
            from src.presentation.tools.knowledge_tools import (
                export_knowledge_graph,
            )

            result = await export_knowledge_graph()
            assert "not enabled" in result.lower() or "Error" in result


# ============================================================================
# Server-level
# ============================================================================


class TestServerStartup:
    """Tests for server.py configuration."""

    def test_configure_logging(self) -> None:
        """configure_logging sets up handlers without error."""
        from src.presentation.server import configure_logging

        configure_logging()  # Should not raise

    def test_tool_count(self) -> None:
        """All 36 expected tools are registered."""
        from src.presentation.mcp_app import mcp

        registered = [t.name for t in mcp._tool_manager._tools.values()]
        assert len(registered) >= 36, (
            f"Expected >=36 tools, got {len(registered)}: {registered}"
        )


# ============================================================================
# Job Service — Concurrency Guard
# ============================================================================


class TestJobServiceConcurrency:
    """Tests for job concurrency limit."""

    async def test_concurrent_job_limit(self) -> None:
        """JobService raises RuntimeError when limit exceeded."""
        from src.application.job_service import JobService

        mock_store = AsyncMock()
        mock_store.create = AsyncMock()
        service = JobService(job_store=mock_store, max_concurrent_jobs=2)

        # Simulate 2 running tasks
        service._running_tasks = {"job_1": MagicMock(), "job_2": MagicMock()}

        with pytest.raises(RuntimeError, match="Too many concurrent jobs"):
            await service.create_ingest_job(["/test.pdf"])


# ============================================================================
# PDF Magic Byte Validation
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
