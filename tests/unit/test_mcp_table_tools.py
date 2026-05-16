"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

# ============================================================================
# Docx Tools
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

    async def test_table_manage_render_large_markdown_returns_preview(self) -> None:
        """Large markdown/html table renders should not be inlined to Cline."""
        large_table = "| A |\n|---|\n" + ("| X |\n" * 30_000)
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.render_table = AsyncMock(
                return_value={
                    "success": True,
                    "format": "markdown",
                    "content": large_table,
                    "row_count": 30_000,
                }
            )
            from src.presentation.tools.table_tools import table_manage

            result = await table_manage("render", table_id="tbl_big", format="markdown")

        assert len(result) < 20_000
        assert "sha256:" in result
        assert "table render" in result.lower()
        assert "| X |\n" * 20_000 not in result

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

    async def test_table_data_get_row_large_cell_returns_bounded_json(self) -> None:
        """Large row cell values should be summarized in JSON responses."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_row.return_value = {
                "row_index": 0,
                "data": {"Finding": "A" * 80_000},
                "citations": {},
            }
            from src.presentation.tools.table_tools import table_data

            result = await table_data("get_row", "tbl_big", row_index=0)

        assert len(result) < 20_000
        assert "sha256:" in result
        assert "A" * 30_000 not in result

    async def test_table_data_get_cell_large_value_returns_preview(self) -> None:
        """Large cell values should not be inlined in full."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_cell.return_value = {"value": "B" * 80_000}
            from src.presentation.tools.table_tools import table_data

            result = await table_data(
                "get_cell",
                "tbl_big",
                row_index=0,
                column_name="Finding",
            )

        assert len(result) < 20_000
        assert "sha256:" in result
        assert "B" * 30_000 not in result

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

    async def test_table_draft_resume_large_payload_returns_preview(self) -> None:
        """Draft resume should summarize large notes and pending row values."""
        draft = SimpleNamespace(
            title="Draft",
            intent="summary",
            table_id="",
            proposed_columns=[{"name": "Finding", "description": "C" * 80_000}],
            extraction_plan=["D" * 80_000 for _ in range(3)],
            pending_rows=[{"Finding": "E" * 80_000}],
            notes="F" * 80_000,
            estimate_tokens=lambda: 100_000,
        )
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_draft.return_value = draft
            from src.presentation.tools.table_tools import table_draft

            result = await table_draft("resume", draft_id="draft_big")

        assert len(result) < 20_000
        assert "sha256:" in result
        assert "C" * 30_000 not in result
        assert "F" * 30_000 not in result


# Profile Tools
# ============================================================================
