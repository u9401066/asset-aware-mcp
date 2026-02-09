"""
Table Tools - A2T (Anything to Table) MCP 工具

包含：
- plan_table_schema: 規劃表格結構
- get_section_content: 讀取章節內容
- create_table_draft: 建立草稿
- update_table_draft: 更新草稿
- add_rows_to_draft: 新增草稿資料
- commit_draft_to_table: 草稿轉正式表格
- list_drafts: 列出草稿
- resume_draft: 恢復草稿
- estimate_tokens: 估算 Token
- create_table: 建立表格
- add_rows: 新增資料列
- update_row: 更新資料列
- delete_row: 刪除資料列
- delete_table: 刪除表格
- list_tables: 列出表格
- update_cell: 更新儲存格
- resume_table: 恢復表格
- preview_table: 預覽表格
- render_table: 渲染表格
"""

from __future__ import annotations

import json
from typing import Any, Literal

from src.presentation.dependencies import asset_service, document_service, table_service
from src.presentation.mcp_app import mcp


@mcp.tool()
async def plan_table_schema(
    question: str,
    doc_ids: list[str] | None = None,
    hints: list[str] | None = None,
) -> str:
    """
    🧠 思考工具：根據問題自動規劃表格結構（Schema Design）。

    這是「先想再做」的抽象化工具，幫助 Agent 在建表前思考：
    - 需要哪些欄位？
    - 每個欄位的資料從哪裡來？
    - 預計有多少列？

    與 Knowledge Graph 並存，不是 fallback。即使 KG 可用，
    也建議先用此工具規劃結構。

    Args:
        question: 使用者的問題或需求（例如：「比較三種藥物的副作用」）
        doc_ids: 相關文件 ID 列表（可選，用於獲取結構提示）
        hints: 額外的結構提示（例如：["包含劑量", "需要引用頁碼"]）

    Returns:
        建議的表格結構（Schema）和抽取計畫
    """
    lines = [
        "# 📋 Table Schema Planning",
        "",
        f"**Question:** {question}",
        "",
    ]

    # Analyze question to suggest intent
    question_lower = question.lower()
    if any(
        kw in question_lower for kw in ["比較", "compare", "vs", "差異", "different"]
    ):
        suggested_intent = "comparison"
        intent_reason = "問題涉及比較分析"
    elif any(
        kw in question_lower for kw in ["引用", "cite", "reference", "來源", "source"]
    ):
        suggested_intent = "citation"
        intent_reason = "問題需要引用來源"
    else:
        suggested_intent = "summary"
        intent_reason = "問題為一般性摘要"

    lines.extend(
        [
            "## Suggested Intent",
            f"**{suggested_intent}** - {intent_reason}",
            "",
            "## Extraction Hints",
        ]
    )

    # Get extraction hints from documents if provided
    extraction_hints = []
    if doc_ids:
        for doc_id in doc_ids:
            manifest = await document_service.get_manifest(doc_id)
            if manifest:
                lines.append(f"\n### From `{doc_id}` ({manifest.title})")

                # Sections as potential data sources
                if manifest.assets.sections:
                    lines.append("**Sections:**")
                    for sec in manifest.assets.sections[:5]:
                        lines.append(f"  - `{sec.id}`: {sec.title}")
                        extraction_hints.append(f"{sec.title} (from {doc_id})")

                # Tables as potential data sources
                if manifest.assets.tables:
                    lines.append("**Existing Tables:**")
                    for tab in manifest.assets.tables[:3]:
                        lines.append(f"  - `{tab.id}`: {tab.caption or 'No caption'}")

                # Figures as potential data sources
                if manifest.assets.figures:
                    lines.append(
                        f"**Figures:** {len(manifest.assets.figures)} available"
                    )

    # Add user hints
    if hints:
        lines.append("\n### User Hints")
        for hint in hints:
            lines.append(f"- {hint}")
            extraction_hints.append(hint)

    # Suggest columns based on intent and question
    lines.extend(
        [
            "",
            "## Suggested Columns",
            "",
            "Based on the question, consider these columns:",
            "",
        ]
    )

    if suggested_intent == "comparison":
        lines.extend(
            [
                "| Column | Type | Purpose |",
                "|--------|------|---------|",
                "| 項目/Item | text | 比較的對象 |",
                "| 特徵1 | text | 第一個比較維度 |",
                "| 特徵2 | text | 第二個比較維度 |",
                "| 差異/Notes | text | 關鍵差異說明 |",
            ]
        )
    elif suggested_intent == "citation":
        lines.extend(
            [
                "| Column | Type | Purpose |",
                "|--------|------|---------|",
                "| 來源/Source | text | 引用來源 |",
                "| 頁碼/Page | number | 頁碼 |",
                "| 內容/Content | text | 引用內容 |",
                "| 備註/Notes | text | 補充說明 |",
            ]
        )
    else:
        lines.extend(
            [
                "| Column | Type | Purpose |",
                "|--------|------|---------|",
                "| 主題/Topic | text | 主題項目 |",
                "| 說明/Description | text | 詳細說明 |",
                "| 公式/Formula | text | 相關公式（如有） |",
                "| 備註/Notes | text | 補充說明 |",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "## Next Steps",
            "",
            "1. **Create Draft:** Use `create_table_draft` to save this plan",
            "2. **Refine:** Adjust columns based on actual content",
            "3. **Execute:** Use `commit_draft_to_table` when ready",
            "",
            "Or directly: `create_table(intent, title, columns)`",
        ]
    )

    return "\n".join(lines)


