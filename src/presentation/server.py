"""
Presentation Layer - MCP Server

FastMCP server with tools and resources for document operations.
Supports async ETL jobs for long-running document processing.
"""

from __future__ import annotations

from typing import cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from src.application.asset_service import AssetService
from src.application.document_service import DocumentService
from src.application.job_service import JobService
from src.application.knowledge_service import KnowledgeService
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
    result = await _asset_service.fetch_asset(doc_id, asset_type, asset_id, max_size=max_size)

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

**Nodes:** {result.get('node_count', 0)} | **Edges:** {result.get('edge_count', 0)}

```mermaid
{result['diagram']}
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
        for etype, count in cast(dict[str, int], result.get("entity_types", {})).items():
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
        caption = (fig.caption[:40] + "...") if fig.caption and len(fig.caption) > 40 else (fig.caption or "-")
        lines.append(f"| `{fig.id}` | {fig.page or '-'} | {fig.width}×{fig.height} | {caption} |")

    lines.extend([
        "",
        "---",
        "_Use `fetch_document_asset(doc_id, 'figure', '<id>')` to retrieve image content._",
    ])

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
        desc = (tab.caption[:50] + "...") if tab.caption and len(tab.caption) > 50 else (tab.caption or "-")
        lines.append(f"| `{tab.id}` | {tab.page or '-'} | {desc} |")

    lines.extend([
        "",
        "---",
        "_Use `fetch_document_asset(doc_id, 'table', '<id>')` to retrieve table content._",
    ])

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

    lines.extend([
        "",
        "---",
        "_Use `fetch_document_asset(doc_id, 'section', '<id>')` to retrieve section text._",
    ])

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
        lines.append(f"## 🔗 Knowledge Graph Entities ({len(manifest.lightrag_entities)})")
        lines.append(", ".join(manifest.lightrag_entities[:15]))
        if len(manifest.lightrag_entities) > 15:
            lines.append(f"_...and {len(manifest.lightrag_entities) - 15} more_")
    lines.append("")

    # Quick actions
    lines.extend([
        "---",
        "## Quick Actions",
        f"- View figures: `document://{doc_id}/figures`",
        f"- View tables: `document://{doc_id}/tables`",
        f"- View sections: `document://{doc_id}/sections`",
        f"- Fetch asset: `fetch_document_asset('{doc_id}', '<type>', '<id>')`",
    ])

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

    lines.extend([
        "",
        "---",
        "_Use `consult_knowledge_graph(query)` to query the graph._",
        "_Use `export_knowledge_graph('mermaid')` to visualize._",
    ])

    return "\n".join(lines)


# ============================================================================
# Server Entry Point
# ============================================================================


def main() -> None:
    """Run the MCP server."""

    # Run with stdio transport
    mcp.run()


if __name__ == "__main__":
    main()
