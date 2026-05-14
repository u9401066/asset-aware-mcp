"""Runtime diagnostics for the Asset-Aware MCP CLI."""

from __future__ import annotations

import importlib.util
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from src.infrastructure.config import Settings


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unknown"


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _pymupdf_status() -> dict[str, Any]:
    status: dict[str, Any] = {"available": False, "version": None, "detail": ""}
    if not _module_available("fitz"):
        status["detail"] = "PyMuPDF import module `fitz` was not found."
        return status

    try:
        import fitz  # type: ignore[import-untyped]
    except Exception as exc:  # pragma: no cover - defensive runtime diagnostic
        status["detail"] = f"PyMuPDF import failed: {exc}"
        return status

    status["available"] = True
    status["version"] = getattr(fitz, "version", [None])[0]
    status["detail"] = "PyMuPDF backend is importable."
    return status


def _marker_status() -> dict[str, Any]:
    status: dict[str, Any] = {"available": False, "version": None, "detail": ""}
    if not _module_available("marker"):
        status["detail"] = "Marker backend is not installed in this Python environment."
        return status

    try:
        from src.infrastructure.marker_adapter import MarkerPDFExtractor

        MarkerPDFExtractor.require_backend_available()
    except Exception as exc:
        status["detail"] = f"Marker backend preflight failed: {exc}"
        return status

    status["available"] = True
    status["version"] = _package_version("marker-pdf")
    status["detail"] = "Marker backend preflight passed."
    return status


def _path_status(path: Path) -> dict[str, Any]:
    parent = path if path.exists() else path.parent
    return {
        "path": str(path),
        "exists": path.exists(),
        "parent_exists": parent.exists(),
        "writable": parent.exists() and parent.is_dir(),
    }


def collect_runtime_status() -> dict[str, Any]:
    """Collect cheap, side-effect-light runtime diagnostics."""
    settings = Settings()
    return {
        "package": {
            "name": "asset-aware-mcp",
            "version": _package_version("asset-aware-mcp"),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "backends": {
            "pymupdf": _pymupdf_status(),
            "marker": _marker_status(),
        },
        "paths": {
            "data_dir": _path_status(settings.data_dir),
            "table_output_dir": _path_status(settings.table_output_dir),
        },
        "features": {
            "lightrag": {
                "enabled": settings.enable_lightrag,
                "working_dir": str(settings.lightrag_working_dir),
            },
            "ollama": {
                "host": settings.ollama_host,
                "model": settings.ollama_model,
                "embedding_model": settings.ollama_embedding_model,
            },
        },
    }


def format_runtime_status(status: dict[str, Any]) -> str:
    """Render diagnostics in a stable human-readable format."""
    package = status["package"]
    pymupdf = status["backends"]["pymupdf"]
    marker = status["backends"]["marker"]
    data_dir = status["paths"]["data_dir"]
    lightrag = status["features"]["lightrag"]
    ollama = status["features"]["ollama"]

    marker_label = "OK" if marker["available"] else "MISSING"
    pymupdf_label = "OK" if pymupdf["available"] else "MISSING"
    data_label = "OK" if data_dir["parent_exists"] else "MISSING"
    lightrag_label = "ENABLED" if lightrag["enabled"] else "DISABLED"

    lines = [
        f"Asset-Aware MCP {package['version']}",
        f"Python: {status['runtime']['python']} ({status['runtime']['executable']})",
        f"PyMuPDF: {pymupdf_label} {pymupdf.get('version') or ''}".rstrip(),
        f"Marker: {marker_label} {marker.get('version') or ''}".rstrip(),
        f"DATA_DIR: {data_label} {data_dir['path']}",
        f"LightRAG: {lightrag_label}",
        f"Ollama: {ollama['host']}",
        f"LLM model: {ollama['model']}",
        f"Embedding model: {ollama['embedding_model']}",
    ]
    if not marker["available"]:
        lines.append(
            "Recommended action: install a compatible Marker extra or use PyMuPDF mode."
        )
    return "\n".join(lines) + "\n"


def registered_tool_names() -> list[str]:
    """Return FastMCP tool names registered by the presentation layer."""
    from src.presentation.server import mcp

    return sorted(tool.name for tool in mcp._tool_manager._tools.values())
