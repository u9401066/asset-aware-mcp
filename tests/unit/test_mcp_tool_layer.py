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

from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.domain.table_entities import ColumnDef, TableContext

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

    async def test_ingest_docx_reports_context_progress(self) -> None:
        """ingest_docx emits MCP progress when Context is injected."""
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.ingest_docx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "docx_test_abc123",
                    "source": "test.docx",
                    "total_blocks": 1,
                    "editable_blocks": 1,
                    "protected_blocks": 0,
                    "assets": 0,
                    "dfm_path": "/data/docx_test_abc123/content.dfm",
                    "integrity": "OK",
                }
            )
            from src.presentation.tools.docx_tools import ingest_docx

            await ingest_docx("/test.docx", ctx=fake_ctx)

        assert fake_ctx.report_progress.await_count >= 2
        assert fake_ctx.log.await_count >= 2

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

    async def test_save_docx_merges_inline_dfm_with_pending_table_context(self) -> None:
        """save_docx should merge editor DFM edits with pending TableContext changes."""
        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch("src.presentation.tools.docx_tools.table_service") as mock_table_svc,
            patch("src.presentation.tools.docx_tools.dfm_table_bridge") as mock_bridge,
        ):
            ir = DocxIR(doc_id="doc123", source_path="workspace/test.docx")
            ir.add_block(
                DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="old")
            )
            ir.add_block(
                DfmBlock(
                    id="t001",
                    block_type=DfmBlockType.TABLE,
                    content="| A |\n| --- |\n| old |",
                )
            )
            tc = TableContext(
                id="tbl_ctx",
                intent="summary",
                title="T",
                columns=[ColumnDef(name="A", type="text")],
                rows=[{"A": "new"}],
                source_doc_id="doc123",
                source_block_id="t001",
            )

            mock_table_svc._tables = {tc.id: tc}
            mock_svc._load_ir.return_value = ir
            mock_svc.parser.parse.return_value = MagicMock(errors=[])

            def apply_inline(ir_obj, _parse_result):
                ir_obj.find_block("p001").content = "editor text"
                return ir_obj

            def apply_table(ir_obj, block_id, table_ctx):
                ir_obj.find_block(block_id).content = "| A |\n| --- |\n| new |"
                return ir_obj

            mock_svc.parser.apply_edits.side_effect = apply_inline
            mock_bridge.apply_table_context_to_ir.side_effect = apply_table
            mock_svc.renderer.render.return_value = (
                "<!-- @b:p001 -->\neditor text\n\n"
                "<!-- dfm:table @b:t001 -->\n| A |\n| --- |\n| new |\n<!-- /dfm:table -->"
            )
            mock_svc.save_docx = AsyncMock(
                return_value={
                    "success": True,
                    "output_path": "/data/doc123/output.docx",
                    "integrity": "OK",
                }
            )

            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx("doc123", "inline dfm", force=True)

            assert "自動同步的表格變更" in result
            call_args = mock_svc.save_docx.await_args
            assert "editor text" in call_args.args[1]
            assert "| new |" in call_args.args[1]
            assert call_args.kwargs["from_md"] is False

    async def test_save_docx_merges_split_md_with_pending_table_context(
        self, tmp_path: Path
    ) -> None:
        """save_docx should merge from_md edits with pending TableContext changes."""
        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch("src.presentation.tools.docx_tools.table_service") as mock_table_svc,
            patch("src.presentation.tools.docx_tools.dfm_table_bridge") as mock_bridge,
        ):
            doc_dir = tmp_path / "doc123"
            doc_dir.mkdir()
            (doc_dir / "content.md").write_text("md body", encoding="utf-8")
            (doc_dir / "format.yaml").write_text(
                "doc_id: doc123\nblocks: {}\n", encoding="utf-8"
            )

            ir = DocxIR(doc_id="doc123", source_path="workspace/test.docx")
            ir.add_block(
                DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="old")
            )
            ir.add_block(
                DfmBlock(
                    id="t001",
                    block_type=DfmBlockType.TABLE,
                    content="| A |\n| --- |\n| old |",
                )
            )
            tc = TableContext(
                id="tbl_ctx",
                intent="summary",
                title="T",
                columns=[ColumnDef(name="A", type="text")],
                rows=[{"A": "split-new"}],
                source_doc_id="doc123",
                source_block_id="t001",
            )

            mock_table_svc._tables = {tc.id: tc}
            mock_svc._load_ir.return_value = ir
            mock_svc.repository.get_doc_dir.return_value = doc_dir
            mock_svc.integrity.check_split_consistency.return_value = MagicMock(
                error_count=0
            )
            mock_svc.parser.parse_split.return_value = MagicMock(errors=[])

            def apply_split(ir_obj, _parse_result):
                ir_obj.find_block("p001").content = "split text"
                return ir_obj

            def apply_table(ir_obj, block_id, table_ctx):
                ir_obj.find_block(block_id).content = "| A |\n| --- |\n| split-new |"
                return ir_obj

            mock_svc.parser.apply_edits.side_effect = apply_split
            mock_bridge.apply_table_context_to_ir.side_effect = apply_table
            mock_svc.renderer.render.return_value = (
                "<!-- @b:p001 -->\nsplit text\n\n"
                "<!-- dfm:table @b:t001 -->\n| A |\n| --- |\n| split-new |\n<!-- /dfm:table -->"
            )
            mock_svc.save_docx = AsyncMock(
                return_value={
                    "success": True,
                    "output_path": "/data/doc123/output.docx",
                    "integrity": "OK",
                }
            )

            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx("doc123", from_md=True)

            assert "自動同步的表格變更" in result
            call_args = mock_svc.save_docx.await_args
            assert "split text" in call_args.args[1]
            assert "split-new" in call_args.args[1]
            assert call_args.kwargs["from_md"] is False

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

    async def test_convert_pdf_to_pptx_success(self) -> None:
        """convert_pdf_to_pptx returns output summary on success."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.convert_pdf_to_pptx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "doc_123",
                    "mode": "content",
                    "output_path": "/workspace/converted.pptx",
                    "slides_created": 5,
                    "figure_slides": 2,
                }
            )
            from src.presentation.tools.document_tools import convert_pdf_to_pptx

            result = await convert_pdf_to_pptx("doc_123")
            assert "✅" in result
            assert "converted.pptx" in result

    async def test_ingest_documents_sync_reports_context_progress(self) -> None:
        """ingest_documents emits MCP progress for synchronous ETL."""
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        async def fake_ingest(
            file_paths,
            use_marker=False,
            progress_callback=None,
            ocr_enabled=False,
            ocr_language="eng",
            rotate_pages=False,
            deskew=False,
        ):
            assert progress_callback is not None
            await progress_callback(1, 4, "Extracting", "Extracting test.pdf")
            await progress_callback(4, 4, "Completed", "Finished test.pdf")
            return [
                MagicMock(
                    success=True,
                    filename="test.pdf",
                    doc_id="doc_123",
                    title="Test",
                    backend="pymupdf",
                    pages_processed=1,
                    tables_found=0,
                    figures_found=0,
                    sections_found=0,
                    processing_time_seconds=0.1,
                )
            ]

        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.ingest = AsyncMock(side_effect=fake_ingest)
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(
                ["workspace/test.pdf"], async_mode=False, ctx=fake_ctx
            )

        assert "Processed" in result
        assert fake_ctx.report_progress.await_count >= 3
        assert fake_ctx.log.await_count >= 2

    async def test_ingest_documents_async_passes_use_marker_to_job(self) -> None:
        """ingest_documents async job preserves use_marker in job parameters."""
        with patch("src.presentation.tools.document_tools.job_service") as mock_jobs:
            mock_jobs.create_ingest_job = AsyncMock(
                return_value=MagicMock(job_id="job_123", estimated_duration_seconds=10)
            )
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(
                ["workspace/test.pdf"], async_mode=True, use_marker=True
            )

        assert "job_123" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"] == {
            "use_marker": True,
            "ocr_enabled": False,
            "ocr_language": "eng",
            "rotate_pages": False,
            "deskew": False,
        }

    async def test_ingest_documents_async_passes_ocr_params_to_job(self) -> None:
        """ingest_documents async job preserves OCR parameters."""
        with patch("src.presentation.tools.document_tools.job_service") as mock_jobs:
            mock_jobs.create_ingest_job = AsyncMock(
                return_value=MagicMock(job_id="job_ocr", estimated_duration_seconds=10)
            )
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(
                ["workspace/test.pdf"],
                async_mode=True,
                ocr_enabled=True,
                ocr_language="chi_tra",
                rotate_pages=True,
                deskew=True,
            )

        assert "job_ocr" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"] == {
            "use_marker": False,
            "ocr_enabled": True,
            "ocr_language": "chi_tra",
            "rotate_pages": True,
            "deskew": True,
        }

    async def test_export_document_segmentation_success(self) -> None:
        """export_document_segmentation writes schema summary."""
        segmentation = MagicMock(
            doc_id="doc_123",
            source_backend="marker",
            segments=[
                MagicMock(
                    reading_order=1,
                    page_number=1,
                    segment_type="Text",
                    segment_id="seg_1",
                )
            ],
            page_count=3,
        )
        segmentation.page_count_summary.return_value = {1: 1}

        with patch(
            "src.presentation.tools.document_tools.segmentation_service"
        ) as mock_seg:
            mock_seg.save_document_segmentation = AsyncMock(
                return_value=Path("workspace/segmentation.json")
            )
            mock_seg.export_document_segmentation = AsyncMock(return_value=segmentation)
            from src.presentation.tools.document_tools import (
                export_document_segmentation,
            )

            result = await export_document_segmentation("doc_123")

        assert "Unified Segmentation Export" in result
        assert "segmentation.json" in result

    async def test_visualize_document_layout_returns_overlay(self) -> None:
        """visualize_document_layout returns text and image payload."""
        segmentation = MagicMock(segments=[MagicMock()], doc_id="doc_123")
        overlay = MagicMock(
            image_base64="ZmFrZQ==",
            width=1200,
            height=1600,
            output_path="workspace/layout.png",
        )

        with (
            patch(
                "src.presentation.tools.document_tools.segmentation_service"
            ) as mock_seg,
            patch(
                "src.presentation.tools.document_tools.layout_visualizer"
            ) as mock_visualizer,
            patch("src.presentation.tools.document_tools.repository") as mock_repo,
        ):
            mock_seg.export_document_segmentation = AsyncMock(return_value=segmentation)
            mock_visualizer.render_page_overlay.return_value = overlay
            mock_repo.get_doc_dir.return_value = Path("workspace/doc_123")
            from src.presentation.tools.document_tools import visualize_document_layout

            result = await visualize_document_layout("doc_123", page=1)

        assert len(result) == 2
        assert result[0].type == "text"
        assert result[1].type == "image"

    async def test_ocr_pdf_document_success(self, tmp_path: Path) -> None:
        """ocr_pdf_document delegates to OCR processor and returns summary."""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        with patch("src.presentation.tools.document_tools.ocr_processor") as mock_ocr:
            mock_ocr.preprocess_pdf.return_value = MagicMock(
                output_path=tmp_path / "sample.ocr.pdf",
                language="eng",
                rotate_pages=True,
                deskew=False,
            )
            from src.presentation.tools.document_tools import ocr_pdf_document

            result = await ocr_pdf_document(
                str(pdf_path),
                language="eng",
                rotate_pages=True,
            )

        assert "OCR preprocessing completed" in result
        assert "sample.ocr.pdf" in result

    async def test_fetch_document_asset_reports_context_progress(self) -> None:
        """fetch_document_asset emits MCP progress when Context is injected."""
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        with patch(
            "src.presentation.tools.document_tools.asset_service"
        ) as mock_assets:
            mock_assets.fetch_asset = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    image_base64=None,
                    asset_id="sec_1",
                    page=1,
                    line_start=0,
                    line_end=3,
                    section_title="Introduction",
                    source_block_id="blk_0001",
                    text_content="section text",
                )
            )
            from src.presentation.tools.document_tools import fetch_document_asset

            result = await fetch_document_asset(
                "doc_123",
                "section",
                "sec_1",
                ctx=fake_ctx,
            )

        assert result[0].type == "text"
        assert "Line Range:" in result[0].text
        assert "L1-3" in result[0].text
        assert fake_ctx.report_progress.await_count >= 2


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

    async def test_consult_knowledge_graph_reports_progress(self) -> None:
        """consult_knowledge_graph emits MCP progress when Context is injected."""
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_structured = AsyncMock(
                return_value={"success": True, "answer": "answer", "references": []}
            )
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph("test", ctx=fake_ctx)

        assert result == {"success": True, "answer": "answer", "references": []}
        assert fake_ctx.report_progress.await_count >= 2

    async def test_consult_knowledge_graph_forwards_new_query_options(self) -> None:
        """consult_knowledge_graph forwards include_references and user_prompt."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_structured = AsyncMock(return_value={"success": True})
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "test",
                mode="mix",
                user_prompt="Summarize as bullets",
                include_references=True,
            )

        assert result == {"success": True}
        mock_svc.query_structured.assert_awaited_once_with(
            "test",
            mode="mix",
            user_prompt="Summarize as bullets",
            include_references=True,
        )

    async def test_consult_knowledge_graph_supports_data_mode(self) -> None:
        """consult_knowledge_graph can return retrieval-only structured data."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_data = AsyncMock(
                return_value={"success": True, "answer": None}
            )
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "test",
                response_mode="data",
            )

        assert result == {"success": True, "answer": None}
        mock_svc.query_data.assert_awaited_once_with(
            "test",
            mode="hybrid",
            user_prompt=None,
        )

    async def test_consult_knowledge_graph_supports_text_mode(self) -> None:
        """consult_knowledge_graph can still return plain text when requested."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query = AsyncMock(return_value="plain answer")
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "test",
                response_mode="text",
            )

        assert result == "plain answer"
        mock_svc.query.assert_awaited_once_with(
            "test",
            mode="hybrid",
            user_prompt=None,
            include_references=False,
        )

    async def test_consult_knowledge_graph_rejects_invalid_response_mode(self) -> None:
        """consult_knowledge_graph should fail fast on invalid response_mode."""
        from src.presentation.tools.knowledge_tools import consult_knowledge_graph

        with pytest.raises(ValueError, match="response_mode must be one of"):
            await consult_knowledge_graph("test", response_mode="yaml")


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
        """All 43 expected tools are registered."""
        from src.presentation.mcp_app import mcp

        registered = [t.name for t in mcp._tool_manager._tools.values()]
        assert len(registered) >= 43, (
            f"Expected >=43 tools, got {len(registered)}: {registered}"
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
