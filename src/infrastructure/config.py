"""
Infrastructure Layer - Configuration

Environment variables and settings.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


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
        default="llama3.1:8b", description="Ollama model for LLM tasks"
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text", description="Ollama model for embeddings"
    )

    # LLM Backend selection
    llm_backend: str = Field(
        default="ollama", description="LLM backend: 'ollama' or 'openai'"
    )

    # OpenAI settings (optional, if using OpenAI backend)
    openai_api_key: str = Field(
        default="", description="OpenAI API key (only if llm_backend='openai')"
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
        default=True, description="Enable LightRAG knowledge graph"
    )
    enable_mistral_ocr: bool = Field(
        default=False, description="Enable Mistral OCR (requires API key)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

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
