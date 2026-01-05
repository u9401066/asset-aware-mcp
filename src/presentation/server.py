"""
Presentation Layer - MCP Server

FastMCP server with tools and resources for document operations.
Supports async ETL jobs for long-running document processing.
"""

from __future__ import annotations

import json
from typing import Any, Literal, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from src.application.asset_service import AssetService
from src.application.document_service import DocumentService
from src.application.job_service import JobService
from src.application.knowledge_service import KnowledgeService
from src.application.table_service import table_service
from src.domain.job import JobStatus
from src.infrastructure.config import settings
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.job_store import FileJobStore
from src.infrastructure.lightrag_adapter import LightRAGAdapter
from src.infrastructure.pdf_extractor import PyMuPDFExtractor

# Initialize FastMCP server
mcp = FastMCP("Asset-Aware Medical RAG")

# Initialize infrastructure
_repository = FileStorage(settings.data_dir)
_pdf_extractor = PyMuPDFExtractor()  # Lightweight, always available
_knowledge_graph = LightRAGAdapter() if settings.enable_lightrag else None
_job_store = FileJobStore(settings.data_dir)

# Initialize application services
_document_service = DocumentService(
    repository=_repository,
    pdf_extractor=_pdf_extractor,
    knowledge_graph=_knowledge_graph,
)
_asset_service = AssetService(repository=_repository)
_knowledge_service = KnowledgeService(knowledge_graph=_knowledge_graph)
_job_service = JobService(job_store=_job_store, document_service=_document_service)


# ============================================================================
# MCP Tools
# ============================================================================


