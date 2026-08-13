"""
Infrastructure Layer - LightRAG Adapter

Integration with LightRAG for knowledge graph operations.
Supports both Ollama (local) and OpenAI backends.
"""

from __future__ import annotations

import asyncio
import re
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any, cast

from src.domain.repositories import KnowledgeGraphInterface

from .config import settings

if TYPE_CHECKING:
    from lightrag import LightRAG  # type: ignore

MIN_LIGHTRAG_HKU_VERSION = (1, 4, 11)
ENTITY_PARSE_STOPWORDS = {
    "and",
    "context",
    "entities",
    "entity",
    "the",
    "this",
    "these",
    "top",
    "terms",
}
_OLLAMA_EMBEDDING_DIMENSION_CACHE: dict[tuple[str, str], int] = {}


def _parse_version_tuple(raw_version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", raw_version)
    if match is None:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _validate_lightrag_hku_distribution() -> None:
    try:
        installed_version = version("lightrag-hku")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "LightRAG backend requires the `lightrag-hku` distribution. "
            "Install the optional extra via "
            "`uv tool install --upgrade 'asset-aware-mcp[lightrag]'` "
            "(or use the VS Code command 'Asset-Aware MCP: Install LightRAG Backend'). "
            "For source checkouts run `uv sync --extra lightrag`. "
            "Do not install the unrelated `lightrag` package from PyPI."
        ) from exc

    if _parse_version_tuple(installed_version) < MIN_LIGHTRAG_HKU_VERSION:
        minimum = ".".join(str(part) for part in MIN_LIGHTRAG_HKU_VERSION)
        raise RuntimeError(
            f"LightRAG backend requires `lightrag-hku>={minimum}`, "
            f"but {installed_version} is installed."
        )


def _clean_entity_candidate(value: str) -> str:
    candidate = value.strip()
    candidate = re.sub(r"^\s*(?:[-*•]|\d+[\.)])\s*", "", candidate)
    candidate = candidate.strip(" \t\r\n`*_\"'“”():：;；,.，。[]{}")
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate


def _parse_entity_candidates(response: str, *, limit: int) -> list[str]:
    """Parse a bounded entity list from LightRAG natural-language output."""
    entities: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        candidate = _clean_entity_candidate(raw)
        if not candidate:
            return
        if candidate.casefold() in ENTITY_PARSE_STOPWORDS:
            return
        if len(candidate) < 2 and not re.search(r"[\u4e00-\u9fff]", candidate):
            return
        key = candidate.casefold()
        if key in seen:
            return
        seen.add(key)
        entities.append(candidate)

    for quoted in re.findall(r"[\"“”']([^\"“”']+)[\"“”']", response):
        add(quoted)

    for line in response.splitlines():
        bullet = re.match(r"^\s*(?:[-*•]|\d+[\.)])\s*(.+)", line)
        if not bullet:
            continue
        for part in re.split(r"[,;，；]", bullet.group(1)):
            add(part)

    term_pattern = (
        r"[\u4e00-\u9fff]{2,}(?:[-\u4e00-\u9fffA-Za-z0-9]+)?"
        r"|[A-Z]{2,}(?:-[A-Za-z0-9]+)*"
        r"|[A-Za-z]+(?:-[A-Za-z0-9]+)+"
        r"|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*"
    )
    for match in re.findall(term_pattern, response):
        add(match)

    return entities[:limit]


def _graphml_key_aliases(root: Any, ns: dict[str, str]) -> dict[str, str]:
    aliases = {
        "d1": "entity_type",
        "d2": "description",
        "d7": "weight",
        "d9": "keywords",
    }
    attr_aliases = {
        "entity_type": "entity_type",
        "description": "description",
        "weight": "weight",
        "keywords": "keywords",
    }
    for key_node in root.findall("g:key", ns):
        key_id = str(key_node.get("id") or "")
        attr_name = str(key_node.get("attr.name") or "")
        if key_id and attr_name in attr_aliases:
            aliases[key_id] = attr_aliases[attr_name]
    return aliases


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
    timeout = float(kwargs.get("timeout", settings.ollama_llm_timeout))

    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if history_messages:
        messages.extend(history_messages)

    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=timeout) as client:
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


