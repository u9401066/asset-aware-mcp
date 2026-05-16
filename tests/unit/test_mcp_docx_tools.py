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

    async def test_get_docx_content_large_dfm_returns_preview(self) -> None:
        """Large DFM files should not be returned wholesale to MCP clients."""
        large_dfm = "<!-- @b:p001 -->\n" + ("A" * 60_000)
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.get_dfm = AsyncMock(return_value=large_dfm)
            mock_svc.repository.get_doc_dir.return_value = Path("/data/doc123")
            from src.presentation.tools.docx_tools import get_docx_content

            result = await get_docx_content("doc123")

        assert len(result) < 20_000
        assert "content.dfm" in result
        assert "sha256:" in result
        assert "A" * 30_000 not in result

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

    async def test_get_docx_content_large_block_metadata_returns_bounded_json(
        self,
    ) -> None:
        """Large block locator metadata should be summarized instead of inlined."""
        large_metadata = {
            "locator_version": "docx-dfm-locator-v1",
            "source_part": "word/document.xml",
            "run_ranges": [
                {"run": index, "char_start": index * 10, "char_end": index * 10 + 9}
                for index in range(2_000)
            ],
            "cell_locators": {
                f"r{index}c0": {"text": "M" * 80, "sha256": f"hash-{index}"}
                for index in range(800)
            },
        }
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.get_block_content = AsyncMock(
                return_value={
                    "id": "t001",
                    "type": "table",
                    "content": "D" * 60_000,
                    "metadata": large_metadata,
                }
            )
            mock_svc.repository.get_doc_dir.return_value = Path("/data/doc123")
            from src.presentation.tools.docx_tools import get_docx_content

            result = await get_docx_content("doc123", block_id="t001")

        assert len(result) < 20_000
        parsed = json.loads(result)
        assert parsed["content_truncated"] is True
        assert parsed["content_sha256"].startswith("sha256:")
        assert parsed["metadata_truncated"] is True
        assert parsed["metadata_sha256"].startswith("sha256:")
        assert parsed["metadata"]["run_ranges_count"] == 2_000
        assert parsed["metadata"]["cell_locators_count"] == 800
        assert "ir.json" in parsed["metadata_artifact_path"]
        assert "D" * 30_000 not in result
        assert "M" * 1_000 not in result

    async def test_list_docx_blocks_caps_large_block_listing(self) -> None:
        """Huge DOCX block catalogs should list a bounded prefix."""
        blocks = [
            {
                "id": f"p{index:04d}",
                "type": "paragraph",
                "editable": True,
                "style": "Normal",
                "preview": "A" * 200,
                "metadata": {"source_part": "word/document.xml"},
            }
            for index in range(700)
        ]
        with patch("src.presentation.tools.docx_tools.docx_service") as mock_svc:
            mock_svc.list_blocks = AsyncMock(return_value=blocks)
            mock_svc.repository.get_doc_dir.return_value = Path("/data/doc123")
            from src.presentation.tools.docx_tools import list_docx_blocks

            result = await list_docx_blocks("doc123")

        assert "Showing first 100 of 700 blocks" in result
        assert "p0099" in result
        assert "p0100" not in result

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

    async def test_docx_validate_roundtrip_large_report_returns_preview(
        self, tmp_path: Path
    ) -> None:
        """Large validator reports should be bounded before returning to MCP."""
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
            report.to_markdown.return_value = "# Report\n" + ("R" * 80_000)
            mock_validator.validate.return_value = report

            from src.presentation.tools.docx_tools import docx_validate_roundtrip

            result = await docx_validate_roundtrip("docx_123")

        assert len(result) < 20_000
        assert "sha256:" in result
        assert "R" * 30_000 not in result

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
