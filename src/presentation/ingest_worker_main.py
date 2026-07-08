"""Presentation composition root for the isolated ingest worker process."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from src.application.ingest_worker import build_parser, run_worker


@dataclass
class _WorkerDependencies:
    document_service: Any
    marker_extractor_factory: Any


def _resolve_worker_profile(profile_name: str = "") -> Any:
    from src.domain.etl_profile import ETLProfile, ETLProfileRegistry
    from src.infrastructure.config import settings

    try:
        if profile_name:
            return ETLProfileRegistry.get(profile_name)
        if settings.etl_profile_json:
            return ETLProfileRegistry.load_from_json(settings.etl_profile_json)
        return ETLProfileRegistry.get(settings.etl_profile)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return ETLProfile.default()


def _build_worker_dependencies(profile_name: str = "") -> _WorkerDependencies:
    """Build only the dependencies needed by isolated PDF ingest workers."""
    from src.application.document_service import DocumentService
    from src.infrastructure.config import settings
    from src.infrastructure.extractor_factory import (
        build_base_extractor,
        build_structured_extractor,
    )
    from src.infrastructure.file_storage import FileStorage
    from src.infrastructure.ocr_processor import OCRProcessor

    profile = _resolve_worker_profile(profile_name)
    repository = FileStorage(settings.data_dir)
    pdf_extractor = build_base_extractor(settings.etl_engine, profile)
    document_service = DocumentService(
        repository=repository,
        pdf_extractor=pdf_extractor,
        knowledge_graph=None,
        marker_extractor=None,
        ocr_processor=OCRProcessor(),
    )

    def marker_extractor_factory() -> Any:
        """Build the configured structured engine on demand inside the worker."""
        engine = (settings.etl_engine or "").lower()
        target = engine if engine in {"docling", "mineru", "marker"} else "marker"
        built = build_structured_extractor(target)
        if built is not None:
            return built
        # Surface an informative backend-unavailable error for the legacy path.
        from src.infrastructure.marker_adapter import MarkerPDFExtractor

        MarkerPDFExtractor.require_backend_available()
        return MarkerPDFExtractor()

    return _WorkerDependencies(
        document_service=document_service,
        marker_extractor_factory=marker_extractor_factory,
    )


async def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dependencies = _build_worker_dependencies(args.etl_profile)
    return await run_worker(
        args,
        document_service=dependencies.document_service,
        marker_extractor_factory=dependencies.marker_extractor_factory,
    )


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
