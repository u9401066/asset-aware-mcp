"""Run raster decoding/encoding in bounded subprocesses, with typed mutation results."""

from __future__ import annotations

import math
import multiprocessing
import tempfile
import time
from pathlib import Path
from typing import Any

from src.domain.native_asset_models import NativeEditResult
from src.infrastructure.native_image_document import NativeImage
from src.infrastructure.pdf_extractor import (
    _AtomicPDFWorkerResultSink,
    _read_pdf_worker_result,
)
from src.infrastructure.pymupdf_preflight import _apply_worker_memory_limit

IMAGE_OPERATIONS = frozenset(
    {
        "inspect",
        "records",
        "read_frame",
        "render",
        "render_region",
        "decompose",
        "create",
        "extract",
        "compose",
        "accept_candidate",
    }
)
MUTATIONS = frozenset({"create", "extract", "compose", "accept_candidate"})
MAX_RESULT_BYTES = 128 * 1024 * 1024


def _worker(sink: _AtomicPDFWorkerResultSink, operation: str, arguments: tuple) -> None:
    try:
        _apply_worker_memory_limit(1536 * 1024 * 1024)
        if operation not in IMAGE_OPERATIONS:
            raise ValueError("Unknown native image operation")
        result = getattr(NativeImage(), operation)(*arguments)
        if operation in MUTATIONS:
            data, report = result
            result = [data, report.model_dump(mode="json")]
        sink.put(("ok", result))
    except Exception as exc:
        sink.put(("error", f"Native image operation failed: {str(exc)[:1500]}"))


class ProcessNativeImage:
    def __init__(self, timeout: float = 60.0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Native image timeout must be finite and positive")
        self.timeout = timeout

    def _run(self, operation: str, *arguments: Any) -> Any:
        if operation not in IMAGE_OPERATIONS:
            raise ValueError("Unknown native image operation")
        with tempfile.TemporaryDirectory(prefix="native-image-") as directory:
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
                raise ValueError("Native image operation exceeded its time limit")
            result = _read_pdf_worker_result(
                path, max_bytes=MAX_RESULT_BYTES, deadline=deadline
            )
            if result.failure:
                raise ValueError(f"Native image {result.failure}")
            if process.exitcode != 0:
                raise ValueError("Native image worker exited unsuccessfully")
            if result.status != "ok":
                raise ValueError(result.payload)
            if operation in MUTATIONS:
                data, report = result.payload
                if not isinstance(data, bytes):
                    raise ValueError(
                        "Native image worker returned invalid document bytes"
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

    def records(self, data: bytes) -> Any:
        return self._run("records", data)

    def read_frame(self, data: bytes, locator: Any) -> Any:
        return self._run("read_frame", data, locator)

    def render(
        self,
        data: bytes,
        locator: Any,
        size: int,
        color_policy: str = "embedded_to_srgb",
    ) -> Any:
        return self._run("render", data, locator, size, color_policy)

    def render_region(
        self,
        data: bytes,
        locator: Any,
        selector: Any,
        size: int,
        color_policy: str = "embedded_to_srgb",
    ) -> Any:
        return self._run("render_region", data, locator, selector, size, color_policy)

    def decompose(self, data: bytes, color_policy: str = "embedded_to_srgb") -> Any:
        return self._run("decompose", data, color_policy)

    def create(self, request: Any) -> Any:
        return self._run("create", request)

    def extract(self, data: bytes, request: Any) -> Any:
        return self._run("extract", data, request)

    def compose(self, request: Any, sources: dict[str, bytes]) -> Any:
        return self._run("compose", request, sources)

    def accept_candidate(
        self, data: bytes, candidate: bytes, request: Any, asset_id: str
    ) -> Any:
        return self._run("accept_candidate", data, candidate, request, asset_id)
