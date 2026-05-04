"""Marker backend error classification and operator guidance."""

from __future__ import annotations

MARKER_INSTALL_HINT = (
    "Marker backend is not installed in the Python environment running this MCP "
    "server. Install it with `uv sync --extra marker` (or `uv sync --extra pdf` "
    "for the compatibility extra), enable the Marker backend in the VS Code "
    "extension, and confirm the MCP server is launched from the asset-aware-mcp "
    "virtual environment."
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
