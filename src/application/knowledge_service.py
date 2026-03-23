"""
Application Layer - Knowledge Service

Use cases for knowledge graph queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.repositories import KnowledgeGraphInterface


class KnowledgeService:
    """
    Application service for knowledge graph operations.

    Provides:
    - Cross-document queries
    - Entity extraction
    - Hybrid search (local + global)
    """

    def __init__(self, knowledge_graph: KnowledgeGraphInterface | None = None):
        """
        Initialize knowledge service.

        Args:
            knowledge_graph: Knowledge graph implementation
        """
        self.knowledge_graph = knowledge_graph

    @property
    def is_available(self) -> bool:
        """Check if knowledge graph is available."""
        return self.knowledge_graph is not None and self.knowledge_graph.is_available

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
            include_references: Include reference list when supported

        Returns:
            Query result as string
        """
        if not self.is_available or self.knowledge_graph is None:
            return (
                "Knowledge graph is not available. Please enable LightRAG in settings."
            )

        try:
            result = await self.knowledge_graph.query(
                query,
                mode=mode,
                user_prompt=user_prompt,
                include_references=include_references,
            )
            return result or "No results found."
        except Exception as e:
            return f"Query failed: {e}"

    async def query_structured(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
        include_references: bool = True,
    ) -> dict[str, Any]:
        """Return structured answer + references + retrieval metadata."""
        if not self.is_available or self.knowledge_graph is None:
            return {
                "success": False,
                "status": "failure",
                "message": "Knowledge graph is not available. Please enable LightRAG in settings.",
                "query": query,
                "mode": mode,
                "answer": None,
                "references": [],
                "counts": {
                    "entities": 0,
                    "relationships": 0,
                    "chunks": 0,
                    "references": 0,
                },
                "retrieval": {"entities": [], "relationships": [], "chunks": []},
                "metadata": {},
                "llm_response": {"content": None, "is_streaming": False},
            }

        try:
            return await self.knowledge_graph.query_structured(
                query,
                mode=mode,
                user_prompt=user_prompt,
                include_references=include_references,
            )
        except Exception as e:
            return {
                "success": False,
                "status": "failure",
                "message": f"Query failed: {e}",
                "query": query,
                "mode": mode,
                "answer": None,
                "references": [],
                "counts": {
                    "entities": 0,
                    "relationships": 0,
                    "chunks": 0,
                    "references": 0,
                },
                "retrieval": {"entities": [], "relationships": [], "chunks": []},
                "metadata": {},
                "llm_response": {"content": None, "is_streaming": False},
            }

    async def query_data(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Return retrieval data and metadata without the final answer synthesis."""
        if not self.is_available or self.knowledge_graph is None:
            return {
                "success": False,
                "status": "failure",
                "message": "Knowledge graph is not available. Please enable LightRAG in settings.",
                "query": query,
                "mode": mode,
                "answer": None,
                "references": [],
                "counts": {
                    "entities": 0,
                    "relationships": 0,
                    "chunks": 0,
                    "references": 0,
                },
                "retrieval": {"entities": [], "relationships": [], "chunks": []},
                "metadata": {},
                "llm_response": {"content": None, "is_streaming": False},
            }

        try:
            return await self.knowledge_graph.query_data(
                query,
                mode=mode,
                user_prompt=user_prompt,
            )
        except Exception as e:
            return {
                "success": False,
                "status": "failure",
                "message": f"Query failed: {e}",
                "query": query,
                "mode": mode,
                "answer": None,
                "references": [],
                "counts": {
                    "entities": 0,
                    "relationships": 0,
                    "chunks": 0,
                    "references": 0,
                },
                "retrieval": {"entities": [], "relationships": [], "chunks": []},
                "metadata": {},
                "llm_response": {"content": None, "is_streaming": False},
            }

    async def compare_documents(self, question: str) -> str:
        """
        Compare information across documents.

        Uses hybrid mode to get both specific details (local)
        and high-level patterns (global).

        Args:
            question: Comparison question (e.g., "Compare drug efficacy across studies")

        Returns:
            Comparison result
        """
        if not self.is_available:
            return "Knowledge graph is not available."

        # Use hybrid mode for cross-document comparisons
        return await self.query(question, mode="hybrid")

    async def get_related_concepts(self, concept: str) -> str:
        """
        Find concepts related to a given concept.

        Args:
            concept: Medical concept to explore

        Returns:
            Related concepts and relationships
        """
        if not self.is_available:
            return "Knowledge graph is not available."

        query = f"What concepts, drugs, or conditions are related to {concept}?"
        return await self.query(query, mode="local")
