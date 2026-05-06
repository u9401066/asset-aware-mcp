"""
Document Resources - MCP Resources for Documents and Knowledge Graph

包含：
- documents://list: 文件列表
- document://{doc_id}/manifest: 文件 Manifest
- document://{doc_id}/segmentation: 統一 segmentation schema
- document://{doc_id}/figures: 文件圖片列表
- document://{doc_id}/tables: 文件表格列表
- document://{doc_id}/sections: 文件章節列表
- document://{doc_id}/outline: 文件大綱
- knowledge-graph://summary: 知識圖譜摘要
"""

from __future__ import annotations

from typing import cast

from src.presentation.dependencies import document_service, knowledge_graph
from src.presentation.mcp_app import mcp
from src.presentation.tools.document_tools import list_documents


def _display_line_range(start_line: int, end_line: int) -> str:
    """Render internal 0-based, end-exclusive line ranges as 1-based display values."""
    if start_line < 0 or end_line < 0 or end_line < start_line:
        return ""
    return f"(L{start_line + 1}-{end_line})"


@mcp.resource("documents://list")
async def resource_document_list() -> str:
    """Dynamic resource listing all processed documents."""
    result: str = await list_documents()
    return result


@mcp.resource("document://{doc_id}/manifest")
async def resource_document_manifest(doc_id: str) -> str:
    """Dynamic resource for document manifest."""
    from src.presentation.tools.document_tools import inspect_document_manifest

    result: str = await inspect_document_manifest(doc_id)
    return result


@mcp.resource("document://{doc_id}/segmentation")
async def resource_document_segmentation(doc_id: str) -> str:
    """Dynamic resource for unified segmentation schema JSON."""
    segmentation_path = (
        document_service.repository.get_doc_dir(doc_id) / "segmentation.json"
    )
    if not segmentation_path.exists():
        return (
            f"Segmentation not found for {doc_id}. "
            "Run export_document_segmentation first to create segmentation.json."
        )
    return segmentation_path.read_text(encoding="utf-8")


@mcp.resource("document://{doc_id}/figures")
async def resource_document_figures(doc_id: str) -> str:
    """
    Dynamic resource listing all figures in a document.

    Returns a concise outline of figures with IDs, pages, and sizes.
    Use fetch_document_asset to retrieve actual image content.
    """
    manifest = await document_service.get_manifest(doc_id)
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
    manifest = await document_service.get_manifest(doc_id)
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

    Returns hierarchical section tree with IDs and line ranges.
    Use fetch_document_asset to retrieve section text.
    """
    manifest = await document_service.get_manifest(doc_id)
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
        line_info = _display_line_range(sec.start_line, sec.end_line)
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
    manifest = await document_service.get_manifest(doc_id)
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
    if knowledge_graph is None:
        return "LightRAG is not enabled. Set ENABLE_LIGHTRAG=true in .env"

    result = await knowledge_graph.export_graph(format="summary", limit=30)

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

    for etype, count in cast("dict[str, int]", result.get("entity_types", {})).items():
        lines.append(f"- **{etype}:** {count}")

    lines.append("\n## Sample Entities")
    for node in cast("list[dict[str, str]]", result.get("sample_nodes", []))[:8]:
        lines.append(f"- {node['id']} ({node['type']})")

    lines.extend(
        [
            "",
            "---",
            "_Use `consult_knowledge_graph(query)` to query the graph._",
            "_Use `export_knowledge_graph('mermaid')` to visualize._",
        ]
    )

    return "\n".join(lines)
