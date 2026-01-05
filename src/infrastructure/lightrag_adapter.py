"""
Infrastructure Layer - LightRAG Adapter

Integration with LightRAG for knowledge graph operations.
Supports both Ollama (local) and OpenAI backends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from src.domain.repositories import KnowledgeGraphInterface

from .config import settings

if TYPE_CHECKING:
    from lightrag import LightRAG  # type: ignore

from lightrag.base import EmbeddingFunc  # type: ignore

# ============================================================================
# Ollama LLM Functions for LightRAG
# ============================================================================


async def ollama_model_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    **kwargs: str | int | float,
) -> str:
    """
    Ollama completion function for LightRAG.

    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
        history_messages: Optional conversation history
        **kwargs: Additional arguments (model, host, etc.)

    Returns:
        Generated text response
    """
    import httpx

    model = str(kwargs.get("model", settings.ollama_model))
    host = str(kwargs.get("host", settings.ollama_host))

    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if history_messages:
        messages.extend(history_messages)

    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{host}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_ctx": kwargs.get("num_ctx", 4096),
                },
            },
        )
        response.raise_for_status()
        result = response.json()
        content: str = result.get("message", {}).get("content", "")
        return content


async def ollama_embedding(
    texts: list[str],
    **kwargs: str | int | float,
) -> np.ndarray:
    """
    Ollama embedding function for LightRAG.

    Args:
        texts: List of texts to embed
        **kwargs: Additional arguments (model, host, etc.)

    Returns:
        NumPy array of embedding vectors (required by LightRAG)
    """
    import httpx

    model = str(kwargs.get("model", settings.ollama_embedding_model))
    host = str(kwargs.get("host", settings.ollama_host))

    embeddings = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for text in texts:
            response = await client.post(
                f"{host}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            result = response.json()
            embeddings.append(result.get("embedding", []))

    # LightRAG requires numpy array with .size attribute
    return np.array(embeddings)


class LightRAGAdapter(KnowledgeGraphInterface):
    """
    Adapter for LightRAG knowledge graph.

    Provides:
    - Document indexing into knowledge graph
    - Hybrid query (local + global)
    - Entity extraction
    """

    def __init__(self, rag: LightRAG | None = None):
        """
        Initialize adapter.

        Args:
            rag: Optional pre-configured LightRAG instance
        """
        self._rag = rag
        self._initialized = rag is not None

    async def _ensure_initialized(self) -> LightRAG:
        """Lazy initialization of LightRAG with Ollama or OpenAI backend."""
        if self._rag is not None:
            return self._rag

        if not settings.enable_lightrag:
            raise RuntimeError("LightRAG is disabled in settings")

        try:
            from lightrag import LightRAG  # type: ignore

            # Ensure working directory exists
            working_dir = settings.lightrag_working_dir
            working_dir.mkdir(parents=True, exist_ok=True)

            # Choose backend based on settings
            if settings.llm_backend == "ollama":
                # Use Ollama (local LLM)
                self._rag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=ollama_model_complete,
                    llm_model_name=settings.ollama_model,
                    llm_model_kwargs={
                        "host": settings.ollama_host,
                        "model": settings.ollama_model,
                    },
                    embedding_func=EmbeddingFunc(
                        embedding_dim=768,  # nomic-embed-text dimension
                        max_token_size=8192,
                        func=ollama_embedding,
                    ),
                    # Tuning for smaller local models
                    entity_extract_max_gleaning=0,  # Reduce extraction passes
                    max_parallel_insert=1,  # Sequential processing for stability
                    llm_model_max_async=1,  # One LLM call at a time
                    chunk_token_size=800,  # Smaller chunks for better extraction
                )
            else:
                # Use OpenAI
                from lightrag.llm import (  # type: ignore
                    openai_complete_if_cache,
                    openai_embedding,
                )

                self._rag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=openai_complete_if_cache,
                    embedding_func=openai_embedding,
                )

            # IMPORTANT: Initialize storages (required by LightRAG)
            await self._rag.initialize_storages()

            self._initialized = True
            return self._rag

        except ImportError as e:
            raise RuntimeError(
                "LightRAG not installed. Install with: pip install lightrag-hku"
            ) from e

    async def insert(self, doc_id: str, text: str) -> None:
        """
        Insert text into knowledge graph.

        Args:
            doc_id: Document identifier for tracking
            text: Full text content to index
        """
        rag = await self._ensure_initialized()

        # Add doc_id as metadata prefix for traceability
        prefixed_text = f"[Document: {doc_id}]\n\n{text}"

        await rag.ainsert(prefixed_text)

    async def query(self, query: str, mode: str = "hybrid") -> str:
        """
        Query the knowledge graph.

        Args:
            query: Natural language query
            mode: Query mode - "local", "global", or "hybrid"

        Returns:
            Query result as string
        """
        rag = await self._ensure_initialized()

        from lightrag import QueryParam  # type: ignore

        result = await rag.aquery(query, param=QueryParam(mode=mode))

        return str(result) if result else ""

    async def extract_entities(self, text: str, limit: int = 5) -> list[str]:
        """
        Extract top entities from text using LightRAG.

        This queries the knowledge graph in "local" mode to find
        the most relevant entities in the given text.

        Args:
            text: Text to extract entities from
            limit: Maximum number of entities to return

        Returns:
            List of entity names
        """
        rag = await self._ensure_initialized()

        try:
            # Use local mode for entity-focused extraction
            from lightrag import QueryParam  # type: ignore

            result = await rag.aquery(
                f"List the top {limit} most important entities (people, organizations, "
                f"medical terms, drugs, diseases) mentioned in this context.",
                param=QueryParam(mode="local"),
            )

            if not result:
                return []

            # Parse entities from response
            # LightRAG returns natural language, so we extract capitalized terms
            import re

            # Find quoted terms or capitalized words
            entities = []

            # Try to find quoted entities first
            quoted = re.findall(r'"([^"]+)"', str(result))
            entities.extend(quoted)

            # Also find capitalized multi-word terms
            caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", str(result))
            for cap in caps:
                if cap not in entities and cap not in ["The", "This", "These", "What"]:
                    entities.append(cap)

            # Deduplicate and limit
            seen = set()
            unique_entities = []
            for e in entities:
                if e.lower() not in seen:
                    seen.add(e.lower())
                    unique_entities.append(e)

            return unique_entities[:limit]

        except Exception:
            return []

    async def export_graph(
        self,
        format: str = "summary",
        limit: int = 50,
        entity_types: list[str] | None = None,
    ) -> dict[str, object]:
        """
        Export knowledge graph data in various formats.

        Args:
            format: Output format - "summary", "json", or "mermaid"
            limit: Maximum number of nodes to include
            entity_types: Filter by entity types (e.g., ["PERSON", "ORGANIZATION"])

        Returns:
            Dict with graph data in requested format
        """
        import xml.etree.ElementTree as ET  # noqa: N817

        graph_file = (
            settings.lightrag_working_dir / "graph_chunk_entity_relation.graphml"
        )

        if not graph_file.exists():
            return {
                "format": format,
                "error": "Knowledge graph not found. Please ingest documents first.",
                "nodes": [],
                "edges": [],
            }

        # Parse GraphML
        tree = ET.parse(graph_file)
        root = tree.getroot()
        ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

        # Extract nodes
        nodes: list[dict[str, str]] = []
        node_ids: set[str] = set()

        node: Any
        for node in root.findall(".//g:node", ns):
            node_id = node.get("id", "")
            entity_type = ""
            description = ""

            data: Any
            for data in node.findall("g:data", ns):
                key = data.get("key", "")
                text = data.text or ""
                if key == "d1":  # entity_type
                    entity_type = text
                elif key == "d2":  # description
                    # Truncate long descriptions
                    description = text[:200] + "..." if len(text) > 200 else text

            # Filter by entity type if specified
            if entity_types and entity_type not in entity_types:
                continue

            if len(nodes) < limit:
                nodes.append(
                    {
                        "id": node_id,
                        "type": entity_type,
                        "description": description,
                    }
                )
                node_ids.add(node_id)

        # Extract edges (only between included nodes)
        edges: list[dict[str, str]] = []
        edge: Any
        for edge in root.findall(".//g:edge", ns):
            source = edge.get("source", "")
            target = edge.get("target", "")

            if source not in node_ids or target not in node_ids:
                continue

            keywords = ""
            weight = "1.0"
            for data in edge.findall("g:data", ns):
                key = data.get("key", "")
                text = data.text or ""
                if key == "d9":  # keywords
                    keywords = text
                elif key == "d7":  # weight
                    weight = text

            edges.append(
                {
                    "source": source,
                    "target": target,
                    "keywords": keywords,
                    "weight": weight,
                }
            )

        # Format output
        if format == "summary":
            # Return statistics and top entities
            type_counts: dict[str, int] = {}
            for n in nodes:
                t = n.get("type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1

            return {
                "format": "summary",
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "entity_types": type_counts,
                "sample_nodes": nodes[:10],
                "sample_edges": edges[:10],
            }

        elif format == "json":
            return {
                "format": "json",
                "nodes": nodes,
                "edges": edges,
            }

        elif format == "mermaid":
            # Generate Mermaid flowchart
            mermaid_lines = ["graph TD"]

            # Sanitize node IDs for Mermaid (remove special chars)
            def sanitize_id(s: str) -> str:
                return "".join(c if c.isalnum() else "_" for c in s)[:30]

            node_map: dict[str, str] = {}
            for i, node in enumerate(nodes[:30]):  # Limit for readability
                safe_id = f"N{i}"
                node_map[node["id"]] = safe_id
                label = node["id"][:25]
                mermaid_lines.append(f'    {safe_id}["{label}"]')

            for edge in edges:
                src = node_map.get(edge["source"])
                tgt = node_map.get(edge["target"])
                if src and tgt:
                    kw = edge.get("keywords", "")[:15]
                    if kw:
                        mermaid_lines.append(f"    {src} -->|{kw}| {tgt}")
                    else:
                        mermaid_lines.append(f"    {src} --> {tgt}")

            return {
                "format": "mermaid",
                "diagram": "\n".join(mermaid_lines),
                "node_count": len(nodes[:30]),
                "edge_count": len(
                    [
                        e
                        for e in edges
                        if node_map.get(e["source"]) and node_map.get(e["target"])
                    ]
                ),
            }

        else:
            return {"format": format, "error": f"Unknown format: {format}"}

    @property
    def is_available(self) -> bool:
        """Check if LightRAG is available and enabled."""
        if not settings.enable_lightrag:
            return False

        try:
            import lightrag  # type: ignore # noqa: F401

            return True
        except ImportError:
            return False


# Singleton instance for convenience
_lightrag_adapter: LightRAGAdapter | None = None


def get_lightrag_adapter() -> LightRAGAdapter:
    """Get or create the LightRAG adapter singleton."""
    global _lightrag_adapter
    if _lightrag_adapter is None:
        _lightrag_adapter = LightRAGAdapter()
    return _lightrag_adapter
