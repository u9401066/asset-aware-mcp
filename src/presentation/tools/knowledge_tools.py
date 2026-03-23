"""
Knowledge Tools - 知識圖譜 MCP 工具

包含：
- consult_knowledge_graph: 查詢知識圖譜
- export_knowledge_graph: 匯出知識圖譜
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from src.presentation.dependencies import knowledge_graph, knowledge_service
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import log_message, report_progress

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    Context = Any


@mcp.tool()
async def consult_knowledge_graph(
    query: str,
    mode: str = "hybrid",
    response_mode: str = "structured",
    user_prompt: str | None = None,
    include_references: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any] | str:
    """
    Query the LightRAG knowledge graph for cross-document insights.

    Query Modes:
    - "local": Specific details from nearby context
    - "global": High-level patterns and themes
    - "hybrid": Both local and global (recommended for most queries)
    - "mix": Knowledge graph + vector retrieval (recommended by newer LightRAG versions)
    - "naive": Vector-only retrieval
    - "bypass": Direct LLM answer path without retrieval

    Best for:
    - Comparing findings across multiple papers
    - Finding drug interactions or dosage patterns
    - Exploring relationships between concepts

    Args:
        query: Natural language question
        mode: Query mode ("local", "global", "hybrid", "mix", "naive", or "bypass")
        response_mode: "structured" (default), "data", or "text"
        user_prompt: Optional instruction applied after retrieval, before answer generation
        include_references: Include source reference list when LightRAG supports it

    Returns:
        Structured MCP-friendly result by default, or plain text when response_mode="text"

    Example:
        consult_knowledge_graph("What are the dosing recommendations for remimazolam?")
        consult_knowledge_graph("Compare sedation outcomes between propofol and remimazolam", mode="global")
    """
    if response_mode not in {"structured", "data", "text"}:
        raise ValueError("response_mode must be one of: structured, data, text")

    await log_message(ctx, "info", f"consult_knowledge_graph start: mode={mode}")
    await report_progress(ctx, 10, message="Querying knowledge graph")

    result: dict[str, Any] | str
    if response_mode == "text":
        result = await knowledge_service.query(
            query,
            mode=mode,
            user_prompt=user_prompt,
            include_references=include_references,
        )
    elif response_mode == "data":
        result = await knowledge_service.query_data(
            query,
            mode=mode,
            user_prompt=user_prompt,
        )
    else:
        result = await knowledge_service.query_structured(
            query,
            mode=mode,
            user_prompt=user_prompt,
            include_references=include_references,
        )

    await report_progress(ctx, 100, message="Knowledge graph query finished")
    await log_message(ctx, "info", "consult_knowledge_graph complete")
    return result


@mcp.tool()
async def export_knowledge_graph(
    format: str = "summary",
    limit: int = 50,
    ctx: Context | None = None,
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
    if knowledge_graph is None:
        return "Error: LightRAG is not enabled. Set ENABLE_LIGHTRAG=true in .env"

    await log_message(
        ctx, "info", f"export_knowledge_graph start: format={format} limit={limit}"
    )
    await report_progress(ctx, 10, message="Exporting knowledge graph")
    result = await knowledge_graph.export_graph(
        format=format,
        limit=limit,
    )
    await report_progress(ctx, 100, message="Knowledge graph export finished")
    await log_message(ctx, "info", "export_knowledge_graph complete")

    if format == "mermaid" and "diagram" in result:
        return (
            "## Knowledge Graph Visualization\n\n"
            f"**Nodes:** {result.get('node_count', 0)} | "
            f"**Edges:** {result.get('edge_count', 0)}\n\n"
            f"```mermaid\n{result['diagram']}\n```\n"
        )
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
            "dict[str, int]", result.get("entity_types", {})
        ).items():
            lines.append(f"- {etype}: {count}")

        lines.append("\n### Sample Nodes")
        for node in cast("list[dict[str, str]]", result.get("sample_nodes", []))[:5]:
            lines.append(f"- **{node['id']}** ({node['type']})")
            if node.get("description"):
                lines.append(f"  _{node['description'][:100]}_")

        lines.append("\n### Sample Relationships")
        for edge in cast("list[dict[str, str]]", result.get("sample_edges", []))[:5]:
            lines.append(f"- {edge['source']} → {edge['target']}")
            if edge.get("keywords"):
                lines.append(f"  _Keywords: {edge['keywords']}_")

        return "\n".join(lines)
    else:
        import json

        return json.dumps(result, indent=2, ensure_ascii=False)
