"""
Presentation Layer - Dependency Container (Composition Root)

集中管理所有基礎設施和應用服務的初始化。
將 DI 邏輯從 server.py 抽離，保持 Presentation Layer 乾淨。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.asset_service import AssetService
from src.application.dfm_table_bridge import DfmTableBridge
from src.application.document_service import DocumentService
from src.application.docx_service import DocxService
from src.application.job_service import JobService
from src.application.knowledge_service import KnowledgeService
from src.application.section_service import SectionService
from src.application.table_service import TableService
from src.domain.etl_profile import ETLProfile
from src.infrastructure.config import settings
from src.infrastructure.excel_renderer import ExcelRenderer
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.job_store import FileJobStore
from src.infrastructure.lightrag_adapter import LightRAGAdapter
from src.infrastructure.pdf_extractor import PyMuPDFExtractor

if TYPE_CHECKING:
    from src.infrastructure.marker_adapter import MarkerPDFExtractor

# ============================================================================
# Infrastructure
# ============================================================================

# Load ETL profile from environment/settings
try:
    from src.domain.etl_profile import ETLProfileRegistry

    etl_profile = ETLProfileRegistry.get(settings.etl_profile)
except KeyError:
    # Fallback to default if configured profile not found
    etl_profile = ETLProfile.default()

repository = FileStorage(settings.data_dir)
pdf_extractor = PyMuPDFExtractor(profile=etl_profile)  # Lightweight, always available
marker_extractor: MarkerPDFExtractor | None = None  # Lazy-loaded
knowledge_graph = LightRAGAdapter() if settings.enable_lightrag else None
job_store = FileJobStore(settings.data_dir)
excel_renderer = ExcelRenderer(settings.table_output_dir)

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
table_service = TableService(
    table_output_dir=settings.table_output_dir,
    table_renderer=excel_renderer,
)
docx_service = DocxService(repository=repository)
dfm_table_bridge = DfmTableBridge()

# Docx round-trip validator
from src.infrastructure.docx_validator import DocxValidator  # noqa: E402

docx_validator = DocxValidator()


# ============================================================================
# Lazy Loaders
# ============================================================================


def get_marker_extractor() -> MarkerPDFExtractor:
    """Lazy-load Marker extractor (heavy model initialization, ~1GB)."""
    global marker_extractor
    if marker_extractor is None:
        from src.infrastructure.marker_adapter import MarkerPDFExtractor

        marker_extractor = MarkerPDFExtractor()
    return marker_extractor


# ============================================================================
# Profile Switching
# ============================================================================


def rebuild_for_profile(profile_name: str) -> ETLProfile:
    """
    Switch the active ETL profile and rebuild dependent services.

    This encapsulates the state mutation logic so that presentation-layer
    tools don't need to know about service construction details.

    Args:
        profile_name: Profile name to switch to

    Returns:
        The new active ETLProfile

    Raises:
        KeyError: If profile not found
    """
    global etl_profile, pdf_extractor, document_service

    new_profile = ETLProfileRegistry.get(profile_name)

    # Update shared profile and recreate dependent services
    etl_profile = new_profile
    pdf_extractor = PyMuPDFExtractor(profile=new_profile)

    # Recreate document service with new extractor
    document_service = DocumentService(
        repository=repository,
        pdf_extractor=pdf_extractor,
        knowledge_graph=knowledge_graph,
        marker_extractor=marker_extractor,
        profile=new_profile,
    )

    return new_profile