@mcp.tool()
async def get_section_content(
    doc_id: str,
    section_id: str,
) -> str:
    """
    📖 Section-level 快取：直接讀取特定章節內容。

    比讀取全文更省 Token！從 manifest 的 sections 直接讀取
    特定行範圍，不需要載入整份文件。

    Args:
        doc_id: 文件 ID
        section_id: 章節 ID（從 manifest 獲取）

    Returns:
        章節內容（Markdown 格式）
    """
    result = await asset_service.fetch_asset(doc_id, "section", section_id)

    if not result.success:
        return f"❌ Error: {result.error}"

    # Estimate tokens
    content = result.text_content or ""
    est_tokens = len(content) // 4

    lines = [
        f"## Section: {section_id}",
        f"**Page:** {result.page or 'Unknown'}",
        f"**Est. Tokens:** ~{est_tokens}",
        "",
        "---",
        "",
        content,
    ]

    return "\n".join(lines)


@mcp.tool()
async def create_table_draft(
    title: str,
    intent: Literal["comparison", "citation", "summary"] | None = None,
    proposed_columns: list[dict] | None = None,
    extraction_plan: list[str] | None = None,
    source_doc_ids: list[str] | None = None,
    source_sections: list[str] | None = None,
    notes: str = "",
) -> str:
    """
    📝 建立表格草稿（Draft）- 支援斷點續傳。

    草稿會自動保存，即使對話中斷也能恢復。
    這是長表格工作流程的起點。

    Args:
        title: 表格標題
        intent: 表格類型 (comparison/citation/summary)
        proposed_columns: 規劃的欄位 [{"name": "...", "type": "text"}]
        extraction_plan: 抽取計畫（要從哪裡取什麼資料）
        source_doc_ids: 來源文件 ID 列表
        source_sections: 來源章節 ID 列表
        notes: 工作筆記

    Returns:
        draft_id 和狀態摘要
    """
    draft_id = table_service.create_draft(
        title=title,
        intent=intent,
        proposed_columns=proposed_columns,
        extraction_plan=extraction_plan,
        source_doc_ids=source_doc_ids,
        source_sections=source_sections,
        notes=notes,
    )

    draft = table_service.get_draft(draft_id)

    lines = [
        f"✅ Draft created: `{draft_id}`",
        "",
        f"**Title:** {draft.title}",
        f"**Intent:** {draft.intent or 'Not set'}",
        f"**Columns:** {len(draft.proposed_columns)}",
        f"**Sources:** {len(draft.source_doc_ids)} docs, {len(draft.source_sections)} sections",
        "",
        "---",
        "**Next steps:**",
        f"- Update: `update_table_draft('{draft_id}', ...)`",
        f"- Add rows: `add_rows_to_draft('{draft_id}', [...])`",
        f"- Commit: `commit_draft_to_table('{draft_id}')`",
    ]

    return "\n".join(lines)


