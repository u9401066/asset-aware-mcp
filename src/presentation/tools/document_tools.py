"""
Document Tools - ETL + 文件管理 MCP 工具

包含：
- parse_pdf_structure: Marker 結構化解析
- search_source_location: 來源位置搜尋
- ingest_documents: PDF 文件攝入
- list_documents: 列出所有文件
- delete_document: 刪除已攝入的 PDF 文件及本地 artifacts
- convert_pdf_to_docx: 將 PDF 內容層重建為 DOCX
- convert_pdf_to_pptx: 將 PDF Markdown 重建為可編輯 PPTX
- inspect_document_manifest: 查看文件 Manifest
- fetch_document_asset: 擷取文件資產
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import ImageContent, TextContent

from src.application.document_service import (
    build_doc_id_unique_suffix,
    build_page_number_map,
    format_page_ranges,
    materialize_pdf_page_subset,
    normalize_page_ranges,
)
from src.infrastructure.config import settings
from src.presentation.dependencies import (
    asset_service,
    document_service,
    get_marker_extractor,
    job_service,
    layout_visualizer,
    ocr_processor,
    pdf_extractor,
    repository,
    segmentation_service,
)
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import (
    create_subrange_progress_callback,
    log_message,
    report_progress,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    Context = Any


def _display_line_range(start_line: int, end_line: int) -> str:
    if start_line < 0 or end_line < 0 or end_line < start_line:
        return "L?"
    return f"L{start_line + 1}-{end_line}"


def _format_line_range(start_line: int | None, end_line: int | None) -> str | None:
    if (
        start_line is None
        or end_line is None
        or start_line < 0
        or end_line < start_line
    ):
        return None
    return _display_line_range(start_line, end_line)


@mcp.tool()
async def parse_pdf_structure(
    pdf_path: str,
    output_dir: str | None = None,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
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
        marker_max_pages_per_chunk: 大型 PDF 時每個 Marker chunk 的最大頁數；0 表示整本一次處理
        extract_figures: 是否輸出 figures/ 與 FigureAsset；大型檔建議可先關閉
        page_ranges: 指定要攝入的頁段，例如 ["1-50", "120-160"]

    Returns:
        解析結果摘要和 doc_id
    """
    import time
    from pathlib import Path

    start = time.time()
    pdf_file = Path(pdf_path)

    await log_message(ctx, "info", f"parse_pdf_structure start: {pdf_path}")
    await report_progress(ctx, 5, message=f"Validating {pdf_file.name}")

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"

    total_page_count = pdf_extractor.get_page_count(pdf_file)
    normalized_page_ranges = normalize_page_ranges(page_ranges, total_page_count)
    page_map = build_page_number_map(normalized_page_ranges)

    # Determine output directory (same convention as ingest_documents)
    if output_dir:
        out_path = Path(output_dir)
        from src.domain.value_objects import DocId

        doc_id_obj = DocId.generate(
            pdf_file.stem,
            build_doc_id_unique_suffix(pdf_file, normalized_page_ranges),
        )
    else:
        from src.domain.value_objects import DocId

        doc_id_obj = DocId.generate(
            pdf_file.stem,
            build_doc_id_unique_suffix(pdf_file, normalized_page_ranges),
        )
        out_path = settings.data_dir / doc_id_obj.value

    try:
        out_path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_file, out_path / "original.pdf")

        active_pdf = pdf_file
        if normalized_page_ranges:
            active_pdf = materialize_pdf_page_subset(
                pdf_file,
                out_path / "selected_pages.pdf",
                normalized_page_ranges,
            )

        if ocr_enabled:
            await report_progress(
                ctx, 15, message=f"Running OCR preprocessing for {pdf_file.name}"
            )
            if ocr_processor is None:
                return "❌ OCR processor not configured."
            active_pdf = ocr_processor.preprocess_pdf(
                pdf_file,
                out_path / "ocr_processed.pdf",
                language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
            ).output_path

        await report_progress(
            ctx, 25, message=f"Loading Marker extractor for {pdf_file.name}"
        )
        extractor = get_marker_extractor()
        await report_progress(
            ctx, 45, message=f"Parsing structure from {pdf_file.name}"
        )
        parse_result = extractor.parse(
            active_pdf,
            extract_images=extract_figures,
            max_pages_per_chunk=(
                marker_max_pages_per_chunk if marker_max_pages_per_chunk > 0 else None
            ),
            page_map=page_map or None,
            reported_page_count=total_page_count if page_map else None,
        )
        manifest = extractor.convert_to_manifest(
            parse_result,
            pdf_file,
            out_path,
            doc_id=doc_id_obj.value,
        )
        await report_progress(ctx, 90, message=f"Finalizing assets for {pdf_file.name}")

        segmentation_path = ""
        try:
            if out_path.is_relative_to(settings.data_dir):
                segmentation_file = (
                    await segmentation_service.save_document_segmentation(
                        manifest.doc_id
                    )
                )
                segmentation_path = str(segmentation_file)
        except Exception:
            segmentation_path = ""

        elapsed = time.time() - start

        lines = [
            "# ✅ PDF Structure Parsed (Marker)",
            "",
            f"**doc_id:** `{manifest.doc_id}`",
            f"**Title:** {manifest.title or 'N/A'}",
            f"**Pages:** {manifest.page_count}",
            f"**Pages Processed:** {len(page_map) or total_page_count}",
            f"**Time:** {elapsed:.1f}s",
            f"**Chunk Size:** {marker_max_pages_per_chunk or 'full document'}",
            f"**Extract Figures:** {'yes' if extract_figures else 'no'}",
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
            f"- Original PDF: `{out_path / 'original.pdf'}`",
            "",
        ]
        if normalized_page_ranges:
            lines.insert(
                7, f"**Page Ranges:** {format_page_ranges(normalized_page_ranges)}"
            )
            lines.insert(-1, f"- Selected PDF: `{out_path / 'selected_pages.pdf'}`")
        if segmentation_path:
            lines.insert(-1, f"- Segmentation: `{segmentation_path}`")

        # Show TOC preview
        if manifest.toc:
            lines.append("## Table of Contents")
            for item in manifest.toc[:10]:
                lines.append(f"- {item}")
            if len(manifest.toc) > 10:
                lines.append(f"- _...and {len(manifest.toc) - 10} more_")

        await report_progress(ctx, 100, message=f"Finished parsing {pdf_file.name}")
        await log_message(
            ctx, "info", f"parse_pdf_structure complete: {manifest.doc_id}"
        )
        return "\n".join(lines)

    except RuntimeError as e:
        await log_message(ctx, "error", f"parse_pdf_structure unavailable: {e}")
        return f"❌ Marker parsing unavailable: {e!s}"
    except Exception as e:
        await log_message(ctx, "error", f"parse_pdf_structure failed: {e}")
        return f"❌ Marker parsing failed: {e!s}"


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
        return f"❌ Search failed: {e!s}"