@mcp.tool()
async def ingest_documents(
    file_paths: list[str],
    async_mode: bool = True,
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
    """
    if async_mode:
        # Create async job and return immediately
        job = await _job_service.create_ingest_job(file_paths)

        return (
            f"# 📋 ETL Job Created\n\n"
            f"**Job ID:** `{job.job_id}`\n"
            f"**Files:** {len(file_paths)}\n"
            f"**Estimated Time:** ~{job.estimated_duration_seconds or 10}s\n\n"
            f'Use `get_job_status("{job.job_id}")` to check progress.\n'
            f"Or use `list_jobs()` to see all active jobs."
        )
    else:
        # Sync mode - wait for completion (original behavior)
        results = await _document_service.ingest(file_paths)

        output_lines = ["# Ingestion Results\n"]
        success_count = sum(1 for r in results if r.success)
        output_lines.append(f"**Processed:** {success_count}/{len(results)} files\n")

        for result in results:
            if result.success:
                output_lines.append(f"\n## ✅ {result.filename}")
                output_lines.append(f"- **doc_id:** `{result.doc_id}`")
                output_lines.append(f"- **title:** {result.title or 'N/A'}")
                output_lines.append(f"- **pages:** {result.pages_processed}")
                output_lines.append(f"- **tables:** {result.tables_found}")
                output_lines.append(f"- **figures:** {result.figures_found}")
                output_lines.append(f"- **sections:** {result.sections_found}")
                output_lines.append(
                    f"- **time:** {result.processing_time_seconds:.2f}s"
                )
            else:
                output_lines.append(f"\n## ❌ {result.filename}")
                output_lines.append(f"- **error:** {result.error}")

        return "\n".join(output_lines)


@mcp.tool()
async def get_job_status(job_id: str) -> str:
    """
    Get the status of an ETL job.

    Use this to check progress of document ingestion started with `ingest_documents`.

    Args:
        job_id: Job ID returned from `ingest_documents`

    Returns:
        Job status including progress, phase, and result (if completed)

    Example:
        get_job_status("job_20251226_143000_abc12345")
    """
    job = await _job_service.get_job(job_id)

    if job is None:
        return f"❌ Job not found: `{job_id}`"

    # Status emoji
    status_emoji = {
        JobStatus.PENDING: "⏳",
        JobStatus.PROCESSING: "🔄",
        JobStatus.COMPLETED: "✅",
        JobStatus.FAILED: "❌",
        JobStatus.CANCELLED: "🚫",
    }

    lines = [
        f"# Job Status: {status_emoji.get(job.status, '❓')} {job.status.value.upper()}\n",
        f"**Job ID:** `{job.job_id}`",
        f"**Type:** {job.job_type.value}",
        f"**Created:** {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Progress bar
    if not job.is_terminal:
        progress = job.progress.percentage
        bar_filled = int(progress / 5)
        bar_empty = 20 - bar_filled
        progress_bar = f"[{'█' * bar_filled}{'░' * bar_empty}] {progress:.0f}%"
        lines.append(f"\n**Progress:** {progress_bar}")
        lines.append(f"**Phase:** {job.progress.current_phase}")
        lines.append(f"**Status:** {job.progress.message}")
    else:
        if job.duration_seconds:
            lines.append(f"**Duration:** {job.duration_seconds:.1f}s")

    # Input/Output
    lines.append(f"\n**Input Files:** {len(job.input_files)}")
    if job.output_doc_ids:
        lines.append(f"**Output Documents:** {len(job.output_doc_ids)}")
        for doc_id in job.output_doc_ids:
            lines.append(f"  - `{doc_id}`")

    # Error (if any)
    if job.error:
        lines.append(f"\n**Error:** {job.error}")

    # Result summary (if completed)
    if job.status == JobStatus.COMPLETED and job.result:
        lines.append("\n---")
        lines.append("✅ **Job completed successfully!**")
        lines.append(f"Created {len(job.output_doc_ids)} document(s).")
        lines.append("Use `inspect_document_manifest(<doc_id>)` to view details.")

    return "\n".join(lines)


@mcp.tool()
async def list_jobs(active_only: bool = False) -> str:
    """
    List ETL jobs.

    Args:
        active_only: If True, only show pending/processing jobs

    Returns:
        List of jobs with status and progress
    """
    if active_only:
        jobs = await _job_service.list_active_jobs()
        title = "Active Jobs"
    else:
        jobs = await _job_service.list_jobs(limit=20)
        title = "Recent Jobs"

    if not jobs:
        if active_only:
            return "No active jobs. All ETL tasks have completed."
        return "No jobs found. Use `ingest_documents` to process files."

    status_emoji = {
        JobStatus.PENDING: "⏳",
        JobStatus.PROCESSING: "🔄",
        JobStatus.COMPLETED: "✅",
        JobStatus.FAILED: "❌",
        JobStatus.CANCELLED: "🚫",
    }

    lines = [f"# {title} ({len(jobs)})\n"]

    for job in jobs:
        emoji = status_emoji.get(job.status, "❓")
        progress = (
            f"{job.progress_percentage:.0f}%"
            if job.progress_percentage < 100
            else "Done"
        )

        lines.append(f"## {emoji} `{job.job_id}`")
        lines.append(f"- **Type:** {job.job_type.value}")
        lines.append(f"- **Status:** {job.status.value} ({progress})")
        if job.current_phase:
            lines.append(f"- **Phase:** {job.current_phase}")
        if job.message:
            lines.append(f"- **Message:** {job.message}")
        if job.error:
            lines.append(f"- **Error:** {job.error}")
        lines.append(
            f"- **Files:** {job.input_file_count} → {job.output_doc_count} docs"
        )
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def cancel_job(job_id: str) -> str:
    """
    Cancel a running ETL job.

    Args:
        job_id: Job ID to cancel

    Returns:
        Confirmation message
    """
    success = await _job_service.cancel_job(job_id)

    if success:
        return f"🚫 Job `{job_id}` has been cancelled."
    else:
        return f"❌ Could not cancel job `{job_id}`. It may have already completed or doesn't exist."


@mcp.tool()
async def list_documents() -> str:
    """
    List all processed documents with summaries.

    Returns:
        List of documents with doc_id, title, and asset counts
    """
    documents = await _document_service.list_documents()

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
    manifest = await _document_service.get_manifest(doc_id)

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
            output_lines.append(f"... and {len(manifest.lightrag_entities) - 20} more")

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
    result = await _asset_service.fetch_asset(
        doc_id, asset_type, asset_id, max_size=max_size
    )

    if not result.success:
        return [TextContent(type="text", text=f"Error: {result.error}")]

    # Format response based on content type
    if result.image_base64:
        # Return ImageContent for vision AI to analyze
        # Also include metadata as TextContent
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
        # For text content (tables, sections, full_text)
        lines = [f"## {asset_type.title()}: {result.asset_id}"]
        if result.page:
            lines.append(f"**Page:** {result.page}")
        lines.append("")
        lines.append(result.text_content or "")
        return [TextContent(type="text", text="\n".join(lines))]


@mcp.tool()
async def consult_knowledge_graph(
    query: str,
    mode: str = "hybrid",
) -> str:
    """
    Query the LightRAG knowledge graph for cross-document insights.

    Query Modes:
    - "local": Specific details from nearby context
    - "global": High-level patterns and themes
    - "hybrid": Both local and global (recommended for most queries)

    Best for:
    - Comparing findings across multiple papers
    - Finding drug interactions or dosage patterns
    - Exploring relationships between concepts

    Args:
        query: Natural language question
        mode: Query mode ("local", "global", or "hybrid")

    Returns:
        Answer synthesized from indexed documents

    Example:
        consult_knowledge_graph("What are the dosing recommendations for remimazolam?")
        consult_knowledge_graph("Compare sedation outcomes between propofol and remimazolam", mode="global")
    """
    return await _knowledge_service.query(query, mode=mode)


@mcp.tool()
async def export_knowledge_graph(
    format: str = "summary",
    limit: int = 50,
) -> str:
    """
    Export the knowledge graph for visualization.

    Use this to understand what entities and relationships exist in the graph.

    Output Formats:
    - "summary": Statistics + sample nodes/edges (default, recommended)
    - "json": Full node and edge data as JSON
    - "mermaid": Mermaid.js diagram syntax for visualization

    Args:
        format: Output format - "summary", "json", or "mermaid"
        limit: Maximum nodes to include (default 50, use smaller for mermaid)

    Returns:
        Graph data in requested format

    Examples:
        # Get overview of the knowledge graph
        export_knowledge_graph("summary")

        # Get Mermaid diagram for visualization (use limit=20 for readability)
        export_knowledge_graph("mermaid", limit=20)

        # Get full JSON data
        export_knowledge_graph("json", limit=100)
    """
    if _knowledge_graph is None:
        return "Error: LightRAG is not enabled. Set ENABLE_LIGHTRAG=true in .env"

    result = await _knowledge_graph.export_graph(
        format=format,
        limit=limit,
    )

    if format == "mermaid" and "diagram" in result:
        # Return mermaid diagram directly for rendering
        return f"""## Knowledge Graph Visualization

**Nodes:** {result.get("node_count", 0)} | **Edges:** {result.get("edge_count", 0)}

```mermaid
{result["diagram"]}
```
"""
    elif format == "summary":
        lines = [
            "## Knowledge Graph Summary",
            "",
            f"**Total Nodes:** {result.get('total_nodes', 0)}",
            f"**Total Edges:** {result.get('total_edges', 0)}",
            "",
            "### Entity Types",
        ]
        for etype, count in cast(
            dict[str, int], result.get("entity_types", {})
        ).items():
            lines.append(f"- {etype}: {count}")

        lines.append("\n### Sample Nodes")
        for node in cast(list[dict[str, str]], result.get("sample_nodes", []))[:5]:
            lines.append(f"- **{node['id']}** ({node['type']})")
            if node.get("description"):
                lines.append(f"  _{node['description'][:100]}_")

        lines.append("\n### Sample Relationships")
        for edge in cast(list[dict[str, str]], result.get("sample_edges", []))[:5]:
            lines.append(f"- {edge['source']} → {edge['target']}")
            if edge.get("keywords"):
                lines.append(f"  _Keywords: {edge['keywords']}_")

        return "\n".join(lines)
    else:
        # JSON format
        import json

        return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================================
# A2T (Anything to Table) Tools
# ============================================================================


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
            manifest = await _document_service.get_manifest(doc_id)
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
    result = await _asset_service.fetch_asset(doc_id, "section", section_id)

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
            est = table_service.estimate_table_tokens(table_id)
            lines.extend(
                [
                    f"## Table `{table_id}`",
                    f"- **Content Tokens:** ~{est['content_tokens']}",
                    f"- **Preview (10 rows):** ~{est['preview_tokens']}",
                    f"- **Full Preview:** ~{est['full_preview_tokens']}",
                    f"- **Rows:** {est['row_count']}",
                    f"- **Tokens/Row:** ~{est['tokens_per_row']}",
                    "",
                ]
            )
        except ValueError as e:
            lines.append(f"❌ Table error: {e}\n")

    if draft_id:
        try:
            draft = table_service.get_draft(draft_id)
            lines.extend(
                [
                    f"## Draft `{draft_id}`",
                    f"- **Total Tokens:** ~{draft.estimate_tokens()}",
                    f"- **Pending Rows:** {len(draft.pending_rows)}",
                    "",
                ]
            )
        except ValueError as e:
            lines.append(f"❌ Draft error: {e}\n")

    if text:
        est_tokens = len(text) // 4
        lines.extend(
            [
                "## Custom Text",
                f"- **Characters:** {len(text)}",
                f"- **Est. Tokens:** ~{est_tokens}",
                "",
            ]
        )

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
            import json

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
        # Note: render_table logic will be implemented in Phase 2
        # For now, we'll return a placeholder if not implemented
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


# ============================================================================
# MCP Resources (Dynamic - Auto-updates with new files)
# ============================================================================


@mcp.resource("documents://list")
async def resource_document_list() -> str:
    """Dynamic resource listing all processed documents."""
    result: str = await list_documents()
    return result


@mcp.resource("document://{doc_id}/manifest")
async def resource_document_manifest(doc_id: str) -> str:
    """Dynamic resource for document manifest."""
    result: str = await inspect_document_manifest(doc_id)
    return result


@mcp.resource("document://{doc_id}/figures")
async def resource_document_figures(doc_id: str) -> str:
    """
    Dynamic resource listing all figures in a document.

    Returns a concise outline of figures with IDs, pages, and sizes.
    Use fetch_document_asset to retrieve actual image content.
    """
    manifest = await _document_service.get_manifest(doc_id)
    if manifest is None:
        return f"Document not found: {doc_id}"

    lines = [
        f"# Figures in {manifest.title or doc_id}",
        "",
        f"**Total Figures:** {len(manifest.assets.figures)}",
        "",
        "| ID | Page | Size | Caption |",
        "|-----|------|------|---------|",
    ]

    for fig in manifest.assets.figures:
        caption = (
            (fig.caption[:40] + "...")
            if fig.caption and len(fig.caption) > 40
            else (fig.caption or "-")
        )
        lines.append(
            f"| `{fig.id}` | {fig.page or '-'} | {fig.width}×{fig.height} | {caption} |"
        )

    lines.extend(
        [
            "",
            "---",
            "_Use `fetch_document_asset(doc_id, 'figure', '<id>')` to retrieve image content._",
        ]
    )

    return "\n".join(lines)


@mcp.resource("document://{doc_id}/tables")
async def resource_document_tables(doc_id: str) -> str:
    """
    Dynamic resource listing all tables in a document.

    Returns a concise outline of tables with IDs and descriptions.
    Use fetch_document_asset to retrieve table content as markdown.
    """
    manifest = await _document_service.get_manifest(doc_id)
    if manifest is None:
        return f"Document not found: {doc_id}"

    lines = [
        f"# Tables in {manifest.title or doc_id}",
        "",
        f"**Total Tables:** {len(manifest.assets.tables)}",
        "",
        "| ID | Page | Description |",
        "|-----|------|-------------|",
    ]

    for tab in manifest.assets.tables:
        desc = (
            (tab.caption[:50] + "...")
            if tab.caption and len(tab.caption) > 50
            else (tab.caption or "-")
        )
        lines.append(f"| `{tab.id}` | {tab.page or '-'} | {desc} |")

    lines.extend(
        [
            "",
            "---",
            "_Use `fetch_document_asset(doc_id, 'table', '<id>')` to retrieve table content._",
        ]
    )

    return "\n".join(lines)


@mcp.resource("document://{doc_id}/sections")
async def resource_document_sections(doc_id: str) -> str:
    """
    Dynamic resource listing all sections in a document.

    Returns a hierarchical outline of document sections.
    Use fetch_document_asset to retrieve section text content.
    """
    manifest = await _document_service.get_manifest(doc_id)
    if manifest is None:
        return f"Document not found: {doc_id}"

    lines = [
        f"# Sections in {manifest.title or doc_id}",
        "",
        f"**Total Sections:** {len(manifest.assets.sections)}",
        "",
    ]

    for sec in manifest.assets.sections:
        indent = "  " * (sec.level - 1) if sec.level > 1 else ""
        line_info = f"(L{sec.start_line}-{sec.end_line})" if sec.start_line else ""
        lines.append(f"{indent}- **{sec.title}** `{sec.id}` {line_info}")

    lines.extend(
        [
            "",
            "---",
            "_Use `fetch_document_asset(doc_id, 'section', '<id>')` to retrieve section text._",
        ]
    )

    return "\n".join(lines)


@mcp.resource("document://{doc_id}/outline")
async def resource_document_outline(doc_id: str) -> str:
    """
    Dynamic resource showing complete document outline.

    Provides a bird's-eye view of the document structure including:
    - Metadata (title, pages, source)
    - Section hierarchy
    - Figure summary
    - Table summary
    - Knowledge graph entities (if indexed)

    This is the recommended starting point for exploring a document.
    """
    manifest = await _document_service.get_manifest(doc_id)
    if manifest is None:
        return f"Document not found: {doc_id}"

    lines = [
        f"# 📄 {manifest.title or 'Untitled Document'}",
        "",
        "## Metadata",
        f"- **ID:** `{doc_id}`",
        f"- **Pages:** {manifest.page_count}",
        f"- **Source:** {manifest.filename or 'Unknown'}",
        "",
    ]

    # Sections outline
    lines.append("## 📑 Sections")
    if manifest.assets.sections:
        for sec in manifest.assets.sections:
            indent = "  " * (sec.level - 1) if sec.level > 1 else ""
            lines.append(f"{indent}- {sec.title}")
    else:
        lines.append("_No sections detected_")
    lines.append("")

    # Figures summary
    lines.append(f"## 🖼️ Figures ({len(manifest.assets.figures)})")
    if manifest.assets.figures:
        for fig in manifest.assets.figures[:5]:
            caption = f": {fig.caption[:30]}..." if fig.caption else ""
            lines.append(f"- `{fig.id}` (P.{fig.page or '?'}){caption}")
        if len(manifest.assets.figures) > 5:
            lines.append(f"- _...and {len(manifest.assets.figures) - 5} more_")
    else:
        lines.append("_No figures detected_")
    lines.append("")

    # Tables summary
    lines.append(f"## 📊 Tables ({len(manifest.assets.tables)})")
    if manifest.assets.tables:
        for tab in manifest.assets.tables[:5]:
            desc = f": {tab.caption[:30]}..." if tab.caption else ""
            lines.append(f"- `{tab.id}` (P.{tab.page or '?'}){desc}")
        if len(manifest.assets.tables) > 5:
            lines.append(f"- _...and {len(manifest.assets.tables) - 5} more_")
    else:
        lines.append("_No tables detected_")
    lines.append("")

    # Knowledge graph entities
    if manifest.lightrag_entities:
        lines.append(
            f"## 🔗 Knowledge Graph Entities ({len(manifest.lightrag_entities)})"
        )
        lines.append(", ".join(manifest.lightrag_entities[:15]))
        if len(manifest.lightrag_entities) > 15:
            lines.append(f"_...and {len(manifest.lightrag_entities) - 15} more_")
    lines.append("")

    # Quick actions
    lines.extend(
        [
            "---",
            "## Quick Actions",
            f"- View figures: `document://{doc_id}/figures`",
            f"- View tables: `document://{doc_id}/tables`",
            f"- View sections: `document://{doc_id}/sections`",
            f"- Fetch asset: `fetch_document_asset('{doc_id}', '<type>', '<id>')`",
        ]
    )

    return "\n".join(lines)


@mcp.resource("knowledge-graph://summary")
async def resource_knowledge_graph_summary() -> str:
    """
    Dynamic resource showing knowledge graph statistics.

    Provides an overview of the indexed knowledge including:
    - Total nodes and edges
    - Entity type distribution
    - Sample entities and relationships
    """
    if _knowledge_graph is None:
        return "LightRAG is not enabled. Set ENABLE_LIGHTRAG=true in .env"

    result = await _knowledge_graph.export_graph(format="summary", limit=30)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [
        "# 🔗 Knowledge Graph Summary",
        "",
        f"**Total Nodes:** {result.get('total_nodes', 0)}",
        f"**Total Edges:** {result.get('total_edges', 0)}",
        "",
        "## Entity Types",
    ]

    for etype, count in cast(dict[str, int], result.get("entity_types", {})).items():
        lines.append(f"- **{etype}:** {count}")

    lines.append("\n## Sample Entities")
    for node in cast(list[dict[str, str]], result.get("sample_nodes", []))[:8]:
        lines.append(f"- {node['id']} ({node['type']})")  # type: ignore

    lines.extend(
        [
            "",
            "---",
            "_Use `consult_knowledge_graph(query)` to query the graph._",
            "_Use `export_knowledge_graph('mermaid')` to visualize._",
        ]
    )

    return "\n".join(lines)


# ============================================================================
# A2T Table Resources (for resumption and token-efficient workflows)
# ============================================================================


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


# ============================================================================
# Server Entry Point
# ============================================================================


def main() -> None:
    """Run the MCP server."""

    # Run with stdio transport
    mcp.run()


if __name__ == "__main__":
    main()
