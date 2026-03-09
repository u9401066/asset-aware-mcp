# Infrastructure Layer - External Dependencies

from .config import settings
from .file_storage import FileStorage
from .job_store import FileJobStore, InMemoryJobStore, JobStoreInterface

try:
    from .lightrag_adapter import LightRAGAdapter

    _HAS_LIGHTRAG = True
except ImportError:
    _HAS_LIGHTRAG = False
    LightRAGAdapter = None  # type: ignore

try:
    from .pdf_extractor import PyMuPDFExtractor

    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False
    PyMuPDFExtractor = None  # type: ignore

try:
    from .marker_adapter import MarkerPDFExtractor

    _HAS_MARKER = True
except ImportError:
    _HAS_MARKER = False
    MarkerPDFExtractor = None  # type: ignore


def get_pdf_extractor() -> PyMuPDFExtractor:
    """
    Get the best available PDF extractor.

    Priority:
    1. PyMuPDF (AGPL licensed)
    """
    if _HAS_PYMUPDF:
        return PyMuPDFExtractor()
    else:
        raise ImportError("No PDF extractor available. Install with:\n  uv add PyMuPDF")


__all__ = [
    "_HAS_LIGHTRAG",
    "_HAS_MARKER",
    # Availability flags
    "_HAS_PYMUPDF",
    "FileJobStore",
    "FileStorage",
    "InMemoryJobStore",
    "JobStoreInterface",
    "LightRAGAdapter",
    "MarkerPDFExtractor",
    # PDF Extractors
    "PyMuPDFExtractor",
    "get_pdf_extractor",
    "settings",
]
