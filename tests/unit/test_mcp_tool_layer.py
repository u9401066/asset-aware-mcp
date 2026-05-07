"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

import asyncio
import hashlib
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

    async def test_save_docx_failure_includes_warnings(self) -> None:
        """save_docx returns diagnostic warnings on failure."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.save_docx = AsyncMock(
                return_value={
                    "success": False,
                    "error": "shape mismatch",
                    "warnings": ["Table t001 row count changed"],
                }
            )
            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx("doc123", "# edited content")
            assert "Table t001 row count changed" in result

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

    async def test_save_docx_forwards_track_change_options(self) -> None:
        """save_docx can opt into native Word Track Changes."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.save_docx = AsyncMock(
                return_value={
                    "success": True,
                    "output_path": "/data/doc123/output.docx",
                    "integrity": "OK",
                    "track_changes": True,
                    "revision_author": "AI Reviewer",
                    "track_change_blocks": 1,
                    "revision_sidecar_path": "/data/doc123/revisions.jsonl",
                    "revision_records": 2,
                }
            )
            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx(
                "doc123",
                "# content",
                track_changes=True,
                revision_author="AI Reviewer",
            )

            assert "追蹤修訂" in result
            assert "revisions.jsonl" in result
            assert "2 records" in result
            call_args = mock_svc.save_docx.await_args
            assert call_args.kwargs["track_changes"] is True
            assert call_args.kwargs["revision_author"] == "AI Reviewer"

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

    async def test_save_docx_warns_when_pending_table_context_is_skipped(self) -> None:
        """Skipped pending TableContext merges must be visible to the caller."""
        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch("src.presentation.tools.docx_tools.table_service") as mock_table_svc,
            patch("src.presentation.tools.docx_tools.dfm_table_bridge") as mock_bridge,
        ):
            ir = DocxIR(doc_id="doc123", source_path="workspace/test.docx")
            ir.add_block(
                DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="old")
            )
            tc = TableContext(
                id="tbl_ctx",
                intent="summary",
                title="T",
                columns=[ColumnDef(name="A", type="text")],
                rows=[{"A": "new"}],
                source_doc_id="doc123",
                source_block_id="missing-table",
            )

            mock_table_svc._tables = {tc.id: tc}
            mock_svc._load_ir.return_value = ir
            mock_svc.parser.parse.return_value = MagicMock(errors=[])
            mock_svc.parser.apply_edits.return_value = ir
            mock_bridge.apply_table_context_to_ir.side_effect = ValueError(
                "block missing-table not found"
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

            assert "tbl_ctx" in result
            assert "block missing-table not found" in result
            call_args = mock_svc.save_docx.await_args
            assert call_args.args[1] == "inline dfm"

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

    async def test_docx_validate_roundtrip_rejects_output_escape(
        self, tmp_path: Path
    ) -> None:
        """docx_validate_roundtrip keeps rebuilt artifacts inside the doc dir."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            doc_dir = tmp_path / "docx_123"
            doc_dir.mkdir()
            (doc_dir / "original.docx").write_bytes(b"docx")

            mock_svc.repository.get_doc_dir.return_value = doc_dir
            mock_svc._load_ir.return_value = {"doc_id": "docx_123"}

            from src.presentation.tools.docx_tools import docx_validate_roundtrip

            result = await docx_validate_roundtrip(
                "docx_123", output_path="../escape.docx"
            )

            assert "❌" in result
            assert "document directory" in result
            mock_svc.adapter.ir_to_docx.assert_not_called()

    async def test_docx_table_from_context_rejects_cross_document_context(
        self,
    ) -> None:
        """docx_table_from_context refuses TableContext from another doc."""
        with patch("src.presentation.tools.docx_tools.table_service") as mock_table_svc:
            tc = TableContext(
                id="tbl_ctx",
                intent="summary",
                title="T",
                columns=[ColumnDef(name="A", type="text")],
                rows=[{"A": "new"}],
                source_doc_id="docx_other",
                source_block_id="t001",
            )
            mock_table_svc._tables = {tc.id: tc}

            from src.presentation.tools.docx_tools import docx_table_from_context

            result = await docx_table_from_context("docx_123", "t001", tc.id)

            assert "❌" in result
            assert "docx_other" in result

    async def test_docx_table_from_context_updates_all_dfm_artifacts(
        self, tmp_path: Path
    ) -> None:
        """docx_table_from_context keeps content.dfm/content.md/format.yaml in sync."""
        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch("src.presentation.tools.docx_tools.table_service") as mock_table_svc,
            patch("src.presentation.tools.docx_tools.dfm_table_bridge") as mock_bridge,
            patch("src.infrastructure.dfm_renderer.DfmRenderer") as mock_renderer_cls,
        ):
            doc_dir = tmp_path / "docx_123"
            doc_dir.mkdir()
            ir = DocxIR(doc_id="docx_123", source_path="workspace/test.docx")
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
                source_doc_id="docx_123",
                source_block_id="t001",
            )
            mock_table_svc._tables = {tc.id: tc}
            mock_svc._load_ir.return_value = ir
            mock_svc.repository.get_doc_dir.return_value = doc_dir

            def apply_table(ir_obj, block_id, _table_ctx):
                ir_obj.find_block(block_id).content = "| A |\n| --- |\n| new |"
                return ir_obj

            mock_bridge.apply_table_context_to_ir.side_effect = apply_table
            renderer = mock_renderer_cls.return_value
            renderer.render.return_value = "dfm text"
            renderer.render_split.return_value = ("md text", "yaml text")

            from src.presentation.tools.docx_tools import docx_table_from_context

            result = await docx_table_from_context("docx_123", "t001", tc.id)

            assert "✅" in result
            assert (doc_dir / "content.dfm").read_text(encoding="utf-8") == "dfm text"
            assert (doc_dir / "content.md").read_text(encoding="utf-8") == "md text"
            assert (doc_dir / "format.yaml").read_text(encoding="utf-8") == "yaml text"
            mock_svc._backup_before_overwrite.assert_called_once_with(doc_dir)
            mock_svc._save_ir.assert_called_once_with(ir, doc_dir / "ir.json")


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

    async def test_parse_pdf_structure_reports_missing_marker_backend(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure returns actionable install guidance when marker is absent."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.domain.marker_errors import MarkerBackendUnavailable
        from src.presentation.tools import document_tools

        monkeypatch.setattr(document_tools.settings, "data_dir", tmp_path / "data")
        monkeypatch.setattr(document_tools.pdf_extractor, "get_page_count", lambda _: 1)
        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=MarkerBackendUnavailable("No module named 'marker'")),
        )

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            async_mode=False,
        )

        assert "Marker Backend Not Available" in result
        assert "uv sync --extra marker" in result
        assert "virtual environment" in result

    async def test_parse_pdf_structure_reports_marker_resource_limit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure gives chunk/fallback guidance for catchable OOM errors."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        marker = MagicMock()
        marker.parse.side_effect = RuntimeError("CUDA out of memory")

        monkeypatch.setattr(document_tools.settings, "data_dir", tmp_path / "data")
        monkeypatch.setattr(document_tools.pdf_extractor, "get_page_count", lambda _: 1)
        monkeypatch.setattr(document_tools, "get_marker_extractor", lambda: marker)

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            async_mode=False,
        )

        assert "Marker Resource Limit" in result
        assert "marker_max_pages_per_chunk=1" in result
        assert "use_marker=False" in result

    async def test_parse_pdf_structure_reports_invalid_page_range_before_work(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(document_tools.pdf_extractor, "get_page_count", lambda _: 1)

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            page_ranges=["2"],
            async_mode=False,
        )

        assert "Invalid PDF or page range" in result

    async def test_parse_pdf_structure_defaults_to_background_marker_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure must return quickly instead of loading Marker inline."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=AssertionError("Marker should load in the job")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_parse", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.parse_pdf_structure(str(pdf_path))

        assert "job_parse" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        args, kwargs = mock_jobs.create_ingest_job.await_args
        assert args[0] == [str(pdf_path)]
        assert kwargs["parameters"]["use_marker"] is True
        assert kwargs["parameters"]["page_ranges"] == []

    async def test_search_source_location_no_blocks(self) -> None:
        """search_source_location returns error when blocks.json missing."""
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_blocks.return_value = None
            from src.presentation.tools.document_tools import (
                search_source_location,
            )

            result = await search_source_location("doc_123", "test query")
            assert "❌" in result

    async def test_find_evidence_spans_returns_span_asset_ref(self) -> None:
        """find_evidence_spans returns citation-ready span refs."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "x" * 40 + "Needle guidance reduced complications."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 2,
                "text": "Needle guidance reduced complications.",
                "metadata": {"line_start": 5, "line_end": 6},
            }
        ]

        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Needle guidance reduced complications.",
            block_id="blk_1",
            page=2,
            line_start=5,
            line_end=6,
            char_start=40,
            char_end=78,
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_123", "reduced")

        assert span.span_id in result
        assert "AssetRef" in result
        assert '"source_type": "span"' in result
        assert '"char_range"' in result

    async def test_find_evidence_spans_rebuilds_stale_citation_index(self) -> None:
        """find_evidence_spans rebuilds cached spans when markdown changed."""
        from src.domain.citation import EvidenceSpan

        markdown = "New exact evidence sentence.\n"
        old_span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(b"old markdown").hexdigest(),
            span_kind="sentence",
            text="Old cached sentence.",
            block_id="blk_old",
        )
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "New exact evidence sentence.",
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [old_span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_123", "New exact")

        assert "New exact evidence sentence." in result
        mock_repo.save_citation_index.assert_called_once()
        saved_spans = mock_repo.save_citation_index.call_args.args[1]
        assert saved_spans
        assert (
            saved_spans[0].source_revision_id
            == hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        )

    async def test_verify_citation_ref_detects_valid_span(self) -> None:
        """verify_citation_ref validates quote hash and source revision."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Exact quote for verification."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]

        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Exact quote for verification.",
            block_id="blk_1",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        ref = {
            "source_type": "span",
            "doc_id": "doc_123",
            "span_id": span.span_id,
            "source_revision_id": span.source_revision_id,
            "locator_version": span.locator_version,
            "block_id": span.block_id,
            "page": span.page,
            "line_range": [span.line_start, span.line_end],
            "char_range": [span.char_start, span.char_end],
            "byte_range": [span.byte_start, span.byte_end],
            "quote": span.text,
            "quote_sha256": span.text_sha256,
        }
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import verify_citation_ref

            result = await verify_citation_ref(ref)

        assert "verified" in result
        assert span.span_id in result

    async def test_verify_citation_ref_detects_locator_mismatch(self) -> None:
        """verify_citation_ref rejects stale or fabricated locator fields."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "0123456789Exact quote for verification."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "Exact quote for verification.",
                "metadata": {"line_start": 2, "line_end": 3},
            }
        ]

        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Exact quote for verification.",
            block_id="blk_1",
            page=1,
            line_start=2,
            line_end=3,
            char_start=10,
            char_end=39,
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        ref = {
            "source_type": "span",
            "doc_id": "doc_123",
            "span_id": span.span_id,
            "source_revision_id": span.source_revision_id,
            "locator_version": "citation-span-v0",
            "block_id": "wrong_block",
            "page": 9,
            "line_range": [20, 21],
            "char_range": [0, 4],
            "byte_range": [0, 4],
            "quote": span.text,
            "quote_sha256": span.text_sha256,
        }
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import verify_citation_ref

            result = await verify_citation_ref(ref)

        assert "mismatch" in result.lower()
        assert "locator_version mismatch" in result
        assert "block_id mismatch" in result
        assert "page mismatch" in result
        assert "line_range mismatch" in result
        assert "char_range mismatch" in result
        assert "byte_range mismatch" in result

    async def test_find_evidence_spans_rebuilds_when_blocks_metadata_changes(
        self,
    ) -> None:
        """find_evidence_spans rebuilds cached spans when block locators drift."""
        from src.domain.citation import EvidenceSpan

        markdown = "Stable evidence sentence.\n"
        old_span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Stable evidence sentence.",
            block_id="blk_1",
            page=9,
            line_start=99,
            line_end=100,
        )
        old_span.locator_source_sha256 = "old-blocks-hash"
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "Stable evidence sentence.",
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [old_span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_123", "Stable evidence")

        assert "**Page:** 1" in result
        mock_repo.save_citation_index.assert_called_once()

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

    async def test_ingest_documents_sync_reports_context_progress(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """ingest_documents emits MCP progress for synchronous ETL."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
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
            marker_max_pages_per_chunk=0,
            extract_figures=True,
            page_ranges=None,
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
            from src.presentation.tools import document_tools

            monkeypatch.setattr(
                document_tools.pdf_extractor,
                "get_page_count",
                MagicMock(return_value=1),
            )

            result = await document_tools.ingest_documents(
                [str(pdf_path)], async_mode=False, ctx=fake_ctx
            )

        assert "Processed" in result
        assert fake_ctx.report_progress.await_count >= 3
        assert fake_ctx.log.await_count >= 2

    async def test_ingest_documents_sync_marker_is_forced_to_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A sync Marker request should become a job before any model load."""
        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=AssertionError("Marker should load in the job")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_marker", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.ingest_documents(
            ["workspace/test.pdf"],
            async_mode=False,
            use_marker=True,
        )

        assert "job_marker" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_async_marker_does_not_load_marker_in_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Async Marker job creation must not block on Marker model loading."""
        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=AssertionError("Marker should load in the job")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_async_marker", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.ingest_documents(
            ["workspace/test.pdf"],
            async_mode=True,
            use_marker=True,
        )

        assert "job_async_marker" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_sync_uncountable_pdf_forces_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If page counting fails, the sync path must fail safe to a job."""
        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools.pdf_extractor,
            "get_page_count",
            MagicMock(side_effect=RuntimeError("cannot count")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_uncountable", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("uncountable PDFs should not run synchronously")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            ["workspace/test.pdf"],
            async_mode=False,
        )

        assert "job_uncountable" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_sync_large_pdf_forces_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Large PDFs should not run in the synchronous MCP request path."""
        pdf_path = tmp_path / "large.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(document_tools, "SYNC_INGEST_FILE_SIZE_MB_LIMIT", 0)
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_large", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("large PDFs should not run synchronously")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)],
            async_mode=False,
        )

        assert "job_large" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_async_passes_use_marker_to_job(self) -> None:
        """ingest_documents async job preserves Marker tuning parameters."""
        with (
            patch("src.presentation.tools.document_tools.job_service") as mock_jobs,
            patch(
                "src.presentation.tools.document_tools.get_marker_extractor"
            ) as mock_marker,
        ):
            mock_jobs.create_ingest_job = AsyncMock(
                return_value=MagicMock(job_id="job_123", estimated_duration_seconds=10)
            )
            mock_marker.return_value = MagicMock()
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(
                ["workspace/test.pdf"],
                async_mode=True,
                use_marker=True,
                marker_max_pages_per_chunk=200,
                extract_figures=False,
                page_ranges=["1-50", "100-120"],
            )

        assert "job_123" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"] == {
            "use_marker": True,
            "ocr_enabled": False,
            "ocr_language": "eng",
            "rotate_pages": False,
            "deskew": False,
            "marker_max_pages_per_chunk": 200,
            "extract_figures": False,
            "page_ranges": ["1-50", "100-120"],
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
            "marker_max_pages_per_chunk": 0,
            "extract_figures": True,
            "page_ranges": [],
        }

    async def test_ingest_documents_async_reports_job_creation_limit(self) -> None:
        """ingest_documents returns an MCP error instead of raising when job queue is full."""
        with patch("src.presentation.tools.document_tools.job_service") as mock_jobs:
            mock_jobs.create_ingest_job = AsyncMock(
                side_effect=RuntimeError("Too many concurrent jobs")
            )
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(["workspace/test.pdf"], async_mode=True)

        assert "Could Not Create ETL Job" in result
        assert "Too many concurrent jobs" in result

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

    async def test_ingest_job_failure_is_not_marked_completed(self) -> None:
        """Failed file results must not be reported as a green completed job."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        class MemoryJobStore:
            def __init__(self) -> None:
                self.jobs: dict[str, Job] = {}

            async def create(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def get(self, job_id: str) -> Job | None:
                return self.jobs.get(job_id)

            async def update(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

        class FailingDocumentService:
            async def ingest(self, *_args, **_kwargs):
                return [
                    IngestResult(
                        doc_id="",
                        filename="bad.pdf",
                        success=False,
                        error="bad pdf",
                    )
                ]

        store = MemoryJobStore()
        job = Job(
            job_id="job_test_failure",
            job_type=JobType.INGEST_PDF,
            input_files=["bad.pdf"],
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=FailingDocumentService(),  # type: ignore[arg-type]
        )

        await service._process_ingest_job(job.job_id)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert stored.error == "1/1 file(s) failed during ingestion"
        assert stored.result is not None
        assert stored.result["files_failed"] == 1
        assert stored.result["failed_files"] == [
            {"file": "bad.pdf", "error": "bad pdf"}
        ]

    async def test_cancel_job_waits_for_running_task_cleanup(self) -> None:
        """cancel_job should not return while the task is still unwinding."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        class MemoryJobStore:
            def __init__(self) -> None:
                self.jobs: dict[str, Job] = {}

            async def create(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def get(self, job_id: str) -> Job | None:
                return self.jobs.get(job_id)

            async def update(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

        cleanup_seen = False
        started = asyncio.Event()

        async def long_running() -> None:
            nonlocal cleanup_seen
            try:
                started.set()
                await asyncio.sleep(3600)
            finally:
                cleanup_seen = True

        store = MemoryJobStore()
        job = Job(
            job_id="job_cancel_wait",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=8),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)
        task = asyncio.create_task(long_running())
        await started.wait()
        service._running_tasks[job.job_id] = task

        assert await service.cancel_job(job.job_id) is True

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.CANCELLED
        assert task.done()
        assert cleanup_seen
        assert job.job_id not in service._running_tasks

    async def test_process_ingest_job_cleans_running_task_when_job_missing(
        self,
    ) -> None:
        """A deleted/corrupt job file must not leak a concurrency slot."""
        from src.application.job_service import JobService

        class EmptyJobStore:
            async def get(self, _job_id: str):
                return None

        service = JobService(job_store=EmptyJobStore())  # type: ignore[arg-type]
        current_task = asyncio.current_task()
        assert current_task is not None
        service._running_tasks["job_missing"] = current_task  # type: ignore[assignment]

        await service._process_ingest_job("job_missing")

        assert "job_missing" not in service._running_tasks


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
