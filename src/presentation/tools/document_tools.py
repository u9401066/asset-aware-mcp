"""
Document Tools - ETL + 文件管理 MCP 工具

包含：
- parse_pdf_structure: Marker 結構化解析
- search_source_location: 來源位置搜尋
- ingest_documents: PDF 文件攝入
- list_documents: 列出所有文件
- inspect_document_manifest: 查看文件 Manifest
- fetch_document_asset: 擷取文件資產
"""

from __future__ import annotations

import json
from typing import Literal

from mcp.types import ImageContent, TextContent

from src.infrastructure.config import settings
from src.presentation.dependencies import (
    asset_service,
    document_service,
    get_marker_extractor,
    job_service,
)
from src.presentation.mcp_app import mcp


@mcp.tool()
async def parse_pdf_structure(
    pdf_path: str,
    output_dir: str | None = None,
) -> str:
    """
    使用 Marker 進行結構化 PDF 解析（高精度）。

    比標準 ingest_documents 提供更豐富的結構資訊：
    - Block-level 解析（每個區塊的 bbox/polygon）
    - 目錄 (TOC) 自動提取
    - Section hierarchy 追蹤
    - 圖片 + 圖說 (caption) 關聯

    輸出目錄結構：
    ```
    data/{doc_id}/
    ├── manifest.json    # DocumentManifest
    ├── content.md       # Markdown 全文
    ├── blocks.json      # 結構化區塊資料
    └── figures/         # 圖片檔案
    ```

    Args:
        pdf_path: PDF 檔案的絕對路徑
        output_dir: 輸出目錄（預設為 data/{doc_id}/）

    Returns:
        解析結果摘要和 doc_id
    """
    import time
    from pathlib import Path

    start = time.time()
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"

    # Determine output directory (same convention as ingest_documents)
    if output_dir:
        out_path = Path(output_dir)
    else:
        from src.domain.value_objects import DocId

        doc_id_obj = DocId.generate(pdf_file.stem, str(pdf_file.absolute()))
        out_path = settings.data_dir / doc_id_obj.value

    try:
        extractor = get_marker_extractor()
        manifest = extractor.extract_to_manifest(pdf_file, out_path)

        elapsed = time.time() - start

        lines = [
            "# ✅ PDF Structure Parsed (Marker)",
            "",
            f"**doc_id:** `{manifest.doc_id}`",
            f"**Title:** {manifest.title or 'N/A'}",
            f"**Pages:** {manifest.page_count}",
            f"**Time:** {elapsed:.1f}s",
            "",
            "## Assets Found",
            f"- **Sections:** {len(manifest.assets.sections)}",
            f"- **Tables:** {len(manifest.assets.tables)}",
            f"- **Figures:** {len(manifest.assets.figures)}",
            "",
            "## Output Files",
            f"- Manifest: `{manifest.manifest_path}`",
            f"- Markdown: `{manifest.markdown_path}`",
            f"- Blocks: `{out_path / 'blocks.json'}`",
            "",
        ]

        # Show TOC preview
        if manifest.toc:
            lines.append("## Table of Contents")
            for item in manifest.toc[:10]:
                lines.append(f"- {item}")
            if len(manifest.toc) > 10:
                lines.append(f"- _...and {len(manifest.toc) - 10} more_")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Marker parsing failed: {str(e)}"


@mcp.tool()
async def search_source_location(
    doc_id: str,
    query: str,
    block_types: list[str] | None = None,
) -> str:
    """
    搜尋文件中的來源位置（頁碼 + bbox）。

    用於驗證答案來源時，精確定位內容在原始 PDF 的位置。

    Args:
        doc_id: 文件 ID
        query: 搜尋關鍵字
        block_types: 限制搜尋的區塊類型（Text, Table, Figure, SectionHeader）

    Returns:
        匹配的區塊列表，包含頁碼和位置
    """
    blocks_path = settings.data_dir / doc_id / "blocks.json"

    if not blocks_path.exists():
        return (
            f"❌ Blocks not found for doc_id: {doc_id}. "
            "Run `ingest_documents` with `use_marker=True` first."
        )

    try:
        blocks_data = json.loads(blocks_path.read_text(encoding="utf-8"))

        if block_types:
            blocks_data = [b for b in blocks_data if b.get("block_type") in block_types]

        query_lower = query.lower()
        matches = []
        for block in blocks_data:
            text = block.get("text", "").lower()
            if query_lower in text:
                matches.append(
                    {
                        "block_id": block.get("block_id"),
                        "block_type": block.get("block_type"),
                        "page": block.get("page"),
                        "bbox": block.get("bbox"),
                        "section": block.get("section_hierarchy"),
                        "snippet": block.get("text", "")[:150] + "...",
                    }
                )

        if not matches:
            return f"No matches found for '{query}' in doc_id: {doc_id}"

        lines = [
            f"# 🔍 Source Locations for '{query}'",
            "",
            f"**Found:** {len(matches)} matches",
            "",
        ]

        for i, m in enumerate(matches[:10], 1):
            lines.append(f"## Match {i}")
            lines.append(f"- **Block:** `{m['block_id']}` ({m['block_type']})")
            lines.append(f"- **Page:** {m['page']}")
            if m.get("bbox"):
                lines.append(f"- **BBox:** {m['bbox']}")
            if m.get("section"):
                lines.append(f"- **Section:** {m['section']}")
            lines.append(f"- **Snippet:** _{m['snippet']}_")
            lines.append("")

        if len(matches) > 10:
            lines.append(f"_...and {len(matches) - 10} more matches_")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Search failed: {str(e)}"


