"""Isolate native CSV/TSV parsing and byte-splice mutation from the MCP server."""

from __future__ import annotations

import math
import multiprocessing
import tempfile
import time
from pathlib import Path
from typing import Any

from src.domain.native_assets import NativeEditResult
from src.infrastructure.native_delimited import NativeDelimited
from src.infrastructure.pdf_extractor import (
    _AtomicPDFWorkerResultSink,
    _read_pdf_worker_result,
)
from src.infrastructure.pymupdf_preflight import _apply_worker_memory_limit

DELIMITED_OPERATIONS = frozenset(
    {"inspect", "read_cell", "decompose", "create", "update"}
)
MUTATIONS = frozenset({"create", "update"})
MAX_RESULT_BYTES = 128 * 1024 * 1024


def _worker(sink: _AtomicPDFWorkerResultSink, operation: str, arguments: tuple) -> None:
    try:
        _apply_worker_memory_limit(1536 * 1024 * 1024)
        if operation not in DELIMITED_OPERATIONS:
            raise ValueError("Unknown native delimited operation")
        result = getattr(NativeDelimited(), operation)(*arguments)
        if operation in MUTATIONS:
            data, report = result
            result = [data, report.model_dump(mode="json")]
        sink.put(("ok", result))
    except Exception as exc:
        sink.put(("error", f"Native delimited operation failed: {str(exc)[:1500]}"))


class ProcessNativeDelimited:
    def __init__(self, timeout: float = 60.0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Native delimited timeout must be finite and positive")
        self.timeout = timeout

    def _run(self, operation: str, *arguments: Any) -> Any:
        with tempfile.TemporaryDirectory(prefix="native-delimited-") as directory:
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
                raise ValueError("Native delimited operation exceeded its time limit")
            result = _read_pdf_worker_result(
                path, max_bytes=MAX_RESULT_BYTES, deadline=deadline
            )
            if result.failure:
                raise ValueError(f"Native delimited {result.failure}")
            if process.exitcode != 0:
                raise ValueError("Native delimited worker exited unsuccessfully")
            if result.status != "ok":
                raise ValueError(result.payload)
            if operation in MUTATIONS:
                data, report = result.payload
                if not isinstance(data, bytes):
                    raise ValueError(
                        "Native delimited worker returned invalid document bytes"
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

    def inspect(self, data: bytes, dialect: Any) -> Any:
        return self._run("inspect", data, dialect)

    def read_cell(self, data: bytes, dialect: Any, row: int, column: int) -> Any:
        return self._run("read_cell", data, dialect, row, column)

    def decompose(self, data: bytes, dialect: Any) -> Any:
        return self._run("decompose", data, dialect)

    def create(self, request: Any) -> Any:
        return self._run("create", request)

    def update(self, data: bytes, dialect: Any, request: Any) -> Any:
        return self._run("update", data, dialect, request)
