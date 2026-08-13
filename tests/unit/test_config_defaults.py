"""Regression tests for side-effect-light runtime defaults."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from src.infrastructure.config import Settings, settings_dotenv_file


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
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert settings.openrouter_model == "liquid/lfm-2.5-1.2b-instruct:free"
    assert settings.enable_lightrag is False


def test_openrouter_env_overrides_are_loaded(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_ollama_model_env(monkeypatch)
    monkeypatch.setenv("LLM_BACKEND", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "liquid/custom:free")

    settings = Settings(_env_file=None)

    assert settings.llm_backend == "openrouter"
    assert settings.openrouter_api_key == "sk-or-test"
    assert settings.openrouter_model == "liquid/custom:free"


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


def test_relocated_data_dir_keeps_default_asset_stores_together(tmp_path) -> None:
    data_dir = tmp_path / "asset-data"

    settings = Settings(data_dir=data_dir, _env_file=None)

    assert settings.table_output_dir == data_dir / "tables"
    assert settings.lightrag_working_dir == data_dir / "lightrag_db"


def test_explicit_asset_store_paths_are_preserved(tmp_path) -> None:
    data_dir = tmp_path / "asset-data"
    table_dir = tmp_path / "custom-tables"
    graph_dir = tmp_path / "custom-graph"

    settings = Settings(
        data_dir=data_dir,
        table_output_dir=table_dir,
        lightrag_working_dir=graph_dir,
        _env_file=None,
    )

    assert settings.table_output_dir == table_dir
    assert settings.lightrag_working_dir == graph_dir


def test_managed_launch_can_disable_implicit_working_directory_dotenv(
    monkeypatch,
) -> None:
    assert settings_dotenv_file({}) == ".env"
    assert settings_dotenv_file({"ASSET_AWARE_DISABLE_DOTENV": "true"}) is None
    assert settings_dotenv_file({"ASSET_AWARE_DISABLE_DOTENV": "1"}) is None
    assert settings_dotenv_file({"ASSET_AWARE_DISABLE_DOTENV": "false"}) == ".env"


def test_global_settings_do_not_reload_workspace_secrets_when_disabled(
    tmp_path,
) -> None:
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=DOTENV_SENTINEL_MUST_NOT_LOAD\n",
        encoding="utf-8",
    )
    script = (
        "from src.infrastructure.config import settings; "
        "print(bool(settings.openai_api_key))"
    )
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        "ASSET_AWARE_DISABLE_DOTENV": "true",
    }

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_config_import_does_not_import_optional_adapters() -> None:
    """Importing settings must not pull optional heavy backends into Cline startup."""
    script = r"""
import builtins
import importlib

original_import = builtins.__import__

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    targets = ("lightrag_adapter", "marker_adapter")
    if any(target in name for target in targets):
        raise AssertionError(f"optional adapter imported during config load: {name}")
    if any(any(target in str(item) for target in targets) for item in fromlist or ()):
        raise AssertionError(f"optional adapter imported during config load: {fromlist}")
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = guarded_import
importlib.import_module("src.infrastructure.config")
print("config-ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "config-ok" in result.stdout
