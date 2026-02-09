"""
Presentation Layer - Dependency Container (Composition Root)

集中管理所有基礎設施和應用服務的初始化。
將 DI 邏輯從 server.py 抽離，保持 Presentation Layer 乾淨。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.asset_service import AssetService
from src.application.document_service import DocumentService
from src.application.job_service import JobService
from src.application.knowledge_service import KnowledgeService
from src.application.section_service import SectionService
from src.infrastructure.config import settings
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.job_store import FileJobStore
from src.infrastructure.lightrag_adapter import LightRAGAdapter
from src.infrastructure.pdf_extractor import PyMuPDFExtractor

if TYPE_CHECKING:
    from src.infrastructure.marker_adapter import MarkerPDFExtractor

# ============================================================================
# Infrastructure
# ============================================================================

repository = FileStorage(settings.data_dir)
pdf_extractor = PyMuPDFExtractor()  # Lightweight, always available
marker_extractor: MarkerPDFExtractor | None = None  # Lazy-loaded
knowledge_graph = LightRAGAdapter() if settings.enable_lightrag else None
job_store = FileJobStore(settings.data_dir)

# ============================================================================
# Application Services
# ============================================================================

document_service = DocumentService(
    repository=repository,
    pdf_extractor=pdf_extractor,
    knowledge_graph=knowledge_graph,
    marker_extractor=marker_extractor,
)
asset_service = AssetService(repository=repository)
knowledge_service = KnowledgeService(knowledge_graph=knowledge_graph)
job_service = JobService(job_store=job_store, document_service=document_service)
section_service = SectionService(data_dir=settings.data_dir)


# ============================================================================
# Lazy Loaders
# ============================================================================


def get_marker_extractor() -> "MarkerPDFExtractor":
    """Lazy-load Marker extractor (heavy model initialization, ~1GB)."""
    global marker_extractor
    if marker_extractor is None:
        from src.infrastructure.marker_adapter import MarkerPDFExtractor

        marker_extractor = MarkerPDFExtractor()
    return marker_extractor
