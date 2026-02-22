"""
Docx Tools - Docx ↔ DFM 雙向轉換 + Table Bridge MCP 工具

包含：
- ingest_docx: 攝入 .docx 文件，轉換為 DFM 格式
- get_docx_content: 取得可編輯的 DFM 內容
- save_docx: 將編輯後的 DFM 存回 .docx
- list_docx_blocks: 列出文件中所有區塊的摘要
- docx_table_to_context: 將 DFM 表格區塊轉為 TableContext（可用 table_manage/table_data 編輯）
- docx_table_from_context: 將 TableContext 寫回 DFM 表格區塊
- docx_chart_data: 提取圖表的底層資料為表格格式
"""

from __future__ import annotations

import json
import logging

from src.presentation.dependencies import (
    dfm_table_bridge,
    docx_service,
    docx_validator,
    table_service,
)
from src.presentation.mcp_app import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def ingest_docx(file_path: str) -> str:
    """
    攝入 .docx 文件，轉換為 DFM (Docx-Flavored Markdown) 格式。

    將 docx 解析為中間表示 (IR)，再轉換為可在 VS Code 中編輯的 DFM 格式。
    支援複雜元素：合併表格、圖表、頁首頁尾、巨集、目錄等。

    輸出目錄結構：
    ```
    data/{doc_id}/
    ├── content.dfm     # 可編輯的 Markdown + YAML 標注
    ├── ir.json          # IR 快照（用於回寫）
    ├── original.docx    # 原始檔案備份
    ├── parts/           # 保留的 XML 零件
    └── assets/          # 圖片和二進位資產
    ```

    Args:
        file_path: .docx 檔案的絕對路徑

    Returns:
        攝入結果摘要（doc_id、區塊數量等）
    """
    result = await docx_service.ingest_docx(file_path)
    logger.info("ingest_docx | file=%s | success=%s", file_path, result.get("success"))

    if not result.get("success"):
        return f"❌ 攝入失敗：{result.get('error', '未知錯誤')}"

    lines = [
        "✅ Docx 攝入成功",
        "",
        f"- **doc_id**: `{result.get('doc_id', '')}`",
        f"- **來源**: {result.get('source', '')}",
        f"- **總區塊數**: {result.get('total_blocks', 0)}",
        f"- **可編輯區塊**: {result.get('editable_blocks', 0)}",
        f"- **受保護區塊**: {result.get('protected_blocks', 0)}",
        f"- **資產數**: {result.get('assets', 0)}",
        f"- **DFM 路徑**: `{result.get('dfm_path', '')}`",
        f"- **完整性**: {result.get('integrity', 'N/A')}",
    ]

    block_types = result.get("block_types", {})
    if block_types:
        lines.append("")
        lines.append("**區塊類型分布**：")
        for bt, count in sorted(block_types.items()):
            lines.append(f"  - {bt}: {count}")

    return "\n".join(lines)


@mcp.tool()
async def get_docx_content(
    doc_id: str,
    block_id: str | None = None,
) -> str:
    """
    取得 docx 文件的可編輯 DFM 內容。

    若指定 block_id，只回傳該區塊的內容；否則回傳完整 DFM。

    Args:
        doc_id: 文件 ID（由 ingest_docx 產生）
        block_id: 可選，特定區塊 ID（如 p001, t001, h001）

    Returns:
        DFM 內容或特定區塊資訊
    """
    if block_id:
        block = await docx_service.get_block_content(doc_id, block_id)
        if block is None:
            return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"
        return json.dumps(block, ensure_ascii=False, indent=2)

    dfm = await docx_service.get_dfm(doc_id)
    if dfm is None:
        return f"❌ 找不到文件 {doc_id}，請先使用 ingest_docx 攝入。"
    return dfm