@mcp.tool()
async def ingest_documents(
    file_paths: list[str],
    async_mode: bool = True,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
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
        marker_max_pages_per_chunk: When using Marker, split very large PDFs into fixed-size page chunks.
                                    Set 0 to parse the whole document in one pass.
        extract_figures: When using Marker, control whether image crops are extracted and saved.
                         Disable this first for image-heavy textbooks to reduce memory pressure.
        page_ranges: 1-indexed inclusive page ranges applied to every input file, e.g. ["1-50", "120-160"].

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
    await log_message(
        ctx,
        "info",
        f"ingest_documents start: files={len(file_paths)} use_marker={use_marker} async_mode={async_mode}",
    )
    await report_progress(ctx, 5, message="Validating ingest request")

    # Lazy-load Marker if requested
    if use_marker and document_service.marker_extractor is None:
        try:
            document_service.marker_extractor = get_marker_extractor()
        except RuntimeError as e:
            return (
                "# ❌ Marker Backend Not Available\n\n"
                f"{e!s}\n\n"
                "Use default PyMuPDF mode, or install the optional Marker dependency first."
            )

    if async_mode:
        await report_progress(ctx, 20, message="Creating background ETL job")
        job = await job_service.create_ingest_job(
            file_paths,
            parameters={
                "use_marker": use_marker,
                "ocr_enabled": ocr_enabled,
                "ocr_language": ocr_language,
                "rotate_pages": rotate_pages,
                "deskew": deskew,
                "marker_max_pages_per_chunk": marker_max_pages_per_chunk,
                "extract_figures": extract_figures,
                "page_ranges": page_ranges or [],
            },
        )
        await report_progress(ctx, 100, message=f"Created job {job.job_id}")
        await log_message(ctx, "info", f"ingest_documents job created: {job.job_id}")

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
        await report_progress(ctx, 15, message="Starting synchronous ingestion")
        results = await document_service.ingest(
            file_paths,
            use_marker=use_marker,
            progress_callback=create_subrange_progress_callback(ctx, 15, 95),
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            page_ranges=page_ranges,
        )
        await report_progress(ctx, 100, message="Synchronous ingestion finished")
        await log_message(ctx, "info", "ingest_documents sync completed")

        backend_label = "Marker" if use_marker else "PyMuPDF"
        output_lines = [f"# Ingestion Results ({backend_label})\n"]
        success_count = sum(1 for r in results if r.success)
        output_lines.append(f"**Processed:** {success_count}/{len(results)} files\n")
        if ocr_enabled:
            output_lines.append(
                f"**OCR:** enabled ({ocr_language}, rotate_pages={rotate_pages}, deskew={deskew})\n"
            )
        if use_marker:
            output_lines.append(
                f"**Marker chunk size:** {marker_max_pages_per_chunk or 'full document'}\n"
            )
            output_lines.append(
                f"**Extract figures:** {'yes' if extract_figures else 'no'}\n"
            )
        if page_ranges:
            output_lines.append(f"**Page ranges:** {', '.join(page_ranges)}\n")

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
        output_lines.append(f"- **text_quality:** {doc.text_quality_status}")
        if doc.ocr_recommended:
            output_lines.append("- **ocr_recommended:** yes")
        output_lines.append(f"- **ingested:** {doc.ingested_at}")
        output_lines.append("")

    return "\n".join(output_lines)


@mcp.tool()
async def delete_document(doc_id: str) -> str:
    """
    刪除已攝入的 PDF 文件及其本地 artifacts。

    會移除 data/{doc_id}/ 下的 manifest、markdown、images、blocks.json 等檔案。
    若啟用了 LightRAG，會一併嘗試刪除對應的知識圖譜文件索引。
    """
    result = await document_service.delete_document(doc_id)
    if not result.get("success"):
        return f"❌ 刪除失敗：{result.get('error', '未知錯誤')}"

    lines = [
        "✅ PDF 文件已刪除",
        f"- **doc_id**: `{result.get('doc_id', '')}`",
        f"- **filename**: {result.get('filename', '')}",
    ]
    if "knowledge_graph_status" in result:
        lines.append(
            f"- **knowledge_graph**: {result.get('knowledge_graph_status', 'unknown')}"
        )
    for warning in result.get("warnings", []):
        lines.append(f"- **warning**: {warning}")
    return "\n".join(lines)


@mcp.tool()
async def convert_pdf_to_docx(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "content",
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 PDF 文件轉為 DOCX。

    轉換範圍：
    - `content`：內容層重建。根據 PDF ETL 的 Markdown/表格/圖片生成可讀 DOCX。
    - `fidelity`：目前不支援，因為 PDF ETL 並非版面可逆。
    """
    await log_message(ctx, "info", f"convert_pdf_to_docx start: {doc_id}")
    await report_progress(ctx, 10, message=f"Converting {doc_id} to DOCX")
    result = await document_service.convert_pdf_to_docx(
        doc_id,
        output_path,
        mode=mode,
    )
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_pdf_to_docx failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished DOCX conversion for {doc_id}")
    await log_message(ctx, "info", f"convert_pdf_to_docx complete: {doc_id}")

    return "\n".join(
        [
            "✅ PDF → DOCX 轉換成功",
            f"- **doc_id**: `{result.get('doc_id', '')}`",
            f"- **mode**: {result.get('mode', mode)}",
            f"- **output_path**: `{result.get('output_path', '')}`",
            f"- **figures_embedded**: {result.get('figures_embedded', 0)}",
            f"- **tables_found**: {result.get('tables_found', 0)}",
        ]
    )


@mcp.tool()
async def convert_pdf_to_pptx(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "content",
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 PDF 文件轉為 PPTX。

    轉換範圍：
    - `content`：依據 PDF ETL 的 Markdown/圖像生成可編輯投影片。
    """
    await log_message(ctx, "info", f"convert_pdf_to_pptx start: {doc_id}")
    await report_progress(ctx, 10, message=f"Converting {doc_id} to PPTX")
    result = await document_service.convert_pdf_to_pptx(
        doc_id,
        output_path,
        mode=mode,
    )
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_pdf_to_pptx failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished PPTX conversion for {doc_id}")
    await log_message(ctx, "info", f"convert_pdf_to_pptx complete: {doc_id}")

    return "\n".join(
        [
            "✅ PDF → PPTX 轉換成功",
            f"- **doc_id**: `{result.get('doc_id', '')}`",
            f"- **mode**: {result.get('mode', mode)}",
            f"- **output_path**: `{result.get('output_path', '')}`",
            f"- **slides_created**: {result.get('slides_created', 0)}",
            f"- **figure_slides**: {result.get('figure_slides', 0)}",
        ]
    )


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
    output_lines.append(f"**text_quality:** {manifest.text_quality_status}")
    output_lines.append(f"**visible_text_chars:** {manifest.visible_text_chars}")
    output_lines.append(f"**visible_text_lines:** {manifest.visible_text_lines}")
    output_lines.append(f"**repeated_line_ratio:** {manifest.repeated_line_ratio:.2f}")
    output_lines.append(f"**ocr_recommended:** {'yes' if manifest.ocr_recommended else 'no'}")
    if manifest.text_quality_reason:
        output_lines.append(f"**text_quality_reason:** {manifest.text_quality_reason}")
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
                f"{indent}- `{sec.id}`: {sec.title} ({_display_line_range(sec.start_line, sec.end_line)})"
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
            output_lines.append(f"... and {len(manifest.lightrag_entities) - 20} more")

    return "\n".join(output_lines)


@mcp.tool()
async def export_document_segmentation(
    doc_id: str,
    page: int | None = None,
    limit: int | None = None,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """匯出整合 manifest、blocks、assets、reading order 的 segmentation schema。"""
    await log_message(ctx, "info", f"export_document_segmentation start: {doc_id}")
    await report_progress(ctx, 10, message=f"Loading manifest for {doc_id}")

    target = await segmentation_service.save_document_segmentation(
        doc_id,
        output_path=output_path,
        page=page,
        limit=limit,
    )
    segmentation = await segmentation_service.export_document_segmentation(
        doc_id,
        page=page,
        limit=limit,
    )

    await report_progress(ctx, 100, message=f"Segmentation exported for {doc_id}")
    await log_message(ctx, "info", f"export_document_segmentation complete: {doc_id}")

    summary_lines = [
        "# Unified Segmentation Export",
        "",
        f"**doc_id:** `{segmentation.doc_id}`",
        f"**backend:** {segmentation.source_backend}",
        f"**reading_order_policy:** {segmentation.reading_order_policy}",
        f"**segments:** {len(segmentation.segments)}",
        f"**pages:** {segmentation.page_count}",
        f"**output:** `{target}`",
        "",
        "## Segment Counts by Page",
    ]
    for page_number, count in segmentation.page_count_summary().items():
        summary_lines.append(f"- Page {page_number}: {count}")

    preview_segments = segmentation.segments[:5]
    if preview_segments:
        summary_lines.extend(["", "## Preview"])
        for segment in preview_segments:
            summary_lines.append(
                f"- #{segment.reading_order} P{segment.page_number} {segment.segment_type}"
                f" [{segment.segment_id}]"
            )

    return "\n".join(summary_lines)


@mcp.tool()
async def visualize_document_layout(
    doc_id: str,
    page: int = 1,
    show_labels: bool = True,
    include_reading_order: bool = True,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> list[TextContent | ImageContent]:
    """產生 PDF page overlay，直接檢查 block bbox、類型與 reading order。"""
    await log_message(
        ctx, "info", f"visualize_document_layout start: {doc_id} page={page}"
    )
    await report_progress(
        ctx, 10, message=f"Loading segmentation for {doc_id} page {page}"
    )

    segmentation = await segmentation_service.export_document_segmentation(
        doc_id, page=page
    )
    await report_progress(
        ctx, 55, message=f"Rendering layout overlay for {doc_id} page {page}"
    )
    overlay = layout_visualizer.render_page_overlay(
        repository.get_doc_dir(doc_id),
        segmentation,
        page,
        show_labels=show_labels,
        include_reading_order=include_reading_order,
        output_path=output_path,
    )

    await report_progress(
        ctx, 100, message=f"Layout overlay ready for {doc_id} page {page}"
    )
    await log_message(
        ctx, "info", f"visualize_document_layout complete: {doc_id} page={page}"
    )

    summary = [
        f"## Layout Overlay: {doc_id}",
        f"**Page:** {page}",
        f"**Segments:** {len(segmentation.segments)}",
        f"**Image Size:** {overlay.width}×{overlay.height}",
    ]
    if overlay.output_path:
        summary.append(f"**Saved To:** {overlay.output_path}")

    return [
        TextContent(type="text", text="\n".join(summary)),
        ImageContent(type="image", data=overlay.image_base64, mimeType="image/png"),
    ]


@mcp.tool()
async def ocr_pdf_document(
    pdf_path: str,
    output_path: str | None = None,
    language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    ctx: Context | None = None,
) -> str:
    """執行按需 OCR 前處理，產生可再供 ingest/parse 使用的 PDF。"""
    pdf_file = Path(pdf_path)
    await log_message(ctx, "info", f"ocr_pdf_document start: {pdf_path}")
    await report_progress(ctx, 10, message=f"Preparing OCR for {pdf_file.name}")

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"
    if ocr_processor is None:
        return "❌ OCR processor not configured."

    target = (
        Path(output_path)
        if output_path
        else pdf_file.with_name(f"{pdf_file.stem}.ocr.pdf")
    )
    result = ocr_processor.preprocess_pdf(
        pdf_file,
        target,
        language=language,
        rotate_pages=rotate_pages,
        deskew=deskew,
    )

    await report_progress(
        ctx, 100, message=f"OCR preprocessing finished for {pdf_file.name}"
    )
    await log_message(ctx, "info", f"ocr_pdf_document complete: {target}")

    return "\n".join(
        [
            "✅ OCR preprocessing completed",
            f"- **input**: `{pdf_path}`",
            f"- **output**: `{result.output_path}`",
            f"- **language**: {result.language}",
            f"- **rotate_pages**: {result.rotate_pages}",
            f"- **deskew**: {result.deskew}",
        ]
    )


@mcp.tool()
async def fetch_document_asset(
    doc_id: str,
    asset_type: str,
    asset_id: str = "full",
    max_size: int | None = None,
    ctx: Context | None = None,
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
    await log_message(
        ctx, "info", f"fetch_document_asset start: {doc_id} {asset_type}:{asset_id}"
    )
    await report_progress(
        ctx, 10, message=f"Fetching {asset_type} {asset_id} from {doc_id}"
    )
    result = await asset_service.fetch_asset(
        doc_id, asset_type, asset_id, max_size=max_size
    )

    if not result.success:
        await log_message(ctx, "error", f"fetch_document_asset failed: {result.error}")
        return [TextContent(type="text", text=f"Error: {result.error}")]

    if result.image_base64:
        await report_progress(
            ctx, 100, message=f"Fetched {asset_type} {asset_id} from {doc_id}"
        )
        metadata_lines = [
            f"## Figure: {result.asset_id}",
            f"**Page:** {result.page or 'Unknown'}",
            f"**Size:** {result.width}×{result.height}",
            f"**Format:** {result.image_media_type}",
        ]
        line_range = _format_line_range(result.line_start, result.line_end)
        if line_range:
            metadata_lines.append(f"**Line Range:** {line_range}")
        if result.section_title:
            metadata_lines.append(f"**Section:** {result.section_title}")
        if result.source_block_id:
            metadata_lines.append(f"**Source Block:** {result.source_block_id}")
        return [
            TextContent(type="text", text="\n".join(metadata_lines)),
            ImageContent(
                type="image",
                data=result.image_base64,
                mimeType=result.image_media_type or "image/png",
            ),
        ]
    else:
        await report_progress(
            ctx, 100, message=f"Fetched {asset_type} {asset_id} from {doc_id}"
        )
        lines = [f"## {asset_type.title()}: {result.asset_id}"]
        if result.page:
            lines.append(f"**Page:** {result.page}")
        line_range = _format_line_range(result.line_start, result.line_end)
        if line_range:
            lines.append(f"**Line Range:** {line_range}")
        if result.section_title:
            lines.append(f"**Section:** {result.section_title}")
        if result.source_block_id:
            lines.append(f"**Source Block:** {result.source_block_id}")
        lines.append("")
        lines.append(result.text_content or "")
        return [TextContent(type="text", text="\n".join(lines))]
