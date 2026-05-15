"""Regression tests for side-effect-light runtime defaults."""

from __future__ import annotations

from src.infrastructure.config import Settings


def _clear_ollama_model_env(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("ENABLE_LIGHTRAG", raising=False)
    monkeypatch.delenv("ASSET_AWARE_HAS_GPU", raising=False)
    monkeypatch.delenv("ASSET_AWARE_USE_GPU", raising=False)
    monkeypatch.delenv("ASSET_AWARE_GPU", raising=False)
    monkeypatch.delenv("NVIDIA_VISIBLE_DEVICES", raising=False)
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)


def test_rag_defaults_to_cpu_granite_without_enabling_knowledge_graph(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_ollama_model_env(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "granite4.1:3b"
    assert settings.ollama_embedding_model == "nomic-embed-text"
    assert settings.enable_lightrag is False


def test_rag_default_uses_8b_granite_when_gpu_hint_is_enabled(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_ollama_model_env(monkeypatch)
    monkeypatch.setenv("ASSET_AWARE_HAS_GPU", "true")

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "granite4.1:8b"
    assert settings.enable_lightrag is False


def test_explicit_ollama_model_overrides_gpu_hint(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_ollama_model_env(monkeypatch)
    monkeypatch.setenv("ASSET_AWARE_HAS_GPU", "true")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model:latest")

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "custom-model:latest"