@mcp.tool()
async def ingest_documents(
    file_paths: list[str],
    async_mode: bool = True,
    use_marker: bool = False,
) -> str:
    """
    Process PDF files and create Document Manifests.

    ETL Pipeline:
    1. Extract text (to markdown) and images
    2. Generate structured Document Manifest
    3. Index in LightRAG (if enabled)

    Args:
        file_paths: List of absolute paths to PDF files
        async_mode: If True (default), returns immediately with a job_id for tracking.
                   If False, waits for completion (may timeout for large files).
        use_marker: If True, use Marker for structured parsing (slower but more accurate).
                   Produces blocks.json with bbox/coordinates for precise source tracking.
                   Default False uses PyMuPDF (faster but less structured).

    Returns:
        - async_mode=True: Job ID for tracking progress with `get_job_status`
        - async_mode=False: Summary of ingestion results

    Example:
        # Async (recommended for large files):
        ingest_documents(["/papers/study1.pdf"])
        # Then check status:
        get_job_status("job_xxx")

        # Sync (small files only):
        ingest_documents(["/papers/small.pdf"], async_mode=False)

        # With Marker for precise source tracking:
        ingest_documents(["/papers/textbook.pdf"], use_marker=True, async_mode=False)
    """
    # Lazy-load Marker if requested
    if use_marker and document_service.marker_extractor is None:
        document_service.marker_extractor = get_marker_extractor()

    if async_mode:
        job = await job_service.create_ingest_job(file_paths)

        backend_note = " (Marker)" if use_marker else ""
        return (
            f"# 📋 ETL Job Created{backend_note}\n\n"
            f"**Job ID:** `{job.job_id}`\n"
            f"**Files:** {len(file_paths)}\n"
            f"**Backend:** {'Marker (structured)' if use_marker else 'PyMuPDF (fast)'}\n"
            f"**Estimated Time:** ~{job.estimated_duration_seconds or 10}s\n\n"
            f'Use `get_job_status("{job.job_id}")` to check progress.\n'
            f"Or use `list_jobs()` to see all active jobs."
        )
    else:
        results = await document_service.ingest(file_paths, use_marker=use_marker)

        backend_label = "Marker" if use_marker else "PyMuPDF"
        output_lines = [f"# Ingestion Results ({backend_label})\n"]
        success_count = sum(1 for r in results if r.success)
        output_lines.append(f"**Processed:** {success_count}/{len(results)} files\n")

        for result in results:
            if result.success:
                output_lines.append(f"\n## ✅ {result.filename}")
                output_lines.append(f"- **doc_id:** `{result.doc_id}`")
                output_lines.append(f"- **title:** {result.title or 'N/A'}")
                output_lines.append(f"- **backend:** {result.backend}")
                output_lines.append(f"- **pages:** {result.pages_processed}")
                output_lines.append(f"- **tables:** {result.tables_found}")
                output_lines.append(f"- **figures:** {result.figures_found}")
                output_lines.append(f"- **sections:** {result.sections_found}")
                output_lines.append(
                    f"- **time:** {result.processing_time_seconds:.2f}s"
                )
                if result.backend == "marker":
                    output_lines.append("- **blocks.json:** ✅ Created")
            else:
                output_lines.append(f"\n## ❌ {result.filename}")
                output_lines.append(f"- **error:** {result.error}")

        return "\n".join(output_lines)


@mcp.tool()
async def list_documents() -> str:
    """
    List all processed documents with summaries.

    Returns:
        List of documents with doc_id, title, and asset counts
    """
    documents = await document_service.list_documents()

    if not documents:
        return "No documents found. Use `ingest_documents` to process PDF files."

    output_lines = [f"# Documents ({len(documents)} total)\n"]

    for doc in documents:
        output_lines.append(f"## {doc.title or doc.filename}")
        output_lines.append(f"- **doc_id:** `{doc.doc_id}`")
        output_lines.append(f"- **filename:** {doc.filename}")
        output_lines.append(f"- **tables:** {doc.table_count}")
        output_lines.append(f"- **figures:** {doc.figure_count}")
        output_lines.append(f"- **sections:** {doc.section_count}")
        output_lines.append(f"- **ingested:** {doc.ingested_at}")
        output_lines.append("")

    return "\n".join(output_lines)