def _chat_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                value = part.get("text") or part.get("content")
                if value:
                    parts.append(str(value))
            elif part:
                parts.append(str(part))
        return "".join(parts)
    return str(content or "")


async def openrouter_model_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    **kwargs: str | int | float,
) -> str:
    """OpenRouter completion function using the OpenAI-compatible chat API."""
    import httpx

    model = str(kwargs.get("model", settings.openrouter_model))
    base_url = str(kwargs.get("base_url", settings.openrouter_base_url)).rstrip("/")
    api_key = str(
        kwargs.get("api_key", settings.openrouter_api_key or settings.openai_api_key)
    ).strip()
    timeout = float(kwargs.get("timeout", settings.ollama_llm_timeout))

    if not api_key:
        raise RuntimeError(
            "OpenRouter backend requires OPENROUTER_API_KEY "
            "(or OPENAI_API_KEY as a compatibility fallback)."
        )

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "temperature": kwargs.get("temperature", 0.2),
                "max_tokens": kwargs.get("max_tokens", 1024),
            },
        )
        response.raise_for_status()
        result = response.json()
        choices = result.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return _chat_content_to_text(message.get("content"))


async def ollama_embedding(
    texts: list[str],
    **kwargs: str | int | float,
) -> Any:
    """
    Ollama embedding function for LightRAG.

    Args:
        texts: List of texts to embed
        **kwargs: Additional arguments (model, host, etc.)

    Returns:
        NumPy array of embedding vectors (required by LightRAG)
    """
    import httpx
    import numpy as np

    model = str(kwargs.get("model", settings.ollama_embedding_model))
    host = str(kwargs.get("host", settings.ollama_host))
    timeout = float(kwargs.get("timeout", settings.ollama_embedding_timeout))

    if not texts:
        return np.array([])

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Try the current batch endpoint first (Ollama v0.5+).
        response = await client.post(
            f"{host}/api/embed",
            json={
                "model": model,
                "input": texts,
            },
        )
        if response.status_code != 404:
            response.raise_for_status()
            result = response.json()
            embeddings = result.get("embeddings", result.get("embedding", []))
            if (
                isinstance(embeddings, list)
                and len(texts) == 1
                and embeddings
                and not isinstance(embeddings[0], list)
            ):
                embeddings = [embeddings]
            return np.array(embeddings)

        # Distinguish model-not-found from endpoint-not-found.
        body = response.text
        if "not found" in body and "model" in body:
            response.raise_for_status()

        embeddings = []
        for text in texts:
            # Legacy /api/embeddings only accepts one prompt per request.
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


