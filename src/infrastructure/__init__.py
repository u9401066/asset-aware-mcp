"""Infrastructure package exports.

Keep this module side-effect-light: importing configuration should not import
optional OCR/KG adapters or their transitive model/runtime dependencies.
"""

from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from .config import settings
from .file_storage import FileStorage
from .job_store import FileJobStore, InMemoryJobStore, JobStoreInterface


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


_HAS_LIGHTRAG = _module_available("lightrag")
_HAS_MARKER = _module_available("marker")
_HAS_PYMUPDF = _module_available("pymupdf")


def __getattr__(name: str) -> Any:
    if name == "LightRAGAdapter":
        from .lightrag_adapter import LightRAGAdapter

        return LightRAGAdapter
    if name == "MarkerPDFExtractor":
        from .marker_adapter import MarkerPDFExtractor

        return MarkerPDFExtractor
    if name == "PyMuPDFExtractor":
        from .pdf_extractor import PyMuPDFExtractor

        return PyMuPDFExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_pdf_extractor() -> Any:
    """Get the default PDF extractor without importing it at package load time."""
    if not _HAS_PYMUPDF:
        raise ImportError("No PDF extractor available. Install PyMuPDF.")
    from .pdf_extractor import PyMuPDFExtractor

    return PyMuPDFExtractor()


__all__ = [
    "_HAS_LIGHTRAG",
    "_HAS_MARKER",
    "_HAS_PYMUPDF",
    "FileJobStore",
    "FileStorage",
    "InMemoryJobStore",
    "JobStoreInterface",
    "LightRAGAdapter",
    "MarkerPDFExtractor",
    "PyMuPDFExtractor",
    "get_pdf_extractor",
    "settings",
]
