"""
Integration test for LightRAG with Ollama backend.

This test requires:
1. Ollama running locally (http://localhost:11434)
2. Models: qwen2.5:7b, nomic-embed-text

Run with: uv run pytest tests/integration/test_lightrag_ollama.py -v
"""

from __future__ import annotations

import pytest

from src.infrastructure.config import settings


@pytest.fixture
def ollama_models() -> set[str] | None:
    """Return locally available Ollama models, or None if Ollama is unavailable."""
    import httpx

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.ollama_host}/api/tags")
            resp.raise_for_status()
            body = resp.json()
            return {
                str(model.get("name") or model.get("model"))
                for model in body.get("models", [])
                if model.get("name") or model.get("model")
            }
    except httpx.RequestError:
        return None


def _require_ollama_model(models: set[str] | None, model: str) -> None:
    if models is None:
        pytest.skip("Ollama not available")
    if model not in models:
        pytest.skip(f"Ollama model not available: run `ollama pull {model}`")


class TestOllamaIntegration:
    """Integration tests for Ollama LLM backend."""

    @pytest.mark.asyncio
    async def test_ollama_completion(self, ollama_models: set[str] | None):
        """Test Ollama LLM completion."""
        _require_ollama_model(ollama_models, settings.ollama_model)

        from src.infrastructure.lightrag_adapter import ollama_model_complete

        result = await ollama_model_complete(
            prompt="What is 2+2? Answer with just the number.",
            model=settings.ollama_model,
            host=settings.ollama_host,
        )

        assert result is not None
        assert len(result) > 0
        assert "4" in result

    @pytest.mark.asyncio
    async def test_ollama_embedding(self, ollama_models: set[str] | None):
        """Test Ollama embedding generation."""
        _require_ollama_model(ollama_models, settings.ollama_embedding_model)

        from src.infrastructure.lightrag_adapter import ollama_embedding

        texts = ["Hello world", "How are you"]
        embeddings = await ollama_embedding(
            texts=texts,
            model=settings.ollama_embedding_model,
            host=settings.ollama_host,
        )

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 768  # nomic-embed-text dimension
        assert len(embeddings[1]) == 768

    @pytest.mark.asyncio
    async def test_lightrag_adapter_initialization(
        self, ollama_models: set[str] | None
    ):
        """Test LightRAG adapter can initialize with Ollama."""
        if ollama_models is None:
            pytest.skip("Ollama not available")

        # Ensure we're using Ollama backend
        assert settings.llm_backend == "ollama"

        from src.infrastructure.lightrag_adapter import LightRAGAdapter

        adapter = LightRAGAdapter()

        # Check availability
        assert adapter.is_available


class TestLightRAGOllamaConfig:
    """Tests for LightRAG Ollama configuration."""

    def test_default_backend_is_ollama(self):
        """Verify default LLM backend is Ollama."""
        assert settings.llm_backend == "ollama"

    def test_ollama_settings_have_defaults(self):
        """Verify Ollama settings have sensible defaults."""
        # These settings can be customized via env, just check they exist
        assert settings.ollama_host.startswith("http")
        assert len(settings.ollama_model) > 0
        assert len(settings.ollama_embedding_model) > 0
