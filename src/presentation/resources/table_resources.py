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

from src.presentation.dependencies import table_service
from src.presentation.markdown_utils import escape_table_cell
from src.presentation.mcp_app import mcp


@mcp.resource("tables://list")
async def resource_table_list() -> str:
    """Dynamic resource listing all A2T tables."""
    tables = table_service.list_tables()
    if not tables:
        return "No tables found."
    lines = ["# 📊 Tables\n"]
    lines.append("| ID | Title | Intent | Rows | Created |")
    lines.append("|----|-------|--------|------|---------|")
    for t in tables:
        lines.append(
            "| `{id}` | {title} | {intent} | {rows} | {created_at} |".format(
                id=escape_table_cell(t["id"]),
                title=escape_table_cell(t["title"]),
                intent=escape_table_cell(t["intent"]),
                rows=escape_table_cell(t["rows"]),
                created_at=escape_table_cell(t["created_at"]),
            )
        )
    return "\n".join(lines)


@mcp.resource("table://{table_id}/content")
async def resource_table_content(table_id: str) -> str:
    """
    Dynamic resource for table content in Markdown format.

    This allows AI to read the saved table without re-fetching all data,
    enabling token-efficient table resumption workflows.
    """
    try:
        table_service.get_table_context(table_id)
        storage_root = table_service.storage_dir.resolve()
        md_path = (storage_root / f"{table_id}.md").resolve()
        md_path.relative_to(storage_root)
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
    drafts = table_service.list_drafts()
    if not drafts:
        return "No drafts found."
    lines = ["# 📝 Drafts\n"]
    lines.append("| ID | Title | Intent | Columns | Pending | Status |")
    lines.append("|----|-------|--------|---------|---------|--------|")
    for d in drafts:
        status = "✅ Has Table" if d["has_table"] else "⏳ Planning"
        lines.append(
            "| `{id}` | {title} | {intent} | {columns} | {pending} | {status} |".format(
                id=escape_table_cell(d["id"]),
                title=escape_table_cell(d["title"]),
                intent=escape_table_cell(d["intent"] or "-"),
                columns=escape_table_cell(d["columns_planned"]),
                pending=escape_table_cell(d["pending_rows"]),
                status=escape_table_cell(status),
            )
        )
    return "\n".join(lines)


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
