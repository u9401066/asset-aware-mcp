"""
Table Tools - A2T (Anything to Table) MCP 工具（v0.2.14 合併版）

7 operation-based tools（原 19 工具合併）：
- plan_table: 規劃 + 模板
- table_manage: 表格 CRUD + Schema 演進
- table_data: 資料列/儲存格 CRUD
- table_cite: 引用管理
- table_history: 變更歷史 + Token 估算
- table_draft: 草稿工作流
- discover_sources: 資料來源探索
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Literal

from src.presentation.dependencies import (
    document_service,
    table_service,
)
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import log_message, report_progress

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    Context = Any

logger = logging.getLogger(__name__)

# ============================================================================
# 1. plan_table — 規劃 + 模板
# ============================================================================


@mcp.tool()
async def plan_table(
    operation: Literal["schema", "templates", "from_template"],
    # schema
    question: str = "",
    doc_ids: list[str] | None = None,
    hints: list[str] | None = None,
    # from_template
    template_name: str = "",
    title_override: str = "",
) -> str:
    """
    📋 表格規劃工具：Schema 設計、模板查詢、模板建表。

    Operations:
    - **schema**: 根據問題自動規劃表格結構
    - **templates**: 列出內建表格模板
    - **from_template**: 從模板快速建立表格

    Args:
        operation: 操作類型
        question: [schema] 使用者問題
        doc_ids: [schema] 相關文件 ID
        hints: [schema] 結構提示
        template_name: [from_template] 模板名稱
        title_override: [from_template] 自訂標題

    Examples:
        plan_table("schema", question="比較三種藥物副作用")
        plan_table("templates")
        plan_table("from_template", template_name="drug_comparison")
    """
    if operation == "schema":
        return await _plan_schema(question, doc_ids, hints)
    elif operation == "templates":
        return _list_templates()
    elif operation == "from_template":
        return _create_from_template(template_name, title_override)
    else:
        return f"❌ Unknown operation: {operation}"


async def _plan_schema(
    question: str,
    doc_ids: list[str] | None,
    hints: list[str] | None,
) -> str:
    """規劃表格結構。"""
    if not question:
        return "❌ `question` is required for schema planning."

    lines = [
        "# 📋 Table Schema Planning",
        "",
        f"**Question:** {question}",
        "",
    ]

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

    if doc_ids:
        for doc_id in doc_ids:
            manifest = await document_service.get_manifest(doc_id)
            if manifest:
                lines.append(f"\n### From `{doc_id}` ({manifest.title})")
                if manifest.assets.sections:
                    lines.append("**Sections:**")
                    for sec in manifest.assets.sections[:5]:
                        lines.append(f"  - `{sec.id}`: {sec.title}")
                if manifest.assets.tables:
                    lines.append("**Existing Tables:**")
                    for tab in manifest.assets.tables[:3]:
                        lines.append(f"  - `{tab.id}`: {tab.caption or 'No caption'}")
                if manifest.assets.figures:
                    lines.append(
                        f"**Figures:** {len(manifest.assets.figures)} available"
                    )

    if hints:
        lines.append("\n### User Hints")
        for hint in hints:
            lines.append(f"- {hint}")

    lines.extend(
        [
            "",
            "## Suggested Columns",
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
                "| 備註/Notes | text | 補充說明 |",
            ]
        )

    lines.extend(
        [
            "",
            "💡 **Tip:** Use `plan_table('templates')` to see built-in templates,",
            "or `table_manage('create', ...)` to directly create a table.",
        ]
    )

    return "\n".join(lines)


def _list_templates() -> str:
    """列出內建模板。"""
    templates = table_service.list_templates()
    if not templates:
        return "No templates available."

    lines = ["# 📑 Table Templates\n"]
    for t in templates:
        lines.append(f"### `{t['name']}` — {t['title']}")
        lines.append(f"*{t['description']}* (intent: {t['intent']})")
        lines.append("")
        lines.append("| Column | Type | Required |")
        lines.append("|--------|------|----------|")
        for c in t["columns"]:
            req = "✅" if c.get("required", True) else "❌"
            lines.append(f"| {c['name']} | {c['type']} | {req} |")
        lines.append("")

    lines.append("💡 Use `plan_table('from_template', template_name='...')` to create.")
    return "\n".join(lines)


def _create_from_template(template_name: str, title_override: str) -> str:
    """從模板建立表格。"""
    if not template_name:
        return "❌ `template_name` is required."
    try:
        table_id = table_service.create_from_template(template_name, title_override)
        preview = table_service.preview_table(table_id)
        return f"✅ Created from template `{template_name}`\n**table_id:** `{table_id}`\n\n{preview}"
    except ValueError as e:
        return f"❌ Error: {e}"


# ============================================================================
# 2. table_manage — 表格 CRUD + Schema 演進
# ============================================================================


@mcp.tool()
async def table_manage(
    operation: Literal[
        "create",
        "delete",
        "list",
        "preview",
        "resume",
        "render",
        "add_column",
        "remove_column",
        "rename_column",
    ],
    # create
    intent: Literal["comparison", "citation", "summary"] | None = None,
    title: str = "",
    columns: list[dict] | None = None,
    source_description: str = "",
    # common
    table_id: str = "",
    # preview
    limit: int = 10,
    # render
    format: Literal["excel", "markdown", "html"] = "excel",
    filename: str = "output",
    # add_column
    column_name: str = "",
    column_type: str = "text",
    required: bool = False,
    default_value: str | None = None,
    enum_values: list[str] | None = None,
    # rename_column
    new_name: str = "",
    ctx: Context | None = None,
) -> str:
    """
    📊 表格管理工具：建立、刪除、列表、預覽、渲染、Schema 演進。

    Operations:
    - **create**: 建立新表格
    - **delete**: 刪除表格
    - **list**: 列出所有表格
    - **preview**: Markdown 預覽
    - **resume**: 恢復工作（Token-efficient）
    - **render**: 渲染為 Excel/Markdown
    - **add_column**: 新增欄位
    - **remove_column**: 移除欄位
    - **rename_column**: 重新命名欄位

    Args:
        operation: 操作類型
        intent: [create] comparison / citation / summary
        title: [create] 表格標題
        columns: [create] 欄位列表 [{"name":"Drug","type":"text"}]
        source_description: [create] 資料來源
        table_id: [大部分操作] 表格 ID
        limit: [preview] 預覽行數
        format: [render] 輸出格式
        filename: [render] 檔案名稱
        column_name: [add/remove/rename_column] 欄位名
        column_type: [add_column] 欄位類型
        required: [add_column] 是否必填
        default_value: [add_column] 預設值
        enum_values: [add_column] enum 可選值
        new_name: [rename_column] 新欄位名

    Examples:
        table_manage("create", intent="comparison", title="Drug Compare",
                     columns=[{"name":"Drug","type":"text"}])
        table_manage("list")
        table_manage("preview", table_id="tbl_xxx")
        table_manage("add_column", table_id="tbl_xxx", column_name="Route",
                     column_type="enum", enum_values=["IV","IM"])
    """
    try:
        if operation == "create":
            return _table_create(intent, title, columns, source_description)
        elif operation == "delete":
            return _table_delete(table_id)
        elif operation == "list":
            return _table_list()
        elif operation == "preview":
            return table_service.preview_table(table_id, limit)
        elif operation == "resume":
            return _table_resume(table_id)
        elif operation == "render":
            return await _table_render(table_id, format, filename, ctx=ctx)
        elif operation == "add_column":
            return _schema_add_column(
                table_id, column_name, column_type, required, default_value, enum_values
            )
        elif operation == "remove_column":
            return _schema_remove_column(table_id, column_name)
        elif operation == "rename_column":
            return _schema_rename_column(table_id, column_name, new_name)
        else:
            return f"❌ Unknown operation: {operation}"
    except ValueError as e:
        return f"❌ Error: {e}"


def _table_create(
    intent: Literal["comparison", "citation", "summary"] | None,
    title: str,
    columns: list[dict] | None,
    source_description: str,
) -> str:
    if not intent or not title or not columns:
        return "❌ `intent`, `title`, and `columns` are required."
    table_id = table_service.create_table(
        intent=intent,
        title=title,
        columns=columns,
        source_description=source_description,
    )
    preview = table_service.preview_table(table_id)
    return f"✅ Table created. **table_id:** `{table_id}`\n\n{preview}"


def _table_delete(table_id: str) -> str:
    if not table_id:
        return "❌ `table_id` is required."
    if table_service.delete_table(table_id):
        return f"✅ Table `{table_id}` deleted."
    return f"❌ Table `{table_id}` not found."


def _table_list() -> str:
    tables = table_service.list_tables()
    if not tables:
        return "No tables found. Use `table_manage('create', ...)` to start."

    lines = ["# 📊 Tables\n"]
    lines.append("| ID | Title | Intent | Rows | Cites | Created |")
    lines.append("|----|-------|--------|------|-------|---------|")
    for t in tables:
        lines.append(
            f"| `{t['id']}` | {t['title']} | {t['intent']} "
            f"| {t['rows']} | {t['citations']} | {t['created_at']} |"
        )
    return "\n".join(lines)


def _table_resume(table_id: str) -> str:
    if not table_id:
        return "❌ `table_id` is required."
    status = table_service.get_table_status(table_id)
    lines = [
        f"# 📋 Resume: {status['title']}",
        "",
        f"**ID:** `{status['id']}` | **Intent:** {status['intent']}",
        f"**Columns:** {', '.join(status['columns'])}",
        f"**Rows:** {status['row_count']} | **Citations:** {status['citation_count']}",
    ]
    if status.get("source_description"):
        lines.append(f"**Source:** {status['source_description']}")
    if status["last_rows"]:
        lines.append("\n## Last Rows")
        lines.append("```json")
        lines.append(json.dumps(status["last_rows"], indent=2, ensure_ascii=False))
        lines.append("```")
    return "\n".join(lines)


async def _table_render(
    table_id: str,
    fmt: Literal["excel", "markdown", "html"],
    filename: str,
    ctx: Context | None = None,
) -> str:
    if not table_id:
        return "❌ `table_id` is required."
    await log_message(ctx, "info", f"table_render start: {table_id} format={fmt}")
    await report_progress(ctx, 15, message=f"Rendering table {table_id}")
    result = await table_service.render_table(table_id, fmt, filename)
    await report_progress(ctx, 100, message=f"Rendered table {table_id}")
    await log_message(ctx, "info", f"table_render complete: {table_id}")
    return (
        f"✅ Rendered!\n"
        f"- **Format:** {result['format']}\n"
        f"- **Path:** `{result['file_path']}`\n"
        f"- **Rows:** {result['row_count']}"
    )


def _schema_add_column(
    table_id: str,
    name: str,
    col_type: str,
    required: bool,
    default_value: Any,
    enum_values: list[str] | None,
) -> str:
    if not table_id or not name:
        return "❌ `table_id` and `column_name` are required."
    result = table_service.add_column(
        table_id, name, col_type, required, default_value, enum_values
    )
    if result["success"]:
        return f"✅ Column `{name}` added. Columns: {result['columns']}"
    return f"❌ {result['error']}"


def _schema_remove_column(table_id: str, name: str) -> str:
    if not table_id or not name:
        return "❌ `table_id` and `column_name` are required."
    result = table_service.remove_column(table_id, name)
    if result["success"]:
        return f"✅ Column `{name}` removed. Columns: {result['columns']}"
    return f"❌ {result['error']}"


def _schema_rename_column(table_id: str, old_name: str, new_name: str) -> str:
    if not table_id or not old_name or not new_name:
        return "❌ `table_id`, `column_name`, and `new_name` are required."
    result = table_service.rename_column(table_id, old_name, new_name)
    if result["success"]:
        return f"✅ Column `{old_name}` → `{new_name}`. Columns: {result['columns']}"
    return f"❌ {result['error']}"


# ============================================================================
# 3. table_data — 資料列/儲存格 CRUD
# ============================================================================


@mcp.tool()
async def table_data(
    operation: Literal[
        "add_rows",
        "get_row",
        "update_row",
        "delete_row",
        "get_cell",
        "update_cell",
        "clear_cell",
    ],
    table_id: str,
    # add_rows / update_row
    rows: list[dict] | None = None,
    row: dict | None = None,
    # row operations
    row_index: int = -1,
    # cell operations
    column_name: str = "",
    value: str | None = None,
) -> str:
    """
    📝 表格資料操作：新增/取得/更新/刪除 列 & 儲存格。

    Operations:
    - **add_rows**: 批次新增資料列
    - **get_row**: 取得單列（含引用）
    - **update_row**: 整列更新
    - **delete_row**: 刪除列
    - **get_cell**: 取得單格（含引用）
    - **update_cell**: 更新單格
    - **clear_cell**: 清除單格

    Args:
        operation: 操作類型
        table_id: 表格 ID
        rows: [add_rows] 資料列列表
        row: [update_row] 新的列資料
        row_index: [get/update/delete_row, cell ops] 列索引 (0-based)
        column_name: [cell ops] 欄位名
        value: [update_cell] 新的值

    Examples:
        table_data("add_rows", "tbl_xxx", rows=[{"Drug":"A","Dose":1}])
        table_data("get_row", "tbl_xxx", row_index=0)
        table_data("update_cell", "tbl_xxx", row_index=0, column_name="Drug", value="B")
    """
    try:
        if operation == "add_rows":
            return _data_add_rows(table_id, rows)
        elif operation == "get_row":
            return _data_get_row(table_id, row_index)
        elif operation == "update_row":
            return _data_update_row(table_id, row_index, row)
        elif operation == "delete_row":
            return _data_delete_row(table_id, row_index)
        elif operation == "get_cell":
            return _data_get_cell(table_id, row_index, column_name)
        elif operation == "update_cell":
            return _data_update_cell(table_id, row_index, column_name, value)
        elif operation == "clear_cell":
            return _data_clear_cell(table_id, row_index, column_name)
        else:
            return f"❌ Unknown operation: {operation}"
    except ValueError as e:
        return f"❌ Error: {e}"


def _data_add_rows(table_id: str, rows: list[dict] | None) -> str:
    if not rows:
        return "❌ `rows` is required."
    result = table_service.add_rows(table_id, rows)
    if result["success"]:
        preview = table_service.preview_table(table_id)
        msg = f"✅ Added {result['added']} rows. Total: {result['total_rows']}.\n\n{preview}"
        if result.get("errors"):
            msg += f"\n⚠️ {len(result['errors'])} rows skipped (validation errors)."
        return msg
    return f"❌ Failed. Errors: {result.get('errors')}"


def _data_get_row(table_id: str, row_index: int) -> str:
    if row_index < 0:
        return "❌ `row_index` is required (0-based)."
    result = table_service.get_row(table_id, row_index)
    lines = [
        f"## Row {result['row_index']}",
        "```json",
        json.dumps(result["data"], indent=2, ensure_ascii=False),
        "```",
    ]
    if result.get("citations"):
        lines.append("\n**Citations:**")
        for col, cite in result["citations"].items():
            refs_count = len(cite.get("refs", []))
            conf = cite.get("confidence", "N/A")
            lines.append(f"  - `{col}`: {refs_count} refs (confidence: {conf})")
    return "\n".join(lines)


def _data_update_row(table_id: str, row_index: int, row: dict | None) -> str:
    if row_index < 0 or not row:
        return "❌ `row_index` and `row` are required."
    result = table_service.update_row(table_id, row_index, row)
    if result["success"]:
        preview = table_service.preview_table(table_id)
        return f"✅ Row {row_index} updated.\n\n{preview}"
    return f"❌ {result.get('errors')}"


def _data_delete_row(table_id: str, row_index: int) -> str:
    if row_index < 0:
        return "❌ `row_index` is required (0-based)."
    result = table_service.delete_row(table_id, row_index)
    preview = table_service.preview_table(table_id)
    return f"✅ Row {row_index} deleted. Total: {result['total_rows']}.\n\n{preview}"


def _data_get_cell(table_id: str, row_index: int, column_name: str) -> str:
    if row_index < 0 or not column_name:
        return "❌ `row_index` and `column_name` are required."
    result = table_service.get_cell(table_id, row_index, column_name)
    lines = [
        f"**Cell [{row_index}:{column_name}]:** `{result['value']}`",
    ]
    if result.get("citation"):
        cite = result["citation"]
        refs_count = len(cite.get("refs", []))
        lines.append(
            f"**Citation:** {refs_count} refs, confidence: {cite.get('confidence', 'N/A')}"
        )
    return "\n".join(lines)


def _data_update_cell(
    table_id: str, row_index: int, column_name: str, value: Any
) -> str:
    if row_index < 0 or not column_name:
        return "❌ `row_index` and `column_name` are required."
    result = table_service.update_cell(table_id, row_index, column_name, value)
    value_str = str(value) if value is not None else ""
    char_count = len(value_str)
    line_count = value_str.count("\n")

    msg = (
        f"✅ Cell updated.\n"
        f"- **[{result['row_index']}:{result['column']}]**\n"
        f"- Old: `{result['old_value']}` → New: `{result['new_value']}`\n"
        f"- **字元數**: {char_count}"
    )
    if line_count > 0:
        msg += f" (含 {line_count} 個換行符，將以 `<br>` 轉義寫入 DFM)"
    return msg


def _data_clear_cell(table_id: str, row_index: int, column_name: str) -> str:
    if row_index < 0 or not column_name:
        return "❌ `row_index` and `column_name` are required."
    result = table_service.clear_cell(table_id, row_index, column_name)
    return f"✅ Cell [{row_index}:{column_name}] cleared. Old value: `{result['old_value']}`"


# ============================================================================
# 4. table_cite — 引用管理
# ============================================================================


@mcp.tool()
async def table_cite(
    operation: Literal["add", "get", "remove", "cell_history"],
    table_id: str,
    row_index: int = -1,
    column_name: str = "",
    # add
    refs: list[dict] | None = None,
    confidence: float | None = None,
    notes: str = "",
    # remove
    ref_index: int | None = None,
) -> str:
    """
    📎 表格引用管理：為儲存格附加、查詢、移除來源引用。

    引用是「平行附加層」，不改變表格資料結構。
    每個引用用 AssetRef 指向具體來源（PDF section、URL、使用者輸入等）。

    Operations:
    - **add**: 新增引用到儲存格
    - **get**: 查詢引用（cell / row / table）
    - **remove**: 移除引用
    - **cell_history**: 查看儲存格變更歷史

    Args:
        operation: 操作類型
        table_id: 表格 ID
        row_index: 列索引 (0-based)，get 時可省略取得全表引用
        column_name: 欄位名，get 時可省略取得整列引用
        refs: [add] 引用列表，每項為 AssetRef dict
            [{"source_type":"section","doc_id":"doc_xxx","asset_id":"sec_01","excerpt":"..."}]
            [{"source_type":"external","url":"https://doi.org/...","label":"Smith 2024"}]
            [{"source_type":"user_input","excerpt":"Patient reported"}]
        confidence: [add] Agent 信心度 0.0~1.0
        notes: [add] 備註
        ref_index: [remove] 移除特定引用索引（不指定則移除整個 cell 引用）

    Examples:
        table_cite("add", "tbl_xxx", row_index=0, column_name="Drug",
                   refs=[{"source_type":"section","doc_id":"doc_a","asset_id":"sec_01",
                          "excerpt":"dose was 5mg"}],
                   confidence=0.9)
        table_cite("get", "tbl_xxx")  # 全表引用
        table_cite("get", "tbl_xxx", row_index=0)  # 全列引用
        table_cite("cell_history", "tbl_xxx", row_index=0, column_name="Drug")
    """
    try:
        if operation == "add":
            return _cite_add(table_id, row_index, column_name, refs, confidence, notes)
        elif operation == "get":
            return _cite_get(table_id, row_index, column_name)
        elif operation == "remove":
            return _cite_remove(table_id, row_index, column_name, ref_index)
        elif operation == "cell_history":
            return _cite_cell_history(table_id, row_index, column_name)
        else:
            return f"❌ Unknown operation: {operation}"
    except ValueError as e:
        return f"❌ Error: {e}"


def _cite_add(
    table_id: str,
    row_index: int,
    column_name: str,
    refs: list[dict] | None,
    confidence: float | None,
    notes: str,
) -> str:
    if row_index < 0 or not column_name or not refs:
        return "❌ `row_index`, `column_name`, and `refs` are required."
    result = table_service.add_citation(
        table_id, row_index, column_name, refs, confidence, notes
    )
    return f"✅ Citation added to {result['cell']}. Total refs: {result['total_refs']}"


def _cite_get(
    table_id: str,
    row_index: int,
    column_name: str,
) -> str:
    ri = row_index if row_index >= 0 else None
    cn = column_name if column_name else None
    result = table_service.get_citations(table_id, ri, cn)

    if "citation" in result:
        # Single cell
        cite = result["citation"]
        if cite is None:
            return f"No citation for {result['cell']}."
        refs = cite.get("refs", [])
        lines = [f"## Citation: {result['cell']}", ""]
        for i, ref in enumerate(refs):
            lines.append(
                f"  [{i}] **{ref['source_type']}**: {ref.get('label', ref.get('excerpt', ref.get('url', ''))[:60])}"
            )
        if cite.get("confidence") is not None:
            lines.append(f"\n**Confidence:** {cite['confidence']}")
        if cite.get("notes"):
            lines.append(f"**Notes:** {cite['notes']}")
        return "\n".join(lines)
    elif "row" in result:
        # Row citations
        cites = result.get("citations", {})
        if not cites:
            return f"No citations for row {result['row']}."
        lines = [f"## Row {result['row']} Citations\n"]
        for col, cite in cites.items():
            refs_count = len(cite.get("refs", []))
            lines.append(f"- **{col}**: {refs_count} refs")
        return "\n".join(lines)
    else:
        # Table-level
        total = result.get("total_citations", 0)
        if total == 0:
            return f"No citations in table `{table_id}`."
        lines = [f"## Table Citations ({total} cells)\n"]
        for key, cite in result.get("citations", {}).items():
            refs_count = len(cite.get("refs", []))
            lines.append(f"- `{key}`: {refs_count} refs")
        return "\n".join(lines)


def _cite_remove(
    table_id: str,
    row_index: int,
    column_name: str,
    ref_index: int | None,
) -> str:
    if row_index < 0 or not column_name:
        return "❌ `row_index` and `column_name` are required."
    result = table_service.remove_citation(table_id, row_index, column_name, ref_index)
    if result["success"]:
        return f"✅ Citation removed from [{row_index}:{column_name}]."
    return f"❌ {result.get('error', 'Unknown error')}"


def _cite_cell_history(
    table_id: str,
    row_index: int,
    column_name: str,
) -> str:
    if row_index < 0 or not column_name:
        return "❌ `row_index` and `column_name` are required."
    history = table_service.get_cell_history(table_id, row_index, column_name)
    if not history:
        return f"No history for [{row_index}:{column_name}]."
    lines = [f"## Cell History [{row_index}:{column_name}]\n"]
    for entry in history:
        ts = entry["timestamp"][:19]
        lines.append(
            f"- **{ts}** `{entry['operation']}`: {entry.get('old_value', '')} → {entry.get('new_value', '')}"
        )
    return "\n".join(lines)


# ============================================================================
# 5. table_history — 變更歷史 + Token 估算
# ============================================================================


@mcp.tool()
async def table_history(
    operation: Literal["changes", "tokens"],
    table_id: str,
    # changes
    limit: int = 20,
    # tokens
    draft_id: str = "",
    text: str = "",
) -> str:
    """
    📜 表格歷史與統計：變更紀錄、Token 估算。

    Operations:
    - **changes**: 查看表格變更歷史
    - **tokens**: 估算 Token 消耗

    Args:
        operation: 操作類型
        table_id: 表格 ID [changes, tokens]
        limit: [changes] 最近 N 筆
        draft_id: [tokens] 草稿 ID（可選）
        text: [tokens] 任意文字（可選）

    Examples:
        table_history("changes", "tbl_xxx")
        table_history("tokens", "tbl_xxx")
    """
    try:
        if operation == "changes":
            return _history_changes(table_id, limit)
        elif operation == "tokens":
            return _history_tokens(table_id, draft_id, text)
        else:
            return f"❌ Unknown operation: {operation}"
    except ValueError as e:
        return f"❌ Error: {e}"


def _history_changes(table_id: str, limit: int) -> str:
    if not table_id:
        return "❌ `table_id` is required."
    history = table_service.get_change_history(table_id, limit)
    if not history:
        return f"No changes recorded for `{table_id}`."
    lines = [f"## Change History (last {min(limit, len(history))})\n"]
    for entry in history:
        ts = entry["timestamp"][:19]
        target = entry["target"]
        op = entry["operation"]
        line = f"- **{ts}** `{op}` on `{target}`"
        if entry.get("old_value") is not None:
            line += f" (old: {_compact(entry['old_value'])})"
        if entry.get("new_value") is not None:
            line += f" → {_compact(entry['new_value'])}"
        lines.append(line)
    return "\n".join(lines)


def _history_tokens(table_id: str, draft_id: str, text: str) -> str:
    lines = ["# 📊 Token Estimation\n"]
    if table_id:
        est = table_service.estimate_table_tokens(table_id)
        lines.append(
            f"**Table `{table_id}`:** ~{est['content_tokens']} tokens "
            f"({est['row_count']} rows, ~{est['tokens_per_row']}/row)"
        )
    if draft_id:
        try:
            draft = table_service.get_draft(draft_id)
            draft_est = draft.estimate_tokens()
            lines.append(
                f"**Draft `{draft_id}`:** ~{draft_est} tokens ({len(draft.pending_rows)} pending rows)"
            )
        except ValueError:
            lines.append(f"**Draft `{draft_id}`:** Not found")
    if text:
        text_est = len(text) // 4
        lines.append(f"**Text:** ~{text_est} tokens ({len(text)} chars)")
    if len(lines) == 1:
        lines.append("Provide `table_id`, `draft_id`, or `text`.")
    return "\n".join(lines)


def _compact(val: Any) -> str:
    """Compact display of a value."""
    s = str(val)
    return s[:50] + "..." if len(s) > 50 else s


# ============================================================================
# 6. table_draft — 草稿工作流
# ============================================================================


@mcp.tool()
async def table_draft(
    operation: Literal[
        "create", "update", "add_rows", "resume", "commit", "list", "delete"
    ],
    # create / update
    draft_id: str = "",
    title: str = "",
    intent: Literal["comparison", "citation", "summary"] | None = None,
    proposed_columns: list[dict] | None = None,
    extraction_plan: list[str] | None = None,
    source_doc_ids: list[str] | None = None,
    source_sections: list[str] | None = None,
    notes: str = "",
    # add_rows
    rows: list[dict] | None = None,
) -> str:
    """
    📝 草稿工作流：建立、更新、新增資料、恢復、提交。

    草稿會自動保存，即使對話中斷也能恢復。
    適合長時間的表格建立流程。

    Operations:
    - **create**: 建立草稿
    - **update**: 更新草稿
    - **add_rows**: 批次新增資料到草稿
    - **resume**: 恢復草稿（Token-efficient）
    - **commit**: 草稿轉正式表格
    - **list**: 列出草稿
    - **delete**: 刪除草稿

    Args:
        operation: 操作類型
        draft_id: [大部分操作] 草稿 ID
        title: [create/update] 標題
        intent: [create/update] comparison / citation / summary
        proposed_columns: [create/update] 欄位定義
        extraction_plan: [create/update] 抽取計畫
        source_doc_ids: [create/update] 來源文件 ID
        source_sections: [create/update] 來源章節 ID
        notes: [create/update] 工作筆記
        rows: [add_rows] 資料列

    Examples:
        table_draft("create", title="Drug Comparison",
                    intent="comparison",
                    proposed_columns=[{"name":"Drug","type":"text"}])
        table_draft("add_rows", draft_id="draft_xxx", rows=[{"Drug":"A"}])
        table_draft("commit", draft_id="draft_xxx")
    """
    try:
        if operation == "create":
            return _draft_create(
                title,
                intent,
                proposed_columns,
                extraction_plan,
                source_doc_ids,
                source_sections,
                notes,
            )
        elif operation == "update":
            return _draft_update(
                draft_id,
                title,
                intent,
                proposed_columns,
                extraction_plan,
                source_sections,
                notes,
            )
        elif operation == "add_rows":
            return _draft_add_rows(draft_id, rows)
        elif operation == "resume":
            return _draft_resume(draft_id)
        elif operation == "commit":
            return _draft_commit(draft_id)
        elif operation == "list":
            return _draft_list()
        elif operation == "delete":
            return _draft_delete(draft_id)
        else:
            return f"❌ Unknown operation: {operation}"
    except ValueError as e:
        return f"❌ Error: {e}"


def _draft_create(
    title: str,
    intent: Literal["comparison", "citation", "summary"] | None,
    proposed_columns: list[dict] | None,
    extraction_plan: list[str] | None,
    source_doc_ids: list[str] | None,
    source_sections: list[str] | None,
    notes: str,
) -> str:
    if not title:
        return "❌ `title` is required."
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
    return (
        f"✅ Draft created: `{draft_id}`\n"
        f"**Title:** {draft.title} | **Intent:** {draft.intent or 'N/A'}\n"
        f"**Columns:** {len(draft.proposed_columns)} | **Sources:** {len(draft.source_doc_ids)} docs"
    )


def _draft_update(
    draft_id: str,
    title: str,
    intent: Literal["comparison", "citation", "summary"] | None,
    proposed_columns: list[dict] | None,
    extraction_plan: list[str] | None,
    source_sections: list[str] | None,
    notes: str,
) -> str:
    if not draft_id:
        return "❌ `draft_id` is required."
    updates: dict[str, Any] = {}
    if title:
        updates["title"] = title
    if intent is not None:
        updates["intent"] = intent
    if proposed_columns is not None:
        updates["proposed_columns"] = proposed_columns
    if extraction_plan is not None:
        updates["extraction_plan"] = extraction_plan
    if source_sections is not None:
        updates["source_sections"] = source_sections
    if notes:
        updates["notes"] = notes

    table_service.update_draft(draft_id, **updates)
    draft = table_service.get_draft(draft_id)
    return (
        f"✅ Draft `{draft_id}` updated.\n"
        f"**Title:** {draft.title} | **Intent:** {draft.intent}\n"
        f"**Columns:** {len(draft.proposed_columns)} | **Pending:** {len(draft.pending_rows)}\n"
        f"**Est. Tokens:** ~{draft.estimate_tokens()}"
    )


def _draft_add_rows(draft_id: str, rows: list[dict] | None) -> str:
    if not draft_id or not rows:
        return "❌ `draft_id` and `rows` are required."
    draft = table_service.get_draft(draft_id)
    draft.pending_rows.extend(rows)
    table_service.update_draft(draft_id, pending_rows=draft.pending_rows)
    return (
        f"✅ Added {len(rows)} rows to draft.\n"
        f"**Total Pending:** {len(draft.pending_rows)} | **Est. Tokens:** ~{draft.estimate_tokens()}"
    )


def _draft_resume(draft_id: str) -> str:
    if not draft_id:
        return "❌ `draft_id` is required."
    draft = table_service.get_draft(draft_id)
    lines = [
        f"# 📋 Draft: {draft.title}",
        "",
        f"**ID:** `{draft_id}` | **Intent:** {draft.intent or 'N/A'}",
        f"**Table:** `{draft.table_id}`"
        if draft.table_id
        else "**Table:** Not created",
    ]
    if draft.proposed_columns:
        lines.append("\n## Columns")
        lines.append("```json")
        lines.append(json.dumps(draft.proposed_columns, indent=2, ensure_ascii=False))
        lines.append("```")
    if draft.extraction_plan:
        lines.append("\n## Plan")
        for i, step in enumerate(draft.extraction_plan, 1):
            lines.append(f"{i}. {step}")
    if draft.pending_rows:
        lines.append(f"\n## Pending ({len(draft.pending_rows)} rows)")
        lines.append("```json")
        lines.append(json.dumps(draft.pending_rows[-2:], indent=2, ensure_ascii=False))
        lines.append("```")
    if draft.notes:
        lines.append(f"\n## Notes\n{draft.notes}")
    lines.append(f"\n**Est. Tokens:** ~{draft.estimate_tokens()}")
    return "\n".join(lines)


def _draft_commit(draft_id: str) -> str:
    if not draft_id:
        return "❌ `draft_id` is required."
    table_id = table_service.commit_draft_to_table(draft_id)
    preview = table_service.preview_table(table_id, limit=5)
    return f"✅ Committed! **table_id:** `{table_id}`\n\n{preview}"


def _draft_list() -> str:
    drafts = table_service.list_drafts()
    if not drafts:
        return "No drafts. Use `table_draft('create', ...)` to start."
    lines = ["# 📝 Drafts\n"]
    lines.append("| ID | Title | Intent | Cols | Pending | Status |")
    lines.append("|----|-------|--------|------|---------|--------|")
    for d in drafts:
        status = "✅ Has Table" if d["has_table"] else "⏳ Planning"
        lines.append(
            f"| `{d['id']}` | {d['title']} | {d['intent'] or '-'} "
            f"| {d['columns_planned']} | {d['pending_rows']} | {status} |"
        )
    return "\n".join(lines)


def _draft_delete(draft_id: str) -> str:
    if not draft_id:
        return "❌ `draft_id` is required."
    if table_service.delete_draft(draft_id):
        return f"✅ Draft `{draft_id}` deleted."
    return f"❌ Draft `{draft_id}` not found."


# ============================================================================
# 7. discover_sources — 資料來源探索
# ============================================================================


@mcp.tool()
async def discover_sources(
    query: str,
    doc_ids: list[str] | None = None,
    include_kg: bool = True,
    limit: int = 10,
) -> str:
    """
    🔍 資料來源探索：跨文件搜尋可用於表格的資料來源。

    整合 Section、Figure、Table、Knowledge Graph 多個資料庫，
    返回統一的 AssetRef 格式結果，可直接用於 table_cite。

    Args:
        query: 搜尋關鍵字
        doc_ids: 限定搜尋的文件（不指定則搜尋所有文件）
        include_kg: 是否包含知識圖譜搜尋
        limit: 每類來源的最大結果數

    Returns:
        發現的資料來源（AssetRef 格式）

    Example:
        discover_sources("remimazolam dosing")
        discover_sources("drug comparison", doc_ids=["doc_abc"])
    """
    lines = [f"# 🔍 Sources for: {query}\n"]
    found_any = False

    # 1. Search in documents
    if doc_ids:
        target_docs = doc_ids
    else:
        # Get all document IDs from service
        try:
            all_docs = await document_service.list_documents()
            target_docs = [d.doc_id for d in all_docs] if all_docs else []
        except Exception:  # Service may be unavailable
            target_docs = []

    for doc_id in target_docs:
        try:
            manifest = await document_service.get_manifest(doc_id)
            if not manifest:
                continue

            doc_results = []

            # Search sections
            if manifest.assets.sections:
                query_lower = query.lower()
                for sec in manifest.assets.sections:
                    if (
                        query_lower in (sec.title or "").lower()
                        or query_lower in (sec.id or "").lower()
                    ):
                        doc_results.append(
                            {
                                "source_type": "section",
                                "doc_id": doc_id,
                                "asset_id": sec.id,
                                "label": sec.title,
                                "page": sec.page,
                            }
                        )

            # Search tables
            if manifest.assets.tables:
                for tab in manifest.assets.tables:
                    if query.lower() in (tab.caption or "").lower():
                        doc_results.append(
                            {
                                "source_type": "table",
                                "doc_id": doc_id,
                                "asset_id": tab.id,
                                "label": tab.caption or tab.id,
                                "page": tab.page,
                            }
                        )

            if doc_results:
                found_any = True
                lines.append(f"## 📄 {doc_id} ({manifest.title})")
                for r in doc_results[:limit]:
                    lines.append(
                        f"  - **{r['source_type']}** `{r['asset_id']}`: "
                        f"{r['label']} (p.{r.get('page', '?')})"
                    )
                    lines.append(
                        f"    ```json\n    {json.dumps(r, ensure_ascii=False)}\n    ```"
                    )
                lines.append("")

        except Exception:
            logger.debug("Failed to parse manifest for doc %s", doc_id)
            continue

    # 2. Search KG
    if include_kg:
        try:
            from src.presentation.dependencies import knowledge_service

            kg_result = await knowledge_service.query(query)
            if kg_result and "No knowledge graph" not in kg_result:
                found_any = True
                lines.append("## 🧠 Knowledge Graph")
                # Show compact result
                kg_preview = (
                    kg_result[:500] + "..." if len(kg_result) > 500 else kg_result
                )
                lines.append(kg_preview)
                lines.append(
                    f"\n  AssetRef: `{json.dumps({'source_type': 'kg_entity', 'label': query}, ensure_ascii=False)}`"
                )
                lines.append("")
        except Exception:
            logger.debug("KG search failed for query: %s", query)

    if not found_any:
        lines.append(
            "No relevant sources found. Try different keywords or ingest documents first."
        )

    lines.append(
        "\n💡 Copy the AssetRef JSON and use `table_cite('add', ...)` to attach as citation."
    )

    return "\n".join(lines)
