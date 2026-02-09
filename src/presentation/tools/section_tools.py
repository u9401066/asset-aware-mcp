"""
Section Tools - Section 動態層級導航 MCP 工具

包含：
- list_section_tree: 列出 section 結構樹
- get_section_detail: 取得 section 詳情
- get_section_blocks: 取得 section 的 blocks
- search_sections: 搜尋 section 名稱
- get_section_content: 讀取章節內容（省 Token 的精確讀取）
"""

from __future__ import annotations

from typing import Literal

from src.presentation.dependencies import asset_service, section_service
from src.presentation.mcp_app import mcp


@mcp.tool()
async def list_section_tree(
    doc_id: str,
    max_depth: int | None = None,
    format: Literal["tree", "flat", "json"] = "tree",
) -> str:
    """
    列出文件的 section 結構樹（動態層級，不 hardcode）。

    從 blocks.json 動態建構 section hierarchy，支援任意深度的章節結構。
    適用於不同格式的書籍/論文。

    Args:
        doc_id: 文件 ID（需先用 use_marker=True 執行 ingest_documents）
        max_depth: 最大顯示深度（None = 顯示全部層級）
        format: 輸出格式
            - tree: 縮排樹狀（預設，美觀）
            - flat: 扁平列表 + 完整 path（適合搜尋）
            - json: JSON 結構（適合程式處理）

    Returns:
        Section 樹狀結構

    Example Output (tree format):
        📖 Chapter 79 Pediatric Critical Care (P2967-2997, 45 blocks)
        ├── 📑 Shock and Sepsis (P2968-2975, 23 blocks)
        │   ├── 📄 Pathophysiology (P2968-2970, 8 blocks)
        │   ├── 📄 Clinical Presentation (P2970-2972, 7 blocks)
        │   └── 📄 Management (P2972-2975, 8 blocks)
        └── 📑 Respiratory Failure (P2975-2985, 30 blocks)
    """
    return await section_service.list_section_tree(doc_id, max_depth, format)


@mcp.tool()
async def get_section_detail(
    doc_id: str,
    path: str,
) -> str:
    """
    取得特定 section 的詳細資訊。

    Args:
        doc_id: 文件 ID
        path: Section 路徑（用 "/" 分隔）
            例如: "Chapter 79/Shock and Sepsis/Pathophysiology"

    Returns:
        Section 詳情：
        - 頁碼範圍
        - Block 統計（總數、直屬、估算 token）
        - 子 section 列表
        - 預覽內容

    Example:
        get_section_detail("abc123", "Chapter 79/Shock and Sepsis")
    """
    return await section_service.get_section_detail(doc_id, path)


@mcp.tool()
async def get_section_blocks(
    doc_id: str,
    path: str,
    include_children: bool = True,
    block_types: list[str] | None = None,
    limit: int | None = None,
) -> str:
    """
    提取特定 section 的所有 blocks（精確來源追蹤）。

    這是出題時取得「精確來源」的主要工具。
    每個 block 都包含 page + bbox，可用於驗證和引用。

    Args:
        doc_id: 文件 ID
        path: Section 路徑（用 "/" 分隔）
        include_children: 是否包含子 section 的 blocks（預設 True）
        block_types: 篩選 block 類型（Text, Table, Figure, SectionHeader）
        limit: 限制返回數量（避免輸出過長）

    Returns:
        Blocks 列表，每個包含：
        - block_id, block_type
        - page, bbox（精確位置）
        - section_hierarchy（完整路徑）
        - text（內容）

    Example:
        # 取得整個章節的內容
        get_section_blocks("abc123", "Chapter 79/Shock and Sepsis")

        # 只取得該節的內容（不含子節）
        get_section_blocks("abc123", "Chapter 79/Shock", include_children=False)

        # 只取得表格
        get_section_blocks("abc123", "Chapter 79", block_types=["Table"])
    """
    return await section_service.get_section_blocks(
        doc_id, path, include_children, block_types, limit
    )


@mcp.tool()
async def search_sections(
    doc_id: str,
    query: str,
    fuzzy: bool = True,
) -> str:
    """
    搜尋 section 名稱（用於快速定位章節）。

    搜尋的是章節標題，不是內容。
    適合快速找到想要閱讀的章節。

    Args:
        doc_id: 文件 ID
        query: 搜尋關鍵字（搜尋章節標題）
        fuzzy: 是否模糊匹配（預設 True）

    Returns:
        匹配的 section 列表 + 完整 path

    Example:
        search_sections("abc123", "shock")

        ## 🔍 Found 2 sections matching "shock"

        1. **Shock and Sepsis**
           - Path: `Chapter 79/Shock and Sepsis`
           - Pages: 2968-2975
           - Blocks: 23

        2. **Cardiogenic Shock**
           - Path: `Chapter 79/Cardiac/Cardiogenic Shock`
           - Pages: 2980-2982
    """
    return await section_service.search_sections(doc_id, query, fuzzy)


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