@mcp.tool()
async def save_docx(
    doc_id: str,
    dfm_content: str | None = None,
    output_path: str | None = None,
    from_md: bool = False,
) -> str:
    """
    將編輯後的內容存回 .docx 檔案。

    支援兩種模式：
    - DFM 模式（預設）：傳入 dfm_content（.dfm 格式全文）
    - MD 模式（from_md=True）：從磁碟讀取 content.md + format.yaml

    回寫流程：
    1. 解析 DFM/MD → 提取修改
    2. 載入原始 IR
    3. 合併修改（格式合併策略）
    4. 重建 .docx

    Args:
        doc_id: 文件 ID
        dfm_content: 編輯後的 DFM 全文（from_md=True 時可省略）
        output_path: 輸出路徑（預設為 data/{doc_id}/output.docx）
        from_md: 若為 True，從磁碟讀取 content.md + format.yaml 而非使用 dfm_content

    Returns:
        儲存結果
    """
    logger.info(
        "save_docx | doc_id=%s | from_md=%s | output=%s",
        doc_id,
        from_md,
        output_path,
    )
    result = await docx_service.save_docx(
        doc_id, dfm_content, output_path, from_md=from_md
    )
    logger.info(
        "save_docx done | doc_id=%s | success=%s | integrity=%s",
        doc_id,
        result.get("success"),
        result.get("integrity", "N/A"),
    )

    if not result.get("success"):
        return f"❌ 儲存失敗：{result.get('error', '未知錯誤')}"

    lines = [
        "✅ Docx 儲存成功",
        f"- **輸出路徑**: `{result.get('output_path', '')}`",
        f"- **完整性**: {result.get('integrity', 'N/A')}",
    ]

    warnings = result.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("⚠️ 警告：")
        lines.extend(f"  - {w}" for w in warnings)

    return "\n".join(lines)


@mcp.tool()
async def list_docx_blocks(doc_id: str) -> str:
    """
    列出 docx 文件中所有區塊的摘要。

    顯示每個區塊的 ID、類型、是否可編輯、樣式名稱和內容預覽。

    Args:
        doc_id: 文件 ID

    Returns:
        區塊摘要列表
    """
    blocks = await docx_service.list_blocks(doc_id)
    if blocks is None:
        return f"❌ 找不到文件 {doc_id}"

    if not blocks:
        return "文件中沒有任何區塊。"

    lines = [f"📄 文件 `{doc_id}` — 共 {len(blocks)} 個區塊\n"]
    lines.append("| ID | 類型 | 可編輯 | 樣式 | 預覽 |")
    lines.append("|---|---|---|---|---|")

    for b in blocks:
        editable = "✅" if b["editable"] else "🔒"
        style = b.get("style") or ""
        preview = b.get("preview", "").replace("|", "\\|")[:50]
        lines.append(f"| {b['id']} | {b['type']} | {editable} | {style} | {preview} |")

    return "\n".join(lines)


@mcp.tool()
async def docx_validate_roundtrip(
    doc_id: str,
    output_path: str | None = None,
) -> str:
    """
    驗證 docx → DFM → docx 的往返保真度 (Round-Trip Fidelity)。

    此工具程式化地比對原始 .docx 與重建後的 .docx，產生結構化報告。
    AI agent 無法直接查看 docx 渲染結果，因此使用此工具驗證編輯後的 docx
    是否正確保留了所有內容。

    比對六大維度：
    1. 結構 (Structure): 段落數、表格數、圖片數
    2. 文字 (Text): 逐段逐段純文字比對
    3. 格式 (Formatting): bold/italic/font/size/color
    4. 表格 (Table): 逐儲存格內容比對
    5. 媒體 (Media): 圖片 hash 比對
    6. 樣式 (Style): 段落樣式名稱比對

    使用方式：
    1. 先用 ingest_docx 攝入原始 docx
    2. 可選：用 get_docx_content / save_docx 做些編輯
    3. 呼叫此工具，取得結構化比對報告

    Args:
        doc_id: 文件 ID（由 ingest_docx 產生）
        output_path: 可選，指定輸出的 .docx 路徑。預設使用 data/{doc_id}/output.docx

    Returns:
        Markdown 格式的驗證報告（含保真度分數和差異列表）
    """
    from pathlib import Path

    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    original_path = doc_dir / "original.docx"

    if not original_path.exists():
        return (
            f"❌ 找不到原始檔案：{original_path}\n請先用 ingest_docx 攝入 .docx 文件。"
        )

    # Load IR
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到 IR：{doc_id}\n請先用 ingest_docx 攝入。"

    # Determine output path
    if output_path:
        rebuilt_path = Path(output_path)
    else:
        rebuilt_path = doc_dir / "roundtrip_validation.docx"

    # Rebuild docx from current IR state
    try:
        docx_service.adapter.ir_to_docx(ir, doc_dir, rebuilt_path)
    except Exception as e:
        return f"❌ 重建 docx 失敗：{e}"

    # Validate
    report = docx_validator.validate(original_path, rebuilt_path)

    return report.to_markdown()


