# Infrastructure Layer - External Dependencies

from .config import settings
from .file_storage import FileStorage
from .job_store import FileJobStore, InMemoryJobStore, JobStoreInterface
from .lightrag_adapter import LightRAGAdapter

# PDF Extractors - Docling preferred (MIT), PyMuPDF fallback (AGPL)
try:
    from .docling_adapter import DoclingAdapter, DoclingConfig, get_docling_adapter

    _HAS_DOCLING = True
except ImportError:
    _HAS_DOCLING = False
    DoclingAdapter = None  # type: ignore
    DoclingConfig = None  # type: ignore
    get_docling_adapter = None  # type: ignore

try:
    from .pdf_extractor import PyMuPDFExtractor

    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False
    PyMuPDFExtractor = None  # type: ignore


def get_pdf_extractor():
    """
    Get the best available PDF extractor.

    Priority:
    1. Docling (MIT licensed, high quality)
    2. PyMuPDF (AGPL licensed, fallback)
    """
    if _HAS_DOCLING:
        return get_docling_adapter()
    elif _HAS_PYMUPDF:
        return PyMuPDFExtractor()
    else:
        raise ImportError(
            "No PDF extractor available. Install with:\n"
            "  uv add docling       # Recommended (MIT)\n"
            "  uv add PyMuPDF       # Fallback (AGPL)"
        )


__all__ = [
    "settings",
    "FileStorage",
    "FileJobStore",
    "InMemoryJobStore",
    "JobStoreInterface",
    "LightRAGAdapter",
    # PDF Extractors
    "DoclingAdapter",
    "DoclingConfig",
    "get_docling_adapter",
    "PyMuPDFExtractor",
    "get_pdf_extractor",
    # Availability flags
    "_HAS_DOCLING",
    "_HAS_PYMUPDF",
]
