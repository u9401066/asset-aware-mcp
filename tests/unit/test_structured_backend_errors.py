"""Regression tests for actionable structured-backend failures."""

from collections.abc import Iterator

import pytest

from src.domain.etl_profile import ETLProfile
from src.domain.marker_errors import (
    MarkerBackendUnavailable,
    format_structured_failure,
)
from src.infrastructure.extractor_factory import build_structured_extractor
from src.infrastructure.marker_adapter import MarkerPDFExtractor
from src.infrastructure.mineru_adapter import MinerUExtractor
from src.infrastructure.pdf_extractor import PyMuPDFExtractor
from src.presentation import dependencies


@pytest.fixture(autouse=True)
def _restore_structured_extractor() -> Iterator[None]:
    previous = dependencies.marker_extractor
    yield
    dependencies.marker_extractor = previous


def test_unavailable_mineru_reports_security_hold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies.settings, "etl_engine", "mineru")
    monkeypatch.setattr(dependencies, "marker_extractor", None)
    monkeypatch.setattr(
        dependencies, "build_structured_extractor", lambda _engine: None
    )

    with pytest.raises(MarkerBackendUnavailable, match="security hold") as exc_info:
        dependencies.get_marker_extractor()

    assert "transformers>=5.5" in str(exc_info.value)
    assert "asset-aware-mcp[mineru]" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("engine", "extractor_type", "expected"),
    [
        ("marker", MarkerPDFExtractor, "Pillow>=12.2.0"),
        ("mineru", MinerUExtractor, "transformers>=5.5"),
    ],
)
def test_factory_rejects_held_backend_even_when_package_is_available(
    monkeypatch: pytest.MonkeyPatch,
    engine: str,
    extractor_type: type,
    expected: str,
) -> None:
    monkeypatch.setattr(
        extractor_type,
        "require_backend_available",
        staticmethod(lambda: None),
    )

    with pytest.raises(MarkerBackendUnavailable, match="security hold") as exc_info:
        build_structured_extractor(engine)

    assert expected in str(exc_info.value)


@pytest.mark.parametrize("engine", ["marker", "mineru"])
def test_held_configuration_keeps_base_composition_available_without_probe(
    monkeypatch: pytest.MonkeyPatch,
    engine: str,
) -> None:
    factory_called = False

    def forbidden_factory(_engine: str | None) -> None:
        nonlocal factory_called
        factory_called = True
        raise AssertionError("held backend factory must not run during startup")

    monkeypatch.setattr(
        dependencies,
        "build_structured_extractor",
        forbidden_factory,
    )

    base = dependencies.build_base_extractor(engine, ETLProfile.default())
    structured = dependencies._build_startup_structured_extractor(engine)

    assert isinstance(base, PyMuPDFExtractor)
    assert structured is None
    assert factory_called is False


def test_legacy_marker_request_never_probes_manually_installed_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_probe_called = False

    def backend_probe() -> None:
        nonlocal backend_probe_called
        backend_probe_called = True

    monkeypatch.setattr(dependencies.settings, "etl_engine", "pymupdf")
    monkeypatch.setattr(dependencies, "marker_extractor", None)
    monkeypatch.setattr(
        MarkerPDFExtractor,
        "require_backend_available",
        staticmethod(backend_probe),
    )

    with pytest.raises(MarkerBackendUnavailable, match="security hold"):
        dependencies.get_marker_extractor()

    assert backend_probe_called is False


def test_unavailable_docling_does_not_report_marker_pillow_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies.settings, "etl_engine", "docling")
    monkeypatch.setattr(dependencies, "marker_extractor", None)
    monkeypatch.setattr(
        dependencies, "build_structured_extractor", lambda _engine: None
    )

    with pytest.raises(
        MarkerBackendUnavailable, match="Docling is selected"
    ) as exc_info:
        dependencies.get_marker_extractor()

    assert "Pillow" not in str(exc_info.value)
    assert "ETL_ENGINE=pymupdf4llm/pymupdf" in str(exc_info.value)


def test_docling_failure_is_not_misreported_as_marker() -> None:
    message = format_structured_failure(
        RuntimeError("worker exited with status 7"),
        "docling",
    )

    assert message == ("Docling structured parsing failed: worker exited with status 7")
    assert "Marker" not in message
    assert "Pillow" not in message


def test_real_marker_resource_failure_keeps_marker_guidance() -> None:
    message = format_structured_failure(
        RuntimeError("CUDA out of memory"),
        "marker",
    )

    assert "Marker ran out of memory" in message
    assert "marker_max_pages_per_chunk=1" in message