@mcp.tool()
async def update_table_draft(
    draft_id: str,
    title: str | None = None,
    intent: Literal["comparison", "citation", "summary"] | None = None,
    proposed_columns: list[dict] | None = None,
    extraction_plan: list[str] | None = None,
    source_sections: list[str] | None = None,
    notes: str | None = None,
) -> str:
    """
    更新草稿內容。

    Args:
        draft_id: 草稿 ID
        其他參數: 要更新的欄位（None 表示不更新）

    Returns:
        更新後的狀態
    """
    updates: dict[str, Any] = {}
    if title is not None:
        updates["title"] = title
    if intent is not None:
        updates["intent"] = intent
    if proposed_columns is not None:
        updates["proposed_columns"] = proposed_columns
    if extraction_plan is not None:
        updates["extraction_plan"] = extraction_plan
    if source_sections is not None:
        updates["source_sections"] = source_sections
    if notes is not None:
        updates["notes"] = notes

    try:
        table_service.update_draft(draft_id, **updates)
        draft = table_service.get_draft(draft_id)

        return (
            f"✅ Draft `{draft_id}` updated.\n\n"
            f"**Title:** {draft.title}\n"
            f"**Intent:** {draft.intent}\n"
            f"**Columns:** {len(draft.proposed_columns)}\n"
            f"**Pending Rows:** {len(draft.pending_rows)}\n"
            f"**Est. Tokens:** ~{draft.estimate_tokens()}"
        )
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def add_rows_to_draft(
    draft_id: str,
    rows: list[dict],
) -> str:
    """
    📦 批次新增資料到草稿（Batch Streaming）。

    資料先暫存在草稿中，不會立即建表。
    適合長表格的分批處理工作流程。

    Args:
        draft_id: 草稿 ID
        rows: 要新增的資料列

    Returns:
        更新後的狀態
    """
    try:
        draft = table_service.get_draft(draft_id)
        draft.pending_rows.extend(rows)
        table_service.update_draft(draft_id, pending_rows=draft.pending_rows)

        return (
            f"✅ Added {len(rows)} rows to draft.\n\n"
            f"**Total Pending:** {len(draft.pending_rows)} rows\n"
            f"**Est. Tokens:** ~{draft.estimate_tokens()}"
        )
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def commit_draft_to_table(
    draft_id: str,
) -> str:
    """
    🚀 將草稿轉換為正式表格。

    這會：
    1. 根據草稿的欄位定義建立表格
    2. 將所有 pending_rows 加入表格
    3. 保留草稿（記錄 table_id）

    Args:
        draft_id: 草稿 ID

    Returns:
        新建的 table_id 和狀態
    """
    try:
        table_id = table_service.commit_draft_to_table(draft_id)
        preview = table_service.preview_table(table_id, limit=5)

        return (
            f"✅ Draft committed to table!\n\n"
            f"**Table ID:** `{table_id}`\n"
            f"**Draft ID:** `{draft_id}` (preserved)\n\n"
            f"{preview}"
        )
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def list_drafts() -> str:
    """
    列出所有草稿。

    Returns:
        草稿列表
    """
    drafts = table_service.list_drafts()

    if not drafts:
        return "No drafts found. Use `create_table_draft` to start planning."

    lines = ["# 📝 Table Drafts\n"]
    lines.append("| ID | Title | Intent | Columns | Pending | Status |")
    lines.append("|----|-------|--------|---------|---------|--------|")

    for d in drafts:
        status = "✅ Has Table" if d["has_table"] else "⏳ Planning"
        lines.append(
            f"| `{d['id']}` | {d['title']} | {d['intent'] or '-'} | "
            f"{d['columns_planned']} | {d['pending_rows']} | {status} |"
        )

    return "\n".join(lines)


