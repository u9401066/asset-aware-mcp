"""
Presentation Layer - MCP Server

FastMCP server with tools and resources for document operations.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from src.application.asset_service import AssetService
from src.application.document_service import DocumentService
from src.application.knowledge_service import KnowledgeService
from src.infrastructure.config import settings
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.lightrag_adapter import LightRAGAdapter
from src.infrastructure.pdf_extractor import PyMuPDFExtractor

# Initialize FastMCP server
mcp = FastMCP("Asset-Aware Medical RAG")

# Initialize infrastructure
_repository = FileStorage(settings.data_dir)
_pdf_extractor = PyMuPDFExtractor()
_knowledge_graph = LightRAGAdapter() if settings.enable_lightrag else None

# Initialize application services
_document_service = DocumentService(
    repository=_repository,
    pdf_extractor=_pdf_extractor,
    knowledge_graph=_knowledge_graph,
)
_asset_service = AssetService(repository=_repository)
_knowledge_service = KnowledgeService(knowledge_graph=_knowledge_graph)


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def ingest_documents(file_paths: list[str]) -> str:
    """
    Process PDF files and create Document Manifests.

    ETL Pipeline:
    1. Extract text (to markdown) and images
    2. Generate structured Document Manifest
    3. Index in LightRAG (if enabled)

    Args:
        file_paths: List of absolute paths to PDF files

    Returns:
        Summary of ingestion results with doc_ids for reference

    Example:
        ingest_documents(["/papers/study1.pdf", "/papers/study2.pdf"])
    """
    results = await _document_service.ingest(file_paths)

    # Format results
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
            output_lines.append(f"- **time:** {result.processing_time_seconds:.2f}s")
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
            output_lines.append(f"{indent}- `{sec.id}`: {sec.title} (L{sec.start_line}-{sec.end_line})")
    else:
        output_lines.append("_No sections found_")

    # LightRAG entities
    if manifest.lightrag_entities:
        output_lines.append(f"\n## Knowledge Graph Entities ({len(manifest.lightrag_entities)})")
        output_lines.append(", ".join(manifest.lightrag_entities[:20]))
        if len(manifest.lightrag_entities) > 20:
            output_lines.append(f"... and {len(manifest.lightrag_entities) - 20} more")

    return "\n".join(output_lines)


@mcp.tool()
async def fetch_document_asset(
    doc_id: str,
    asset_type: str,
    asset_id: str = "full",
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

    Returns:
        For figures: ImageContent that vision AI can directly analyze
        For others: TextContent in markdown format

    Example:
        # Get Table 1 from document
        fetch_document_asset("abc123", "table", "tab_1")

        # Get figure with verification info
        fetch_document_asset("abc123", "figure", "fig_2_1")
    """
    result = await _asset_service.fetch_asset(doc_id, asset_type, asset_id)

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


# ============================================================================
# MCP Resources (Dynamic - Auto-updates with new files)
# ============================================================================

@mcp.resource("documents://list")
async def resource_document_list() -> str:
    """Dynamic resource listing all processed documents."""
    return await list_documents()


@mcp.resource("document://{doc_id}/manifest")
async def resource_document_manifest(doc_id: str) -> str:
    """Dynamic resource for document manifest."""
    return await inspect_document_manifest(doc_id)


# ============================================================================
# Server Entry Point
# ============================================================================

def main():
    """Run the MCP server."""

    # Run with stdio transport
    mcp.run()


if __name__ == "__main__":
    main()
