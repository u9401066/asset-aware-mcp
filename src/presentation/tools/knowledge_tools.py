"""
Knowledge Tools - 知識圖譜 MCP 工具

包含：
- consult_knowledge_graph: 查詢知識圖譜
- export_knowledge_graph: 匯出知識圖譜
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, cast

from mcp.server.mcpserver import Context  # noqa: TC002 - runtime injection marker

from src.presentation.dependencies import knowledge_graph, knowledge_service
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import log_message, report_progress
from src.presentation.response_limits import (
    format_limited_json_response,
    format_limited_text_response,
)

KNOWLEDGE_TOOL_TIMEOUT_SECONDS = 45.0
KNOWLEDGE_VERIFY_DOC_LIMIT = 5
KNOWLEDGE_EXPORT_LIMIT_MAX = 200


def _normalize_op(op: str) -> str:
    return op.strip().lower().replace("-", "_")


def _extract_doc_ids(value: Any) -> list[str]:
    """Best-effort doc_id extraction from structured LightRAG responses."""
    doc_ids: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = str(key).lower()
                if (
                    normalized in {"doc_id", "source_doc_id", "document_id"}
                    and isinstance(child, str)
                    and child.startswith("doc_")
                ):
                    doc_ids.add(child)
                visit(child)
        elif isinstance(item, list | tuple | set):
            for child in item:
                visit(child)
        elif isinstance(item, str):
            doc_ids.update(re.findall(r"\bdoc_[A-Za-z0-9_]+\b", item))

    visit(value)
    return sorted(doc_ids)


def _foam_link_target(value: Any) -> str:
    """Return a conservative Foam note target for KG entity links."""
    target = str(value or "").strip()
    target = re.sub(r"\s+", " ", target)
    target = target.replace("[[", "").replace("]]", "").replace("|", "-")
    return target or "unknown"


def _entity_wikilink(entity_id: Any) -> str:
    return f"[[{_foam_link_target(entity_id)}]]"


def _verified_evidence_foam_links(payload: dict[str, Any]) -> list[str]:
    """Collect unique Foam wikilinks from verified evidence bundles."""
    links: list[str] = []
    seen: set[str] = set()
    for bundle in payload.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        for entry in bundle.get("entries", []):
            if not isinstance(entry, dict):
                continue
            foam = entry.get("foam") or {}
            if not isinstance(foam, dict):
                continue
            link = str(foam.get("wikilink") or "").strip()
            if link and link not in seen:
                seen.add(link)
                links.append(link)
    return links


async def _verified_evidence_payload(
    *,
    query: str,
    doc_ids: list[str] | None,
    result: Any,
    evidence_limit: int,
) -> dict[str, Any]:
    from src.presentation.tools.document_tools import citation_bundle

    evidence_limit = max(1, min(evidence_limit, 10))
    discovered_doc_ids = list(dict.fromkeys(doc_ids or _extract_doc_ids(result)))
    target_doc_ids = discovered_doc_ids[:KNOWLEDGE_VERIFY_DOC_LIMIT]
    if not target_doc_ids:
        return {
            "success": False,
            "status": "skipped",
            "reason": (
                "No doc_ids were provided or discoverable in the knowledge graph "
                "response. Pass doc_ids=[...] to verify against citation indexes."
            ),
            "query": query,
            "bundles": [],
        }

    bundles: list[dict[str, Any]] = []
    for doc_id in target_doc_ids:
        bundle = await citation_bundle(
            doc_id,
            query=query,
            limit=evidence_limit,
            include_verification=True,
            output_format="json",
        )
        if isinstance(bundle, dict):
            bundles.append(bundle)

    return {
        "success": any(bundle.get("success") for bundle in bundles),
        "status": "verified"
        if any(bundle.get("success") for bundle in bundles)
        else "empty",
        "query": query,
        "doc_ids": target_doc_ids,
        "omitted_doc_ids_count": max(0, len(discovered_doc_ids) - len(target_doc_ids)),
        "bundles": bundles,
    }


def _format_verified_evidence(payload: dict[str, Any]) -> str:
    if payload.get("status") == "skipped":
        return f"## Verified Evidence\n\nSkipped: {payload.get('reason', '')}"
    lines = ["## Verified Evidence", ""]
    for bundle in payload.get("bundles", []):
        doc_id = bundle.get("doc_id", "")
        if not bundle.get("success"):
            lines.append(f"- `{doc_id}`: {bundle.get('error', 'no evidence')}")
            continue
        lines.append(
            f"- `{doc_id}`: {bundle.get('returned', 0)}/{bundle.get('matched_count', 0)} spans"
        )
        for entry in bundle.get("entries", [])[:3]:
            foam_link = str((entry.get("foam") or {}).get("wikilink") or "")
            link_suffix = f" {foam_link}" if foam_link else ""
            lines.append(
                "  - "
                f"`{entry.get('span_id')}` "
                f"{link_suffix}"
                f"p.{entry.get('page') or '?'} "
                f"{entry.get('line_display') or ''}: "
                f"{str(entry.get('quote') or '')[:120]}"
            )
    return "\n".join(lines)


@mcp.tool()
async def consult_knowledge_graph(
    query: str,
    mode: str = "hybrid",
    response_mode: str = "structured",
    user_prompt: str | None = None,
    include_references: bool = False,
    verify_references: bool = False,
    doc_ids: list[str] | None = None,
    evidence_limit: int = 5,
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
        verify_references: Attach citation-index evidence bundles for referenced docs
        doc_ids: Optional explicit document IDs to verify against
        evidence_limit: Max evidence spans per document bundle

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
    effective_include_references = include_references or verify_references

    query_task: Any
    if response_mode == "text":
        query_task = knowledge_service.query(
            query,
            mode=mode,
            user_prompt=user_prompt,
            include_references=effective_include_references,
        )
    elif response_mode == "data":
        query_task = knowledge_service.query_data(
            query,
            mode=mode,
            user_prompt=user_prompt,
        )
    else:
        query_task = knowledge_service.query_structured(
            query,
            mode=mode,
            user_prompt=user_prompt,
            include_references=effective_include_references,
        )

    try:
        result: dict[str, Any] | str = await asyncio.wait_for(
            query_task,
            timeout=KNOWLEDGE_TOOL_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await log_message(ctx, "error", "consult_knowledge_graph timed out")
        payload: dict[str, Any] = {
            "success": False,
            "status": "timeout",
            "error": (
                "Knowledge graph query exceeded the MCP request timeout guard. "
                "Retry with a narrower query or inspect the LightRAG runtime logs."
            ),
            "query": query,
            "mode": mode,
            "response_mode": response_mode,
            "timeout_seconds": KNOWLEDGE_TOOL_TIMEOUT_SECONDS,
        }
        if response_mode == "text":
            return str(payload["error"])
        return payload

    if verify_references:
        await report_progress(ctx, 90, message="Verifying knowledge graph evidence")
        verified = await _verified_evidence_payload(
            query=query,
            doc_ids=doc_ids,
            result=result,
            evidence_limit=evidence_limit,
        )
        foam_links = _verified_evidence_foam_links(verified)
        if isinstance(result, dict):
            result = {
                **result,
                "verified_evidence": verified,
                "foam_links": foam_links,
                "verified_foam_links": foam_links,
                "foam_link_details": [
                    {"link": link, "link_kind": "verified_evidence"}
                    for link in foam_links
                ],
            }
        else:
            result = f"{result}\n\n{_format_verified_evidence(verified)}"

    await report_progress(ctx, 100, message="Knowledge graph query finished")
    await log_message(ctx, "info", "consult_knowledge_graph complete")
    if isinstance(result, str):
        return format_limited_text_response(
            title="Knowledge Graph Query",
            text=result,
            language="markdown",
            guidance="retry with a narrower query or response_mode='structured'",
        )
    result = format_limited_json_response(
        title="Knowledge Graph Query",
        payload=result,
        guidance="retry with a narrower query or response_mode='text'",
    )
    return result


def _format_knowledge_graph_foam(result: dict[str, Any], *, limit: int) -> str:
    if "error" in result:
        return f"Error: {result['error']}"

    nodes = cast("list[dict[str, Any]]", result.get("nodes", []))[:limit]
    edges = cast("list[dict[str, Any]]", result.get("edges", []))[:limit]

    lines = [
        "## Knowledge Graph Discovery Link Candidates",
        "",
        f"**Nodes:** {len(nodes)}",
        f"**Edges:** {len(edges)}",
        "",
        "### Entities",
    ]
    if not nodes:
        lines.append("_No entities exported_")
    for node in nodes:
        entity_id = node.get("id", "")
        entity_type = str(node.get("type") or "unknown")
        description = str(node.get("description") or "").strip()
        line = f"- {_entity_wikilink(entity_id)} ({entity_type})"
        if description:
            line += f": {description[:160]}"
        lines.append(line)

    lines.extend(["", "### Relationships"])
    if not edges:
        lines.append("_No relationships exported_")
    for edge in edges:
        source = _entity_wikilink(edge.get("source", ""))
        target = _entity_wikilink(edge.get("target", ""))
        keywords = str(edge.get("keywords") or "").strip()
        line = f"- {source} -> {target}"
        if keywords:
            line += f" ({keywords})"
        lines.append(line)

    lines.extend(
        [
            "",
            "---",
            "_Entity links are KG discovery links. Use `consult_knowledge_graph(..., verify_references=True)` for citation-ready evidence links._",
        ]
    )
    return "\n".join(lines)


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
    - "foam": Foam/wiki-link entity and relationship list
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

    limit = max(1, min(limit, KNOWLEDGE_EXPORT_LIMIT_MAX))
    await log_message(
        ctx, "info", f"export_knowledge_graph start: format={format} limit={limit}"
    )
    await report_progress(ctx, 10, message="Exporting knowledge graph")
    try:
        backend_format = "json" if format == "foam" else format
        result = await asyncio.wait_for(
            knowledge_graph.export_graph(
                format=backend_format,
                limit=limit,
            ),
            timeout=KNOWLEDGE_TOOL_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await log_message(ctx, "error", "export_knowledge_graph timed out")
        return (
            "Knowledge graph export timed out before completion. "
            f"format={format}, limit={limit}, "
            f"timeout_seconds={KNOWLEDGE_TOOL_TIMEOUT_SECONDS}"
        )
    await report_progress(ctx, 100, message="Knowledge graph export finished")
    await log_message(ctx, "info", "export_knowledge_graph complete")

    if format == "foam":
        return format_limited_text_response(
            title="Knowledge Graph Foam Export",
            text=_format_knowledge_graph_foam(result, limit=limit),
            language="markdown",
            guidance="lower the limit for a smaller graph view",
        )
    if format == "mermaid" and "diagram" in result:
        text = (
            "## Knowledge Graph Visualization\n\n"
            f"**Nodes:** {result.get('node_count', 0)} | "
            f"**Edges:** {result.get('edge_count', 0)}\n\n"
            f"```mermaid\n{result['diagram']}\n```\n"
        )
        return format_limited_text_response(
            title="Knowledge Graph Mermaid Export",
            text=text,
            language="markdown",
            guidance="lower the limit for a smaller diagram",
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

        return format_limited_text_response(
            title="Knowledge Graph Summary",
            text="\n".join(lines),
            language="markdown",
            guidance="lower the limit for a smaller graph summary",
        )
    else:
        import json

        return format_limited_text_response(
            title="Knowledge Graph JSON Export",
            text=json.dumps(result, indent=2, ensure_ascii=False),
            language="json",
            guidance="use format='summary' or a lower limit for a smaller response",
        )


@mcp.tool()
async def knowledge(
    op: str,
    query: str | None = None,
    mode: str = "hybrid",
    response_mode: str = "structured",
    user_prompt: str | None = None,
    include_references: bool = False,
    verify_references: bool = False,
    doc_ids: list[str] | None = None,
    evidence_limit: int = 5,
    format: str = "summary",
    limit: int = 50,
    ctx: Context | None = None,
) -> Any:
    """
    Consolidated knowledge-graph entrypoint.

    Existing consult/export tools remain registered and keep their separate
    contracts for clients that prefer explicit tool names.
    """
    operation = _normalize_op(op)
    if operation in {"consult", "query"}:
        if not query:
            return "Missing required parameter: query is required."
        return await consult_knowledge_graph(
            query,
            mode=mode,
            response_mode=response_mode,
            user_prompt=user_prompt,
            include_references=include_references,
            verify_references=verify_references,
            doc_ids=doc_ids,
            evidence_limit=evidence_limit,
            ctx=ctx,
        )
    if operation == "export":
        return await export_knowledge_graph(format, limit, ctx=ctx)
    return (
        f"Unsupported knowledge op `{op}`. "
        "Supported operations: consult, export, query."
    )