@mcp.tool()
async def resume_draft(
    draft_id: str,
) -> str:
    """
    📋 恢復草稿工作（Token-efficient resumption）。

    返回草稿的完整狀態，包含：
    - 規劃的結構
    - 抽取計畫
    - 已暫存的資料
    - 工作筆記

    Args:
        draft_id: 草稿 ID

    Returns:
        草稿完整狀態
    """
    try:
        draft = table_service.get_draft(draft_id)

        lines = [
            f"# 📋 Resume Draft: {draft.title}",
            "",
            f"**ID:** `{draft_id}`",
            f"**Intent:** {draft.intent or 'Not set'}",
            f"**Table:** `{draft.table_id}`"
            if draft.table_id
            else "**Table:** Not created yet",
            "",
        ]

        # Columns
        if draft.proposed_columns:
            lines.append("## Proposed Columns")
            lines.append("```json")
            lines.append(
                json.dumps(draft.proposed_columns, indent=2, ensure_ascii=False)
            )
            lines.append("```")

        # Extraction plan
        if draft.extraction_plan:
            lines.append("\n## Extraction Plan")
            for i, step in enumerate(draft.extraction_plan, 1):
                lines.append(f"{i}. {step}")

        # Sources
        if draft.source_doc_ids or draft.source_sections:
            lines.append("\n## Sources")
            if draft.source_doc_ids:
                lines.append(f"**Documents:** {', '.join(draft.source_doc_ids)}")
            if draft.source_sections:
                lines.append(f"**Sections:** {', '.join(draft.source_sections)}")

        # Pending rows (show last 2)
        if draft.pending_rows:
            lines.append(f"\n## Pending Rows ({len(draft.pending_rows)} total)")
            lines.append("Last 2 rows:")
            lines.append("```json")
            lines.append(
                json.dumps(draft.pending_rows[-2:], indent=2, ensure_ascii=False)
            )
            lines.append("```")

        # Notes
        if draft.notes:
            lines.append(f"\n## Working Notes\n{draft.notes}")

        # Token estimate
        lines.append(f"\n---\n**Est. Tokens:** ~{draft.estimate_tokens()}")

        return "\n".join(lines)
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def estimate_tokens(
    table_id: str | None = None,
    draft_id: str | None = None,
    text: str | None = None,
) -> str:
    """
    📊 估算 Token 消耗。

    可以估算：
    - 表格的 token 數
    - 草稿的 token 數
    - 任意文字的 token 數

    Args:
        table_id: 表格 ID（可選）
        draft_id: 草稿 ID（可選）
        text: 任意文字（可選）

    Returns:
        Token 估算結果
    """
    lines = ["# 📊 Token Estimation\n"]

    if table_id:
        try:
            status = table_service.get_table_status(table_id)
            # Rough estimate: ~4 chars per token
            content = table_service.preview_table(table_id, limit=1000)
            est = len(content) // 4
            lines.append(f"**Table `{table_id}`:** ~{est} tokens ({status['row_count']} rows)")
        except ValueError:
            lines.append(f"**Table `{table_id}`:** Not found")

    if draft_id:
        try:
            draft = table_service.get_draft(draft_id)
            est = draft.estimate_tokens()
            lines.append(f"**Draft `{draft_id}`:** ~{est} tokens ({len(draft.pending_rows)} pending rows)")
        except ValueError:
            lines.append(f"**Draft `{draft_id}`:** Not found")

    if text:
        est = len(text) // 4
        lines.append(f"**Text:** ~{est} tokens ({len(text)} chars)")

    if len(lines) == 1:
        lines.append("Provide `table_id`, `draft_id`, or `text` to estimate.")

    return "\n".join(lines)


@mcp.tool()
async def create_table(
    intent: Literal["comparison", "citation", "summary"],
    title: str,
    columns: list[dict],
    source_description: str = "",
) -> str:
    """
    建立一張新表格，定義欄位結構。

    Args:
        intent: 表格類型，影響自動美化邏輯
            - comparison: 橫向對比 (自動加入差異標註)
            - citation: 文獻引用 (自動加入來源連結)
            - summary: 摘要總結 (自動加入編號)
        title: 表格標題
        columns: 欄位定義列表，例如 [{"name": "藥物", "type": "text"}]
        source_description: 資料來源說明

    Returns:
        table_id: 用於後續操作的識別碼
    """
    table_id = table_service.create_table(
        intent=intent,
        title=title,
        columns=columns,
        source_description=source_description,
    )
    preview = table_service.preview_table(table_id)
    return f"✅ Table created successfully. **table_id:** `{table_id}`\n\n{preview}"


@mcp.tool()
async def add_rows(
    table_id: str,
    rows: list[dict],
) -> str:
    """
    新增資料列到表格（可多次呼叫）。

    Args:
        table_id: create_table 返回的識別碼
        rows: 資料列列表，每列為 {column_name: value} 字典

    Returns:
        執行結果摘要
    """
    try:
        result = table_service.add_rows(table_id, rows)
        if result["success"]:
            preview = table_service.preview_table(table_id)
            msg = f"✅ Added {result['added']} rows. Total: {result['total_rows']}.\n\n{preview}"
            if result.get("errors"):
                msg += f"\n⚠️ Warning: {len(result['errors'])} rows had validation errors and were skipped."
            return msg
        else:
            return f"❌ Failed to add rows. Errors: {result.get('errors')}"
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def update_row(
    table_id: str,
    index: int,
    row: dict,
) -> str:
    """
    更新表格中的特定資料列。

    Args:
        table_id: 表格識別碼
        index: 資料列索引 (0-based)
        row: 新的資料列內容

    Returns:
        執行結果
    """
    try:
        result = table_service.update_row(table_id, index, row)
        if result["success"]:
            preview = table_service.preview_table(table_id)
            return f"✅ Row {index} updated successfully.\n\n{preview}"
        else:
            return f"❌ Failed to update row. Errors: {result.get('errors')}"
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def delete_row(
    table_id: str,
    index: int,
) -> str:
    """
    刪除表格中的特定資料列。

    Args:
        table_id: 表格識別碼
        index: 資料列索引 (0-based)

    Returns:
        執行結果
    """
    try:
        result = table_service.delete_row(table_id, index)
        preview = table_service.preview_table(table_id)
        return (
            f"✅ Row {index} deleted. Total rows: {result['total_rows']}.\n\n{preview}"
        )
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def delete_table(
    table_id: str,
) -> str:
    """
    刪除整張表格及其相關檔案。

    Args:
        table_id: 表格識別碼

    Returns:
        執行結果
    """
    if table_service.delete_table(table_id):
        return f"✅ Table `{table_id}` and its files have been deleted."
    else:
        return f"❌ Table `{table_id}` not found."


