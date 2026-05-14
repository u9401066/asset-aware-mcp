"""Regression tests for side-effect-light runtime defaults."""

from __future__ import annotations

from src.infrastructure.config import Settings


def test_rag_defaults_to_granite_without_enabling_knowledge_graph(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("ENABLE_LIGHTRAG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "granite4.1"
    assert settings.ollama_embedding_model == "nomic-embed-text"
    assert settings.enable_lightrag is False
