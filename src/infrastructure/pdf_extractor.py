"""
Infrastructure Layer - PDF Extractor

Implementation using PyMuPDF (fitz) for PDF processing.
Key feature: Extracts images WITH page numbers for verification.
"""

from __future__ import annotations

import logging
import math
import multiprocessing
import os
import re
import shutil
import signal
import stat
import struct
import subprocess
import tempfile
import threading
import time
from collections import Counter
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import msgpack
import pymupdf as fitz  # type: ignore[import-untyped]

from src.domain.etl_profile import ETLProfile
from src.domain.repositories import PDFExtractorInterface

from .config import settings

logger = logging.getLogger(__name__)
DEFAULT_TABLE_TIMEOUT_SECONDS = 4.0
DEFAULT_TABLE_DOCUMENT_TIMEOUT_SECONDS = 25.0
DEFAULT_TEXT_DOCUMENT_TIMEOUT_SECONDS = 30.0
DEFAULT_IMAGE_DOCUMENT_TIMEOUT_SECONDS = 25.0
DEFAULT_FAST_IMAGE_DOCUMENT_TIMEOUT_SECONDS = 90.0
DEFAULT_CAPTION_DOCUMENT_TIMEOUT_SECONDS = 20.0
DEFAULT_IMAGE_STRATEGY_TIMEOUT_SECONDS = 3.0
DEFAULT_SAFETY_AUDIT_DOCUMENT_TIMEOUT_SECONDS = 20.0
DEFAULT_NATIVE_STRUCTURE_DOCUMENT_TIMEOUT_SECONDS = 10.0
DEFAULT_FIGURE_CROP_X_PADDING = 12.0
DEFAULT_FIGURE_CROP_TOP_PADDING = 18.0
DEFAULT_FIGURE_CROP_BOTTOM_PADDING = 72.0
DEFAULT_FIGURE_CROP_ZOOM = 2.0
PDF_AI_SAFETY_REPORT_VERSION = "pdf-ai-safety-v1"
PDF_NATIVE_STRUCTURE_REPORT_VERSION = "pdf-native-structure-v1"
PDF_AUDIT_MAX_ISSUES_ENV = "ASSET_AWARE_PDF_AUDIT_MAX_ISSUES"
PDF_AUDIT_MAX_PAGES_ENV = "ASSET_AWARE_PDF_AUDIT_MAX_PAGES"
PDF_STRUCTURE_MAX_PAGES_ENV = "ASSET_AWARE_PDF_STRUCTURE_MAX_PAGES"
DEFAULT_PDF_AUDIT_MAX_ISSUES = 200
DEFAULT_PDF_AUDIT_MAX_PAGES = 200
DEFAULT_PDF_STRUCTURE_MAX_PAGES = 500
PDF_WORKER_RESULT_POLL_SECONDS = 0.05
PDF_WORKER_TERMINATE_GRACE_SECONDS = 1.0
PDF_WORKER_KILL_GRACE_SECONDS = 1.0
DEFAULT_PDF_WORKER_RESULT_MAX_MIB = 512.0
MIN_PDF_WORKER_RESULT_MAX_MIB = 1.0
MAX_PDF_WORKER_RESULT_MAX_MIB = 512.0
MAX_PDF_WORKER_RESULT_CONTAINER_ITEMS = 1_000_000
MAX_PDF_WORKER_RESULT_NESTING = 100
PDF_WORKER_RESULT_ENVELOPE_VERSION = 1
PDF_WORKER_RESULT_READ_MIB_PER_SECOND = 16.0
PDF_WORKER_RESULT_MIN_READ_BUDGET_SECONDS = 0.01
_SUSPICIOUS_AI_INSTRUCTION_RE = re.compile(
    r"("
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions"
    r"|disregard\s+(all\s+)?(previous|prior|above)\s+instructions"
    r"|reveal\s+(the\s+)?system\s+prompt"
    r"|system\s+prompt"
    r"|prompt\s+injection"
    r"|developer\s+message"
    r"|忽略(以上|先前|前面).{0,8}(指令|指示)"
    r"|透露.{0,8}系統提示"
    r")",
    re.IGNORECASE,
)


