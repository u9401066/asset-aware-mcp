"""Regressions for LightRAG lazy initialization without optional imports."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from typing import Any, ClassVar

import pytest

import src.infrastructure.lightrag_adapter as lightrag_adapter
from src.infrastructure.lightrag_adapter import LightRAGAdapter


class _FakeEmbeddingFunc:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def _install_fake_lightrag(
    monkeypatch: pytest.MonkeyPatch,
    fake_rag_type: type[Any],
) -> None:
    package = types.ModuleType("lightrag")
    package.LightRAG = fake_rag_type  # type: ignore[attr-defined]
    base = types.ModuleType("lightrag.base")
    base.EmbeddingFunc = _FakeEmbeddingFunc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "lightrag", package)
    monkeypatch.setitem(sys.modules, "lightrag.base", base)


def _configure_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_dimension(_host: str, _model: str) -> int:
        await asyncio.sleep(0)
        return 4

    monkeypatch.setattr(
        lightrag_adapter, "_validate_lightrag_hku_distribution", lambda: None
    )
    monkeypatch.setattr(
        lightrag_adapter, "_resolve_ollama_embedding_dimension", fake_dimension
    )
    monkeypatch.setattr(lightrag_adapter.settings, "enable_lightrag", True)
    monkeypatch.setattr(lightrag_adapter.settings, "llm_backend", "ollama")
    monkeypatch.setattr(
        lightrag_adapter.settings, "lightrag_working_dir", tmp_path / "graph"
    )


@pytest.mark.asyncio
async def test_concurrent_first_calls_share_one_ready_lightrag_instance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeRAG:
        created: ClassVar[list[FakeRAG]] = []

        def __init__(self, **_kwargs: Any) -> None:
            self.ready = False
            self.initialize_calls = 0
            self.created.append(self)

        async def initialize_storages(self) -> None:
            self.initialize_calls += 1
            await asyncio.sleep(0.01)
            self.ready = True

    _install_fake_lightrag(monkeypatch, FakeRAG)
    _configure_fake_runtime(monkeypatch, tmp_path)
    adapter = LightRAGAdapter()

    first, second = await asyncio.gather(
        adapter._ensure_initialized(),
        adapter._ensure_initialized(),
    )

    assert first is second
    assert first.ready is True
    assert first.initialize_calls == 1
    assert FakeRAG.created == [first]


@pytest.mark.asyncio
async def test_failed_lightrag_initialization_is_not_cached_and_can_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeRAG:
        attempts = 0

        def __init__(self, **_kwargs: Any) -> None:
            self.ready = False

        async def initialize_storages(self) -> None:
            type(self).attempts += 1
            if self.attempts == 1:
                raise RuntimeError("transient storage failure")
            self.ready = True

    _install_fake_lightrag(monkeypatch, FakeRAG)
    _configure_fake_runtime(monkeypatch, tmp_path)
    adapter = LightRAGAdapter()

    with pytest.raises(RuntimeError, match="transient storage failure"):
        await adapter._ensure_initialized()
    assert adapter._rag is None
    assert adapter._initialized is False

    recovered = await adapter._ensure_initialized()

    assert recovered.ready is True
    assert adapter._rag is recovered
    assert adapter._initialized is True
    assert FakeRAG.attempts == 2