@mcp.tool()
async def list_tables() -> str:
    """
    列出所有目前正在處理或已儲存的表格。

    Returns:
        表格列表 (Markdown 格式)
    """
    tables = table_service.list_tables()
    if not tables:
        return "No tables found. Use `create_table` to start a new one."

    lines = ["# 📊 Available Tables\n"]
    lines.append("| ID | Title | Intent | Rows | Created |")
    lines.append("|----|-------|--------|------|---------|")
    for t in tables:
        lines.append(
            f"| `{t['id']}` | {t['title']} | {t['intent']} | {t['rows']} | {t['created_at']} |"
        )

    return "\n".join(lines)


@mcp.tool()
async def update_cell(
    table_id: str,
    row_index: int,
    column_name: str,
    value: str,
) -> str:
    """
    更新表格中的單一儲存格（Cell-level CRUD）。

    Args:
        table_id: 表格識別碼
        row_index: 資料列索引 (0-based)
        column_name: 欄位名稱
        value: 新的值

    Returns:
        執行結果
    """
    try:
        result = table_service.update_cell(table_id, row_index, column_name, value)
        return (
            f"✅ Cell updated successfully.\n\n"
            f"- **Row:** {result['row_index']}\n"
            f"- **Column:** {result['column']}\n"
            f"- **Old:** {result['old_value']}\n"
            f"- **New:** {result['new_value']}"
        )
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def resume_table(table_id: str) -> str:
    """
    恢復未完成的表格工作（節省 Token 的恢復機制）。

    返回表格的緊湊狀態，包含結構定義和最後幾筆資料，
    讓 AI 可以繼續工作而不需要重新載入全部內容。

    Args:
        table_id: 表格識別碼

    Returns:
        表格緊湊狀態（結構 + 最後 2 筆資料）
    """
    try:
        status = table_service.get_table_status(table_id)

        lines = [
            f"# 📋 Resume Table: {status['title']}",
            "",
            f"**ID:** `{status['id']}`",
            f"**Intent:** {status['intent']}",
            f"**Columns:** {', '.join(status['columns'])}",
            f"**Current Rows:** {status['row_count']}",
            f"**Source:** {status['source_description']}",
            "",
        ]

        if status["last_rows"]:
            lines.append("## Last Rows (for context)")
            lines.append("```json")
            lines.append(json.dumps(status["last_rows"], indent=2, ensure_ascii=False))
            lines.append("```")

        lines.extend(
            [
                "",
                "---",
                "**Continue with:**",
                f"- `add_rows('{table_id}', [...])` - 新增更多資料",
                f"- `preview_table('{table_id}')` - 查看完整表格",
                f"- `render_table('{table_id}')` - 輸出為 Excel",
            ]
        )

        return "\n".join(lines)
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def preview_table(
    table_id: str,
    limit: int = 10,
) -> str:
    """
    預覽表格內容（Markdown 格式）。

    Args:
        table_id: create_table 返回的識別碼
        limit: 預覽行數限制

    Returns:
        Markdown 格式的表格預覽
    """
    try:
        return table_service.preview_table(table_id, limit)
    except ValueError as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def render_table(
    table_id: str,
    format: Literal["excel", "markdown", "html"] = "excel",
    filename: str = "output",
) -> str:
    """
    渲染最終輸出，自動套用美化。

    Args:
        table_id: create_table 返回的識別碼
        format: 輸出格式 (目前僅支援 excel)
        filename: 輸出檔案名稱 (不含副檔名)

    Returns:
        渲染結果與檔案路徑
    """
    try:
        if hasattr(table_service, "render_table"):
            result = await table_service.render_table(table_id, format, filename)
            return (
                f"✅ Table rendered successfully!\n\n"
                f"- **Format:** {result['format']}\n"
                f"- **Path:** `{result['file_path']}`\n"
                f"- **Rows:** {result['row_count']}"
            )
        else:
            return "🚧 `render_table` is still under development (Phase 2)."
    except Exception as e:
        return f"❌ Error during rendering: {str(e)}"