@mcp.tool()
async def inspect_document_manifest(doc_id: str) -> str:
    """
    Get detailed Document Manifest for precise asset retrieval.

    The manifest contains:
    - Document metadata (title, pages, etc.)
    - Tables list with IDs and descriptions
    - Figures list with IDs, page numbers, and dimensions
    - Sections list with IDs and titles
    - LightRAG entities (if indexed)

    Use this to discover available assets before fetching.

    Args:
        doc_id: Document identifier from ingest_documents or list_documents

    Returns:
        Structured manifest in markdown format
    """
    manifest = await document_service.get_manifest(doc_id)

    if not manifest:
        return f"Document not found: `{doc_id}`"

    output_lines = [f"# Document Manifest: {manifest.title or manifest.filename}\n"]
    output_lines.append(f"**doc_id:** `{manifest.doc_id}`")
    output_lines.append(f"**pages:** {manifest.page_count}")
    output_lines.append(f"**ingested:** {manifest.ingested_at}")

    # Tables section
    output_lines.append(f"\n## Tables ({len(manifest.assets.tables)})")
    if manifest.assets.tables:
        for table in manifest.assets.tables:
            output_lines.append(f"\n### `{table.id}` (page {table.page})")
            output_lines.append(f"_{table.caption}_")
            output_lines.append(f"Rows: {table.row_count}, Cols: {table.col_count}")
    else:
        output_lines.append("_No tables found_")

    # Figures section
    output_lines.append(f"\n## Figures ({len(manifest.assets.figures)})")
    if manifest.assets.figures:
        for fig in manifest.assets.figures:
            output_lines.append(f"\n### `{fig.id}` (page {fig.page})")
            if fig.caption:
                output_lines.append(f"_{fig.caption}_")
            output_lines.append(f"Size: {fig.width}×{fig.height} ({fig.ext})")
    else:
        output_lines.append("_No figures found_")

    # Sections section
    output_lines.append(f"\n## Sections ({len(manifest.assets.sections)})")
    if manifest.assets.sections:
        for sec in manifest.assets.sections:
            indent = "  " * (sec.level - 1) if sec.level > 1 else ""
            output_lines.append(
                f"{indent}- `{sec.id}`: {sec.title} (L{sec.start_line}-{sec.end_line})"
            )
    else:
        output_lines.append("_No sections found_")

    # LightRAG entities
    if manifest.lightrag_entities:
        output_lines.append(
            f"\n## Knowledge Graph Entities ({len(manifest.lightrag_entities)})"
        )
        output_lines.append(", ".join(manifest.lightrag_entities[:20]))
        if len(manifest.lightrag_entities) > 20:
            output_lines.append(
                f"... and {len(manifest.lightrag_entities) - 20} more"
            )

    return "\n".join(output_lines)


@mcp.tool()
async def fetch_document_asset(
    doc_id: str,
    asset_type: str,
    asset_id: str = "full",
    max_size: int | None = None,
) -> list[TextContent | ImageContent]:
    """
    Fetch specific content from a document with precision.

    Asset Types:
    - "table": Returns table as markdown (with page number)
    - "figure": Returns image as base64 with page number for verification
    - "section": Returns section text content
    - "full_text": Returns entire document as markdown

    Args:
        doc_id: Document identifier
        asset_type: One of "table", "figure", "section", "full_text"
        asset_id: Asset ID from manifest (e.g., "tab_1", "fig_1_1", "sec_methods")
                  Use "full" for full_text type
        max_size: Maximum image dimension (longest edge) for figures.
                  - None (default): Use default 1024px
                  - 0: Return original size (no resize)
                  - N: Resize to Npx longest edge (e.g., 512, 768, 2048)

    Returns:
        For figures: ImageContent that vision AI can directly analyze
        For others: TextContent in markdown format

    Example:
        # Get Table 1 from document
        fetch_document_asset("abc123", "table", "tab_1")

        # Get figure with default resize (1024px)
        fetch_document_asset("abc123", "figure", "fig_2_1")

        # Get figure at specific size (512px for smaller context)
        fetch_document_asset("abc123", "figure", "fig_2_1", max_size=512)

        # Get original image (no resize)
        fetch_document_asset("abc123", "figure", "fig_2_1", max_size=0)
    """
    result = await asset_service.fetch_asset(
        doc_id, asset_type, asset_id, max_size=max_size
    )

    if not result.success:
        return [TextContent(type="text", text=f"Error: {result.error}")]

    if result.image_base64:
        metadata = (
            f"## Figure: {result.asset_id}\n"
            f"**Page:** {result.page or 'Unknown'}\n"
            f"**Size:** {result.width}×{result.height}\n"
            f"**Format:** {result.image_media_type}"
        )
        return [
            TextContent(type="text", text=metadata),
            ImageContent(
                type="image",
                data=result.image_base64,
                mimeType=result.image_media_type or "image/png",
            ),
        ]
    else:
        lines = [f"## {asset_type.title()}: {result.asset_id}"]
        if result.page:
            lines.append(f"**Page:** {result.page}")
        lines.append("")
        lines.append(result.text_content or "")
        return [TextContent(type="text", text="\n".join(lines))]
