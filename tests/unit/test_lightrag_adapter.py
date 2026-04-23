"""Unit tests for LightRAG adapter contracts."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.lightrag_adapter import LightRAGAdapter


class FakeLightRAG:
    """Minimal async LightRAG double accepted by LightRAGAdapter."""

    def __init__(self) -> None:
        self.ainsert = AsyncMock()
        self.aquery = AsyncMock(return_value="")


@pytest.mark.asyncio
async def test_insert_uses_doc_id_contract_for_delete() -> None:
    rag = FakeLightRAG()
    adapter = LightRAGAdapter(rag)  # type: ignore[arg-type]

    await adapter.insert("doc_alpha_123", "Body text")

    rag.ainsert.assert_awaited_once_with(
        "[Document: doc_alpha_123]\n\nBody text",
        ids="doc_alpha_123",
    )
