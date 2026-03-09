"""
Knowledge Tools - 知識圖譜 MCP 工具

包含：
- consult_knowledge_graph: 查詢知識圖譜
- export_knowledge_graph: 匯出知識圖譜
"""

from __future__ import annotations

from typing import cast

from src.presentation.dependencies import knowledge_graph, knowledge_service
from src.presentation.mcp_app import mcp


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
    return await knowledge_service.query(query, mode=mode)


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
    if knowledge_graph is None:
        return "Error: LightRAG is not enabled. Set ENABLE_LIGHTRAG=true in .env"

    result = await knowledge_graph.export_graph(
        format=format,
        limit=limit,
    )

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
