"""Isolate native PDF parsing, mutation and rendering from the MCP server."""

from __future__ import annotations

import math
import multiprocessing
import tempfile
import time
from pathlib import Path
from typing import Any

from src.domain.native_assets import NativeEditResult
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.pdf_extractor import (
    _AtomicPDFWorkerResultSink,
    _read_pdf_worker_result,
)
from src.infrastructure.pymupdf_preflight import _apply_worker_memory_limit

PDF_OPERATIONS = frozenset(
    {
        "inspect",
        "read_page",
        "create",
        "insert",
        "edit",
        "delete",
        "reorder",
        "render",
        "render_region",
        "decompose",
        "inspect_annotations",
        "read_annotation",
        "decompose_annotations",
        "edit_annotations",
    }
)
MUTATIONS = frozenset(
    {"create", "insert", "edit", "delete", "reorder", "edit_annotations"}
)
MAX_RESULT_BYTES = 128 * 1024 * 1024


def _worker(sink: _AtomicPDFWorkerResultSink, operation: str, arguments: tuple) -> None:
    try:
        _apply_worker_memory_limit(1536 * 1024 * 1024)
        if operation not in PDF_OPERATIONS:
            raise ValueError("Unknown native PDF operation")
        result = getattr(NativePdf(), operation)(*arguments)
        if operation in MUTATIONS:
            data, report = result
            result = [data, report.model_dump(mode="json")]
        sink.put(("ok", result))
    except Exception as exc:
        sink.put(("error", f"Native PDF operation failed: {str(exc)[:1500]}"))


class ProcessNativePdf:
    def __init__(self, timeout: float = 60.0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Native PDF timeout must be finite and positive")
        self.timeout = timeout

    def _run(self, operation: str, *arguments: Any) -> Any:
        with tempfile.TemporaryDirectory(prefix="native-pdf-") as directory:
            return self._execute(
                Path(directory) / "result.msgpack", operation, arguments
            )

    def _execute(self, path: Path, operation: str, arguments: tuple) -> Any:
        context = multiprocessing.get_context("spawn")
        sink = _AtomicPDFWorkerResultSink(str(path), MAX_RESULT_BYTES)
        process = context.Process(target=_worker, args=(sink, operation, arguments))
        deadline = time.monotonic() + self.timeout
        try:
            process.start()
            process.join(max(0, deadline - time.monotonic()))
            if process.is_alive():
                raise ValueError("Native PDF operation exceeded its time limit")
            result = _read_pdf_worker_result(
                path, max_bytes=MAX_RESULT_BYTES, deadline=deadline
            )
            if result.failure:
                raise ValueError(f"Native PDF {result.failure}")
            if process.exitcode != 0:
                raise ValueError("Native PDF worker exited unsuccessfully")
            if result.status != "ok":
                raise ValueError(result.payload)
            if operation in MUTATIONS:
                data, report = result.payload
                if not isinstance(data, bytes):
                    raise ValueError(
                        "Native PDF worker returned invalid document bytes"
                    )
                return data, NativeEditResult.model_validate(report)
            return result.payload
        finally:
            if process.pid is not None:
                process.join(timeout=1)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                process.close()

    def inspect(self, data: bytes) -> Any:
        return self._run("inspect", data)

    def inspect_annotations(self, data: bytes) -> Any:
        return self._run("inspect_annotations", data)

    def read_annotation(self, data: bytes, locator: Any) -> Any:
        return self._run("read_annotation", data, locator)

    def decompose_annotations(self, data: bytes) -> Any:
        return self._run("decompose_annotations", data)

    def edit_annotations(self, data: bytes, request: Any) -> Any:
        return self._run("edit_annotations", data, request)

    def decompose(self, data: bytes) -> Any:
        return self._run("decompose", data)

    def read_page(self, data: bytes, locator: Any) -> Any:
        return self._run("read_page", data, locator)

    def create(self, request: Any, sources: dict[str, bytes]) -> Any:
        return self._run("create", request, sources)

    def insert(self, data: bytes, request: Any, sources: dict[str, bytes]) -> Any:
        return self._run("insert", data, request, sources)

    def edit(self, data: bytes, edits: list) -> Any:
        return self._run("edit", data, edits)

    def delete(self, data: bytes, references: list) -> Any:
        return self._run("delete", data, references)

    def reorder(self, data: bytes, references: list) -> Any:
        return self._run("reorder", data, references)

    def render(self, data: bytes, locator: Any, width: int) -> Any:
        return self._run("render", data, locator, width)

    def render_region(
        self, data: bytes, locator: Any, selector: Any, width: int
    ) -> Any:
        return self._run("render_region", data, locator, selector, width)
