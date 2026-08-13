"""Runtime diagnostics for the Asset-Aware MCP CLI."""

from __future__ import annotations

import importlib.util
import platform
import sys
import sysconfig
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from src.infrastructure.config import Settings

PREFERRED_RUNTIME_PYTHON = "3.11"


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unknown"


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _import_status(module_name: str, distribution: str) -> dict[str, Any]:
    status: dict[str, Any] = {
        "available": False,
        "version": None,
        "detail": "",
    }
    if not _module_available(module_name):
        status["detail"] = f"Python module `{module_name}` was not found."
        return status

    try:
        __import__(module_name, fromlist=["*"])
    except Exception as exc:  # pragma: no cover - depends on host native libs
        status["detail"] = f"Import failed for `{module_name}`: {exc}"
        return status

    status["available"] = True
    status["version"] = _package_version(distribution)
    status["detail"] = f"Python module `{module_name}` is importable."
    return status


def _platform_tag_summary() -> dict[str, Any]:
    summary: dict[str, Any] = {
        "sysconfig_platform": sysconfig.get_platform(),
        "machine": platform.machine(),
        "python_implementation": platform.python_implementation(),
        "implementation_name": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag,
        "packaging_tags": [],
        "detail": "stdlib platform summary available.",
    }
    try:
        from packaging.tags import sys_tags
    except Exception as exc:  # packaging is optional in the published runtime
        summary["detail"] = f"packaging.tags unavailable: {exc}"
        return summary

    summary["packaging_tags"] = [str(tag) for tag in list(sys_tags())[:10]]
    summary["detail"] = "packaging.tags summary available."
    return summary


def _pymupdf_status() -> dict[str, Any]:
    status: dict[str, Any] = {"available": False, "version": None, "detail": ""}
    if not _module_available("pymupdf"):
        status["detail"] = "PyMuPDF import module `pymupdf` was not found."
        return status

    try:
        import pymupdf as fitz  # type: ignore[import-untyped]
    except Exception as exc:  # pragma: no cover - defensive runtime diagnostic
        status["detail"] = f"PyMuPDF import failed: {exc}"
        return status

    status["available"] = True
    status["version"] = getattr(fitz, "version", [None])[0]
    status["detail"] = "PyMuPDF backend is importable."
    return status


def _marker_status() -> dict[str, Any]:
    """Report the packaged Marker route as held even if manually installed.

    A local ``marker`` import is not enough to make the backend supported: the
    packaged dependency graph stays empty until marker-pdf accepts a patched
    Pillow range. Diagnostics must not turn an unsupported import into an
    apparent green light.
    """
    return {
        "available": False,
        "version": _package_version("marker-pdf"),
        "security_hold": True,
        "detail": (
            "Marker is on a packaging security hold: marker-pdf 1.10.2 pins "
            "Pillow<11 while asset-aware-mcp requires Pillow>=12.2.0."
        ),
    }


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
    preferred_major, preferred_minor = PREFERRED_RUNTIME_PYTHON.split(".", 1)
    return {
        "package": {
            "name": "asset-aware-mcp",
            "version": _package_version("asset-aware-mcp"),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "preferred_python": PREFERRED_RUNTIME_PYTHON,
            "preferred_python_active": (
                sys.version_info.major == int(preferred_major)
                and sys.version_info.minor == int(preferred_minor)
            ),
            "platform": platform.platform(),
            "executable": sys.executable,
            "platform_tags": _platform_tag_summary(),
        },
        "backends": {
            "pymupdf": _pymupdf_status(),
            "marker": _marker_status(),
        },
        "native_dependencies": {
            "pillow": _import_status("PIL.Image", "Pillow"),
            "lxml": _import_status("lxml.etree", "lxml"),
            "pydantic_core": _import_status("pydantic_core", "pydantic-core"),
            "mcp": _import_status("mcp", "mcp"),
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
    native = status["native_dependencies"]
    data_dir = status["paths"]["data_dir"]
    lightrag = status["features"]["lightrag"]
    ollama = status["features"]["ollama"]

    marker_label = (
        "SECURITY HOLD"
        if marker.get("security_hold")
        else ("OK" if marker["available"] else "MISSING")
    )
    pymupdf_label = "OK" if pymupdf["available"] else "MISSING"
    pillow_label = "OK" if native["pillow"]["available"] else "MISSING"
    lxml_label = "OK" if native["lxml"]["available"] else "MISSING"
    pydantic_core_label = "OK" if native["pydantic_core"]["available"] else "MISSING"
    mcp_label = "OK" if native["mcp"]["available"] else "MISSING"
    data_label = "OK" if data_dir["parent_exists"] else "MISSING"
    lightrag_label = "ENABLED" if lightrag["enabled"] else "DISABLED"

    lines = [
        f"Asset-Aware MCP {package['version']}",
        f"Python: {status['runtime']['python']} ({status['runtime']['executable']})",
        f"Preferred Python: {status['runtime']['preferred_python']}",
        f"Runtime platform: {status['runtime']['platform_tags']['sysconfig_platform']}",
        f"PyMuPDF: {pymupdf_label} {pymupdf.get('version') or ''}".rstrip(),
        f"Marker: {marker_label} {marker.get('version') or ''}".rstrip(),
        f"Pillow: {pillow_label} {native['pillow'].get('version') or ''}".rstrip(),
        f"lxml: {lxml_label} {native['lxml'].get('version') or ''}".rstrip(),
        (
            f"pydantic-core: {pydantic_core_label} "
            f"{native['pydantic_core'].get('version') or ''}"
        ).rstrip(),
        f"MCP SDK: {mcp_label} {native['mcp'].get('version') or ''}".rstrip(),
        f"DATA_DIR: {data_label} {data_dir['path']}",
        f"LightRAG: {lightrag_label}",
        f"Ollama: {ollama['host']}",
        f"LLM model: {ollama['model']}",
        f"Embedding model: {ollama['embedding_model']}",
    ]
    if marker.get("security_hold"):
        lines.append(
            "Recommended action: use PyMuPDF, PyMuPDF4LLM, or Docling; do not "
            "install the held Marker dependency graph."
        )
    return "\n".join(lines) + "\n"


def registered_tool_names() -> list[str]:
    """Return MCP v2 tool names registered by the presentation layer."""
    from src.presentation.server import mcp

    return sorted(mcp.registered_tool_names)
