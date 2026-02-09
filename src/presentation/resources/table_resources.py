"""
Table Resources - MCP Resources for A2T Tables and Drafts

包含：
- tables://list: 表格列表
- table://{table_id}/content: 表格內容
- table://{table_id}/status: 表格狀態
- drafts://list: 草稿列表
- draft://{draft_id}/content: 草稿內容
"""

from __future__ import annotations

import json

from src.application.table_service import table_service
from src.infrastructure.config import settings
from src.presentation.mcp_app import mcp
from src.presentation.tools.table_tools import list_drafts, list_tables


@mcp.resource("tables://list")
async def resource_table_list() -> str:
    """Dynamic resource listing all A2T tables."""
    result: str = await list_tables()
    return result


@mcp.resource("table://{table_id}/content")
async def resource_table_content(table_id: str) -> str:
    """
    Dynamic resource for table content in Markdown format.

    This allows AI to read the saved table without re-fetching all data,
    enabling token-efficient table resumption workflows.
    """
    try:
        # Read from saved MD file directly
        md_path = settings.table_output_dir / f"{table_id}.md"
        if md_path.exists():
            return md_path.read_text(encoding="utf-8")
        else:
            # Fallback to preview
            return table_service.preview_table(table_id, limit=100)
    except ValueError:
        return f"Table not found: {table_id}"


@mcp.resource("table://{table_id}/status")
async def resource_table_status(table_id: str) -> str:
    """
    Dynamic resource for compact table status.

    Returns minimal info needed to resume work on a table:
    - Structure (columns)
    - Row count
    - Last 2 rows for context

    This is the most token-efficient way to resume table work.
    """
    try:
        status = table_service.get_table_status(table_id)
        return json.dumps(status, indent=2, ensure_ascii=False)
    except ValueError:
        return f"Table not found: {table_id}"


@mcp.resource("drafts://list")
async def resource_draft_list() -> str:
    """Dynamic resource listing all A2T drafts."""
    result: str = await list_drafts()
    return result


@mcp.resource("draft://{draft_id}/content")
async def resource_draft_content(draft_id: str) -> str:
    """
    Dynamic resource for draft content.

    Returns the full draft state for resumption.
    """
    try:
        draft = table_service.get_draft(draft_id)
        return json.dumps(
            {
                "table_id": draft.table_id,
                "intent": draft.intent,
                "title": draft.title,
                "proposed_columns": draft.proposed_columns,
                "extraction_plan": draft.extraction_plan,
                "source_doc_ids": draft.source_doc_ids,
                "source_sections": draft.source_sections,
                "pending_rows": draft.pending_rows,
                "notes": draft.notes,
                "est_tokens": draft.estimate_tokens(),
            },
            indent=2,
            ensure_ascii=False,
        )
    except ValueError:
        return f"Draft not found: {draft_id}"
