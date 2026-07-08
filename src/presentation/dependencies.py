"""
Presentation Layer - Dependency Container (Composition Root)

集中管理所有基礎設施和應用服務的初始化。
將 DI 邏輯從 server.py 抽離，保持 Presentation Layer 乾淨。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.application.asset_service import AssetService
from src.application.dfm_table_bridge import DfmTableBridge
from src.application.document_service import DocumentService
from src.application.docx_service import DocxService
from src.application.job_service import JobService
from src.application.knowledge_service import KnowledgeService
from src.application.pdf_report_service import PdfArtifactReportService
from src.application.section_service import SectionService
from src.application.segmentation_service import SegmentationService
from src.application.structural_pointer_service import StructuralPointerService
from src.application.table_service import TableService
from src.domain.etl_profile import ETLProfile
from src.domain.marker_errors import MarkerBackendUnavailable
from src.infrastructure.config import settings
from src.infrastructure.excel_renderer import ExcelRenderer
from src.infrastructure.extractor_factory import (
    build_base_extractor,
    build_structured_extractor,
)
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.job_store import FileJobStore
from src.infrastructure.layout_visualizer import LayoutVisualizer
from src.infrastructure.ocr_processor import OCRProcessor
from src.infrastructure.subprocess_ingest_worker_runner import (
    SubprocessIngestWorkerRunner,
)

if TYPE_CHECKING:
    from src.domain.repositories import KnowledgeGraphInterface
    from src.infrastructure.structured_extractor import StructuredPDFExtractor


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
# fallback; the structured extractor is the optional high-fidelity engine
# (docling / mineru / marker) injected into the marker_extractor slot, or None
# when base-only or the backend is not installed.
pdf_extractor = build_base_extractor(settings.etl_engine, etl_profile)
marker_extractor = build_structured_extractor(settings.etl_engine)
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
    """Lazy-load the configured structured extractor (docling/mineru/marker).

    Heavy backends (ML models or a CLI) initialise on first use. When no
    structured engine is configured, falls back to the legacy Marker engine so
    the historical ``use_marker`` behaviour (and its informative Pillow<11
    error) is preserved.
    """
    global marker_extractor
    if marker_extractor is None:
        engine = (settings.etl_engine or "").lower()
        target = engine if engine in {"docling", "mineru", "marker"} else "marker"
        marker_extractor = build_structured_extractor(target)
    if marker_extractor is None:
        # Selected/legacy backend unavailable; surface a clear, actionable error.
        from src.infrastructure.marker_adapter import MarkerPDFExtractor

        MarkerPDFExtractor.require_backend_available()
        raise MarkerBackendUnavailable(
            "No structured PDF engine is available. Set ETL_ENGINE=docling or "
            "ETL_ENGINE=mineru and install the matching optional extra."
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
        profile=new_profile,
        ocr_processor=ocr_processor,
    )
    job_service.set_document_service(document_service)
    pdf_report_service = PdfArtifactReportService(
        repository=repository,
        pdf_extractor=pdf_extractor,
    )

    return new_profile
