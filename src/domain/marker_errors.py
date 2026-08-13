"""Marker backend error classification and operator guidance."""

from __future__ import annotations

MARKER_INSTALL_HINT = (
    "Marker backend is on a production security hold in packaged asset-aware-mcp "
    "because marker-pdf 1.10.2 pins Pillow<11 while the secure runtime "
    "requires Pillow>=12.2.0. Use the default PyMuPDF path with `use_marker=False` "
    "until upstream marker-pdf supports patched Pillow."
)
MINERU_INSTALL_HINT = (
    "MinerU backend is unavailable and the packaged [mineru] extra is on a "
    "security hold: MinerU 3.4.4 requires transformers<5 while current fixes "
    "require transformers>=5.5. Use ETL_ENGINE=docling, pymupdf4llm, or "
    "pymupdf. The adapter is retained only for isolated upstream evaluation."
)
MARKER_RESOURCE_HINT = (
    "Marker ran out of memory or was interrupted by the runtime. Retry with "
    "`extract_figures=False` and `marker_max_pages_per_chunk=1`, or use the "
    "default PyMuPDF path with `use_marker=False`. Marker's OCR stack can need "
    "substantial RAM/VRAM even for short OCR-heavy PDFs."
)


class MarkerBackendUnavailable(RuntimeError):
    """Raised when marker-pdf is not installed in the active runtime."""


def is_marker_backend_unavailable(error: BaseException) -> bool:
    """Return True when an exception chain points to a missing Marker backend."""
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, MarkerBackendUnavailable):
            return True
        if isinstance(current, ModuleNotFoundError):
            missing_name = getattr(current, "name", "") or str(current)
            if missing_name == "marker" or "No module named 'marker'" in str(current):
                return True
        current = current.__cause__ or current.__context__
    return False


def is_marker_resource_error(error: BaseException) -> bool:
    """Return True for catchable Marker memory / process-killed failures."""
    if isinstance(error, MemoryError):
        return True
    text = str(error).lower()
    resource_markers = (
        "out of memory",
        "cuda out of memory",
        "exit code 137",
        "exit status 137",
        "sigkill",
        "killed",
        "cannot allocate memory",
    )
    return any(marker in text for marker in resource_markers)


def format_marker_failure(error: BaseException) -> str:
    """Format Marker failures into concise, actionable operator guidance."""
    if is_marker_backend_unavailable(error):
        return f"{MARKER_INSTALL_HINT} Original error: {error!s}"
    if is_marker_resource_error(error):
        return f"{MARKER_RESOURCE_HINT} Original error: {error!s}"
    return f"Marker parsing failed: {error!s}"


def structured_engine_label(engine_name: str) -> str:
    """Return a stable user-facing label for a structured PDF engine."""
    normalized = engine_name.strip().lower().split(":", 1)[0]
    return {
        "docling": "Docling",
        "mineru": "MinerU",
        "marker": "Marker",
    }.get(normalized, normalized.replace("_", " ").title() or "Structured PDF")


def format_structured_failure(error: BaseException, engine_name: str) -> str:
    """Format a structured failure without misidentifying its engine."""
    normalized = engine_name.strip().lower().split(":", 1)[0]
    if normalized == "marker":
        return format_marker_failure(error)

    label = structured_engine_label(normalized)
    if isinstance(error, MarkerBackendUnavailable) or type(error).__name__.endswith(
        "BackendUnavailable"
    ):
        return f"{label} backend is unavailable: {error!s}"
    if is_marker_resource_error(error):
        return (
            f"{label} structured parsing exceeded available memory or was interrupted. "
            "Retry with fewer pages or figures disabled, or use the PyMuPDF backend. "
            f"Original error: {error!s}"
        )
    return f"{label} structured parsing failed: {error!s}"


def is_structured_backend_unavailable(error: BaseException) -> bool:
    """Recognize backend-unavailable errors across structured adapters."""
    current: BaseException | None = error
    while current is not None:
        if is_marker_backend_unavailable(current) or type(current).__name__.endswith(
            "BackendUnavailable"
        ):
            return True
        current = current.__cause__ or current.__context__
    return False
