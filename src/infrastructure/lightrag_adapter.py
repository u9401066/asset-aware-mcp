"""
Infrastructure Layer - LightRAG Adapter

Integration with LightRAG for knowledge graph operations.
Supports both Ollama (local) and OpenAI backends.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.domain.repositories import KnowledgeGraphInterface

from .config import settings

if TYPE_CHECKING:
    from lightrag import LightRAG

from lightrag.base import EmbeddingFunc


# ============================================================================
# Ollama LLM Functions for LightRAG
# ============================================================================

async def ollama_model_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    **kwargs,
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
    
    model = kwargs.get("model", settings.ollama_model)
    host = kwargs.get("host", settings.ollama_host)
    
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
        return result.get("message", {}).get("content", "")


async def ollama_embedding(
    texts: list[str],
    **kwargs,
) -> list[list[float]]:
    """
    Ollama embedding function for LightRAG.
    
    Args:
        texts: List of texts to embed
        **kwargs: Additional arguments (model, host, etc.)
        
    Returns:
        List of embedding vectors
    """
    import httpx
    
    model = kwargs.get("model", settings.ollama_embedding_model)
    host = kwargs.get("host", settings.ollama_host)
    
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
    
    return embeddings


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
            from lightrag import LightRAG

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
                )
            else:
                # Use OpenAI
                from lightrag.llm import openai_complete_if_cache, openai_embedding
                
                self._rag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=openai_complete_if_cache,
                    embedding_func=openai_embedding,
                )
            
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

        from lightrag import QueryParam

        result = await rag.aquery(
            query,
            param=QueryParam(mode=mode)
        )

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
            from lightrag import QueryParam

            result = await rag.aquery(
                f"List the top {limit} most important entities (people, organizations, "
                f"medical terms, drugs, diseases) mentioned in this context.",
                param=QueryParam(mode="local")
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
            caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', str(result))
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

    @property
    def is_available(self) -> bool:
        """Check if LightRAG is available and enabled."""
        if not settings.enable_lightrag:
            return False

        try:
            import lightrag  # noqa: F401
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
