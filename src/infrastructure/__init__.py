# Infrastructure Layer - External Dependencies

from .config import settings
from .file_storage import FileStorage
from .job_store import FileJobStore, InMemoryJobStore, JobStoreInterface
from .lightrag_adapter import LightRAGAdapter

try:
    from .pdf_extractor import PyMuPDFExtractor

    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False
    PyMuPDFExtractor = None  # type: ignore


def get_pdf_extractor() -> PyMuPDFExtractor:
    """
    Get the best available PDF extractor.

    Priority:
    1. PyMuPDF (AGPL licensed)
    """
    if _HAS_PYMUPDF:
        return PyMuPDFExtractor()
    else:
        raise ImportError(
            "No PDF extractor available. Install with:\n"
            "  uv add PyMuPDF"
        )


__all__ = [
    "settings",
    "FileStorage",
    "FileJobStore",
    "InMemoryJobStore",
    "JobStoreInterface",
    "LightRAGAdapter",
    # PDF Extractors
    "PyMuPDFExtractor",
    "get_pdf_extractor",
    # Availability flags
    "_HAS_PYMUPDF",
]