# ============================================================================
# DFM ↔ Table Bridge Tools
# ============================================================================


@mcp.tool()
async def docx_table_to_context(
    doc_id: str,
    block_id: str,
    register: bool = True,
) -> str:
    """
    將 docx 中的表格區塊轉為 TableContext，使其可用 table_manage/table_data 工具結構化編輯。

    這是 DFM 表格與 A2T（Anything-to-Table）系統的橋樑：
    - DFM 表格 → TableContext → table_data (add_rows/update_cell) → table_cite (引用) → 寫回

    轉換後的 TableContext 自動註冊到 table_service，可直接使用以下工具操作：
    - table_data: add_rows, update_cell, delete_row
    - table_cite: add/remove citations
    - table_history: 查看變更歷史
    - table_manage: render (匯出 Excel/Markdown/HTML)

    Args:
        doc_id: 文件 ID（由 ingest_docx 產生）
        block_id: 表格區塊 ID（如 t001, t002）
        register: 是否自動註冊到 table_service（預設 True）

    Returns:
        TableContext 摘要（table_id + 欄位 + 行數）
    """
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到文件 {doc_id}，請先 ingest_docx。"

    block = ir.find_block(block_id)
    if block is None:
        return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"

    try:
        tc = dfm_table_bridge.block_to_table_context(
            block,
            doc_id=doc_id,
            source_description=f"Table {block_id} from {ir.source_filename}",
        )
    except ValueError as e:
        return f"❌ 轉換失敗：{e}"

    # Register to table_service for subsequent tool operations
    if register:
        table_service._tables[tc.id] = tc

    lines = [
        "✅ 表格區塊已轉為 TableContext",
        "",
        f"- **table_id**: `{tc.id}`",
        f"- **來源區塊**: `{block_id}`",
        f"- **欄位數**: {len(tc.columns)}",
        f"- **行數**: {tc.row_count}",
        "",
        "**欄位定義**：",
    ]
    lines.extend(f"  - `{col.name}` ({col.type})" for col in tc.columns)

    if tc.rows:
        lines.append("")
        lines.append("**前 3 行預覽**：")
        preview_rows = tc.rows[:3]
        col_names = tc.column_names
        lines.append("| " + " | ".join(col_names) + " |")
        lines.append("| " + " | ".join("---" for _ in col_names) + " |")
        for row in preview_rows:
            cells = [str(row.get(c, ""))[:30] for c in col_names]
            lines.append("| " + " | ".join(cells) + " |")

    if register:
        lines.append("")
        lines.append("💡 **接下來可用以下工具操作此表格**：")
        lines.append(f"  - `table_data(op='add_rows', table_id='{tc.id}', ...)`")
        lines.append(f"  - `table_data(op='update_cell', table_id='{tc.id}', ...)`")
        lines.append(f"  - `table_cite(op='add', table_id='{tc.id}', ...)`")
        lines.append(
            f"  - `table_manage(op='render', table_id='{tc.id}', format='excel')`"
        )
        lines.append(
            f"  - 完成後用 `docx_table_from_context(doc_id='{doc_id}', block_id='{block_id}', table_id='{tc.id}')` 寫回"
        )

    return "\n".join(lines)