async def _resolve_ollama_embedding_dimension(host: str, model: str) -> int:
    """Probe and cache the real vector size exposed by an Ollama model."""
    cache_key = (host, model)
    cached = _OLLAMA_EMBEDDING_DIMENSION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    vectors = await ollama_embedding(
        ["asset-aware embedding dimension probe"],
        host=host,
        model=model,
    )
    shape: tuple[Any, ...] = tuple(getattr(vectors, "shape", ()))
    if len(shape) != 2 or shape[0] != 1 or shape[1] <= 0:
        raise RuntimeError(
            f"Ollama returned an invalid embedding shape for model {model!r}: {shape!r}"
        )

    dimension = int(shape[1])
    _OLLAMA_EMBEDDING_DIMENSION_CACHE[cache_key] = dimension
    return dimension


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
        if rag is not None and not hasattr(rag, "aquery"):
            raise TypeError(
                "LightRAGAdapter expects a LightRAG instance or None. "
                "Pass no argument for the default configured adapter."
            )
        self._rag = rag
        self._initialized = rag is not None
        self._initialization_lock = asyncio.Lock()

    @staticmethod
    def _build_query_param(
        mode: str,
        *,
        user_prompt: str | None = None,
        include_references: bool = False,
    ) -> Any:
        from lightrag import QueryParam  # type: ignore

        return QueryParam(
            mode=mode,
            user_prompt=user_prompt,
            include_references=include_references,
        )

    @staticmethod
    def _normalize_query_result(
        query: str,
        requested_mode: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize LightRAG output into a stable MCP-friendly structure."""
        data = cast("dict[str, Any]", result.get("data", {}))
        metadata = cast("dict[str, Any]", result.get("metadata", {}))
        llm_response = cast("dict[str, Any]", result.get("llm_response", {}))
        entities = cast("list[dict[str, Any]]", data.get("entities", []))
        relationships = cast("list[dict[str, Any]]", data.get("relationships", []))
        chunks = cast("list[dict[str, Any]]", data.get("chunks", []))
        references = cast("list[dict[str, Any]]", data.get("references", []))

        return {
            "success": result.get("status") == "success",
            "status": result.get("status", "failure"),
            "message": result.get("message", ""),
            "query": query,
            "mode": metadata.get("query_mode", metadata.get("mode", requested_mode)),
            "answer": llm_response.get("content"),
            "references": references,
            "counts": {
                "entities": len(entities),
                "relationships": len(relationships),
                "chunks": len(chunks),
                "references": len(references),
            },
            "retrieval": {
                "entities": entities,
                "relationships": relationships,
                "chunks": chunks,
            },
            "metadata": metadata,
            "llm_response": {
                "content": llm_response.get("content"),
                "is_streaming": llm_response.get("is_streaming", False),
            },
        }

    async def _ensure_initialized(self) -> LightRAG:
        """Lazy initialization of LightRAG with Ollama or OpenAI backend."""
        if self._rag is not None and self._initialized:
            return self._rag

        async with self._initialization_lock:
            if self._rag is not None and self._initialized:
                return self._rag

            if not settings.enable_lightrag:
                raise RuntimeError("LightRAG is disabled in settings")

            try:
                _validate_lightrag_hku_distribution()
                from lightrag import LightRAG  # type: ignore
                from lightrag.base import EmbeddingFunc  # type: ignore

                # Ensure working directory exists
                working_dir = settings.lightrag_working_dir
                working_dir.mkdir(parents=True, exist_ok=True)

                # Build into a local variable. Publishing ``self._rag`` before
                # initialize_storages() completes lets a concurrent caller use
                # an unready instance against the same on-disk stores.
                backend = settings.llm_backend.strip().lower()
                if backend == "ollama":
                    embedding_dimension = await _resolve_ollama_embedding_dimension(
                        settings.ollama_host,
                        settings.ollama_embedding_model,
                    )
                    rag = LightRAG(
                        working_dir=str(working_dir),
                        llm_model_func=ollama_model_complete,
                        llm_model_name=settings.ollama_model,
                        llm_model_kwargs={
                            "host": settings.ollama_host,
                            "model": settings.ollama_model,
                        },
                        embedding_func=EmbeddingFunc(
                            embedding_dim=embedding_dimension,
                            max_token_size=8192,
                            func=ollama_embedding,
                        ),
                        # Tuning for smaller local models
                        entity_extract_max_gleaning=0,  # Reduce extraction passes
                        max_parallel_insert=1,  # Sequential processing for stability
                        llm_model_max_async=1,  # One LLM call at a time
                        chunk_token_size=800,  # Smaller chunks for better extraction
                    )
                elif backend == "openrouter":
                    embedding_dimension = await _resolve_ollama_embedding_dimension(
                        settings.ollama_host,
                        settings.ollama_embedding_model,
                    )
                    rag = LightRAG(
                        working_dir=str(working_dir),
                        llm_model_func=openrouter_model_complete,
                        llm_model_name=settings.openrouter_model,
                        llm_model_kwargs={
                            "api_key": settings.openrouter_api_key
                            or settings.openai_api_key,
                            "base_url": settings.openrouter_base_url,
                            "model": settings.openrouter_model,
                        },
                        embedding_func=EmbeddingFunc(
                            embedding_dim=embedding_dimension,
                            max_token_size=8192,
                            func=ollama_embedding,
                        ),
                        entity_extract_max_gleaning=0,
                        max_parallel_insert=1,
                        llm_model_max_async=1,
                        chunk_token_size=800,
                    )
                else:
                    # Use OpenAI
                    from lightrag.llm import (  # type: ignore
                        openai_complete_if_cache,
                        openai_embedding,
                    )

                    rag = LightRAG(
                        working_dir=str(working_dir),
                        llm_model_func=openai_complete_if_cache,
                        embedding_func=openai_embedding,
                    )

                # IMPORTANT: Initialize storages (required by LightRAG) before
                # making the instance visible to any other MCP request.
                await rag.initialize_storages()

            except ImportError as e:
                self._rag = None
                self._initialized = False
                raise RuntimeError(
                    "LightRAG backend is not available. Install the optional extra: "
                    "`uv tool install --upgrade 'asset-aware-mcp[lightrag]'` "
                    "(or `uv sync --extra lightrag` for source checkouts). "
                    "Do not install the unrelated `lightrag` package from PyPI."
                ) from e
            except Exception:
                # Do not cache a partial instance; the next request may retry
                # after a transient Ollama or storage failure is resolved.
                self._rag = None
                self._initialized = False
                raise

            self._rag = rag
            self._initialized = True
            return rag

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

        await rag.ainsert(prefixed_text, ids=doc_id)

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
        include_references: bool = False,
    ) -> str:
        """
        Query the knowledge graph.

        Args:
            query: Natural language query
            mode: Query mode - "local", "global", "hybrid", "mix", "naive", or "bypass"
            user_prompt: Optional post-retrieval instruction for answer shaping
            include_references: Include source reference list when supported

        Returns:
            Query result as string
        """
        rag = await self._ensure_initialized()

        param = self._build_query_param(
            mode,
            user_prompt=user_prompt,
            include_references=include_references,
        )

        result = await rag.aquery(query, param=param)

        return str(result) if result else ""

    async def query_structured(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
        include_references: bool = True,
    ) -> dict[str, Any]:
        """Query LightRAG and return answer + references + retrieval metadata."""
        rag = await self._ensure_initialized()
        param = self._build_query_param(
            mode,
            user_prompt=user_prompt,
            include_references=include_references,
        )
        result = await rag.aquery_llm(query, param=param)
        return self._normalize_query_result(query, mode, result)

    async def query_data(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Query LightRAG retrieval layer without generating the final LLM answer."""
        rag = await self._ensure_initialized()
        param = self._build_query_param(mode, user_prompt=user_prompt)
        result = await rag.aquery_data(query, param=param)
        return self._normalize_query_result(query, mode, result)

    async def delete_document(
        self,
        doc_id: str,
        *,
        delete_llm_cache: bool = False,
    ) -> dict[str, Any]:
        """Delete a document from LightRAG and keep graph/vector stores in sync."""
        rag = await self._ensure_initialized()

        result = await rag.adelete_by_doc_id(
            doc_id,
            delete_llm_cache=delete_llm_cache,
        )
        return {
            "status": getattr(result, "status", "fail"),
            "doc_id": getattr(result, "doc_id", doc_id),
            "message": getattr(result, "message", ""),
            "status_code": getattr(result, "status_code", 500),
            "file_path": getattr(result, "file_path", None),
        }

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

            context = text.strip()
            if len(context) > 4000:
                context = context[:4000] + "\n...[truncated]"
            result = await rag.aquery(
                f"List the top {limit} most important entities (people, organizations, "
                f"medical terms, drugs, diseases) mentioned in this context.\n\n"
                f"Context:\n{context}",
                param=QueryParam(mode="local"),
            )

            if not result:
                return []

            return _parse_entity_candidates(str(result), limit=limit)

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
        import xml.etree.ElementTree as ET  # nosec B405

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
        tree = ET.parse(graph_file)  # noqa: S314  # nosec B314
        root = tree.getroot()
        ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
        key_aliases = _graphml_key_aliases(root, ns)

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
                field_name = key_aliases.get(key, key)
                if field_name == "entity_type":
                    entity_type = text
                elif field_name == "description":
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
                field_name = key_aliases.get(key, key)
                if field_name == "keywords":
                    keywords = text
                elif field_name == "weight":
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
            _validate_lightrag_hku_distribution()
            from lightrag import LightRAG, QueryParam  # type: ignore # noqa: F401
            from lightrag.base import EmbeddingFunc  # type: ignore # noqa: F401

            return True
        except (ImportError, AttributeError, RuntimeError):
            return False


# Singleton instance for convenience
_lightrag_adapter: LightRAGAdapter | None = None


def get_lightrag_adapter() -> LightRAGAdapter:
    """Get or create the LightRAG adapter singleton."""
    global _lightrag_adapter
    if _lightrag_adapter is None:
        _lightrag_adapter = LightRAGAdapter()
    return _lightrag_adapter
