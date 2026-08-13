"""Unit tests for LightRAG adapter contracts."""

from __future__ import annotations

import builtins
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("lightrag")

import src.infrastructure.lightrag_adapter as lightrag_adapter  # noqa: E402
from src.infrastructure.lightrag_adapter import (  # noqa: E402
    _OLLAMA_EMBEDDING_DIMENSION_CACHE,
    LightRAGAdapter,
    _resolve_ollama_embedding_dimension,
    ollama_embedding,
    ollama_model_complete,
)


class FakeLightRAG:
    """Minimal async LightRAG double accepted by LightRAGAdapter."""

    def __init__(self) -> None:
        self.ainsert = AsyncMock()
        self.aquery = AsyncMock(return_value="")


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        *,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "request failed",
                request=httpx.Request("POST", "http://ollama.test"),
                response=httpx.Response(self.status_code),
            )


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


@pytest.mark.asyncio
async def test_extract_entities_parses_multilingual_medical_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeQueryParam:
        def __init__(self, mode: str) -> None:
            self.mode = mode

    fake_module = types.ModuleType("lightrag")
    fake_module.QueryParam = FakeQueryParam
    monkeypatch.setitem(sys.modules, "lightrag", fake_module)

    rag = FakeLightRAG()
    rag.aquery.return_value = "- 瑞馬唑侖\n- IL-6\n- TNF-alpha\n- Remimazolam"
    adapter = LightRAGAdapter(rag)  # type: ignore[arg-type]

    entities = await adapter.extract_entities("context", limit=5)

    assert entities == ["瑞馬唑侖", "IL-6", "TNF-alpha", "Remimazolam"]


@pytest.mark.asyncio
async def test_export_graph_reads_graphml_attribute_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    graphml = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="k_type" for="node" attr.name="entity_type" attr.type="string"/>
  <key id="k_desc" for="node" attr.name="description" attr.type="string"/>
  <key id="k_weight" for="edge" attr.name="weight" attr.type="double"/>
  <key id="k_kw" for="edge" attr.name="keywords" attr.type="string"/>
  <graph id="G" edgedefault="undirected">
    <node id="Remimazolam">
      <data key="k_type">DRUG</data>
      <data key="k_desc">Sedation agent</data>
    </node>
    <node id="Propofol">
      <data key="k_type">DRUG</data>
      <data key="k_desc">Comparator</data>
    </node>
    <edge source="Remimazolam" target="Propofol">
      <data key="k_weight">0.8</data>
      <data key="k_kw">sedation comparison</data>
    </edge>
  </graph>
</graphml>
"""
    (tmp_path / "graph_chunk_entity_relation.graphml").write_text(
        graphml,
        encoding="utf-8",
    )
    monkeypatch.setattr(lightrag_adapter.settings, "lightrag_working_dir", tmp_path)

    result = await LightRAGAdapter().export_graph(format="json", limit=10)

    assert result["nodes"][0]["type"] == "DRUG"
    assert result["nodes"][0]["description"] == "Sedation agent"
    assert result["edges"][0]["keywords"] == "sedation comparison"
    assert result["edges"][0]["weight"] == "0.8"


@pytest.mark.asyncio
async def test_ollama_embedding_batches_api_embed_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
            calls.append((url, json))
            return FakeResponse({"embeddings": [[1.0, 2.0], [3.0, 4.0]]})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    embeddings = await ollama_embedding(
        ["alpha", "beta"],
        model="nomic-test",
        host="http://ollama.test",
    )

    assert np.array_equal(embeddings, np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert calls == [
        (
            "http://ollama.test/api/embed",
            {"model": "nomic-test", "input": ["alpha", "beta"]},
        )
    ]


@pytest.mark.asyncio
async def test_ollama_embedding_falls_back_to_legacy_embeddings_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
            calls.append((url, json))
            if url.endswith("/api/embed"):
                return FakeResponse({}, status_code=404, text="endpoint not found")
            return FakeResponse({"embedding": [float(len(calls)), 9.0]})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    embeddings = await ollama_embedding(
        ["alpha", "beta"],
        model="nomic-test",
        host="http://ollama.test",
    )

    assert np.array_equal(embeddings, np.array([[2.0, 9.0], [3.0, 9.0]]))
    assert calls == [
        (
            "http://ollama.test/api/embed",
            {"model": "nomic-test", "input": ["alpha", "beta"]},
        ),
        (
            "http://ollama.test/api/embeddings",
            {"model": "nomic-test", "prompt": "alpha"},
        ),
        (
            "http://ollama.test/api/embeddings",
            {"model": "nomic-test", "prompt": "beta"},
        ),
    ]


@pytest.mark.asyncio
async def test_ollama_embedding_dimension_is_probed_and_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def fake_embedding(texts: list[str], **_kwargs: str | int | float) -> Any:
        nonlocal calls
        calls += 1
        assert texts == ["asset-aware embedding dimension probe"]
        return np.array([[0.0, 0.1, 0.2, 0.3]])

    _OLLAMA_EMBEDDING_DIMENSION_CACHE.clear()
    monkeypatch.setattr(lightrag_adapter, "ollama_embedding", fake_embedding)

    first = await _resolve_ollama_embedding_dimension(
        "http://ollama.test", "custom-embed"
    )
    second = await _resolve_ollama_embedding_dimension(
        "http://ollama.test", "custom-embed"
    )

    assert first == second == 4
    assert calls == 1


@pytest.mark.asyncio
async def test_ollama_embedding_dimension_rejects_invalid_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_embedding(_texts: list[str], **_kwargs: str | int | float) -> Any:
        return np.array([])

    _OLLAMA_EMBEDDING_DIMENSION_CACHE.clear()
    monkeypatch.setattr(lightrag_adapter, "ollama_embedding", fake_embedding)

    with pytest.raises(RuntimeError, match="invalid embedding shape"):
        await _resolve_ollama_embedding_dimension("http://ollama.test", "broken-embed")


@pytest.mark.asyncio
async def test_ollama_model_complete_uses_configurable_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeouts: list[float] = []

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            timeouts.append(timeout)

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, _url: str, json: dict[str, Any]) -> FakeResponse:
            assert json["stream"] is False
            return FakeResponse({"message": {"content": "ok"}})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        lightrag_adapter.settings, "ollama_llm_timeout", 333.0, raising=False
    )

    result = await ollama_model_complete(
        "hello",
        model="qwen-test",
        host="http://ollama.test",
    )

    assert result == "ok"
    assert timeouts == [333.0]
