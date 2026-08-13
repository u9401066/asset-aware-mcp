"""
Infrastructure Layer - Configuration

Environment variables and settings.
"""

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

DEFAULT_OLLAMA_CPU_MODEL = "granite4.1:3b"
DEFAULT_OLLAMA_GPU_MODEL = "granite4.1:8b"
DEFAULT_OLLAMA_MODEL = DEFAULT_OLLAMA_CPU_MODEL
DEFAULT_OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "liquid/lfm-2.5-1.2b-instruct:free"
GPU_MODEL_HINT_ENV_VARS = (
    "ASSET_AWARE_HAS_GPU",
    "ASSET_AWARE_USE_GPU",
    "ASSET_AWARE_GPU",
)
GPU_VISIBLE_DEVICE_ENV_VARS = ("NVIDIA_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES")
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
FALSE_ENV_VALUES = {"0", "false", "no", "off", "none", "void", "-1"}


def _normalized_env_value(value: str | None) -> str:
    return (value or "").strip().lower()


def env_prefers_gpu_model(env: Mapping[str, str] | None = None) -> bool:
    """Return whether environment hints prefer the GPU-sized local model.

    This intentionally avoids probing hardware or starting subprocesses during
    settings import. Operators can opt into the larger default with
    ``ASSET_AWARE_HAS_GPU=true`` or by running in a GPU container that sets
    ``NVIDIA_VISIBLE_DEVICES``/``CUDA_VISIBLE_DEVICES``.
    """
    source = os.environ if env is None else env
    for key in GPU_MODEL_HINT_ENV_VARS:
        value = _normalized_env_value(source.get(key))
        if value in TRUE_ENV_VALUES:
            return True
        if value in FALSE_ENV_VALUES:
            return False

    for key in GPU_VISIBLE_DEVICE_ENV_VARS:
        value = _normalized_env_value(source.get(key))
        if value and value not in FALSE_ENV_VALUES:
            return True
    return False


def default_ollama_model(env: Mapping[str, str] | None = None) -> str:
    """Choose the pinned Granite default without requiring KG dependencies."""
    return (
        DEFAULT_OLLAMA_GPU_MODEL
        if env_prefers_gpu_model(env)
        else DEFAULT_OLLAMA_CPU_MODEL
    )


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Paths
    data_dir: Path = Field(
        default=Path("./data"), description="Directory for storing processed documents"
    )
    table_output_dir: Path = Field(
        default=Path("./data/tables"), description="Directory for A2T generated tables"
    )

    # Mistral API (optional, for OCR)
    mistral_api_key: str = Field(
        default="", description="Mistral API key for OCR (optional)"
    )

    # LightRAG settings
    lightrag_working_dir: Path = Field(
        default=Path("./data/lightrag_db"), description="LightRAG working directory"
    )

    # Ollama settings (Local LLM)
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    ollama_model: str = Field(
        default_factory=default_ollama_model,
        description="Ollama model for LLM tasks",
    )
    ollama_embedding_model: str = Field(
        default=DEFAULT_OLLAMA_EMBEDDING_MODEL,
        description="Ollama model for embeddings",
    )
    ollama_llm_timeout: float = Field(
        default=300.0, description="Ollama chat request timeout in seconds"
    )
    ollama_embedding_timeout: float = Field(
        default=120.0, description="Ollama embedding request timeout in seconds"
    )

    # LLM Backend selection
    llm_backend: str = Field(
        default="ollama",
        description="LLM backend: 'ollama', 'openai', or 'openrouter'",
    )

    # ETL Profile selection
    etl_profile: str = Field(
        default="default",
        description="ETL extraction profile: 'default', 'arxiv', 'nature', 'ieee', 'elsevier'",
    )
    etl_profile_json: Path | None = Field(
        default=None,
        description="Optional JSON file path for a custom ETL extraction profile",
    )

    # PDF -> asset extraction engine selection
    etl_engine: str = Field(
        default="pymupdf",
        description=(
            "High-fidelity PDF->asset engine: 'pymupdf' (default, fast, no models), "
            "'pymupdf4llm' (layout-aware drop-in), 'docling' (MIT; layout+table+"
            "formula+figure), 'mineru' (adapter-only security hold while its "
            "transformers cap excludes patched releases), or 'marker' (adapter-only "
            "security hold while pinned to Pillow<11). "
            "Structured engines are lazy-loaded and used when use_marker/structured "
            "parsing is requested."
        ),
    )
    docling_python_path: str = Field(
        default="",
        description=(
            "Optional path to an isolated Python interpreter that has 'docling' "
            "installed (e.g. .venv-docling/bin/python on POSIX or "
            ".venv-docling\\Scripts\\python.exe on Windows). Lets the Docling engine "
            "run in a subprocess when it cannot be installed in the main environment "
            "(e.g. pre-release Python without torch wheels). When empty, the adapter "
            "auto-detects the DOCLING_PYTHON_PATH env var or ./.venv-docling. "
            "Install via: python scripts/setup_docling.py"
        ),
    )

    # OpenAI settings (optional, if using OpenAI backend)
    openai_api_key: str = Field(
        default="", description="OpenAI API key (only if llm_backend='openai')"
    )
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key (only if llm_backend='openrouter')",
    )
    openrouter_base_url: str = Field(
        default=DEFAULT_OPENROUTER_BASE_URL,
        description="OpenRouter OpenAI-compatible API base URL",
    )
    openrouter_model: str = Field(
        default=DEFAULT_OPENROUTER_MODEL,
        description="OpenRouter model for fast low-cost summaries and draft RAG answers",
    )
    lightrag_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for LightRAG",
    )

    # MCP Server settings
    mcp_server_name: str = Field(
        default="asset-aware-mcp", description="MCP server name"
    )

    # Processing settings
    max_image_size_mb: float = Field(
        default=10.0, description="Maximum image size in MB to process"
    )
    image_output_format: str = Field(
        default="png", description="Output format for extracted images"
    )

    # Feature flags
    enable_lightrag: bool = Field(
        default=False, description="Enable LightRAG knowledge graph"
    )
    enable_mistral_ocr: bool = Field(
        default=False, description="Enable Mistral OCR (requires API key)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _align_default_asset_directories(self) -> "Settings":
        """Keep default-derived stores inside the configured data plane.

        ``DATA_DIR`` is commonly relocated by the VS Code extension and by
        subprocess workers. Explicit output paths remain authoritative; only
        omitted defaults follow the relocated root.
        """
        configured_fields = self.model_fields_set
        if "table_output_dir" not in configured_fields:
            self.table_output_dir = self.data_dir / "tables"
        if "lightrag_working_dir" not in configured_fields:
            self.lightrag_working_dir = self.data_dir / "lightrag_db"
        return self

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.table_output_dir.mkdir(parents=True, exist_ok=True)
        if self.enable_lightrag:
            self.lightrag_working_dir.mkdir(parents=True, exist_ok=True)

    def get_doc_dir(self, doc_id: str) -> Path:
        """Get directory for a specific document."""
        doc_dir = self.data_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir


# Global settings instance
settings = Settings()
