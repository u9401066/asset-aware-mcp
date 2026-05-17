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
                    "load_status": "skipped_large",
                    "artifact_path": "C:/tmp/table|1.json",
                    "artifact_bytes": 2048,
                    "created_at": "2026-05-07",
                }
            ]
            from src.presentation.tools.table_tools import table_manage

            result = await table_manage("list")

        assert "`tbl\\|1`" in result
        assert "Alpha \\| Beta" in result
        assert "compare \\| summarize" in result
        assert "skipped_large" in result
        assert "2048 bytes" in result

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
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.render_table = AsyncMock(
                return_value={
                    "success": True,
                    "format": "markdown",
                    "file_path": "C:/tmp/tbl_big.render.md",
                    "artifact_only": True,
                    "sha256": "abc123",
                    "preview": "| A |\n|---|\n| X |",
                    "row_count": 30_000,
                }
            )
            from src.presentation.tools.table_tools import table_manage

            result = await table_manage("render", table_id="tbl_big", format="markdown")

        assert len(result) < 20_000
        assert "abc123" in result
        assert "Artifact Only" in result
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

    async def test_table_data_query_rows_routes_without_new_tool(self) -> None:
        """table_data query_rows exposes paging/search/coverage inside one facade."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.query_rows.return_value = {
                "table_id": "tbl_1",
                "schema_version": "a2t-table-v2",
                "row_count": 10,
                "matched_count": 1,
                "page": {"offset": 0, "limit": 5, "next_offset": None},
                "rows": [
                    {
                        "row_id": "row_a",
                        "row_index": 0,
                        "data": {"Drug": "A"},
                        "coverage": {
                            "cited_cells": 1,
                            "total_cells": 2,
                            "coverage_ratio": 0.5,
                        },
                    }
                ],
            }
            from src.presentation.tools.table_tools import table_data

            result = await table_data(
                "query_rows",
                "tbl_1",
                search="A",
                include_coverage=True,
            )

        assert "row_a" in result
        assert "Matched:** 1" in result

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

    async def test_table_data_clear_cell_passes_row_id(self) -> None:
        """clear_cell supports stable row IDs through the facade."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.clear_cell.return_value = {"success": True, "old_value": "A"}
            from src.presentation.tools.table_tools import table_data

            result = await table_data(
                "clear_cell",
                "tbl_1",
                row_id="row_a",
                column_name="Drug",
            )

        mock_svc.clear_cell.assert_called_once_with(
            "tbl_1",
            -1,
            "Drug",
            row_id="row_a",
        )
        assert "cleared" in result

    async def test_table_cite_add_missing_params(self) -> None:
        """table_cite add requires row_index, column_name, refs."""
        from src.presentation.tools.table_tools import table_cite

        result = await table_cite("add", "tbl_123")
        assert "❌" in result

    async def test_table_cite_coverage_routes_without_new_tool(self) -> None:
        """table_cite coverage reports citation coverage through the facade."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.citation_coverage.return_value = {
                "table_id": "tbl_1",
                "schema_version": "a2t-table-v2",
                "row_count": 1,
                "column_count": 2,
                "total_cells": 2,
                "cited_cells": 1,
                "coverage_ratio": 0.5,
                "page": {"offset": 5, "limit": 10, "next_offset": None},
                "rows": [],
            }
            from src.presentation.tools.table_tools import table_cite

            result = await table_cite("coverage", "tbl_1", offset=5, limit=10)

        mock_svc.citation_coverage.assert_called_once_with(
            "tbl_1",
            offset=5,
            limit=10,
        )
        assert "coverage_ratio" in result
        assert "0.5" in result

    async def test_table_cite_get_unknown_row_id_returns_error(self) -> None:
        """Unknown row IDs should not fall back to table-level citations."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_citations.side_effect = ValueError("Unknown row_id: row_bad")
            from src.presentation.tools.table_tools import table_cite

            result = await table_cite("get", "tbl_1", row_id="row_bad")

        assert "Unknown row_id" in result

    async def test_table_cite_cell_history_passes_row_id(self) -> None:
        """cell_history can follow stable row IDs after row deletion."""
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_cell_history.return_value = [
                {
                    "timestamp": "2026-05-17T00:00:00",
                    "operation": "update_cell",
                    "old_value": "A",
                    "new_value": "B",
                }
            ]
            from src.presentation.tools.table_tools import table_cite

            result = await table_cite(
                "cell_history",
                "tbl_1",
                row_id="row_a",
                column_name="Drug",
            )

        mock_svc.get_cell_history.assert_called_once_with(
            "tbl_1",
            -1,
            "Drug",
            row_id="row_a",
        )
        assert "update_cell" in result

    async def test_table_history_changes_missing_id(self) -> None:
        """table_history changes requires table_id."""
        from src.presentation.tools.table_tools import table_history

        result = await table_history("changes", "")
        assert "❌" in result

    async def test_table_history_tokens_can_use_draft_without_table_id(self) -> None:
        """table_history tokens should not require table_id when draft_id is enough."""
        draft = SimpleNamespace(
            pending_rows=[{"Drug": "A"}], estimate_tokens=lambda: 42
        )
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_draft.return_value = draft
            from src.presentation.tools.table_tools import table_history

            result = await table_history("tokens", draft_id="draft_1")

        assert "Draft `draft_1`" in result
        assert "~42 tokens" in result

    async def test_table_draft_create_missing_title(self) -> None:
        """table_draft create requires title."""
        from src.presentation.tools.table_tools import table_draft

        result = await table_draft("create")
        assert "❌" in result

    async def test_table_draft_update_passes_source_doc_ids(self) -> None:
        """table_draft update should refresh source_doc_ids, not only sections."""
        draft = SimpleNamespace(
            title="Draft",
            intent="summary",
            proposed_columns=[],
            pending_rows=[],
            estimate_tokens=lambda: 0,
        )
        with patch("src.presentation.tools.table_tools.table_service") as mock_svc:
            mock_svc.get_draft.return_value = draft
            from src.presentation.tools.table_tools import table_draft

            result = await table_draft(
                "update",
                draft_id="draft_1",
                source_doc_ids=["doc_a", "doc_b"],
            )

        assert "updated" in result
        mock_svc.update_draft.assert_called_once_with(
            "draft_1",
            source_doc_ids=["doc_a", "doc_b"],
        )

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
