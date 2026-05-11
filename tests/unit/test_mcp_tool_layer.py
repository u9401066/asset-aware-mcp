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

    async def test_save_docx_keeps_successful_table_context_when_one_skips(
        self,
    ) -> None:
        """A stale pending TableContext must not discard successful table edits."""
        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch("src.presentation.tools.docx_tools.table_service") as mock_table_svc,
            patch("src.presentation.tools.docx_tools.dfm_table_bridge") as mock_bridge,
        ):
            ir = DocxIR(doc_id="doc123", source_path="workspace/test.docx")
            ir.add_block(
                DfmBlock(
                    id="t001",
                    block_type=DfmBlockType.TABLE,
                    content="| A |\n| --- |\n| old |",
                )
            )
            good = TableContext(
                id="tbl_good",
                intent="summary",
                title="Good",
                columns=[ColumnDef(name="A", type="text")],
                rows=[{"A": "new"}],
                source_doc_id="doc123",
                source_block_id="t001",
            )
            stale = TableContext(
                id="tbl_stale",
                intent="summary",
                title="Stale",
                columns=[ColumnDef(name="A", type="text")],
                rows=[{"A": "skip"}],
                source_doc_id="doc123",
                source_block_id="missing-table",
            )

            mock_table_svc._tables = {good.id: good, stale.id: stale}
            mock_svc._load_ir.return_value = ir
            mock_svc.parser.parse.return_value = MagicMock(errors=[])
            mock_svc.parser.apply_edits.return_value = ir

            def apply_table(ir_obj, block_id, _table_ctx):
                if block_id == "missing-table":
                    raise ValueError("block missing-table not found")
                ir_obj.find_block(block_id).content = "| A |\n| --- |\n| new |"
                return ir_obj

            mock_bridge.apply_table_context_to_ir.side_effect = apply_table
            mock_svc.renderer.render.return_value = "<!-- dfm:table @b:t001 -->\n| A |\n| --- |\n| new |\n<!-- /dfm:table -->"
            mock_svc.save_docx = AsyncMock(
                return_value={
                    "success": True,
                    "output_path": "/data/doc123/output.docx",
                    "integrity": "OK",
                }
            )

            from src.presentation.tools.docx_tools import save_docx

            result = await save_docx("doc123", "inline dfm", force=True)

            assert "TableContext" in result
            assert "tbl_stale" in result
            assert "block missing-table not found" in result
            call_args = mock_svc.save_docx.await_args
            assert "| new |" in call_args.args[1]

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
                        "metadata": {
                            "source_part": "word/document.xml",
                            "paragraph_index": 0,
                        },
                    },
                    {
                        "id": "t001",
                        "type": "table",
                        "editable": True,
                        "style": "TableGrid",
                        "preview": "Col1 | Col2",
                        "metadata": {
                            "source_part": "word/document.xml",
                            "table_index": 0,
                        },
                    },
                ]
            )
            from src.presentation.tools.docx_tools import list_docx_blocks

            result = await list_docx_blocks("doc123")
            assert "p001" in result
            assert "t001" in result
            assert "word/document.xml p#0" in result
            assert "word/document.xml t#0" in result
            assert "Col1 \\| Col2" in result
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

    async def test_list_docx_documents_escapes_pipe_cells(self) -> None:
        """list_docx_documents escapes table pipes in filenames."""
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.list_documents = AsyncMock(
                return_value=[
                    {
                        "doc_id": "docx_123",
                        "filename": "demo | pipe.docx",
                        "total_blocks": 7,
                        "has_output_docx": False,
                        "has_output_pdf": False,
                        "updated_at": "2026-02-10T08:00:00",
                    }
                ]
            )
            from src.presentation.tools.docx_tools import list_docx_documents

            result = await list_docx_documents()

        assert "demo \\| pipe.docx" in result

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

            result = await convert_docx_to_pdf("docx_123", async_mode=False)
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

            result = await convert_docx_to_doc("docx_123", async_mode=False)
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

    async def test_docx_op_routes_save(self) -> None:
        """docx(op='save') keeps the existing save_docx contract as its backend."""
        with patch(
            "src.presentation.tools.docx_tools.save_docx",
            new_callable=AsyncMock,
        ) as mock_save:
            mock_save.return_value = "saved"
            from src.presentation.tools.docx_tools import docx

            result = await docx(
                "save",
                doc_id="docx_123",
                dfm_content="dfm",
                output_path="out.docx",
                from_md=True,
                force=True,
                track_changes=True,
                revision_author="Reviewer",
            )

        assert result == "saved"
        mock_save.assert_awaited_once_with(
            "docx_123",
            dfm_content="dfm",
            output_path="out.docx",
            from_md=True,
            force=True,
            track_changes=True,
            revision_author="Reviewer",
            ctx=None,
        )

    async def test_docx_op_rejects_missing_doc_id(self) -> None:
        """docx(op='get') requires doc_id before delegating."""
        from src.presentation.tools.docx_tools import docx

        result = await docx("get")

        assert "doc_id is required" in result

    async def test_docx_table_op_routes_chart_data(self) -> None:
        """docx_table(op='chart_data') exposes chart extraction via one entrypoint."""
        with patch(
            "src.presentation.tools.docx_tools.docx_chart_data",
            new_callable=AsyncMock,
        ) as mock_chart:
            mock_chart.return_value = "chart"
            from src.presentation.tools.docx_tools import docx_table

            result = await docx_table(
                "chart_data",
                doc_id="docx_123",
                block_id="c001",
                register=False,
            )

        assert result == "chart"
        mock_chart.assert_awaited_once_with("docx_123", "c001", register=False)

    async def test_docx_table_op_rejects_unknown_operation(self) -> None:
        """docx_table(op, ...) fails closed for unsupported operations."""
        from src.presentation.tools.docx_tools import docx_table

        result = await docx_table("normalize", doc_id="docx_123", block_id="t001")

        assert "Unsupported docx_table op" in result

    async def test_docx_table_edit_plan_reports_structural_changes(self) -> None:
        """docx_table_edit_plan separates cell updates from row/column changes."""
        from src.presentation.tools import docx_tools

        block = DfmBlock(
            id="t001",
            block_type=DfmBlockType.TABLE,
            content="| A | B |\n|---|---|\n| 1 | 2 |\n",
        )
        ir = MagicMock()
        ir.find_block.return_value = block
        tc = TableContext(
            id="tbl_plan",
            intent="summary",
            title="Plan",
            columns=[
                ColumnDef(name="A", type="text"),
                ColumnDef(name="B", type="text"),
                ColumnDef(name="C", type="text"),
            ],
            rows=[{"A": "1", "B": "changed", "C": "new"}],
        )
        mock_table_service = MagicMock()
        mock_table_service._tables = {"tbl_plan": tc}

        with (
            patch("src.presentation.tools.docx_tools.docx_service") as mock_svc,
            patch(
                "src.presentation.tools.docx_tools.table_service", mock_table_service
            ),
        ):
            mock_svc._load_ir.return_value = ir

            result = await docx_tools.docx_table_edit_plan(
                "docx_123",
                "t001",
                table_id="tbl_plan",
            )

        assert "add_columns" in result
        assert "`update_cell`: 1" in result
        assert "review required" in result


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

    async def test_job_op_routes_existing_tools(self) -> None:
        """job(op, ...) provides one operation-based entrypoint for job CRUD."""
        with patch("src.presentation.tools.job_tools.get_job_status") as mock_status:
            mock_status.return_value = "job status"
            from src.presentation.tools.job_tools import job

            result = await job("get", job_id="job_123")

        assert result == "job status"
        mock_status.assert_awaited_once_with("job_123")

    async def test_job_op_rejects_unknown_operation(self) -> None:
        """job(op, ...) fails closed for unknown operations."""
        from src.presentation.tools.job_tools import job

        result = await job("archive", job_id="job_123")

        assert "Unsupported job op" in result

    async def test_job_op_rejects_missing_job_id_for_cancel(self) -> None:
        """job(op='cancel') requires a target job_id."""
        from src.presentation.tools.job_tools import job

        result = await job("cancel")

        assert "job_id is required" in result

    async def test_job_op_routes_cancel(self) -> None:
        """job(op='cancel') delegates to the legacy cancellation tool."""
        with patch("src.presentation.tools.job_tools.cancel_job") as mock_cancel:
            mock_cancel.return_value = "cancelled"
            from src.presentation.tools.job_tools import job

            result = await job("cancel", job_id="job_123")

        assert result == "cancelled"
        mock_cancel.assert_awaited_once_with("job_123")

    async def test_get_job_status_shows_backend_warnings_and_artifacts(self) -> None:
        """Completed jobs expose backend, warnings, artifacts, and next commands."""
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        job = Job(
            job_id="job_status_details",
            job_type=JobType.INGEST_PDF,
            status=JobStatus.COMPLETED,
            input_files=["paper.pdf"],
            output_doc_ids=["doc_123"],
            progress=JobProgress(total_steps=8, current_step=8, percentage=100),
            result={
                "documents": [
                    {
                        "file": "paper.pdf",
                        "doc_id": "doc_123",
                        "backend": "pymupdf_fallback",
                        "warnings": ["Marker was unavailable"],
                        "artifacts": {
                            "manifest": "data/doc_123/doc_123_manifest.json",
                            "markdown": "data/doc_123/doc_123_full.md",
                            "blocks": "data/doc_123/blocks.json",
                        },
                        "blocks_available": True,
                    }
                ],
                "warnings": ["Marker was unavailable"],
            },
        )

        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.get_job = AsyncMock(return_value=job)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_status_details")

        assert "pymupdf_fallback" in result
        assert "Marker was unavailable" in result
        assert "data/doc_123/blocks.json" in result
        assert 'export_document_segmentation("doc_123")' in result


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
        """parse_pdf_structure async_mode=False still returns a background job."""
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
            return_value=MagicMock(
                job_id="job_sync_parse", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            async_mode=False,
        )

        assert "job_sync_parse" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["operation"] == "parse_pdf_structure"
        assert kwargs["parameters"]["require_marker"] is True

    async def test_parse_pdf_structure_reports_marker_resource_limit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure reports ignored output_dir instead of running inline."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_output_dir", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            output_dir=str(tmp_path / "custom"),
        )

        assert "job_output_dir" in result
        assert "`output_dir` is ignored" in result

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
        assert kwargs["parameters"]["operation"] == "parse_pdf_structure"
        assert kwargs["parameters"]["require_marker"] is True
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

    async def test_find_evidence_spans_reports_empty_blocks_without_zero_byte_index(
        self, tmp_path: Path
    ) -> None:
        """Empty MarkerOutput blocks should not recreate a 0-byte citation index."""
        blocks = [
            {
                "block_id": "mk_1",
                "block_type": "MarkdownOutput",
                "page": 1,
                "text": "",
            }
        ]
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = []
            mock_repo.load_markdown.return_value = "# Abstract\n\nBody"
            mock_repo.load_blocks.return_value = blocks
            mock_repo.get_doc_dir.return_value = tmp_path
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_empty")

        assert "No citation-ready evidence spans" in result
        assert "did not contain citeable text" in result
        assert not (tmp_path / "citation_index.jsonl").exists()
        status = json.loads(
            (tmp_path / "citation_index.status.json").read_text(encoding="utf-8")
        )
        assert status["found"] == 0
        mock_repo.save_citation_index.assert_not_called()

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

    async def test_citation_bundle_exports_verified_entries(self) -> None:
        """citation_bundle returns AssetRefs plus structured verification."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Stable evidence for bundle export."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 3,
                "text": markdown,
                "metadata": {"line_start": 1, "line_end": 2},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_1",
            page=3,
            line_start=1,
            line_end=2,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_123",
                query="bundle",
                output_format="json",
            )

        assert result["success"] is True
        assert result["entries"][0]["asset_ref"]["span_id"] == span.span_id
        assert result["entries"][0]["verification"]["valid"] is True
        assert result["entries"][0]["locator_source_sha256"]
        assert result["entries"][0]["foam"]["block_anchor"].startswith("^spn-")
        assert result["entries"][0]["foam"]["wikilink"].startswith("[[doc_123#^spn-")

    async def test_citation_bundle_exports_foam_evidence_pack(self) -> None:
        """citation_bundle(output_format='foam') returns Foam-ready anchors."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Stable evidence for Foam promotion."
        blocks = [
            {
                "block_id": "blk_foam",
                "block_type": "Text",
                "page": 4,
                "text": markdown,
                "metadata": {"line_start": 2, "line_end": 3},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_foam",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_foam",
            page=4,
            line_start=2,
            line_end=3,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_foam",
                query="Foam",
                output_format="foam",
                citation_key="paper-key",
            )

        assert result.startswith("---\n")
        assert 'type: "evidence_pack"' in result
        assert "[[paper-key#^spn-" in result
        assert "![[paper-key#^spn-" in result
        assert "^spn-" in result
        assert span.source_revision_id in result
        assert span.text_sha256 in result
        assert '"source_type": "span"' in result

    async def test_citation_bundle_writes_foam_pack_and_index(
        self, tmp_path: Path
    ) -> None:
        """citation_bundle can persist a Foam evidence pack and index block."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Writable Foam evidence."
        blocks = [
            {
                "block_id": "blk_write",
                "block_type": "Text",
                "page": 2,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_write",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_write",
            page=2,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_write",
                output_format="foam",
                citation_key="paper-key",
                wiki_root=str(tmp_path),
                output_path="evidence/paper-key.md",
                index_path="Evidence Index.md",
                overwrite=True,
            )

        note_path = tmp_path / "evidence" / "paper-key.md"
        index_path = tmp_path / "Evidence Index.md"
        assert result["success"] is True
        assert Path(result["output_path"]) == note_path
        assert note_path.exists()
        assert index_path.exists()
        assert "[[paper-key#^spn-" in note_path.read_text(encoding="utf-8")
        assert "[[paper-key#^spn-" in index_path.read_text(encoding="utf-8")

    async def test_evidence_claim_promotion_returns_verified_candidates(self) -> None:
        """Claim promotion proposes exact-quote candidates with forced verification."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Claim-worthy evidence reduces uncertainty."
        blocks = [
            {
                "block_id": "blk_claim",
                "block_type": "Text",
                "page": 3,
                "text": markdown,
                "metadata": {"line_start": 1, "line_end": 2},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_claim",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_claim",
            page=3,
            line_start=1,
            line_end=2,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                op="claim_promotion",
                doc_id="doc_claim",
                query="uncertainty",
                output_format="json",
                citation_key="paper-key",
            )

        assert result["success"] is True
        assert result["verification_required"] is True
        assert result["entries"][0]["promotion_status"] == "ready"
        assert result["entries"][0]["verified"] is True
        assert result["entries"][0]["claim_text"] == markdown
        assert result["entries"][0]["asset_ref"]["span_id"] == span.span_id
        assert result["entries"][0]["foam"]["block_anchor"].startswith("^clm-")

    async def test_evidence_claim_promotion_writes_verified_foam_pack(
        self, tmp_path: Path
    ) -> None:
        """Claim promotion writes Foam only after verification succeeds."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Verified claim evidence belongs in the wiki."
        blocks = [
            {
                "block_id": "blk_claim_write",
                "block_type": "Text",
                "page": 5,
                "text": markdown,
                "metadata": {"line_start": 4, "line_end": 5},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_claim_write",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_claim_write",
            page=5,
            line_start=4,
            line_end=5,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                op="promote_claims",
                doc_id="doc_claim_write",
                output_format="foam",
                citation_key="paper-key",
                wiki_root=str(tmp_path),
                output_path="claims/paper-key-claims.md",
                index_path="Evidence Index.md",
                overwrite=True,
            )

        note_path = tmp_path / "claims" / "paper-key-claims.md"
        assert result["success"] is True
        assert Path(result["output_path"]) == note_path
        note_text = note_path.read_text(encoding="utf-8")
        assert 'type: "claim_promotion_pack"' in note_text
        assert "^clm-" in note_text
        assert "Verified claim evidence belongs in the wiki" in note_text
        assert "### Verification Payload" in note_text
        assert '"verification": {' in note_text
        assert '"valid": true' in note_text
        assert '"status": "verified"' in note_text
        assert "[[paper-key-claims#^clm-" in (tmp_path / "Evidence Index.md").read_text(
            encoding="utf-8"
        )

    async def test_evidence_claim_promotion_blocks_unverified_foam_write(
        self, tmp_path: Path
    ) -> None:
        """Foam writes are blocked if the candidate AssetRef fails verification."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256
        from src.presentation.tools.citation_support import asset_ref_from_span

        markdown = "Stale claim evidence should not be promoted."
        blocks = [
            {
                "block_id": "blk_claim_block",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_claim_block",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_claim_block",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        bad_ref = asset_ref_from_span(span)
        bad_ref["locator_version"] = "citation-span-v0"

        with (
            patch("src.presentation.tools.document_tools.repository") as mock_repo,
            patch(
                "src.presentation.tools.document_tools.asset_ref_from_span",
                return_value=bad_ref,
            ),
        ):
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                op="claims",
                doc_id="doc_claim_block",
                output_format="foam",
                wiki_root=str(tmp_path),
                overwrite=True,
            )

        assert result["success"] is False
        assert result["blocked_count"] == 1
        assert "verify first" in result["error"]

    async def test_evidence_health_validates_foam_asset_refs(
        self, tmp_path: Path
    ) -> None:
        """evidence(op='health') verifies embedded AssetRefs and Foam anchors."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Healthy Foam evidence."
        blocks = [
            {
                "block_id": "blk_health",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_health",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_health",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle, evidence

            await citation_bundle(
                "doc_health",
                output_format="foam",
                citation_key="paper-key",
                wiki_root=str(tmp_path),
                output_path="paper-key.md",
                overwrite=True,
            )
            result = await evidence(
                "health",
                wiki_root=str(tmp_path),
                output_format="json",
            )

        assert result["success"] is True
        assert result["files_scanned"] >= 1
        assert result["span_asset_refs"] == 1
        assert result["valid_refs"] == 1
        assert result["invalid_refs"] == 0
        assert result["wikilink_issues"] == 0

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

            result = await convert_pdf_to_docx("doc_123", async_mode=False)
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

            result = await convert_pdf_to_pptx("doc_123", async_mode=False)
            assert "✅" in result
            assert "converted.pptx" in result

    async def test_convert_pdf_to_docx_defaults_to_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Conversion defaults to a background job and does not run inline."""
        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_conversion_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_convert_docx",
                estimated_duration_seconds=20,
            )
        )
        mock_service = MagicMock()
        mock_service.convert_pdf_to_docx = AsyncMock(
            side_effect=AssertionError("conversion should run inside the job")
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.convert_pdf_to_docx("doc_123")

        assert "job_convert_docx" in result
        mock_jobs.create_conversion_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_conversion_job.await_args
        assert kwargs["operation"] == "pdf_to_docx"
        assert kwargs["parameters"]["target_format"] == "docx"
        assert callable(kwargs["handler"])
        mock_service.convert_pdf_to_docx.assert_not_awaited()

    async def test_ingest_documents_sync_forces_background_job_and_reports_progress(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A sync MCP PDF ingest request should not run ETL in the request."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_sync_pdf", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("MCP sync PDF ingest must use a job")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)], async_mode=False, ctx=fake_ctx
        )

        assert "job_sync_pdf" in result
        assert "background worker" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["operation"] == "ingest_documents"
        assert kwargs["parameters"]["use_marker"] is False
        assert kwargs["parameters"]["page_ranges"] == []
        mock_service.ingest.assert_not_awaited()
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

    async def test_ingest_documents_sync_pdf_skips_page_count_before_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The sync MCP path should not probe PDF pages before job creation."""
        from src.presentation.tools import document_tools

        page_count = MagicMock(
            side_effect=AssertionError("page counting belongs in the job")
        )
        monkeypatch.setattr(
            document_tools.pdf_extractor,
            "get_page_count",
            page_count,
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_no_page_probe", estimated_duration_seconds=10
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

        assert "job_no_page_probe" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        page_count.assert_not_called()

    async def test_ingest_documents_sync_pdf_never_counts_pages_in_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Sync PDF ingest should skip page-count probes and create a job."""
        pdf_path = tmp_path / "small.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        page_count = MagicMock(
            side_effect=AssertionError("page counting belongs in the job")
        )
        monkeypatch.setattr(document_tools.pdf_extractor, "get_page_count", page_count)
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_sync_pdf", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("PDFs should not run synchronously")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)],
            async_mode=False,
        )

        assert "job_sync_pdf" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        page_count.assert_not_called()

    async def test_ingest_documents_sync_lightrag_does_not_inline_indexing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """LightRAG indexing stays out of the synchronous MCP request path."""
        pdf_path = tmp_path / "kg.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools.pdf_extractor,
            "get_page_count",
            MagicMock(return_value=1),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_lightrag", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.knowledge_graph = MagicMock(is_available=True)
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("LightRAG should run in the job")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)],
            async_mode=False,
        )

        assert "job_lightrag" in result
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
            "operation": "ingest_documents",
            "require_marker": False,
            "etl_profile": "default",
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
            "operation": "ingest_documents",
            "require_marker": False,
            "etl_profile": "default",
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

    async def test_ocr_pdf_document_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """ocr_pdf_document returns a background OCR job instead of blocking."""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_ocr_doc", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.ocr_pdf_document(
            str(pdf_path),
            language="eng",
            rotate_pages=True,
        )

        assert "job_ocr_doc" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["operation"] == "ocr_pdf_document"
        assert kwargs["parameters"]["ocr_enabled"] is True
        assert kwargs["parameters"]["rotate_pages"] is True

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

    async def test_document_op_routes_list(self) -> None:
        """document(op, ...) exposes PDF document CRUD through one entrypoint."""
        with patch(
            "src.presentation.tools.document_tools.list_documents",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = "documents"
            from src.presentation.tools.document_tools import document

            result = await document("list")

        assert result == "documents"
        mock_list.assert_awaited_once_with()

    async def test_document_op_rejects_unknown_operation(self) -> None:
        """document(op, ...) fails closed for unsupported operations."""
        from src.presentation.tools.document_tools import document

        result = await document("compress")

        assert "Unsupported document op" in result

    async def test_document_op_routes_delete(self) -> None:
        """document(op='delete') delegates to the legacy delete tool."""
        with patch(
            "src.presentation.tools.document_tools.delete_document",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_delete.return_value = "deleted"
            from src.presentation.tools.document_tools import document

            result = await document("delete", doc_id="doc_123")

        assert result == "deleted"
        mock_delete.assert_awaited_once_with("doc_123")

    async def test_document_asset_op_routes_get(self) -> None:
        """document_asset(op='get') delegates to the legacy precise asset fetcher."""
        payload = [MagicMock(type="text", text="asset")]
        with patch(
            "src.presentation.tools.document_tools.fetch_document_asset",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = payload
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "get",
                doc_id="doc_123",
                asset_type="section",
                asset_id="sec_1",
                max_size=512,
            )

        assert result == payload
        mock_fetch.assert_awaited_once_with(
            "doc_123",
            "section",
            "sec_1",
            max_size=512,
            ctx=None,
        )

    async def test_document_asset_op_rejects_missing_get_type(self) -> None:
        """document_asset(op='get') requires an asset_type."""
        from src.presentation.tools.document_tools import document_asset

        result = await document_asset("get", doc_id="doc_123", asset_id="sec_1")

        assert isinstance(result, str)
        assert "asset_type is required" in result

    async def test_document_asset_writes_table_and_figure_foam_notes(
        self, tmp_path: Path
    ) -> None:
        """document_asset(op='foam_notes') writes table/figure evidence notes."""
        from src.domain.entities import (
            DocumentAssets,
            DocumentManifest,
            FigureAsset,
            TableAsset,
        )

        manifest = DocumentManifest(
            doc_id="doc_assets",
            filename="paper.pdf",
            source_pdf_sha256="pdf-hash",
            assets=DocumentAssets(
                tables=[
                    TableAsset(
                        id="tab_1",
                        page=2,
                        markdown="| A | B |\n| --- | --- |\n| x | y |",
                        row_count=1,
                        col_count=2,
                        source_block_id="blk_tab",
                        source_order=3,
                        line_start=10,
                        line_end=13,
                        section_title="Results",
                    )
                ],
                figures=[
                    FigureAsset(
                        id="fig_1_1",
                        page=3,
                        path=str(tmp_path / "fig.png"),
                        caption="Workflow diagram",
                        width=640,
                        height=480,
                        source_block_id="blk_fig",
                        source_order=4,
                        line_start=20,
                        line_end=21,
                        section_title="Methods",
                    )
                ],
            ),
        )
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_service:
            mock_service.get_manifest = AsyncMock(return_value=manifest)
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "foam_notes",
                doc_id="doc_assets",
                asset_type="all",
                asset_id="all",
                wiki_root=str(tmp_path),
                output_dir="assets",
                index_path="Evidence Index.md",
                citation_key="paper-key",
                response_format="json",
                overwrite=True,
            )

        assert result["success"] is True
        assert result["written_count"] == 2
        note_texts = [
            Path(item["path"]).read_text(encoding="utf-8") for item in result["written"]
        ]
        assert any('type: "table_evidence"' in text for text in note_texts)
        assert any('type: "figure_evidence"' in text for text in note_texts)
        assert any('"source_type": "table"' in text for text in note_texts)
        assert any('"source_type": "figure"' in text for text in note_texts)
        index_text = (tmp_path / "Evidence Index.md").read_text(encoding="utf-8")
        assert "[[paper-key-tab-1#^tab-" in index_text
        assert "[[paper-key-fig-1-1#^fig-" in index_text

    async def test_evidence_health_validates_table_and_figure_asset_refs(
        self, tmp_path: Path
    ) -> None:
        """Foam health verifies table/figure AssetRefs against the manifest."""
        from src.domain.entities import (
            DocumentAssets,
            DocumentManifest,
            FigureAsset,
            TableAsset,
        )

        manifest = DocumentManifest(
            doc_id="doc_assets",
            filename="paper.pdf",
            source_pdf_sha256="pdf-hash",
            assets=DocumentAssets(
                tables=[
                    TableAsset(
                        id="tab_1",
                        page=2,
                        markdown="| A | B |\n| --- | --- |\n| x | y |",
                        source_block_id="blk_tab",
                        source_order=3,
                        line_start=10,
                        line_end=13,
                    )
                ],
                figures=[
                    FigureAsset(
                        id="fig_1_1",
                        page=3,
                        path=str(tmp_path / "fig.png"),
                        caption="Workflow diagram",
                        width=640,
                        height=480,
                        source_block_id="blk_fig",
                        source_order=4,
                        line_start=20,
                        line_end=21,
                    )
                ],
            ),
        )
        with (
            patch("src.presentation.tools.document_tools.document_service") as mock_svc,
            patch("src.presentation.tools.document_tools.repository") as mock_repo,
        ):
            mock_svc.get_manifest = AsyncMock(return_value=manifest)
            mock_repo.load_manifest.return_value = manifest
            from src.presentation.tools.document_tools import document_asset, evidence

            await document_asset(
                "foam_notes",
                doc_id="doc_assets",
                asset_type="all",
                asset_id="all",
                wiki_root=str(tmp_path),
                output_dir="assets",
                citation_key="paper-key",
                response_format="json",
                overwrite=True,
            )
            result = await evidence(
                "health",
                wiki_root=str(tmp_path),
                output_format="json",
            )

        assert result["success"] is True
        assert result["asset_refs"] == 2
        assert result["valid_refs"] == 2
        assert result["invalid_refs"] == 0
        assert result["wikilink_issues"] == 0

    async def test_evidence_op_routes_find(self) -> None:
        """evidence(op='find') keeps citation span lookup behind one entrypoint."""
        with patch(
            "src.presentation.tools.document_tools.find_evidence_spans",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = "spans"
            from src.presentation.tools.document_tools import evidence

            result = await evidence("find", doc_id="doc_123", query="dose", limit=3)

        assert result == "spans"
        mock_find.assert_awaited_once_with(
            "doc_123",
            query="dose",
            span_id="",
            span_kinds=None,
            limit=3,
        )

    async def test_convert_document_routes_pdf_to_docx(self) -> None:
        """convert_document routes PDF document conversions through one entrypoint."""
        with patch(
            "src.presentation.tools.document_tools.convert_pdf_to_docx",
            new_callable=AsyncMock,
        ) as mock_convert:
            mock_convert.return_value = "converted"
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document(
                "doc_123",
                "docx",
                source_format="pdf",
                output_path="out.docx",
                mode="content",
            )

        assert result == "converted"
        mock_convert.assert_awaited_once_with(
            "doc_123",
            output_path="out.docx",
            mode="content",
            async_mode=True,
            ctx=None,
        )

    async def test_convert_document_rejects_unsupported_pair(self) -> None:
        """convert_document fails closed for unsupported source/target pairs."""
        from src.presentation.tools.document_tools import convert_document

        result = await convert_document("doc_123", "xlsx", source_format="pdf")

        assert "Unsupported conversion" in result

    async def test_convert_document_auto_uses_source_extension_first(self) -> None:
        """Auto source detection must not treat a PDF path as a DOCX doc_id."""
        with patch(
            "src.presentation.tools.docx_tools.convert_docx_to_doc",
            new_callable=AsyncMock,
        ) as mock_convert:
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document("paper.pdf", "doc")

        assert "Unsupported conversion" in result
        mock_convert.assert_not_awaited()

    async def test_convert_document_routes_docx_to_pdf(self) -> None:
        """convert_document preserves DOCX conversion output-path handling."""
        with patch(
            "src.presentation.tools.docx_tools.convert_docx_to_pdf",
            new_callable=AsyncMock,
        ) as mock_convert:
            mock_convert.return_value = "pdf"
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document(
                "docx_123",
                "pdf",
                source_format="docx",
                output_path="out.pdf",
                mode="fidelity",
            )

        assert result == "pdf"
        mock_convert.assert_awaited_once_with(
            "docx_123",
            output_path="out.pdf",
            mode="fidelity",
            async_mode=True,
            ctx=None,
        )

    async def test_convert_document_routes_markdown_to_docx(self) -> None:
        """convert_document routes Markdown exports without changing export roots."""
        with patch(
            "src.presentation.tools.docx_tools.export_markdown",
            new_callable=AsyncMock,
        ) as mock_export:
            mock_export.return_value = "docx"
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document(
                "notes.md",
                "docx",
                source_format="markdown",
                output_path="notes.docx",
            )

        assert result == "docx"
        mock_export.assert_awaited_once_with(
            md_path="notes.md",
            md_text=None,
            output_path="notes.docx",
            output_format="docx",
            async_mode=True,
            ctx=None,
        )

    async def test_document_asset_op_routes_section_tree(self) -> None:
        """document_asset(op='tree') keeps section-tree affordances available."""
        with patch(
            "src.presentation.tools.section_tools.list_section_tree",
            new_callable=AsyncMock,
        ) as mock_tree:
            mock_tree.return_value = "tree"
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "tree",
                doc_id="doc_123",
                max_depth=2,
                response_format="flat",
            )

        assert result == "tree"
        mock_tree.assert_awaited_once_with("doc_123", 2, "flat")

    async def test_document_asset_op_routes_section_blocks(self) -> None:
        """document_asset(op='blocks') preserves include_children and block filters."""
        with patch(
            "src.presentation.tools.section_tools.get_section_blocks",
            new_callable=AsyncMock,
        ) as mock_blocks:
            mock_blocks.return_value = "blocks"
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "blocks",
                doc_id="doc_123",
                path="Intro",
                include_children=False,
                block_types=["Table"],
                limit=5,
            )

        assert result == "blocks"
        mock_blocks.assert_awaited_once_with(
            "doc_123",
            "Intro",
            False,
            ["Table"],
            5,
        )

    async def test_evidence_op_routes_locate(self) -> None:
        """evidence(op='locate') keeps source-location search available."""
        with patch(
            "src.presentation.tools.document_tools.search_source_location",
            new_callable=AsyncMock,
        ) as mock_locate:
            mock_locate.return_value = "locations"
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                "locate",
                doc_id="doc_123",
                query="needle",
                block_types=["Text"],
            )

        assert result == "locations"
        mock_locate.assert_awaited_once_with(
            "doc_123",
            "needle",
            block_types=["Text"],
        )

    async def test_evidence_op_routes_bundle_foam_options(self) -> None:
        """evidence(op='bundle') preserves Foam bundle options."""
        with patch(
            "src.presentation.tools.document_tools.citation_bundle",
            new_callable=AsyncMock,
        ) as mock_bundle:
            mock_bundle.return_value = "foam pack"
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                "bundle",
                doc_id="doc_123",
                query="dose",
                output_format="foam",
                citation_key="paper-key",
                limit=2,
            )

        assert result == "foam pack"
        mock_bundle.assert_awaited_once_with(
            "doc_123",
            query="dose",
            span_id="",
            span_kinds=None,
            limit=2,
            include_verification=True,
            output_format="foam",
            citation_key="paper-key",
            wiki_root="",
            output_path="",
            index_path="",
            update_index=True,
            overwrite=False,
        )

    async def test_evidence_op_routes_health(self) -> None:
        """evidence(op='health') audits a Foam wiki root."""
        from src.presentation.tools.document_tools import evidence

        result = await evidence(
            "health", wiki_root="/missing/wiki", output_format="json"
        )

        assert result["success"] is False
        assert "wiki_root does not exist" in result["error"]

    async def test_evidence_op_routes_verify(self) -> None:
        """evidence(op='verify') delegates AssetRef verification unchanged."""
        ref = {"source_type": "span", "doc_id": "doc_123", "span_id": "span_1"}
        with patch(
            "src.presentation.tools.document_tools.verify_citation_ref",
            new_callable=AsyncMock,
        ) as mock_verify:
            mock_verify.return_value = "verified"
            from src.presentation.tools.document_tools import evidence

            result = await evidence("verify", ref=ref)

        assert result == "verified"
        mock_verify.assert_awaited_once_with(ref)


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

    async def test_table_manage_list_escapes_pipe_cells(self) -> None:
        """table_manage(op='list') escapes Markdown table cell pipes."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.list_tables.return_value = [
                {
                    "id": "tbl|1",
                    "title": "Alpha | Beta",
                    "intent": "compare | summarize",
                    "rows": 2,
                    "citations": 1,
                    "created_at": "2026-05-07",
                }
            ]
            from src.presentation.tools.table_tools import table_manage

            result = await table_manage("list")

        assert "`tbl\\|1`" in result
        assert "Alpha \\| Beta" in result
        assert "compare \\| summarize" in result

    async def test_table_draft_list_escapes_pipe_cells(self) -> None:
        """table_draft(op='list') escapes Markdown table cell pipes."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.list_drafts.return_value = [
                {
                    "id": "draft|1",
                    "title": "Draft | Title",
                    "intent": "extract | cite",
                    "columns_planned": 3,
                    "pending_rows": 1,
                    "has_table": False,
                }
            ]
            from src.presentation.tools.table_tools import table_draft

            result = await table_draft("list")

        assert "`draft\\|1`" in result
        assert "Draft \\| Title" in result
        assert "extract \\| cite" in result

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

    async def test_etl_profile_op_routes_set(self) -> None:
        """etl_profile(op='set') delegates to the existing profile switcher."""
        with patch(
            "src.presentation.tools.profile_tools.set_etl_profile",
            new_callable=AsyncMock,
        ) as mock_set:
            mock_set.return_value = {"success": True}
            from src.presentation.tools.profile_tools import etl_profile

            result = await etl_profile("set", name="arxiv")

        assert result == {"success": True}
        mock_set.assert_awaited_once_with("arxiv")

    async def test_etl_profile_op_rejects_missing_name(self) -> None:
        """etl_profile(op='get') requires a profile name."""
        from src.presentation.tools.profile_tools import etl_profile

        result = await etl_profile("get")

        assert result["success"] is False
        assert "name is required" in result["error"]

    async def test_etl_profile_op_routes_load(self) -> None:
        """etl_profile(op='load') delegates custom profile loading."""
        with patch(
            "src.presentation.tools.profile_tools.load_etl_profile_from_json",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"success": True}
            from src.presentation.tools.profile_tools import etl_profile

            result = await etl_profile("load", json_path="profile.json")

        assert result == {"success": True}
        mock_load.assert_awaited_once_with("profile.json")

    async def test_detect_etl_profile_from_sample_text(self) -> None:
        """detect_etl_profile recommends a profile with reasons."""
        from src.presentation.tools.profile_tools import detect_etl_profile

        result = await detect_etl_profile(
            sample_text="arXiv:2601.12345\n1. Introduction\nBody",
        )

        assert result["success"] is True
        assert result["recommended_profile"] == "arxiv"
        assert result["confidence"] > 0.4
        assert any("arXiv" in reason for reason in result["reasons"])

    async def test_set_etl_profile_rebinds_document_tool_services(self) -> None:
        """Profile switching updates already-imported presentation service aliases."""
        from src.presentation import dependencies
        from src.presentation.tools import document_tools, profile_tools, table_tools

        old_profile_name = dependencies.etl_profile.name

        result = await profile_tools.set_etl_profile("default")

        try:
            assert result["success"] is True
            assert document_tools.document_service is dependencies.document_service
            assert document_tools.pdf_extractor is dependencies.pdf_extractor
            assert table_tools.document_service is dependencies.document_service
            assert (
                dependencies.job_service.document_service
                is dependencies.document_service
            )
        finally:
            dependencies.rebuild_for_profile(old_profile_name)
            document_tools.document_service = dependencies.document_service
            document_tools.pdf_extractor = dependencies.pdf_extractor
            table_tools.document_service = dependencies.document_service
            dependencies.job_service.set_document_service(dependencies.document_service)


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

    async def test_export_knowledge_graph_times_out_in_request_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Slow graph export should return a bounded timeout message."""
        from src.presentation.tools import knowledge_tools

        async def slow_export(*_args, **_kwargs):
            await asyncio.sleep(3600)

        mock_graph = MagicMock()
        mock_graph.export_graph = AsyncMock(side_effect=slow_export)
        monkeypatch.setattr(knowledge_tools, "knowledge_graph", mock_graph)
        monkeypatch.setattr(
            knowledge_tools,
            "KNOWLEDGE_TOOL_TIMEOUT_SECONDS",
            0.01,
        )

        result = await knowledge_tools.export_knowledge_graph(format="summary", limit=5)

        assert "timed out" in result
        assert "limit=5" in result

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

    async def test_consult_knowledge_graph_times_out_in_request_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Slow LightRAG calls should return a bounded timeout record."""
        from src.presentation.tools import knowledge_tools

        async def slow_query(*_args, **_kwargs):
            await asyncio.sleep(3600)

        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_structured = AsyncMock(side_effect=slow_query)
            monkeypatch.setattr(
                knowledge_tools,
                "KNOWLEDGE_TOOL_TIMEOUT_SECONDS",
                0.01,
            )

            result = await knowledge_tools.consult_knowledge_graph("test")

        assert isinstance(result, dict)
        assert result["status"] == "timeout"
        assert result["query"] == "test"

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

    async def test_consult_knowledge_graph_attaches_verified_evidence(self) -> None:
        """KG answers can attach verified citation bundles for source docs."""
        with (
            patch(
                "src.presentation.tools.knowledge_tools.knowledge_service"
            ) as mock_svc,
            patch(
                "src.presentation.tools.document_tools.citation_bundle",
                new_callable=AsyncMock,
            ) as mock_bundle,
        ):
            mock_svc.query_structured = AsyncMock(
                return_value={
                    "success": True,
                    "answer": "ok",
                    "references": [{"doc_id": "doc_123"}],
                }
            )
            mock_bundle.return_value = {
                "success": True,
                "doc_id": "doc_123",
                "returned": 1,
                "matched_count": 1,
                "entries": [{"span_id": "spn_1"}],
            }
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "dose",
                verify_references=True,
                evidence_limit=2,
            )

        assert result["verified_evidence"]["success"] is True
        mock_svc.query_structured.assert_awaited_once_with(
            "dose",
            mode="hybrid",
            user_prompt=None,
            include_references=True,
        )
        mock_bundle.assert_awaited_once_with(
            "doc_123",
            query="dose",
            limit=2,
            include_verification=True,
            output_format="json",
        )

    async def test_consult_knowledge_graph_rejects_invalid_response_mode(self) -> None:
        """consult_knowledge_graph should fail fast on invalid response_mode."""
        from src.presentation.tools.knowledge_tools import consult_knowledge_graph

        with pytest.raises(ValueError, match="response_mode must be one of"):
            await consult_knowledge_graph("test", response_mode="yaml")

    async def test_knowledge_op_routes_export(self) -> None:
        """knowledge(op='export') keeps export as an explicit operation."""
        with patch(
            "src.presentation.tools.knowledge_tools.export_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_export:
            mock_export.return_value = "graph"
            from src.presentation.tools.knowledge_tools import knowledge

            result = await knowledge("export", format="summary", limit=10)

        assert result == "graph"
        mock_export.assert_awaited_once_with("summary", 10, ctx=None)

    async def test_knowledge_op_routes_query(self) -> None:
        """knowledge(op='query') delegates to consult_knowledge_graph."""
        with patch(
            "src.presentation.tools.knowledge_tools.consult_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_consult:
            mock_consult.return_value = {"answer": "ok"}
            from src.presentation.tools.knowledge_tools import knowledge

            result = await knowledge(
                "query",
                query="dose",
                mode="mix",
                response_mode="data",
                user_prompt="brief",
                include_references=True,
            )

        assert result == {"answer": "ok"}
        mock_consult.assert_awaited_once_with(
            "dose",
            mode="mix",
            response_mode="data",
            user_prompt="brief",
            include_references=True,
            verify_references=False,
            doc_ids=None,
            evidence_limit=5,
            ctx=None,
        )

    async def test_knowledge_op_rejects_unknown_operation(self) -> None:
        """knowledge(op, ...) fails closed for unsupported operations."""
        from src.presentation.tools.knowledge_tools import knowledge

        result = await knowledge("mutate", query="test")

        assert isinstance(result, str)
        assert "Unsupported knowledge op" in result


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
        """Legacy and consolidated MCP tools are registered during compatibility window."""
        from src.presentation.mcp_app import mcp

        registered = {t.name for t in mcp._tool_manager._tools.values()}
        expected = {
            "document",
            "document_asset",
            "docx",
            "docx_table",
            "convert_document",
            "evidence",
            "job",
            "etl_profile",
            "knowledge",
            "ingest_documents",
            "ingest_docx",
            "save_docx",
            "citation_bundle",
            "detect_etl_profile",
            "docx_table_edit_plan",
            "find_evidence_spans",
            "verify_citation_ref",
            "get_job_status",
        }
        assert expected <= registered
        assert len(registered) == 62, f"Expected 62 tools, got {len(registered)}"


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

    async def test_conversion_job_completes_with_artifact_payload(self) -> None:
        """JobService can run conversion handlers outside the MCP request path."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobStatus, JobSummary

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

            async def list_active(self) -> list[JobSummary]:
                return []

            async def list_all(self, _limit: int = 20) -> list[JobSummary]:
                return []

            async def cleanup_old(self, _max_age_hours: int) -> int:
                return 0

        async def handler(progress) -> dict:
            await progress.report(step=2, phase="Converting", message="running")
            return {
                "success": True,
                "operation": "pdf_to_docx",
                "output_path": "/workspace/out.docx",
            }

        store = MemoryJobStore()
        service = JobService(job_store=store)
        job = await service.create_conversion_job(
            operation="pdf_to_docx",
            handler=handler,
            parameters={"source": "doc_123"},
        )
        task = service._running_tasks[job.job_id]
        await asyncio.wait_for(task, timeout=1)

        stored = await store.get(job.job_id)
        assert stored.status == JobStatus.COMPLETED
        assert stored.result["conversion"]["output_path"] == "/workspace/out.docx"

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
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="",
                filename="bad.pdf",
                success=False,
                error="bad pdf",
                warnings=["Isolated ingest worker log: logs/bad.log"],
            )
        )

        await service._process_ingest_job(job.job_id)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert stored.error == "1/1 file(s) failed during ingestion"
        assert stored.result is not None
        assert stored.result["files_failed"] == 1
        assert stored.result["failed_files"] == [
            {
                "file": "bad.pdf",
                "error": "bad pdf",
                "warnings": ["Isolated ingest worker log: logs/bad.log"],
            }
        ]
        assert stored.result["warnings"] == ["Isolated ingest worker log: logs/bad.log"]

    async def test_pymupdf_job_uses_isolated_worker_not_event_loop_ingest(
        self, temp_dir: Path
    ) -> None:
        """Background PyMuPDF jobs also avoid blocking the MCP event loop."""
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

        class EventLoopDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("PyMuPDF ingest should run in an isolated worker")

        doc_dir = temp_dir / "doc_pymupdf"
        doc_dir.mkdir()
        EventLoopDocumentService.repository.get_doc_dir.return_value = doc_dir

        store = MemoryJobStore()
        job = Job(
            job_id="job_pymupdf_worker",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": False},
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=EventLoopDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_pymupdf",
                filename="paper.pdf",
                success=True,
                backend="pymupdf",
            )
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_pymupdf"]
        service._run_isolated_ingest_worker.assert_awaited_once()

    async def test_marker_job_uses_isolated_worker_not_event_loop_ingest(
        self, temp_dir: Path
    ) -> None:
        """Marker jobs run through the subprocess worker path."""
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

        class EventLoopDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("Marker ingest should run in an isolated worker")

        doc_dir = temp_dir / "doc_marker"
        doc_dir.mkdir()
        (doc_dir / "blocks.json").write_text("[]", encoding="utf-8")
        EventLoopDocumentService.repository.get_doc_dir.return_value = doc_dir

        store = MemoryJobStore()
        job = Job(
            job_id="job_marker_worker",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": True, "extract_figures": True},
            progress=JobProgress(total_steps=9),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=EventLoopDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_marker",
                filename="paper.pdf",
                success=True,
                backend="marker",
            )
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_marker"]
        assert stored.result is not None
        assert stored.result["documents"][0]["backend"] == "marker"
        assert stored.result["documents"][0]["blocks_available"] is True
        service._run_isolated_ingest_worker.assert_awaited_once()

    async def test_process_ingest_job_delegates_to_injected_worker_runner(
        self, temp_dir: Path
    ) -> None:
        """JobService should depend on an ingest worker runner port."""
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

        class EventLoopDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("DocumentService.ingest must stay in the worker")

        class FakeIngestWorkerRunner:
            def __init__(self) -> None:
                self.requests = []

            async def run_ingest_worker(self, request):
                self.requests.append(request)
                return IngestResult(
                    doc_id="doc_runner",
                    filename="paper.pdf",
                    success=True,
                    backend="marker",
                )

        doc_dir = temp_dir / "doc_runner"
        doc_dir.mkdir()
        EventLoopDocumentService.repository.get_doc_dir.return_value = doc_dir
        runner = FakeIngestWorkerRunner()
        store = MemoryJobStore()
        job = Job(
            job_id="job_runner_port",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": True, "extract_figures": True},
            progress=JobProgress(total_steps=9),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=EventLoopDocumentService(),  # type: ignore[arg-type]
            ingest_worker_runner=runner,
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert len(runner.requests) == 1
        request = runner.requests[0]
        assert request.job_id == job.job_id
        assert request.file_path == "paper.pdf"
        assert request.parameters["use_marker"] is True
        assert request.progress_offset == 0
        assert request.progress_total_steps == 9
        assert request.progress_prefix == "[1/1] "
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_runner"]
        assert stored.result is not None
        assert stored.result["documents"][0]["backend"] == "marker"

    async def test_isolated_ingest_worker_reads_result_and_redirects_stdio_to_log(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The subprocess worker command returns JSON and keeps logs inspectable."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult

        created: dict[str, object] = {}

        class FakeProcess:
            returncode = 0

            async def wait(self) -> int:
                return 0

            def terminate(self) -> None:
                raise AssertionError("terminate should not be needed")

            def kill(self) -> None:
                raise AssertionError("kill should not be needed")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            created["cmd"] = cmd
            created["kwargs"] = kwargs
            kwargs["stdout"].write("worker booted\n")
            kwargs["stdout"].flush()
            result_path = Path(cmd[cmd.index("--result-json") + 1])
            result_path.write_text(
                IngestResult(
                    doc_id="doc_worker",
                    filename="paper.pdf",
                    backend="marker",
                ).model_dump_json(),
                encoding="utf-8",
            )
            return FakeProcess()

        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.tempfile.gettempdir",
            lambda: str(tmp_path),
        )
        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.asyncio.create_subprocess_exec",
            fake_create_subprocess_exec,
        )

        job_store = MagicMock()
        job_store.jobs_dir = tmp_path / "jobs"
        service = JobService(job_store=job_store)

        result = await service._run_isolated_ingest_worker(
            "job_worker",
            "paper.pdf",
            {
                "use_marker": True,
                "require_marker": True,
                "ocr_language": "eng",
                "marker_max_pages_per_chunk": 7,
                "page_ranges": ["1-2"],
                "extract_figures": True,
                "etl_profile": "arxiv",
            },
        )

        cmd = created["cmd"]
        kwargs = created["kwargs"]
        assert isinstance(cmd, tuple)
        assert "-m" in cmd
        assert "src.presentation.ingest_worker_main" in cmd
        assert "--use-marker" in cmd
        assert "--require-marker" in cmd
        assert "--extract-figures" in cmd
        assert "--etl-profile" in cmd
        assert "--progress-json" in cmd
        assert kwargs["stdin"] is asyncio.subprocess.DEVNULL
        assert kwargs["stdout"] is not asyncio.subprocess.DEVNULL
        assert kwargs["stderr"] is asyncio.subprocess.STDOUT
        assert kwargs["env"]["ETL_PROFILE"] == "arxiv"
        assert result.doc_id == "doc_worker"
        log_paths = list((tmp_path / "logs").glob("ingest_job_worker_paper_*.log"))
        assert len(log_paths) == 1
        log_path = log_paths[0]
        assert log_path.read_text(encoding="utf-8") == "worker booted\n"
        assert any(str(log_path) in warning for warning in result.warnings)

    async def test_isolated_ingest_worker_heartbeat_updates_job_from_progress_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Parent progress is refreshed while the isolated worker is still running."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobType

        class MemoryJobStore:
            def __init__(self) -> None:
                self.jobs: dict[str, Job] = {}
                self.jobs_dir = tmp_path / "jobs"

            async def create(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def get(self, job_id: str) -> Job | None:
                return self.jobs.get(job_id)

            async def update(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

        class FakeProcess:
            pid = 1234
            returncode: int | None = None

            async def wait(self) -> int:
                await asyncio.sleep(0.05)
                self.returncode = 0
                return 0

            def terminate(self) -> None:
                raise AssertionError("terminate should not be needed")

            def kill(self) -> None:
                raise AssertionError("kill should not be needed")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            kwargs["stdout"].write("marker log tail\n")
            kwargs["stdout"].flush()
            progress_path = Path(cmd[cmd.index("--progress-json") + 1])
            progress_path.write_text(
                json.dumps(
                    {
                        "step": 3,
                        "total": 9,
                        "phase": "Marker Parse",
                        "message": "Loading Marker models",
                    }
                ),
                encoding="utf-8",
            )
            result_path = Path(cmd[cmd.index("--result-json") + 1])
            result_path.write_text(
                IngestResult(
                    doc_id="doc_worker",
                    filename="paper.pdf",
                    backend="marker",
                ).model_dump_json(),
                encoding="utf-8",
            )
            return FakeProcess()

        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.asyncio.create_subprocess_exec",
            fake_create_subprocess_exec,
        )
        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.WORKER_HEARTBEAT_SECONDS",
            0.01,
            raising=False,
        )

        store = MemoryJobStore()
        job = Job(
            job_id="job_heartbeat",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=9),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)

        result = await service._run_isolated_ingest_worker(
            job.job_id,
            "paper.pdf",
            {"use_marker": True, "extract_figures": True},
        )

        stored = await store.get(job.job_id)
        assert result.success is True
        assert stored is not None
        assert stored.progress.current_phase == "Marker Parse"
        assert stored.progress.message == "Loading Marker models"
        assert stored.progress.current_step == 3
        assert stored.progress.percentage == pytest.approx(100 / 3)

    async def test_isolated_ingest_worker_invalid_result_returns_failure_with_log_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Partial worker JSON is reported as a failed result instead of escaping."""
        from src.application.job_service import JobService

        class FakeProcess:
            returncode = 0

            async def wait(self) -> int:
                return 0

            def terminate(self) -> None:
                raise AssertionError("terminate should not be needed")

            def kill(self) -> None:
                raise AssertionError("kill should not be needed")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            kwargs["stdout"].write("traceback line\n")
            kwargs["stdout"].flush()
            result_path = Path(cmd[cmd.index("--result-json") + 1])
            result_path.write_text('{"success": false', encoding="utf-8")
            return FakeProcess()

        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.asyncio.create_subprocess_exec",
            fake_create_subprocess_exec,
        )
        job_store = MagicMock()
        job_store.jobs_dir = tmp_path / "jobs"
        service = JobService(job_store=job_store)

        result = await service._run_isolated_ingest_worker(
            "job_bad_result",
            "paper.pdf",
            {"use_marker": True},
        )

        log_paths = list((tmp_path / "logs").glob("ingest_job_bad_result_paper_*.log"))
        assert len(log_paths) == 1
        log_path = log_paths[0]
        assert result.success is False
        assert "Could not read isolated ingest worker result" in (result.error or "")
        assert str(log_path) in (result.error or "")
        assert log_path.read_text(encoding="utf-8") == "traceback line\n"

    async def test_ingest_worker_writes_result_and_progress_atomically(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Worker result/progress JSON writers preserve existing files on failure."""
        from src.application import ingest_worker
        from src.domain.entities import IngestResult

        result_path = tmp_path / "result.json"
        result_path.write_text(
            IngestResult(doc_id="old", filename="paper.pdf").model_dump_json(),
            encoding="utf-8",
        )

        original_write_text = Path.write_text

        def fail_after_partial_tmp_write(self: Path, *args, **kwargs) -> int:
            original_write_text(self, '{"partial"', encoding="utf-8")
            raise RuntimeError("disk full")

        monkeypatch.setattr(Path, "write_text", fail_after_partial_tmp_write)

        with pytest.raises(RuntimeError, match="disk full"):
            ingest_worker._write_result(
                result_path,
                IngestResult(doc_id="new", filename="paper.pdf"),
            )

        monkeypatch.setattr(Path, "write_text", original_write_text)
        assert json.loads(result_path.read_text(encoding="utf-8"))["doc_id"] == "old"
        assert not list(tmp_path.glob("*.tmp"))

        callback = ingest_worker._make_progress_callback(tmp_path / "progress.json")
        await callback(2, 9, "Marker Parse", "Loading Marker models")

        progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
        assert progress["step"] == 2
        assert progress["total"] == 9
        assert progress["phase"] == "Marker Parse"
        assert progress["message"] == "Loading Marker models"
        assert "ts" in progress
        assert not list(tmp_path.glob("*.tmp"))

    async def test_ingest_job_result_preserves_backend_warnings(self) -> None:
        """Background jobs keep degraded backend warnings in their final result."""
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

        class FallbackDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                return [
                    IngestResult(
                        doc_id="doc_fallback",
                        filename="paper.pdf",
                        success=True,
                        backend="pymupdf_fallback",
                        warnings=["Marker requested; PyMuPDF fallback used"],
                    )
                ]

        FallbackDocumentService.repository.get_doc_dir.return_value = Path("data/doc")
        store = MemoryJobStore()
        job = Job(
            job_id="job_fallback",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": False},
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)
        service = JobService(
            job_store=store,
            document_service=FallbackDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_fallback",
                filename="paper.pdf",
                success=True,
                backend="pymupdf_fallback",
                warnings=["Marker requested; PyMuPDF fallback used"],
            )
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.result is not None
        assert stored.result["degraded"] is True
        assert stored.result["warnings"] == ["Marker requested; PyMuPDF fallback used"]
        assert stored.result["documents"][0]["backend"] == "pymupdf_fallback"

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

    async def test_cancel_job_preserves_worker_cancellation_message(self) -> None:
        """cancel_job must not overwrite the worker's final cancellation update."""
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

        store = MemoryJobStore()
        job = Job(
            job_id="job_cancel_message",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=8, message="worker started"),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)

        started = asyncio.Event()

        async def worker() -> None:
            try:
                started.set()
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                latest = await store.get(job.job_id)
                assert latest is not None
                latest.cancel()
                latest.progress.message = "Job cancelled by user"
                await store.update(latest)
                raise

        task = asyncio.create_task(worker())
        await started.wait()
        service._running_tasks[job.job_id] = task

        assert await service.cancel_job(job.job_id) is True

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.CANCELLED
        assert stored.progress.message == "Job cancelled by user"

    async def test_reconcile_stale_active_jobs_after_restart(self) -> None:
        """Persisted active jobs without in-memory tasks are failed on read/list."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobSummary, JobType

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

            async def list_active(self):
                return [
                    JobSummary.from_job(job)
                    for job in self.jobs.values()
                    if not job.is_terminal
                ]

            async def list_all(self, limit: int = 20):
                return [JobSummary.from_job(job) for job in self.jobs.values()]

        store = MemoryJobStore()
        job = Job(
            job_id="job_stale",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=8),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)

        active = await service.list_active_jobs()
        stored = await store.get(job.job_id)

        assert active == []
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert "restarted" in (stored.error or "")

    async def test_reconcile_does_not_fail_other_live_owner_job(self) -> None:
        """Shared DATA_DIR instances must not fail jobs owned by a live process."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobSummary, JobType

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

            async def list_active(self):
                return [
                    JobSummary.from_job(job)
                    for job in self.jobs.values()
                    if not job.is_terminal
                ]

        store = MemoryJobStore()
        job = Job(
            job_id="job_other_owner",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"job_owner_id": "other", "job_owner_pid": 12345},
            progress=JobProgress(total_steps=8),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)
        service._process_is_alive = MagicMock(return_value=True)  # type: ignore[method-assign]

        active = await service.list_active_jobs()
        stored = await store.get(job.job_id)

        assert len(active) == 1
        assert stored is not None
        assert stored.status == JobStatus.PROCESSING

    async def test_process_ingest_job_uses_captured_document_service(self) -> None:
        """Profile switches must not alter a job's already captured service."""
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

        class OriginalDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                return [
                    IngestResult(
                        doc_id="doc_original",
                        filename="paper.pdf",
                        success=True,
                    )
                ]

        class NewDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("new service should not handle captured job")

        OriginalDocumentService.repository.get_doc_dir.return_value = Path("data/doc")
        store = MemoryJobStore()
        job = Job(
            job_id="job_profile_isolated",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": False},
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)
        original = OriginalDocumentService()
        service = JobService(job_store=store, document_service=original)  # type: ignore[arg-type]
        service.set_document_service(NewDocumentService())  # type: ignore[arg-type]
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_original",
                filename="paper.pdf",
                success=True,
            )
        )

        await service._process_ingest_job(job.job_id, original)  # type: ignore[arg-type]

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_original"]

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