@mcp.tool()
async def docx_table_from_context(
    doc_id: str,
    block_id: str,
    table_id: str,
    save_dfm: bool = True,
) -> str:
    """
    將 TableContext 的資料寫回 docx 的 DFM 表格區塊。

    這是 docx_table_to_context 的反向操作：
    TableContext (已用 table_data 等工具編輯) → 覆蓋 DFM 表格內容

    保留原始的 Word 表格樣式、欄位寬度、合併儲存格等格式資訊，僅更新文字內容。

    Args:
        doc_id: 文件 ID
        block_id: 表格區塊 ID（如 t001）
        table_id: TableContext 的 table_id（由 docx_table_to_context 產生）
        save_dfm: 是否自動更新 content.dfm 檔案（預設 True）

    Returns:
        操作結果
    """
    tc = table_service._tables.get(table_id)
    if tc is None:
        return (
            f"❌ 找不到 TableContext `{table_id}`，請先用 docx_table_to_context 轉換。"
        )

    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到文件 {doc_id}"

    try:
        dfm_table_bridge.apply_table_context_to_ir(ir, block_id, tc)
    except ValueError as e:
        return f"❌ 寫回失敗：{e}"

    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    docx_service._save_ir(ir, doc_dir / "ir.json")

    result_lines = [
        "✅ TableContext 已寫回 DFM 表格區塊",
        "",
        f"- **文件**: `{doc_id}`",
        f"- **區塊**: `{block_id}`",
        f"- **表格**: `{table_id}`",
        f"- **行數**: {tc.row_count}",
    ]

    if save_dfm:
        from src.infrastructure.dfm_renderer import DfmRenderer

        renderer = DfmRenderer()
        dfm_text = renderer.render(ir)
        dfm_path = doc_dir / "content.dfm"
        dfm_path.write_text(dfm_text, encoding="utf-8")
        result_lines.append(f"- **DFM 已更新**: `{dfm_path}`")

    result_lines.append("")
    result_lines.append(
        f"💡 用 `save_docx(doc_id='{doc_id}', ...)` 可將修改寫回 .docx 檔案。"
    )

    return "\n".join(result_lines)


@mcp.tool()
async def docx_chart_data(
    doc_id: str,
    block_id: str,
    register: bool = True,
) -> str:
    """
    提取 docx 圖表的底層資料為表格格式 (TableContext)。

    Word 圖表內嵌 Excel 資料。此工具提取該數據為結構化表格，
    可用 table_manage 的 render 功能匯出為 Excel/Markdown/HTML。

    如有原始 chart XML 可解析系列資料（長條圖、折線圖、圓餅圖等）。
    若無 XML，則回傳圖表的元資料摘要。

    Args:
        doc_id: 文件 ID
        block_id: 圖表區塊 ID（如 c001）
        register: 是否自動註冊到 table_service（預設 True）

    Returns:
        圖表資料的 TableContext 摘要
    """
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到文件 {doc_id}"

    block = ir.find_block(block_id)
    if block is None:
        return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"

    if block.block_type.value != "chart":
        return f"❌ 區塊 {block_id} 類型為 {block.block_type.value}，不是 chart"

    # Try to load chart XML from preserved parts
    chart_xml = None
    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    if block.binary_ref:
        chart_path = doc_dir / block.binary_ref
        if chart_path.exists():
            import contextlib

            with contextlib.suppress(UnicodeDecodeError):
                chart_xml = chart_path.read_text(encoding="utf-8")

    tc = dfm_table_bridge.extract_chart_data(block, chart_xml)
    if tc is None:
        return f"❌ 無法提取圖表 {block_id} 的資料"

    if register:
        table_service._tables[tc.id] = tc

    lines = [
        "✅ 圖表資料已轉為 TableContext",
        "",
        f"- **table_id**: `{tc.id}`",
        f"- **來源區塊**: `{block_id}`",
        f"- **圖表類型**: {block.chart_type or 'unknown'}",
        f"- **欄位數**: {len(tc.columns)}",
        f"- **行數**: {tc.row_count}",
    ]

    if tc.rows:
        lines.append("")
        col_names = tc.column_names
        lines.append("| " + " | ".join(col_names) + " |")
        lines.append("| " + " | ".join("---" for _ in col_names) + " |")
        for row in tc.rows[:10]:
            cells = [str(row.get(c, ""))[:20] for c in col_names]
            lines.append("| " + " | ".join(cells) + " |")
        if tc.row_count > 10:
            lines.append(f"... 共 {tc.row_count} 行")

    if register:
        lines.append("")
        lines.append("💡 **可用以下工具操作此資料**：")
        lines.append(
            f"  - `table_manage(op='render', table_id='{tc.id}', format='excel')` 匯出 Excel"
        )
        lines.append(
            f"  - `table_manage(op='render', table_id='{tc.id}', format='markdown')` 匯出 MD"
        )
        lines.append(
            f"  - `table_data(op='update_cell', table_id='{tc.id}', ...)` 修改數據"
        )

    return "\n".join(lines)