def _extract_tables_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run PyMuPDF table extraction in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        tables = extractor._extract_tables_direct(Path(pdf_path_str))
        result_sink.put(("ok", tables))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _extract_text_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run rich PyMuPDF text extraction in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        markdown = extractor._extract_text_direct(Path(pdf_path_str))
        result_sink.put(("ok", markdown))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _extract_text_fast_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run the lightweight text fallback inside the same process boundary."""
    try:
        extractor = PyMuPDFExtractor()
        markdown = extractor._extract_text_fast(Path(pdf_path_str))
        result_sink.put(("ok", markdown))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _extract_images_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run PyMuPDF image extraction in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        images = extractor._extract_images_direct(Path(pdf_path_str))
        result_sink.put(("ok", images))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _extract_images_fast_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run fast PyMuPDF image fallback in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        images = extractor._extract_images_fast(Path(pdf_path_str))
        result_sink.put(("ok", images))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _extract_figure_captions_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run PyMuPDF figure caption extraction in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        captions = extractor._extract_figure_captions_direct(Path(pdf_path_str))
        result_sink.put(("ok", captions))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _audit_ai_safety_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run PDF AI safety audit in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        report = extractor._audit_ai_safety_direct(Path(pdf_path_str))
        result_sink.put(("ok", report))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _extract_native_structure_worker(pdf_path_str: str, result_sink: Any) -> None:
    """Run native PDF structure extraction in a child process."""
    try:
        extractor = PyMuPDFExtractor()
        report = extractor._extract_native_structure_direct(Path(pdf_path_str))
        result_sink.put(("ok", report))
    except Exception as exc:  # pragma: no cover - worker isolation path
        result_sink.put(("error", str(exc)))


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _env_timeout_seconds(name: str, default: float) -> float:
    """Read a finite PDF timeout while preserving the legacy direct-mode opt-out.

    Non-numeric and non-finite values cannot provide a real wall-clock bound,
    so they fail safely to the finite positive default. Existing finite values
    less than or equal to zero remain an explicit compatibility opt-out; each
    public extraction method handles that value before starting a worker.
    """
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        timeout_seconds = float(raw_value)
    except ValueError:
        return default
    if not math.isfinite(timeout_seconds):
        logger.warning(
            "Ignoring non-finite PDF timeout in %s; using %.1fs",
            name,
            default,
        )
        return default
    return timeout_seconds


def _env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return max(0, int(raw_value))
    except ValueError:
        return default


def _get_pdf_worker_context() -> Any:
    """Prefer fork isolation when available, otherwise use spawn for portability."""
    try:
        return multiprocessing.get_context("fork")
    except (RuntimeError, ValueError):
        return multiprocessing.get_context("spawn")


@dataclass(frozen=True)
class _PDFWorkerResult:
    """Outcome from a process-isolated PDF worker."""

    status: str | None = None
    payload: Any = None
    timed_out: bool = False
    failure: str | None = None


class _SizeLimitedResultWriter:
    """Binary writer that rejects oversized aggregate worker results."""

    def __init__(self, raw_file: Any, max_bytes: int) -> None:
        self._raw_file = raw_file
        self._max_bytes = max_bytes
        self._bytes_written = 0

    def write(self, data: bytes | bytearray | memoryview) -> int:
        next_size = self._bytes_written + len(data)
        if next_size > self._max_bytes:
            raise ValueError(
                f"PDF worker result exceeds the configured {self._max_bytes}-byte limit"
            )
        written = int(self._raw_file.write(data))
        if written != len(data):
            raise OSError(
                f"short PDF worker result write: expected {len(data)}, wrote {written}"
            )
        self._bytes_written += written
        return written


class _MessagePackResultEncoder:
    """Stream supported PDF result values without building one giant frame."""

    def __init__(self, writer: _SizeLimitedResultWriter) -> None:
        self._writer = writer
        self._packer = msgpack.Packer(use_bin_type=True, strict_types=True)
        self._active_containers: set[int] = set()

    def pack(self, value: Any) -> None:
        """Encode JSON-like values plus binary blobs and integer map keys."""
        self._pack_value(value, depth=0)

    def _pack_value(self, value: Any, *, depth: int) -> None:
        if depth > MAX_PDF_WORKER_RESULT_NESTING:
            raise ValueError("PDF worker result exceeds the MessagePack nesting limit")

        if value is None or type(value) in {bool, int, float, str}:
            self._writer.write(self._packer.pack(value))
            return

        if isinstance(value, bytes):
            self._write_binary(value)
            return

        if isinstance(value, (list, tuple)):
            self._pack_container(value, depth=depth, is_map=False)
            return

        if isinstance(value, dict):
            self._pack_container(value, depth=depth, is_map=True)
            return

        raise TypeError(
            f"unsupported PDF worker MessagePack value: {type(value).__name__}"
        )

    def _pack_container(
        self,
        value: list[Any] | tuple[Any, ...] | dict[Any, Any],
        *,
        depth: int,
        is_map: bool,
    ) -> None:
        container_id = id(value)
        if container_id in self._active_containers:
            raise ValueError("PDF worker result contains a recursive container")
        if len(value) > MAX_PDF_WORKER_RESULT_CONTAINER_ITEMS:
            raise ValueError(
                "PDF worker result exceeds the MessagePack container item limit"
            )

        self._active_containers.add(container_id)
        try:
            if is_map:
                assert isinstance(value, dict)
                self._writer.write(self._packer.pack_map_header(len(value)))
                for key, item in value.items():
                    if type(key) not in {str, int}:
                        raise TypeError(
                            "PDF worker MessagePack map keys must be strings or integers"
                        )
                    self._pack_value(key, depth=depth + 1)
                    self._pack_value(item, depth=depth + 1)
            else:
                assert isinstance(value, (list, tuple))
                self._writer.write(self._packer.pack_array_header(len(value)))
                for item in value:
                    self._pack_value(item, depth=depth + 1)
        finally:
            self._active_containers.remove(container_id)

    def _write_binary(self, value: bytes) -> None:
        length = len(value)
        if length <= 0xFF:
            header = b"\xc4" + struct.pack(">B", length)
        elif length <= 0xFFFF:
            header = b"\xc5" + struct.pack(">H", length)
        elif length <= 0xFFFFFFFF:
            header = b"\xc6" + struct.pack(">I", length)
        else:
            raise ValueError("PDF worker binary value is too large for MessagePack")
        self._writer.write(header)
        self._writer.write(value)


@dataclass(frozen=True)
class _AtomicPDFWorkerResultSink:
    """Publish one safely encoded child result in a private directory."""

    result_path: str
    max_bytes: int

    def _partial_path(self) -> Path:
        return Path(f"{self.result_path}.{os.getpid()}.partial")

    def put(self, result: tuple[str, Any]) -> None:
        """MessagePack one result to a partial file, then atomically publish it."""
        if (
            not isinstance(result, tuple)
            or len(result) != 2
            or result[0] not in {"ok", "error"}
        ):
            raise ValueError("PDF worker result has an invalid envelope")
        envelope = {
            "version": PDF_WORKER_RESULT_ENVELOPE_VERSION,
            "status": result[0],
            "payload": result[1],
        }
        partial_path = self._partial_path()
        try:
            descriptor = os.open(
                partial_path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            with os.fdopen(descriptor, "wb") as raw_file:
                writer = _SizeLimitedResultWriter(raw_file, self.max_bytes)
                _MessagePackResultEncoder(writer).pack(envelope)
                raw_file.flush()
                os.fsync(raw_file.fileno())
            partial_path.replace(self.result_path)
        finally:
            # The parent removes the entire private directory after reaping the
            # child, including a partial file left by an OOM or kill.
            with suppress(OSError):
                partial_path.unlink(missing_ok=True)


def _pdf_worker_result_max_bytes() -> int:
    """Return a bounded file-result limit configured in MiB."""
    raw_value = os.environ.get(
        "PYMUPDF_WORKER_RESULT_MAX_MIB",
        str(DEFAULT_PDF_WORKER_RESULT_MAX_MIB),
    )
    try:
        configured_mib = float(raw_value)
    except ValueError:
        configured_mib = DEFAULT_PDF_WORKER_RESULT_MAX_MIB
    if not math.isfinite(configured_mib) or configured_mib <= 0:
        configured_mib = DEFAULT_PDF_WORKER_RESULT_MAX_MIB
    bounded_mib = max(
        MIN_PDF_WORKER_RESULT_MAX_MIB,
        min(configured_mib, MAX_PDF_WORKER_RESULT_MAX_MIB),
    )
    return int(bounded_mib * 1024 * 1024)


def _reject_pdf_worker_ext(code: int, data: bytes) -> Any:
    """Reject extension values; PDF worker results need no custom types."""
    raise ValueError(
        f"PDF worker result contains unsupported MessagePack extension {code}"
    )


def _strict_pdf_worker_map(pairs: list[tuple[Any, Any]]) -> dict[Any, Any]:
    """Build a map while rejecting duplicate and unsupported key types."""
    result: dict[Any, Any] = {}
    for key, value in pairs:
        if type(key) not in {str, int}:
            raise ValueError(
                "PDF worker result contains an unsupported MessagePack map key"
            )
        if key in result:
            raise ValueError("PDF worker result contains a duplicate map key")
        result[key] = value
    return result


def _validate_pdf_worker_result_value(decoded: Any) -> None:
    """Reject decoded types or nesting that the worker encoder cannot emit."""
    pending: list[tuple[Any, int]] = [(decoded, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_PDF_WORKER_RESULT_NESTING:
            raise ValueError("PDF worker result exceeds the MessagePack nesting limit")
        if value is None or type(value) in {bool, int, float, str, bytes}:
            continue
        if isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
            continue
        if isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
            continue
        raise ValueError(
            f"PDF worker result contains unsupported decoded type: "
            f"{type(value).__name__}"
        )


def _decode_pdf_worker_result_stream(
    result_file: Any,
    *,
    max_bytes: int,
    expected_size: int,
) -> Any:
    """Decode exactly one bounded MessagePack value from a file stream."""
    max_container_items = min(max_bytes, MAX_PDF_WORKER_RESULT_CONTAINER_ITEMS)
    unpacker = msgpack.Unpacker(
        result_file,
        raw=False,
        use_list=True,
        strict_map_key=False,
        unicode_errors="strict",
        max_buffer_size=max_bytes,
        max_str_len=max_bytes,
        max_bin_len=max_bytes,
        max_array_len=max_container_items,
        max_map_len=max_container_items,
        max_ext_len=0,
        ext_hook=_reject_pdf_worker_ext,
        object_pairs_hook=_strict_pdf_worker_map,
    )
    decoded = unpacker.unpack()
    if unpacker.tell() != expected_size:
        raise ValueError(
            "worker result contains trailing data or multiple MessagePack objects"
        )
    _validate_pdf_worker_result_value(decoded)
    return decoded


def _read_pdf_worker_result(
    result_path: Path,
    *,
    max_bytes: int,
    deadline: float | None = None,
) -> _PDFWorkerResult:
    """Read one bounded MessagePack result from an atomically published file."""
    try:
        result_stat = result_path.lstat()
    except FileNotFoundError:
        return _PDFWorkerResult(failure="worker exited without a result")
    except OSError as exc:
        return _PDFWorkerResult(failure=f"worker result could not be inspected: {exc}")

    if not stat.S_ISREG(result_stat.st_mode):
        return _PDFWorkerResult(failure="worker result is not a regular file")
    if result_stat.st_size <= 0:
        return _PDFWorkerResult(failure="worker result is empty")
    if result_stat.st_size > max_bytes:
        return _PDFWorkerResult(
            failure=(f"worker result exceeds the configured {max_bytes}-byte limit")
        )
    if os.name != "nt" and result_stat.st_mode & 0o077:
        return _PDFWorkerResult(failure="worker result permissions are not private")
    getuid = getattr(os, "getuid", None)
    if getuid is not None and result_stat.st_uid != getuid():
        return _PDFWorkerResult(failure="worker result has an unexpected owner")

    descriptor: int | None = None
    try:
        if deadline is not None and deadline <= time.monotonic():
            return _PDFWorkerResult(
                timed_out=True,
                failure="timed out before decoding the worker result",
            )

        open_flags = (
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        )
        descriptor = os.open(result_path, open_flags)
        opened_stat = os.fstat(descriptor)
        if (
            opened_stat.st_dev != result_stat.st_dev
            or opened_stat.st_ino != result_stat.st_ino
            or opened_stat.st_size != result_stat.st_size
            or not stat.S_ISREG(opened_stat.st_mode)
        ):
            return _PDFWorkerResult(
                failure="worker result changed before it could be read"
            )
        with os.fdopen(descriptor, "rb") as result_file:
            descriptor = None
            decoded = _decode_pdf_worker_result_stream(
                result_file,
                max_bytes=max_bytes,
                expected_size=opened_stat.st_size,
            )
    except (
        OSError,
        TypeError,
        ValueError,
        msgpack.BufferFull,
        msgpack.ExtraData,
        msgpack.FormatError,
        msgpack.OutOfData,
        msgpack.StackError,
    ) as exc:
        return _PDFWorkerResult(failure=f"worker result could not be read: {exc}")
    finally:
        if descriptor is not None:
            os.close(descriptor)

    if deadline is not None and time.monotonic() > deadline:
        return _PDFWorkerResult(
            timed_out=True,
            failure="timed out while decoding the worker result",
        )

    if (
        not isinstance(decoded, dict)
        or set(decoded) != {"version", "status", "payload"}
        or type(decoded.get("version")) is not int
        or decoded.get("version") != PDF_WORKER_RESULT_ENVELOPE_VERSION
        or not isinstance(decoded.get("status"), str)
        or decoded.get("status") not in {"ok", "error"}
    ):
        return _PDFWorkerResult(failure="worker result has an invalid envelope")
    status = decoded["status"]
    payload = decoded["payload"]
    return _PDFWorkerResult(status=status, payload=payload)


def _stop_pdf_worker(process: Any) -> None:
    """Reap a PDF worker, escalating from terminate to kill when necessary."""
    try:
        if not process.is_alive():
            process.join(0)
        else:
            process.terminate()
            process.join(PDF_WORKER_TERMINATE_GRACE_SECONDS)
            if process.is_alive():
                kill = getattr(process, "kill", None)
                if kill is not None:
                    kill()
                    process.join(PDF_WORKER_KILL_GRACE_SECONDS)
    except Exception:
        logger.debug("Failed to stop PDF worker cleanly", exc_info=True)
    finally:
        try:
            if not process.is_alive():
                close = getattr(process, "close", None)
                if close is not None:
                    close()
        except Exception:
            logger.debug("Failed to close PDF worker process", exc_info=True)


def _run_isolated_pdf_worker(
    *,
    target: Any,
    pdf_path: Path,
    timeout_seconds: float,
) -> _PDFWorkerResult:
    """Run one PDF worker with file-backed, bounded, atomic result transport.

    Large PDF assets never cross a multiprocessing pipe. The child streams a
    size-limited, non-executable MessagePack envelope into a private partial
    file and publishes it with ``os.replace`` only after the complete payload
    is durable. The parent waits only for process exit, so a pipe frame can
    never make ``Queue.get(timeout=...)`` block past the document deadline.
    Timeout/OOM/crash paths have no published result and fail closed; the
    private result directory is always removed after the process is reaped.

    Worker execution and atomic result publication are bounded by
    ``timeout_seconds``. Bounded parent decode starts only when a conservative
    size-derived time budget remains, rejects extension/custom types, and is
    rejected if it finishes after the deadline. It deliberately does not
    install process-global signal handlers, so an embedding application's
    existing timeout is never replaced or delayed. Forced termination and kill
    add at most the two fixed cleanup grace periods.
    """
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        return _PDFWorkerResult(
            failure="worker timeout must be finite and greater than zero"
        )
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    context = _get_pdf_worker_context()
    result_directory: Path | None = None
    process: Any | None = None

    try:
        result_directory = Path(tempfile.mkdtemp(prefix="asset-aware-pdf-worker-"))
        result_directory.chmod(0o700)
        result_path = result_directory / "result.msgpack"
        max_result_bytes = _pdf_worker_result_max_bytes()
        result_sink = _AtomicPDFWorkerResultSink(
            result_path=str(result_path),
            max_bytes=max_result_bytes,
        )
        process = context.Process(
            target=target,
            args=(str(pdf_path), result_sink),
            daemon=True,
        )

        try:
            process.start()
        except Exception as exc:
            return _PDFWorkerResult(failure=f"worker failed to start: {exc}")

        while process.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return _PDFWorkerResult(
                    timed_out=True,
                    failure=f"timed out after {timeout_seconds:.1f}s",
                )
            process.join(min(PDF_WORKER_RESULT_POLL_SECONDS, remaining))

        process.join(0)
        if time.monotonic() > deadline:
            return _PDFWorkerResult(
                timed_out=True,
                failure=f"timed out after {timeout_seconds:.1f}s",
            )

        if not result_path.exists():
            return _PDFWorkerResult(
                failure=(
                    "worker exited without a result "
                    f"(exit code {getattr(process, 'exitcode', None)})"
                )
            )

        try:
            result_size = result_path.stat().st_size
        except OSError as exc:
            return _PDFWorkerResult(
                failure=f"worker result could not be inspected: {exc}"
            )
        minimum_read_budget = max(
            PDF_WORKER_RESULT_MIN_READ_BUDGET_SECONDS,
            result_size / (PDF_WORKER_RESULT_READ_MIB_PER_SECOND * 1024 * 1024),
        )
        if deadline - time.monotonic() < minimum_read_budget:
            return _PDFWorkerResult(
                timed_out=True,
                failure=(
                    f"timed out after {timeout_seconds:.1f}s before safely "
                    f"reading the {result_size}-byte worker result"
                ),
            )

        result = _read_pdf_worker_result(
            result_path,
            max_bytes=max_result_bytes,
            deadline=deadline,
        )
        if result.timed_out:
            return result
        if time.monotonic() > deadline:
            return _PDFWorkerResult(
                timed_out=True,
                failure=f"timed out after {timeout_seconds:.1f}s",
            )
        return result
    except Exception as exc:
        return _PDFWorkerResult(failure=f"worker setup failed: {exc}")
    finally:
        if process is not None:
            _stop_pdf_worker(process)
        if result_directory is not None:
            shutil.rmtree(result_directory, ignore_errors=True)


@dataclass
class ExtractedImage:
    """Data class for extracted image information."""

    page: int  # 1-indexed page number
    image_bytes: bytes
    ext: str
    width: int
    height: int
    index_on_page: int  # Image index on this page


class PyMuPDFExtractor(PDFExtractorInterface):
    """
    PDF extraction using PyMuPDF.

    Features:
    - Text extraction with formatting hints
    - Image extraction with page number tracking
    - Page comments in markdown for traceability
    - Configurable via ETLProfile (font thresholds, noise filters, etc.)
    """

    #: Engine identity persisted to DocumentManifest.source_engine and
    #: IngestResult.backend so ingested-document provenance survives the
    #: ephemeral ingest call. Subclasses (e.g. PyMuPDF4LLMExtractor) override
    #: this to their own engine name.
    ENGINE_NAME: str = "pymupdf"

    def __init__(
        self,
        profile: ETLProfile | None = None,
        max_image_size_mb: float | None = None,
    ):
        """
        Initialize extractor.

        Args:
            profile: ETL extraction profile (default: ETLProfile.default())
            max_image_size_mb: Maximum image size to extract (default from settings)
        """
        self.profile = profile or ETLProfile.default()
        self.max_image_size_mb = max_image_size_mb or settings.max_image_size_mb

        # Pre-compile regexes from profile (once, at init)
        self._heading_noise_re = self.profile.compile_heading_noise_re()
        self._table_caption_re = self.profile.compile_table_caption_re()
        self._figure_caption_re = self.profile.compile_figure_caption_re()
        self._numbered_section_re = self.profile.compile_numbered_section_re()

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF as markdown.

        Includes page markers as HTML comments for traceability:
        <!-- Page 1 -->

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown-formatted text with page markers
        """
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_TEXT_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_TEXT_DOCUMENT_TIMEOUT_SECONDS,
        )

        if timeout_seconds <= 0:
            return self._extract_text_direct(pdf_path)

        deadline = time.monotonic() + timeout_seconds
        worker_result = _run_isolated_pdf_worker(
            target=_extract_text_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            raise TimeoutError(
                "PyMuPDF text extraction timed out for "
                f"{pdf_path} after {timeout_seconds:.1f}s"
            )

        rich_finished_at = time.monotonic()
        if rich_finished_at >= deadline:
            raise TimeoutError(
                "PyMuPDF text extraction exhausted its "
                f"{timeout_seconds:.1f}s hard deadline"
            )

        if worker_result.status == "ok" and isinstance(worker_result.payload, str):
            return worker_result.payload

        rich_failure = (
            worker_result.failure
            if worker_result.status is None
            else str(worker_result.payload)
        )
        remaining_seconds = deadline - rich_finished_at
        if remaining_seconds <= 0:
            raise TimeoutError(
                "PyMuPDF text extraction exhausted its "
                f"{timeout_seconds:.1f}s deadline before the fast fallback"
            )

        logger.warning(
            "PyMuPDF rich text extraction worker failed for %s: %s; using bounded fast text fallback",
            pdf_path,
            rich_failure,
        )
        fallback_result = _run_isolated_pdf_worker(
            target=_extract_text_fast_worker,
            pdf_path=pdf_path,
            timeout_seconds=remaining_seconds,
        )
        if fallback_result.timed_out:
            raise TimeoutError(
                "PyMuPDF fast text fallback timed out within the shared "
                f"{timeout_seconds:.1f}s text extraction deadline"
            )
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "PyMuPDF fast text fallback exhausted the shared "
                f"{timeout_seconds:.1f}s text extraction deadline"
            )
        if fallback_result.status == "ok" and isinstance(fallback_result.payload, str):
            return fallback_result.payload

        fallback_failure = (
            fallback_result.failure
            if fallback_result.status is None
            else str(fallback_result.payload)
        )
        raise RuntimeError(
            "PyMuPDF text extraction failed: "
            f"rich worker: {rich_failure}; fast fallback: {fallback_failure}"
        )

    def _extract_text_direct(self, pdf_path: Path) -> str:
        """Original rich text extraction with font-aware heading heuristics."""
        doc = fitz.open(str(pdf_path))
        text_parts = []

        try:
            for page_num, page in enumerate(doc):
                # Add page marker
                text_parts.append(f"\n<!-- Page {page_num + 1} -->\n")

                # Get text with formatting info
                page_text = self._extract_page_text(page)
                if page_text:
                    text_parts.append(page_text)
        finally:
            doc.close()

        raw_markdown = "\n".join(text_parts)

        # Post-process: merge consecutive same-level headings
        # (PDF wraps long headings across multiple lines, each becoming a separate # heading)
        return self._merge_consecutive_headings(raw_markdown)

    def _extract_text_fast(self, pdf_path: Path) -> str:
        """Fast fallback text extraction that preserves page markers."""
        pdftotext_bin = shutil.which("pdftotext")
        if pdftotext_bin:
            try:
                result = subprocess.run(
                    [pdftotext_bin, "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                raw_pages = result.stdout.split("\f")
                fallback_text_parts: list[str] = []
                page_counter = 0
                for page_text in raw_pages:
                    if not page_text.strip() and page_counter >= len(raw_pages) - 1:
                        continue
                    page_counter += 1
                    fallback_text_parts.append(f"\n<!-- Page {page_counter} -->\n")
                    if page_text.strip():
                        fallback_text_parts.append(page_text.strip())
                if fallback_text_parts:
                    return "\n".join(fallback_text_parts)
            except Exception:
                logger.debug("pdftotext fallback failed", exc_info=True)

        doc = fitz.open(str(pdf_path))
        text_parts: list[str] = []

        try:
            for page_num, page in enumerate(doc):
                text_parts.append(f"\n<!-- Page {page_num + 1} -->\n")
                page_text = page.get_text("text")
                if page_text:
                    text_parts.append(page_text.strip())
        finally:
            doc.close()

        return "\n".join(text_parts)

    def _merge_consecutive_headings(self, markdown: str) -> str:
        """
        Merge consecutive markdown headings of the same level into one.

        PDF text extraction often splits long headings across multiple lines,
        producing fragmented headings like:
            ## Relationship Between the
            ## Intensive Care Unit and the
            ## Operating Room

        This merges them into:
            ## Relationship Between the Intensive Care Unit and the Operating Room

        Also handles standalone chapter numbers (e.g. '# 79') by combining
        them with adjacent chapter titles into 'Chapter {num}: {title}'.
        """
        lines = markdown.split("\n")
        merged: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                level = header_match.group(1)
                title_parts = [header_match.group(2).strip()]

                # Look ahead for consecutive same-level headings
                j = i + 1
                while j < len(lines):
                    next_match = re.match(r"^(#{1,6})\s+(.+)$", lines[j])
                    if next_match and next_match.group(1) == level:
                        title_parts.append(next_match.group(2).strip())
                        j += 1
                    else:
                        break

                merged_title = " ".join(title_parts)
                merged.append(f"{level} {merged_title}")
                i = j
            else:
                merged.append(line)
                i += 1

        # Second pass: handle standalone chapter numbers for H1
        # e.g. '# 79' near '# Pediatric and Neonatal Critical Care'
        #  → '# Chapter 79: Pediatric and Neonatal Critical Care'
        result: list[str] = []
        skip_indices: set[int] = set()

        for idx, line in enumerate(merged):
            if idx in skip_indices:
                continue

            h1_match = re.match(r"^#\s+(.+)$", line)
            if h1_match:
                text = h1_match.group(1).strip()
                # Check if this H1 is just a number (chapter number)
                if re.match(r"^\d+$", text):
                    chapter_num = text
                    # Look nearby (within 5 lines) for another H1 with actual title
                    title_found = None
                    title_idx = None
                    for search_dir in [-1, 1]:  # search before, then after
                        for offset in range(1, 6):
                            check_idx = idx + search_dir * offset
                            if (
                                0 <= check_idx < len(merged)
                                and check_idx not in skip_indices
                            ):
                                check_match = re.match(r"^#\s+(.+)$", merged[check_idx])
                                if check_match:
                                    candidate = check_match.group(1).strip()
                                    if not re.match(r"^\d+$", candidate):
                                        title_found = candidate
                                        title_idx = check_idx
                                        break
                        if title_found:
                            break

                    if title_found and title_idx is not None:
                        skip_indices.add(title_idx)
                        result.append(f"# Chapter {chapter_num}: {title_found}")
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)

        return "\n".join(result)

    @staticmethod
    def _section_level_from_number(text: str) -> int:
        """Determine heading level from numbered section prefix.

        "1. Intro" → 1, "3.1. Methods" → 2, "3.1.1. Detail" → 3
        """
        m = re.match(r"^[A-Z]?(\d+(?:\.\d+)*)", text)
        if not m:
            return 1
        parts = m.group(1).split(".")
        depth = len([p for p in parts if p])  # count non-empty parts
        return min(depth, 3)  # cap at H3

    def _extract_page_text(self, page: fitz.Page) -> str:
        """Extract text from a single page with basic formatting."""
        blocks = page.get_text("dict")["blocks"]
        lines = []

        for block in blocks:
            if block["type"] != 0:  # Skip non-text blocks
                continue

            for line in block.get("lines", []):
                line_text = ""

                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue

                    font_size = span.get("size", 12)
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 16)
                    stripped = text.strip()

                    # Detect headings by font size
                    # Filter: must be >= min_heading_length and not noise
                    is_heading_candidate = (
                        len(stripped) >= self.profile.min_heading_length
                        and not self._heading_noise_re.match(stripped)
                    )

                    heading_applied = False
                    if is_heading_candidate:
                        if font_size > self.profile.font_thresholds.h1:
                            text = f"# {text}"
                            heading_applied = True
                        elif font_size > self.profile.font_thresholds.h2:
                            text = f"## {text}"
                            heading_applied = True
                        elif font_size > self.profile.font_thresholds.h3:
                            text = f"### {text}"
                            heading_applied = True

                    # Strategy 2: Bold numbered section headings
                    # (catches double-column papers where headings are same
                    #  font size as body text, just bold)
                    if not heading_applied and is_bold and is_heading_candidate:
                        if self._numbered_section_re.match(stripped):
                            level = self._section_level_from_number(stripped)
                            prefix = "#" * min(level + 1, 4)  # +1 since title is H1/H2
                            text = f"{prefix} {text}"
                            heading_applied = True
                        elif stripped.lower() in self.profile.section_keywords:
                            text = f"## {text}"
                            heading_applied = True

                    # Detect bold (flag bit 2^4 = 16)
                    if is_bold and not heading_applied:
                        text = f"**{text}**"

                    line_text += text

                if line_text.strip():
                    lines.append(line_text)

        return "\n".join(lines)

    def extract_images(self, pdf_path: Path) -> list[dict]:
        """
        Extract images from PDF in a child process with a document timeout.

        A handful of textbook chapters can spend minutes inside PyMuPDF image
        heuristics. Running image extraction in a subprocess lets the chapter
        ingest continue even when a difficult document exceeds the budget.
        """
        if not _env_flag("PYMUPDF_ENABLE_VECTOR_IMAGES", True) and not _env_flag(
            "PYMUPDF_ENABLE_REGION_IMAGES",
            True,
        ):
            return self._extract_images_fast(pdf_path)

        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_IMAGE_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_IMAGE_DOCUMENT_TIMEOUT_SECONDS,
        )

        if timeout_seconds <= 0:
            return self._extract_images_direct(pdf_path)

        worker_result = _run_isolated_pdf_worker(
            target=_extract_images_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            logger.warning(
                "PyMuPDF image extraction timed out for %s after %.1fs; using isolated page-crop fallback",
                pdf_path,
                timeout_seconds,
            )
            return self._extract_images_fast_with_timeout(pdf_path)

        if worker_result.status == "ok" and isinstance(worker_result.payload, list):
            return worker_result.payload

        if worker_result.status is None:
            logger.warning(
                "PyMuPDF image extraction worker produced no result for %s: %s; using isolated page-crop fallback",
                pdf_path,
                worker_result.failure,
            )
            return self._extract_images_fast_with_timeout(pdf_path)

        logger.warning(
            "PyMuPDF image extraction worker failed for %s: %s; using isolated page-crop fallback",
            pdf_path,
            worker_result.payload,
        )
        return self._extract_images_fast_with_timeout(pdf_path)

    def _extract_images_fast_with_timeout(self, pdf_path: Path) -> list[dict]:
        """Run fast fallback in a child process so fallback cannot hang ingestion."""
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_FAST_IMAGE_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_FAST_IMAGE_DOCUMENT_TIMEOUT_SECONDS,
        )

        if timeout_seconds <= 0:
            return self._extract_images_fast(pdf_path)

        worker_result = _run_isolated_pdf_worker(
            target=_extract_images_fast_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            logger.warning(
                "PyMuPDF fast image fallback timed out for %s after %.1fs; skipping images",
                pdf_path,
                timeout_seconds,
            )
            return []

        if worker_result.status == "ok" and isinstance(worker_result.payload, list):
            return worker_result.payload

        if worker_result.status is None:
            logger.warning(
                "PyMuPDF fast image fallback produced no result for %s: %s; skipping images",
                pdf_path,
                worker_result.failure,
            )
            return []

        logger.warning(
            "PyMuPDF fast image fallback failed for %s: %s; skipping images",
            pdf_path,
            worker_result.payload,
        )
        return []

    def _extract_images_direct(self, pdf_path: Path) -> list[dict]:
        """
        Extract all images from PDF with page numbers using multi-strategy approach.

        Strategy:
        1. XObject images (standard embedded images)
        2. Vector graphics rendering (for charts/diagrams drawn with paths)
        3. Smart region detection (finds non-text areas and renders them)

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with:
            - page: int (1-indexed)
            - image_bytes: bytes
            - ext: str
            - width: int
            - height: int
            - index_on_page: int
        """
        doc = fitz.open(str(pdf_path))
        images = []

        try:
            for page_num, page in enumerate(doc):
                page_images_found = []

                # Strategy 1: Extract XObject images (standard)
                page_images = page.get_images(full=True)
                for img_index, img in enumerate(page_images):
                    try:
                        image_data = self._extract_single_image(doc, img)
                        if image_data:
                            image_rects = page.get_image_rects(img[0])
                            if not image_rects:
                                img_dict = {
                                    "page": page_num + 1,
                                    "image_bytes": image_data["image"],
                                    "ext": image_data["ext"],
                                    "width": image_data["width"],
                                    "height": image_data["height"],
                                    "index_on_page": img_index + 1,
                                    "extraction_strategy": "xobject_raw",
                                }
                                images.append(img_dict)
                                page_images_found.append(img_dict)
                                continue

                            for rect_index, image_rect in enumerate(image_rects):
                                crop_data = self._render_page_crop(
                                    page,
                                    image_rect,
                                )
                                if not crop_data:
                                    continue
                                rect_suffix = (
                                    img_index + 1
                                    if len(image_rects) == 1
                                    else ((img_index + 1) * 100 + rect_index + 1)
                                )
                                img_dict = {
                                    "page": page_num + 1,
                                    "image_bytes": image_data["image"],
                                    "ext": image_data["ext"],
                                    "width": image_data["width"],
                                    "height": image_data["height"],
                                    "index_on_page": rect_suffix,
                                    "bbox": self._rect_to_list(image_rect),
                                    "page_image_bytes": crop_data["image"],
                                    "page_image_ext": crop_data["ext"],
                                    "page_crop_bbox": crop_data["bbox"],
                                    "page_crop_width": crop_data["width"],
                                    "page_crop_height": crop_data["height"],
                                    "extraction_strategy": "xobject_page_crop",
                                }
                                images.append(img_dict)
                                page_images_found.append(img_dict)
                        elif image_data:
                            img_dict = {
                                "page": page_num + 1,
                                "image_bytes": image_data["image"],
                                "ext": image_data["ext"],
                                "width": image_data["width"],
                                "height": image_data["height"],
                                "index_on_page": img_index + 1,
                            }
                            images.append(img_dict)
                            page_images_found.append(img_dict)
                    except Exception:
                        logger.debug(
                            "Image extraction failed on page %d",
                            page_num,
                            exc_info=True,
                        )
                        continue

                # Strategy 2: Vector graphics detection
                if _env_flag("PYMUPDF_ENABLE_VECTOR_IMAGES", True):
                    try:
                        vector_images = self._run_with_timeout(
                            lambda page=page: self._extract_vector_graphics_regions(
                                page
                            ),
                            env_var="PYMUPDF_IMAGE_TIMEOUT_SECONDS",
                            default_seconds=DEFAULT_IMAGE_STRATEGY_TIMEOUT_SECONDS,
                            operation="vector graphics extraction",
                        )
                        for idx, vector_image in enumerate(vector_images):
                            # Check if this overlaps with existing XObject images
                            if not self._overlaps_existing_images(
                                vector_image["bbox"], page_images_found
                            ):
                                images.append(
                                    {
                                        "page": page_num + 1,
                                        "image_bytes": vector_image["image"],
                                        "ext": vector_image["ext"],
                                        "width": vector_image["width"],
                                        "height": vector_image["height"],
                                        "index_on_page": 900 + idx,  # 900+ for vector
                                        "bbox": self._rect_to_list(
                                            vector_image["bbox"]
                                        ),
                                        "page_crop_bbox": self._rect_to_list(
                                            vector_image["bbox"]
                                        ),
                                        "extraction_strategy": "vector_region",
                                    }
                                )
                    except Exception:
                        logger.debug("Vector graphics extraction failed", exc_info=True)

                # Strategy 3: Smart region detection (find non-text areas)
                if _env_flag("PYMUPDF_ENABLE_REGION_IMAGES", True):
                    try:
                        region_images = self._run_with_timeout(
                            lambda page=page: self._extract_non_text_regions(page),
                            env_var="PYMUPDF_IMAGE_TIMEOUT_SECONDS",
                            default_seconds=DEFAULT_IMAGE_STRATEGY_TIMEOUT_SECONDS,
                            operation="smart region extraction",
                        )
                        for idx, region_image in enumerate(region_images):
                            # Check if already captured
                            if not self._overlaps_existing_images(
                                region_image["bbox"], page_images_found
                            ):
                                images.append(
                                    {
                                        "page": page_num + 1,
                                        "image_bytes": region_image["image"],
                                        "ext": region_image["ext"],
                                        "width": region_image["width"],
                                        "height": region_image["height"],
                                        "index_on_page": 800 + idx,  # 800+ for regions
                                        "bbox": self._rect_to_list(
                                            region_image["bbox"]
                                        ),
                                        "page_crop_bbox": self._rect_to_list(
                                            region_image["bbox"]
                                        ),
                                        "extraction_strategy": "non_text_region",
                                    }
                                )
                    except Exception:
                        logger.debug("Region detection failed", exc_info=True)

        finally:
            doc.close()

        return images

    def _render_page_crop(
        self, page: fitz.Page, bbox: fitz.Rect
    ) -> dict[str, Any] | None:
        """Render an expanded page-region crop around a figure bbox."""
        if bbox.is_empty:
            return None

        x_padding = _env_float(
            "PYMUPDF_FIGURE_CROP_X_PADDING",
            DEFAULT_FIGURE_CROP_X_PADDING,
        )
        top_padding = _env_float(
            "PYMUPDF_FIGURE_CROP_TOP_PADDING",
            DEFAULT_FIGURE_CROP_TOP_PADDING,
        )
        bottom_padding = _env_float(
            "PYMUPDF_FIGURE_CROP_BOTTOM_PADDING",
            DEFAULT_FIGURE_CROP_BOTTOM_PADDING,
        )
        zoom = _env_float("PYMUPDF_FIGURE_CROP_ZOOM", DEFAULT_FIGURE_CROP_ZOOM)

        clip = fitz.Rect(
            bbox.x0 - x_padding,
            bbox.y0 - top_padding,
            bbox.x1 + x_padding,
            bbox.y1 + bottom_padding,
        )
        clip = clip & page.rect
        if clip.is_empty:
            return None

        pix = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            clip=clip,
            alpha=False,
        )
        image_bytes = pix.tobytes("png")
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > self.max_image_size_mb:
            return None

        return {
            "image": image_bytes,
            "ext": "png",
            "width": pix.width,
            "height": pix.height,
            "bbox": self._rect_to_list(clip),
        }

    @staticmethod
    def _rect_to_list(rect: fitz.Rect | list[float] | tuple[float, ...]) -> list[float]:
        """Normalize fitz rectangles for JSON-safe manifest metadata."""
        if isinstance(rect, fitz.Rect):
            values = [rect.x0, rect.y0, rect.x1, rect.y1]
        else:
            values = list(rect[:4])
        return [round(float(value), 3) for value in values]

    def _extract_images_fast(self, pdf_path: Path) -> list[dict]:
        """Fast fallback that only extracts embedded XObject images."""
        doc = fitz.open(str(pdf_path))
        images: list[dict[str, Any]] = []

        try:
            for page_num, page in enumerate(doc):
                page_images = page.get_images(full=True)
                for img_index, img in enumerate(page_images):
                    try:
                        image_data = self._extract_single_image(doc, img)
                        if not image_data:
                            continue
                        image_rects = page.get_image_rects(img[0])
                        if not image_rects:
                            images.append(
                                {
                                    "page": page_num + 1,
                                    "image_bytes": image_data["image"],
                                    "ext": image_data["ext"],
                                    "width": image_data["width"],
                                    "height": image_data["height"],
                                    "index_on_page": img_index + 1,
                                    "extraction_strategy": "xobject_raw",
                                }
                            )
                            continue

                        for rect_index, image_rect in enumerate(image_rects):
                            crop_data = self._render_page_crop(page, image_rect)
                            if not crop_data:
                                continue
                            rect_suffix = (
                                img_index + 1
                                if len(image_rects) == 1
                                else ((img_index + 1) * 100 + rect_index + 1)
                            )
                            images.append(
                                {
                                    "page": page_num + 1,
                                    "image_bytes": image_data["image"],
                                    "ext": image_data["ext"],
                                    "width": image_data["width"],
                                    "height": image_data["height"],
                                    "index_on_page": rect_suffix,
                                    "bbox": self._rect_to_list(image_rect),
                                    "page_image_bytes": crop_data["image"],
                                    "page_image_ext": crop_data["ext"],
                                    "page_crop_bbox": crop_data["bbox"],
                                    "page_crop_width": crop_data["width"],
                                    "page_crop_height": crop_data["height"],
                                    "extraction_strategy": "xobject_page_crop",
                                }
                            )
                    except Exception:
                        logger.debug(
                            "Fast image extraction failed on page %d",
                            page_num,
                            exc_info=True,
                        )
                        continue
        finally:
            doc.close()

        return images

    def _extract_vector_graphics(self, page: fitz.Page) -> dict | None:
        """
        Detect and render vector graphics (drawings) as an image.
        Useful for PDFs where figures are not stored as XObject images.
        """
        drawings = page.get_drawings()
        # Threshold for "significant" graphics (e.g., more than 20 paths)
        if not drawings or len(drawings) < 20:
            return None

        # Calculate bounding box of all drawings
        bbox = None
        for d in drawings:
            # Skip very small or thin lines that might be artifacts
            r = d["rect"]
            if r.width < 1 and r.height < 1:
                continue
            bbox = r if bbox is None else bbox | r

        # If bbox is too small or empty, skip
        if not bbox or bbox.is_empty or bbox.width < 50 or bbox.height < 50:
            return None

        # Render the area with a reasonable resolution (zoom=2 for 144 DPI)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=False)

        image_bytes = pix.tobytes("png")

        # Check size limit
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > self.max_image_size_mb:
            return None

        return {
            "image": image_bytes,
            "ext": "png",
            "width": pix.width,
            "height": pix.height,
        }

    def _extract_vector_graphics_regions(self, page: fitz.Page) -> list[dict[str, Any]]:
        """
        Detect and extract multiple vector graphics regions as separate images.
        More aggressive than _extract_vector_graphics.
        """
        drawings = page.get_drawings()
        if not drawings or len(drawings) < 10:
            return []

        # Group drawings by spatial proximity (cluster analysis)
        clusters = self._cluster_drawings(drawings)
        results = []

        for cluster_bbox in clusters:
            # Skip small regions
            if cluster_bbox.width < 80 or cluster_bbox.height < 80:
                continue

            try:
                # Render the region
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, clip=cluster_bbox, alpha=False)

                image_bytes = pix.tobytes("png")
                size_mb = len(image_bytes) / (1024 * 1024)

                if size_mb <= self.max_image_size_mb:
                    results.append(
                        {
                            "image": image_bytes,
                            "ext": "png",
                            "width": pix.width,
                            "height": pix.height,
                            "bbox": cluster_bbox,
                        }
                    )
            except Exception:
                logger.debug("Cluster rendering failed", exc_info=True)
                continue

        return results

    def _cluster_drawings(self, drawings: list) -> list[fitz.Rect]:
        """
        Cluster drawings into regions based on spatial proximity.
        Simple algorithm: merge bboxes that are close to each other.
        """
        if not drawings:
            return []

        # Get all rects
        rects = []
        for d in drawings:
            r = d["rect"]
            if r.width > 1 or r.height > 1:  # Skip tiny artifacts
                rects.append(r)

        if not rects:
            return []

        # Sort by y-coordinate (top to bottom)
        rects.sort(key=lambda r: r.y0)

        clusters = []
        current_cluster = rects[0]

        for rect in rects[1:]:
            # Check if rect is close to current cluster (within 50 points)
            distance = max(
                0,
                rect.y0 - current_cluster.y1,  # vertical distance
                rect.x0 - current_cluster.x1,  # horizontal distance
            )

            if distance < 50:
                # Merge into current cluster
                current_cluster = current_cluster | rect
            else:
                # Start new cluster if current is significant
                if current_cluster.width > 80 and current_cluster.height > 80:
                    clusters.append(current_cluster)
                current_cluster = rect

        # Don't forget the last cluster
        if current_cluster.width > 80 and current_cluster.height > 80:
            clusters.append(current_cluster)

        return clusters

    def _extract_non_text_regions(self, page: fitz.Page) -> list[dict[str, Any]]:
        """
        Extract non-text regions from the page.
        Strategy: Find areas without text blocks and render them as images.
        """
        # Get text blocks
        text_blocks = page.get_text("blocks")
        page_rect = page.rect

        # Create a set of text bboxes
        text_rects = []
        for block in text_blocks:
            if block[6] == 0:  # Type 0 = text block
                bbox = fitz.Rect(block[:4])
                text_rects.append(bbox)

        # If page is mostly text, skip this strategy
        if len(text_rects) > 20:
            return []

        # Find potential image regions (areas with significant empty space)
        # Divide page into grid and check coverage
        results = []
        grid_size = 4
        cell_width = page_rect.width / grid_size
        cell_height = page_rect.height / grid_size

        for row in range(grid_size):
            for col in range(grid_size):
                cell = fitz.Rect(
                    col * cell_width,
                    row * cell_height,
                    (col + 1) * cell_width,
                    (row + 1) * cell_height,
                )

                # Check if this cell has minimal text coverage
                text_coverage = 0
                for text_rect in text_rects:
                    intersection = cell & text_rect
                    if not intersection.is_empty:
                        text_coverage += intersection.get_area()

                cell_area = cell.get_area()
                if cell_area > 0 and text_coverage / cell_area < 0.1:
                    # Less than 10% text coverage - might be an image region
                    try:
                        # Check if there's actual content (not just white space)
                        zoom = 1.5
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, clip=cell, alpha=False)

                        # Simple heuristic: check if region has color variation
                        if self._has_visual_content(pix):
                            image_bytes = pix.tobytes("png")
                            size_mb = len(image_bytes) / (1024 * 1024)

                            if size_mb <= self.max_image_size_mb:
                                results.append(
                                    {
                                        "image": image_bytes,
                                        "ext": "png",
                                        "width": pix.width,
                                        "height": pix.height,
                                        "bbox": cell,
                                    }
                                )
                    except Exception:
                        logger.debug("Table region rendering failed", exc_info=True)
                        continue

        return results

    def _has_visual_content(self, pix: fitz.Pixmap) -> bool:
        """
        Check if a pixmap has actual visual content (not just blank/white).
        Simple heuristic based on color variance.
        """
        # Sample some pixels
        samples = pix.samples
        if len(samples) < 100:
            return False

        # Check variance in pixel values
        sample_size = min(1000, len(samples))
        sample_bytes = samples[:sample_size]

        # Calculate simple variance
        mean_val = sum(sample_bytes) / len(sample_bytes)
        variance = sum((b - mean_val) ** 2 for b in sample_bytes) / len(sample_bytes)

        # If variance is too low, it's probably blank
        return bool(variance > 100)  # Threshold for "interesting" content

    def _overlaps_existing_images(
        self, bbox: fitz.Rect, existing_images: list[dict]
    ) -> bool:
        """
        Check if a bounding box overlaps significantly with existing images.
        Used to avoid duplicate extractions.

        Overlap threshold: >50% of smaller area means significant overlap.
        """
        if not existing_images:
            return False

        new_area = bbox.width * bbox.height
        if new_area <= 0:
            return False

        for img in existing_images:
            # Check if existing image has bbox info
            if "bbox" not in img:
                # XObject images don't have bbox, skip overlap check for them
                continue

            existing_bbox = img["bbox"]
            # Handle both fitz.Rect and tuple/list formats
            if isinstance(existing_bbox, (list, tuple)):
                existing_bbox = fitz.Rect(existing_bbox)

            # Calculate intersection
            intersection = bbox & existing_bbox
            if intersection.is_empty:
                continue

            intersection_area = intersection.width * intersection.height
            existing_area = existing_bbox.width * existing_bbox.height

            # Overlap ratio based on smaller of the two areas
            min_area = min(new_area, existing_area)
            if min_area > 0 and intersection_area / min_area > 0.5:
                return True

        return False

    def _extract_single_image(self, doc: fitz.Document, img: tuple) -> dict | None:
        """Extract a single image from document."""
        xref = img[0]
        base_image = doc.extract_image(xref)

        if not base_image:
            return None

        image_bytes = base_image["image"]

        # Check size limit
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > self.max_image_size_mb:
            return None

        return {
            "image": image_bytes,
            "ext": base_image.get("ext", "png"),
            "width": base_image.get("width", 0),
            "height": base_image.get("height", 0),
        }

    def get_page_count(self, pdf_path: Path) -> int:
        """Get total page count of PDF."""
        doc = fitz.open(str(pdf_path))
        try:
            return len(doc)
        finally:
            doc.close()

    def get_metadata(self, pdf_path: Path) -> dict:
        """Get PDF metadata (title, author, etc.)."""
        doc = fitz.open(str(pdf_path))
        try:
            return doc.metadata or {}
        finally:
            doc.close()

    def get_toc(self, pdf_path: Path) -> list[tuple[int, str, int]]:
        """
        Get PDF built-in Table of Contents (bookmark outline).

        Returns:
            List of (level, title, page_number) tuples.
            Much more reliable than font-size heuristics.
        """
        doc = fitz.open(str(pdf_path))
        try:
            toc: list[tuple[int, str, int]] = (
                doc.get_toc()
            )  # [(level, title, page), ...]
            return toc
        finally:
            doc.close()

    def get_title(self, pdf_path: Path) -> str:
        """
        Get document title from PDF metadata.

        Returns:
            Title string, or empty string if not available.
        """
        meta = self.get_metadata(pdf_path)
        return (meta.get("title") or "").strip()

    def audit_ai_safety(self, pdf_path: Path) -> dict[str, Any]:
        """Best-effort PDF AI safety audit with document-level isolation."""
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_SAFETY_AUDIT_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_SAFETY_AUDIT_DOCUMENT_TIMEOUT_SECONDS,
        )
        if timeout_seconds <= 0:
            return self._audit_ai_safety_direct(pdf_path)

        worker_result = _run_isolated_pdf_worker(
            target=_audit_ai_safety_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            logger.warning(
                "PDF AI safety audit timed out for %s after %.1fs",
                pdf_path,
                timeout_seconds,
            )
            return self._skipped_ai_safety_report(
                f"timed out after {timeout_seconds:.1f}s"
            )

        if worker_result.status == "ok" and isinstance(worker_result.payload, dict):
            return worker_result.payload

        if worker_result.status is None:
            return self._skipped_ai_safety_report(
                worker_result.failure or "worker returned no result"
            )

        logger.warning(
            "PDF AI safety audit worker failed for %s: %s",
            pdf_path,
            worker_result.payload,
        )
        return self._skipped_ai_safety_report(str(worker_result.payload))

    def _audit_ai_safety_direct(self, pdf_path: Path) -> dict[str, Any]:
        """Best-effort PDF AI safety audit without mutating extracted text."""
        doc = fitz.open(str(pdf_path))
        issues: list[dict[str, Any]] = []
        span_count = 0
        issue_count = 0
        issues_by_reason: Counter[str] = Counter()
        issues_by_severity: Counter[str] = Counter()
        max_issues = _env_int(PDF_AUDIT_MAX_ISSUES_ENV, DEFAULT_PDF_AUDIT_MAX_ISSUES)
        max_pages = _env_int(PDF_AUDIT_MAX_PAGES_ENV, DEFAULT_PDF_AUDIT_MAX_PAGES)
        pages_scanned = 0

        try:
            page_total = len(doc)
            for page_index, page in enumerate(doc):
                if max_pages > 0 and page_index >= max_pages:
                    break
                pages_scanned += 1
                page_number = page_index + 1
                page_rect = page.rect
                try:
                    text_dict = page.get_text("dict")
                except Exception:
                    logger.debug(
                        "Failed to read text dictionary for %s page %d",
                        pdf_path,
                        page_number,
                        exc_info=True,
                    )
                    continue

                for block in text_dict.get("blocks", []):
                    if not isinstance(block, dict):
                        continue
                    for line in block.get("lines", []):
                        if not isinstance(line, dict):
                            continue
                        for span in line.get("spans", []):
                            if not isinstance(span, dict):
                                continue
                            text = str(span.get("text") or "")
                            if not text.strip():
                                continue
                            span_count += 1
                            bbox = self._coerce_bbox(span.get("bbox"))
                            font_size = self._coerce_float(span.get("size"))
                            color = self._coerce_int_or_none(span.get("color"))

                            reasons: list[tuple[str, str]] = []
                            if font_size is not None and font_size <= 3.0:
                                reasons.append(("tiny_font_text", "warning"))
                            if color is not None and self._is_near_white_color(color):
                                reasons.append(("white_or_near_white_text", "warning"))
                            if bbox and self._bbox_is_off_page(bbox, page_rect):
                                reasons.append(("off_page_text", "warning"))
                            if bbox and self._bbox_has_no_area(bbox):
                                reasons.append(("zero_area_text", "warning"))
                            if _SUSPICIOUS_AI_INSTRUCTION_RE.search(text):
                                reasons.append(("prompt_injection_text", "high"))

                            for reason, severity in reasons:
                                issue_count += 1
                                issues_by_reason[reason] += 1
                                issues_by_severity[severity] += 1
                                if len(issues) < max_issues:
                                    issues.append(
                                        {
                                            "issue_id": f"pdf_safety_{issue_count}",
                                            "page": page_number,
                                            "severity": severity,
                                            "reason": reason,
                                            "bbox": bbox or [],
                                            "font_size": font_size,
                                            "color": color,
                                            "text_preview": " ".join(text.split())[
                                                :200
                                            ],
                                            "text_sha256": self._sha256_text(text),
                                        }
                                    )
        finally:
            doc.close()

        pages_omitted = max(0, page_total - pages_scanned)
        issues_omitted = max(0, issue_count - len(issues))
        return {
            "schema_version": PDF_AI_SAFETY_REPORT_VERSION,
            "backend": "pymupdf",
            "status": "warning" if issue_count else "ok",
            "truncated": bool(pages_omitted or issues_omitted),
            "summary": {
                "pages": page_total,
                "pages_scanned": pages_scanned,
                "pages_omitted": pages_omitted,
                "text_spans_scanned": span_count,
                "issue_count": issue_count,
                "issues_retained": len(issues),
                "issues_omitted": issues_omitted,
                "issues_by_reason": dict(sorted(issues_by_reason.items())),
                "issues_by_severity": dict(sorted(issues_by_severity.items())),
            },
            "issues": issues,
        }

    def extract_native_structure(self, pdf_path: Path) -> dict[str, Any]:
        """Extract lightweight native PDF structure with document-level isolation."""
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_NATIVE_STRUCTURE_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_NATIVE_STRUCTURE_DOCUMENT_TIMEOUT_SECONDS,
        )
        if timeout_seconds <= 0:
            return self._extract_native_structure_direct(pdf_path)

        worker_result = _run_isolated_pdf_worker(
            target=_extract_native_structure_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            logger.warning(
                "Native PDF structure extraction timed out for %s after %.1fs",
                pdf_path,
                timeout_seconds,
            )
            return self._skipped_native_structure_report(
                f"timed out after {timeout_seconds:.1f}s"
            )

        if worker_result.status == "ok" and isinstance(worker_result.payload, dict):
            return worker_result.payload

        if worker_result.status is None:
            return self._skipped_native_structure_report(
                worker_result.failure or "worker returned no result"
            )

        logger.warning(
            "Native PDF structure extraction worker failed for %s: %s",
            pdf_path,
            worker_result.payload,
        )
        return self._skipped_native_structure_report(str(worker_result.payload))

    def _extract_native_structure_direct(self, pdf_path: Path) -> dict[str, Any]:
        """Extract lightweight native PDF structure metadata for audit artifacts."""
        doc = fitz.open(str(pdf_path))
        try:
            metadata = doc.metadata or {}
            try:
                toc = [
                    {"level": int(level), "title": str(title), "page": int(page)}
                    for level, title, page in doc.get_toc()
                ]
            except Exception:
                logger.debug("Failed to extract PDF outline", exc_info=True)
                toc = []
            pages: list[dict[str, Any]] = []
            total_links = 0
            total_widgets = 0
            max_pages = _env_int(
                PDF_STRUCTURE_MAX_PAGES_ENV,
                DEFAULT_PDF_STRUCTURE_MAX_PAGES,
            )
            for page_index, page in enumerate(doc):
                if max_pages > 0 and page_index >= max_pages:
                    break
                try:
                    links = page.get_links() or []
                except Exception:
                    logger.debug(
                        "Failed to extract PDF links on page %d",
                        page_index + 1,
                        exc_info=True,
                    )
                    links = []
                try:
                    widgets = list(page.widgets() or [])
                except Exception:
                    logger.debug(
                        "Failed to extract PDF widgets on page %d",
                        page_index + 1,
                        exc_info=True,
                    )
                    widgets = []
                total_links += len(links)
                total_widgets += len(widgets)
                pages.append(
                    {
                        "page": page_index + 1,
                        "width": float(page.rect.width),
                        "height": float(page.rect.height),
                        "rotation": int(page.rotation or 0),
                        "link_count": len(links),
                        "widget_count": len(widgets),
                    }
                )

            catalog = self._read_catalog_keys(doc)
            struct_tree = str(catalog.get("StructTreeRoot") or "")
            mark_info = str(catalog.get("MarkInfo") or "")
            language = str(catalog.get("Lang") or "")
            tag_tree_status = (
                "detected"
                if struct_tree and struct_tree.lower() not in {"null", "none"}
                else "not_detected"
            )

            return {
                "schema_version": PDF_NATIVE_STRUCTURE_REPORT_VERSION,
                "backend": "pymupdf",
                "metadata": metadata,
                "capabilities": {
                    "outline": bool(toc),
                    "page_geometry": True,
                    "links": total_links > 0,
                    "forms": total_widgets > 0,
                    "catalog_keys": bool(catalog),
                    "tag_tree": tag_tree_status == "detected",
                    "language": bool(language),
                },
                "outline": toc,
                "pages": pages,
                "catalog": catalog,
                "truncated": max_pages > 0 and len(doc) > max_pages,
                "tag_tree": {
                    "status": tag_tree_status if catalog else "unavailable",
                    "struct_tree_root": struct_tree,
                    "mark_info": mark_info,
                    "language": language,
                    "note": (
                        "PyMuPDF lightweight backend reports catalog-level tag "
                        "signals; full PDF/UA validation is out of scope."
                    ),
                },
                "summary": {
                    "page_count": len(doc),
                    "pages_reported": len(pages),
                    "pages_omitted": max(0, len(doc) - len(pages)),
                    "outline_items": len(toc),
                    "link_count": total_links,
                    "form_widget_count": total_widgets,
                },
            }
        finally:
            doc.close()

    @staticmethod
    def _skipped_ai_safety_report(reason: str) -> dict[str, Any]:
        return {
            "schema_version": PDF_AI_SAFETY_REPORT_VERSION,
            "backend": "pymupdf",
            "status": "skipped",
            "summary": {
                "pages": 0,
                "text_spans_scanned": 0,
                "issue_count": 0,
                "issues_by_reason": {},
                "issues_by_severity": {},
            },
            "issues": [],
            "reason": reason,
        }

    @staticmethod
    def _skipped_native_structure_report(reason: str) -> dict[str, Any]:
        return {
            "schema_version": PDF_NATIVE_STRUCTURE_REPORT_VERSION,
            "backend": "pymupdf",
            "status": "skipped",
            "metadata": {},
            "capabilities": {},
            "outline": [],
            "pages": [],
            "catalog": {},
            "tag_tree": {"status": "unavailable"},
            "summary": {
                "page_count": 0,
                "outline_items": 0,
                "link_count": 0,
                "form_widget_count": 0,
            },
            "reason": reason,
        }

    def extract_tables(self, pdf_path: Path) -> list[dict]:
        """
        Extract tables from PDF using a child process with a document timeout.

        PyMuPDF's table finder can occasionally hang on complex textbook pages.
        Running it in a subprocess lets us preserve full document ingest while
        safely dropping tables for the problematic document if it exceeds the
        configured timeout.
        """
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_TABLE_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_TABLE_DOCUMENT_TIMEOUT_SECONDS,
        )

        if timeout_seconds <= 0:
            return self._extract_tables_direct(pdf_path)

        worker_result = _run_isolated_pdf_worker(
            target=_extract_tables_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            logger.warning(
                "PyMuPDF table extraction timed out for %s after %.1fs; skipping tables for this document",
                pdf_path,
                timeout_seconds,
            )
            return []

        if worker_result.status == "ok" and isinstance(worker_result.payload, list):
            return worker_result.payload

        if worker_result.status is None:
            logger.warning(
                "PyMuPDF table extraction worker produced no result for %s: %s; skipping tables for this document",
                pdf_path,
                worker_result.failure,
            )
            return []

        logger.warning(
            "PyMuPDF table extraction worker failed for %s: %s",
            pdf_path,
            worker_result.payload,
        )
        return []

    def _extract_tables_direct(self, pdf_path: Path) -> list[dict]:
        """
        Extract tables from PDF using PyMuPDF's find_tables().

        Note: This is a heuristic-based approach, not as accurate as
        Docling's TableFormer model. Works best for simple grid tables.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with table info
        """
        doc = fitz.open(str(pdf_path))
        tables = []
        table_index = 0

        try:
            for page_num, page in enumerate(doc):
                try:
                    # PyMuPDF's experimental table finder
                    page_tables = self._find_tables_with_timeout(page)

                    for tab in page_tables:
                        table_index += 1

                        # Extract table data
                        try:
                            # Get table as pandas DataFrame if available
                            if hasattr(tab, "to_pandas"):
                                try:
                                    df = tab.to_pandas()
                                    markdown = df.to_markdown(index=False)
                                    row_count = len(df)
                                    col_count = len(df.columns)
                                except Exception:
                                    # Fallback when tabulate is missing
                                    markdown = self._table_to_markdown(tab)
                                    row_count = getattr(tab, "row_count", 0)
                                    col_count = getattr(tab, "col_count", 0)
                            else:
                                # Fallback: extract cells manually
                                markdown = self._table_to_markdown(tab)
                                row_count = getattr(tab, "row_count", 0)
                                col_count = getattr(tab, "col_count", 0)

                            # Filter noise tables (empty or single-column)
                            if (
                                row_count < self.profile.filters.min_table_rows
                                or col_count < self.profile.filters.min_table_cols
                            ):
                                table_index -= 1  # Don't count filtered tables
                                continue

                            # Detect caption from text near the table
                            caption = self._detect_table_caption(page, tab, table_index)

                            tables.append(
                                {
                                    "id": f"tab_{table_index}",
                                    "page": page_num + 1,
                                    "markdown": markdown,
                                    "caption": caption,
                                    "row_count": row_count,
                                    "col_count": col_count,
                                    "preview": markdown[:100] if markdown else "",
                                    "has_header": True,
                                    "source": "pymupdf",
                                }
                            )
                        except Exception:
                            logger.debug("Table cell extraction failed", exc_info=True)
                            continue

                except Exception:
                    # find_tables() may not be available in older versions
                    logger.debug(
                        "find_tables() failed on page %d", page_num, exc_info=True
                    )
                    continue

        finally:
            doc.close()

        return tables

    @staticmethod
    def _sha256_text(text: str) -> str:
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _coerce_bbox(value: object) -> list[float]:
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return []
        coords: list[float] = []
        for item in value:
            number = PyMuPDFExtractor._coerce_float(item)
            if number is None:
                return []
            coords.append(number)
        return coords

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _coerce_int_or_none(value: object) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if not isinstance(value, str):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _is_near_white_color(color: int) -> bool:
        red = (color >> 16) & 0xFF
        green = (color >> 8) & 0xFF
        blue = color & 0xFF
        return red >= 240 and green >= 240 and blue >= 240

    @staticmethod
    def _bbox_is_off_page(bbox: list[float], page_rect: fitz.Rect) -> bool:
        left, top, right, bottom = bbox
        return (
            right < 0
            or bottom < 0
            or left > float(page_rect.width)
            or top > float(page_rect.height)
        )

    @staticmethod
    def _bbox_has_no_area(bbox: list[float]) -> bool:
        left, top, right, bottom = bbox
        return right <= left or bottom <= top

    @staticmethod
    def _read_catalog_keys(doc: fitz.Document) -> dict[str, str]:
        if not hasattr(doc, "pdf_catalog") or not hasattr(doc, "xref_get_key"):
            return {}
        try:
            catalog_xref = doc.pdf_catalog()
        except Exception:
            return {}
        if not catalog_xref:
            return {}

        values: dict[str, str] = {}
        for key in ("StructTreeRoot", "MarkInfo", "Lang", "PageLabels"):
            try:
                _kind, value = doc.xref_get_key(catalog_xref, key)
            except Exception:
                logger.debug("Failed to read PDF catalog key %s", key, exc_info=True)
                continue
            if value not in {"", "null", "None", None}:
                values[key] = str(value)
        return values

    def _find_tables_with_timeout(self, page: fitz.Page) -> Any:
        """
        Run PyMuPDF's experimental table finder with a per-page timeout.

        Some textbook pages trigger very slow `find_tables()` scans and can stall a
        whole batch ingest. Timing out the problematic page is preferable to
        aborting the entire chapter/document.
        """
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_TABLE_TIMEOUT_SECONDS",
            DEFAULT_TABLE_TIMEOUT_SECONDS,
        )

        return self._run_with_timeout(
            page.find_tables,
            timeout_seconds=timeout_seconds,
            operation="table extraction",
        )

    def _run_with_timeout(
        self,
        func: Any,
        *,
        timeout_seconds: float | None = None,
        env_var: str | None = None,
        default_seconds: float = DEFAULT_IMAGE_STRATEGY_TIMEOUT_SECONDS,
        operation: str = "operation",
    ) -> Any:
        """
        Execute a callable with an optional wall-clock timeout.

        Timeout guards are best-effort and only active on Unix main-thread runs.
        When unavailable, the callable executes normally. An already-active
        process timer is never replaced; its existing handler governs instead.
        """
        if timeout_seconds is None:
            timeout_seconds = _env_timeout_seconds(env_var or "", default_seconds)
        elif not math.isfinite(timeout_seconds):
            timeout_seconds = default_seconds

        if (
            timeout_seconds <= 0
            or threading.current_thread() is not threading.main_thread()
        ):
            return func()

        sigalrm = getattr(signal, "SIGALRM", None)
        itimer_real = getattr(signal, "ITIMER_REAL", None)
        getitimer = getattr(signal, "getitimer", None)
        setitimer = getattr(signal, "setitimer", None)
        if (
            sigalrm is None
            or itimer_real is None
            or not callable(getitimer)
            or not callable(setitimer)
        ):
            return func()

        def _handle_timeout(_signum: int, _frame: Any) -> None:
            raise TimeoutError(
                f"PyMuPDF {operation} timed out after {timeout_seconds:.1f}s"
            )

        previous_handler = signal.getsignal(sigalrm)
        previous_timer = getitimer(itimer_real)
        if previous_timer != (0.0, 0.0):
            # Never replace an embedding application's outer deadline. Its
            # handler remains installed and governs this nested operation.
            return func()

        try:
            signal.signal(sigalrm, _handle_timeout)
            setitimer(itimer_real, timeout_seconds)
            return func()
        finally:
            setitimer(itimer_real, 0)
            signal.signal(sigalrm, previous_handler)

    def _detect_table_caption(
        self, page: fitz.Page, table: Any, table_index: int
    ) -> str:
        """
        Detect table caption from text above or below the table.

        Searches for patterns like 'Table 1. ...', 'Table 2: ...' etc.
        in a region above/below the table bounding box.
        """
        if not hasattr(table, "bbox"):
            return ""

        bbox = table.bbox
        page_h = page.rect.height
        margin = 80  # pixels to search above/below

        # Search above first (most common position)
        above = fitz.Rect(
            max(0, bbox[0] - 50),
            max(0, bbox[1] - margin),
            min(page.rect.width, bbox[2] + 50),
            bbox[1],
        )
        # Then below
        below = fitz.Rect(
            max(0, bbox[0] - 50),
            bbox[3],
            min(page.rect.width, bbox[2] + 50),
            min(page_h, bbox[3] + margin),
        )

        for region in (above, below):
            text = page.get_text("text", clip=region).strip()
            if not text:
                continue
            match = self._table_caption_re.search(text)
            if match:
                cap_num = match.group(1)
                # Reject implausible table numbers (e.g. "Table 34733")
                if int(cap_num) > self.profile.filters.max_caption_number:
                    continue
                cap_text = match.group(2).strip()
                # Take first line only (caption may bleed into body text)
                cap_text = cap_text.split("\n")[0].rstrip(".")
                return f"Table {cap_num}. {cap_text}".strip()

        return ""

    def extract_figure_captions(self, pdf_path: Path) -> dict[int, list[dict]]:
        """
        Extract figure captions from all pages.

        Returns:
            Dict mapping page number (1-indexed) to list of caption dicts:
            [{"number": "1", "caption": "Figure 1. Description..."}]
        """
        timeout_seconds = _env_timeout_seconds(
            "PYMUPDF_CAPTION_DOCUMENT_TIMEOUT_SECONDS",
            DEFAULT_CAPTION_DOCUMENT_TIMEOUT_SECONDS,
        )

        if timeout_seconds <= 0:
            return self._extract_figure_captions_direct(pdf_path)

        worker_result = _run_isolated_pdf_worker(
            target=_extract_figure_captions_worker,
            pdf_path=pdf_path,
            timeout_seconds=timeout_seconds,
        )

        if worker_result.timed_out:
            logger.warning(
                "PyMuPDF figure caption extraction timed out for %s after %.1fs; skipping captions",
                pdf_path,
                timeout_seconds,
            )
            return {}

        if worker_result.status == "ok" and isinstance(worker_result.payload, dict):
            return worker_result.payload

        if worker_result.status is None:
            logger.warning(
                "PyMuPDF figure caption extraction worker produced no result for %s: %s; skipping captions",
                pdf_path,
                worker_result.failure,
            )
            return {}

        logger.warning(
            "PyMuPDF figure caption extraction worker failed for %s: %s; skipping captions",
            pdf_path,
            worker_result.payload,
        )
        return {}

    def _extract_figure_captions_direct(self, pdf_path: Path) -> dict[int, list[dict]]:
        """Extract figure captions directly without worker isolation."""
        doc = fitz.open(str(pdf_path))
        captions: dict[int, list[dict]] = {}

        try:
            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                matches = self._figure_caption_re.finditer(text)
                page_captions: list[dict] = []
                seen_numbers: set[str] = set()  # dedup by figure number
                text_blocks = page.get_text("blocks")
                for m in matches:
                    fig_num = m.group(1)
                    # Reject implausible figure numbers
                    if (
                        int(fig_num.split(".", 1)[0])
                        > self.profile.filters.max_caption_number
                    ):
                        continue
                    # Dedup: keep only the first occurrence of each figure number per page
                    if fig_num in seen_numbers:
                        continue
                    fig_text = m.group(2).strip().split("\n")[0].rstrip(".")
                    # Require minimum body length (filter fragments)
                    if len(fig_text) < self.profile.filters.min_caption_body_len:
                        continue
                    seen_numbers.add(fig_num)
                    caption = f"Figure {fig_num}. {fig_text}".strip()
                    page_captions.append(
                        {
                            "number": fig_num,
                            "caption": caption,
                            "bbox": self._find_caption_bbox(text_blocks, caption),
                        }
                    )
                if page_captions:
                    captions[page_num + 1] = page_captions
        finally:
            doc.close()

        return captions

    def _find_caption_bbox(
        self,
        text_blocks: list[tuple],
        caption: str,
    ) -> list[float]:
        """Best-effort location for a detected caption in page text blocks."""
        normalized_caption = self._normalize_caption_text(caption)
        best_bbox: list[float] = []
        best_score = 0

        for block in text_blocks:
            if len(block) < 5:
                continue
            block_text = str(block[4] or "")
            normalized_block = self._normalize_caption_text(block_text)
            if not normalized_block:
                continue
            score = 0
            if normalized_caption and normalized_caption in normalized_block:
                score = len(normalized_caption)
            elif (
                normalized_caption[:24] and normalized_caption[:24] in normalized_block
            ):
                score = len(normalized_caption[:24])
            if score > best_score:
                best_score = score
                best_bbox = [round(float(value), 3) for value in block[:4]]

        return best_bbox

    @staticmethod
    def _normalize_caption_text(text: str) -> str:
        """Normalize caption text for fuzzy block lookup."""
        normalized = text.lower().replace("figure", "fig")
        return re.sub(r"[^a-z0-9]+", "", normalized)

    def _table_to_markdown(self, table: Any) -> str:
        """Convert PyMuPDF table to markdown format."""
        if not hasattr(table, "extract"):
            return ""

        try:
            cells = table.extract()
            if not cells:
                return ""

            lines = []
            for i, row in enumerate(cells):
                # Clean cells
                clean_row = [str(cell).strip() if cell else "" for cell in row]
                lines.append("| " + " | ".join(clean_row) + " |")

                # Add header separator after first row
                if i == 0:
                    separator = "| " + " | ".join(["---"] * len(clean_row)) + " |"
                    lines.append(separator)

            return "\n".join(lines)

        except Exception:
            return ""
