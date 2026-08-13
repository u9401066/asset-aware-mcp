"""
Presentation Layer - Dependency Container (Composition Root)

集中管理所有基礎設施和應用服務的初始化。
將 DI 邏輯從 server.py 抽離，保持 Presentation Layer 乾淨。
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from src.application.asset_service import AssetService
from src.application.dfm_table_bridge import DfmTableBridge
from src.application.document_service import DocumentService
from src.application.docx_service import DocxService
from src.application.job_service import JobService
from src.application.knowledge_service import KnowledgeService
from src.application.pdf_preflight_service import PDFPreflightService
from src.application.pdf_report_service import PdfArtifactReportService
from src.application.section_service import SectionService
from src.application.segmentation_service import SegmentationService
from src.application.structural_pointer_service import StructuralPointerService
from src.application.table_service import TableService
from src.domain.etl_profile import ETLProfile
from src.domain.marker_errors import MARKER_INSTALL_HINT, MarkerBackendUnavailable
from src.infrastructure.config import settings
from src.infrastructure.excel_renderer import ExcelRenderer
from src.infrastructure.extractor_factory import (
    HELD_STRUCTURED_ENGINES,
    build_base_extractor,
    build_structured_extractor,
    held_structured_backend_error,
)
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.job_store import FileJobStore
from src.infrastructure.layout_visualizer import LayoutVisualizer
from src.infrastructure.ocr_processor import OCRProcessor
from src.infrastructure.pymupdf_preflight import PyMuPDFPreflightInspector
from src.infrastructure.subprocess_ingest_worker_runner import (
    SubprocessIngestWorkerRunner,
)

if TYPE_CHECKING:
    from src.domain.repositories import KnowledgeGraphInterface
    from src.infrastructure.structured_extractor import StructuredPDFExtractor

logger = logging.getLogger(__name__)


def _build_knowledge_graph() -> KnowledgeGraphInterface | None:
    """Build the optional knowledge graph backend only when enabled."""
    if not settings.enable_lightrag:
        return None

    try:
        from src.infrastructure.lightrag_adapter import LightRAGAdapter
    except ImportError as exc:
        raise RuntimeError(
            "LightRAG is enabled, but the LightRAG backend is not installed. "
            "Install the optional extra via "
            "`uv tool install --upgrade 'asset-aware-mcp[lightrag]'` "
            "(or run the VS Code command 'Asset-Aware MCP: Install LightRAG Backend'), "
            "or set ENABLE_LIGHTRAG=false."
        ) from exc

    return LightRAGAdapter()


def _build_startup_structured_extractor(
    engine: str | None,
) -> StructuredPDFExtractor | None:
    """Compose an active backend without making held config break startup.

    Diagnostics and the base PyMuPDF pipeline must remain available when an old
    environment still selects Marker or MinerU. A real structured request is
    rejected later by :func:`get_marker_extractor` with the canonical hold error.
    """
    normalized = (engine or "").lower()
    if normalized in HELD_STRUCTURED_ENGINES:
        logger.warning(
            "ETL_ENGINE=%s is on a production security hold; starting with the "
            "base PDF extractor only",
            normalized,
        )
        return None
    return build_structured_extractor(normalized)


# ============================================================================
# Infrastructure
# ============================================================================

# Load ETL profile from environment/settings
try:
    from src.domain.etl_profile import ETLProfileRegistry

    if settings.etl_profile_json:
        etl_profile = ETLProfileRegistry.load_from_json(settings.etl_profile_json)
    else:
        etl_profile = ETLProfileRegistry.get(settings.etl_profile)
except (FileNotFoundError, KeyError, json.JSONDecodeError):
    # Fallback to default if configured profile cannot be loaded
    etl_profile = ETLProfile.default()

repository = FileStorage(settings.data_dir)
# Engine selection (config-driven via ETL_ENGINE): the base extractor is always
# available (PyMuPDF, or the layout-aware pymupdf4llm) and doubles as the fast
# fallback. Docling is the only active structured engine. Held Marker/MinerU
# configuration starts with no structured extractor so diagnostics and the base
# server remain available; an actual structured request fails closed later.
pdf_extractor = build_base_extractor(settings.etl_engine, etl_profile)
marker_extractor = _build_startup_structured_extractor(settings.etl_engine)
knowledge_graph = _build_knowledge_graph()
job_store = FileJobStore(settings.data_dir)
excel_renderer = ExcelRenderer(settings.table_output_dir)
layout_visualizer = LayoutVisualizer()
ocr_processor = OCRProcessor()
ingest_worker_runner = SubprocessIngestWorkerRunner(job_store=job_store)

# ============================================================================
# Application Services
# ============================================================================

document_service = DocumentService(
    repository=repository,
    pdf_extractor=pdf_extractor,
    knowledge_graph=knowledge_graph,
    marker_extractor=marker_extractor,
    structured_engine_name=settings.etl_engine,
    ocr_processor=ocr_processor,
)
asset_service = AssetService(repository=repository)
knowledge_service = KnowledgeService(knowledge_graph=knowledge_graph)
job_service = JobService(
    job_store=job_store,
    document_service=document_service,
    ingest_worker_runner=ingest_worker_runner,
)
pdf_report_service = PdfArtifactReportService(
    repository=repository,
    pdf_extractor=pdf_extractor,
)
pdf_preflight_service = PDFPreflightService(
    inspector=PyMuPDFPreflightInspector(),
)
segmentation_service = SegmentationService(repository=repository)
section_service = SectionService(repository=repository)
structural_pointer_service = StructuralPointerService(
    repository=repository,
    segmentation_service=segmentation_service,
)
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


def get_marker_extractor() -> StructuredPDFExtractor:
    """Lazy-load the configured active structured extractor (Docling only).

    Marker and MinerU are production security holds even when manually installed.
    A legacy ``use_marker`` request on a base engine therefore reports the hold
    instead of probing or constructing ``MarkerPDFExtractor``.
    """
    global marker_extractor
    if marker_extractor is None:
        engine = (settings.etl_engine or "").lower()
        if engine in HELD_STRUCTURED_ENGINES:
            raise held_structured_backend_error(engine)
        if engine != "docling":
            raise MarkerBackendUnavailable(MARKER_INSTALL_HINT)
        marker_extractor = build_structured_extractor(engine)
    if marker_extractor is None:
        # Active backend unavailable; do not disguise it as the Marker hold.
        raise MarkerBackendUnavailable(
            "Docling is selected but unavailable. Install the maintained "
            "[docling] extra or isolated .venv-docling runtime, or set "
            "ETL_ENGINE=pymupdf4llm/pymupdf."
        )
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
    global etl_profile, pdf_extractor, document_service, job_service, pdf_report_service

    new_profile = ETLProfileRegistry.get(profile_name)

    # Update shared profile and recreate dependent services
    etl_profile = new_profile
    pdf_extractor = build_base_extractor(settings.etl_engine, new_profile)

    # Recreate document service with new extractor
    document_service = DocumentService(
        repository=repository,
        pdf_extractor=pdf_extractor,
        knowledge_graph=knowledge_graph,
        marker_extractor=marker_extractor,
        structured_engine_name=settings.etl_engine,
        profile=new_profile,
        ocr_processor=ocr_processor,
    )
    job_service.set_document_service(document_service)
    pdf_report_service = PdfArtifactReportService(
        repository=repository,
        pdf_extractor=pdf_extractor,
    )

    return new_profile
