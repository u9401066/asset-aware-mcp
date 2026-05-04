"""Unit tests for LightRAG adapter contracts."""

from __future__ import annotations

import builtins
import sys
import types
from unittest.mock import AsyncMock

import pytest

import src.infrastructure.lightrag_adapter as lightrag_adapter
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


def test_is_available_returns_false_without_importing_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = LightRAGAdapter()
    monkeypatch.setattr(lightrag_adapter.settings, "enable_lightrag", False)

    original_import = builtins.__import__

    def fail_lightrag_import(
        name: str,
        globals=None,
        locals=None,
        fromlist=(),
        level: int = 0,
    ):
        if name.startswith("lightrag"):
            raise AssertionError("LightRAG should not be imported when disabled")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_lightrag_import)

    assert adapter.is_available is False


def test_is_available_rejects_wrong_lightrag_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = LightRAGAdapter()
    monkeypatch.setattr(lightrag_adapter.settings, "enable_lightrag", True)

    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals=None,
        locals=None,
        fromlist=(),
        level: int = 0,
    ):
        if name == "lightrag" and fromlist:
            raise ImportError("cannot import name 'QueryParam'")
        if name == "lightrag.base":
            raise ImportError("No module named 'lightrag.base'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert adapter.is_available is False


@pytest.mark.asyncio
async def test_disabled_lightrag_raises_without_importing_optional_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = LightRAGAdapter()
    monkeypatch.setattr(lightrag_adapter.settings, "enable_lightrag", False)

    original_import = builtins.__import__

    def fail_lightrag_import(
        name: str,
        globals=None,
        locals=None,
        fromlist=(),
        level: int = 0,
    ):
        if name.startswith("lightrag"):
            raise AssertionError("LightRAG should not be imported when disabled")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_lightrag_import)

    with pytest.raises(RuntimeError, match="disabled"):
        await adapter._ensure_initialized()


@pytest.mark.asyncio
async def test_extract_entities_includes_text_context_in_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeQueryParam:
        def __init__(self, mode: str) -> None:
            self.mode = mode

    fake_module = types.ModuleType("lightrag")
    fake_module.QueryParam = FakeQueryParam
    monkeypatch.setitem(sys.modules, "lightrag", fake_module)

    rag = FakeLightRAG()
    rag.aquery.return_value = '"Remimazolam"'
    adapter = LightRAGAdapter(rag)  # type: ignore[arg-type]

    entities = await adapter.extract_entities(
        "UniqueContextTerm remimazolam sedation protocol",
        limit=3,
    )

    prompt = rag.aquery.await_args.args[0]
    assert "UniqueContextTerm" in prompt
    assert "Context:" in prompt
    assert entities == ["Remimazolam"]
