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
    structured_engine_name: str


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
        HELD_STRUCTURED_ENGINES,
        build_base_extractor,
        build_structured_extractor,
        held_structured_backend_error,
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
        structured_engine_name=settings.etl_engine,
    )

    def marker_extractor_factory() -> Any:
        """Build the configured structured engine on demand inside the worker."""
        from src.domain.marker_errors import (
            MARKER_INSTALL_HINT,
            MarkerBackendUnavailable,
        )

        engine = (settings.etl_engine or "").lower()
        if engine in HELD_STRUCTURED_ENGINES:
            raise held_structured_backend_error(engine)
        if engine != "docling":
            raise MarkerBackendUnavailable(MARKER_INSTALL_HINT)
        built = build_structured_extractor(engine)
        if built is not None:
            return built
        raise MarkerBackendUnavailable(
            "Docling is selected but unavailable. Install the maintained "
            "[docling] extra or isolated .venv-docling runtime, or set "
            "ETL_ENGINE=pymupdf4llm/pymupdf."
        )

    return _WorkerDependencies(
        document_service=document_service,
        marker_extractor_factory=marker_extractor_factory,
        structured_engine_name=document_service.structured_engine_name,
    )


async def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dependencies = _build_worker_dependencies(args.etl_profile)
    return await run_worker(
        args,
        document_service=dependencies.document_service,
        marker_extractor_factory=dependencies.marker_extractor_factory,
        structured_engine_name=dependencies.structured_engine_name,
    )


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
