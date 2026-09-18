"""Native PDF worker handoff cannot hang on large or partial result frames."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from src.infrastructure import native_pdf_process
from src.infrastructure.native_pdf_process import ProcessNativePdf


def _large_worker(sink, operation, arguments):
    sink.put(("ok", {"binary": b"x" * (8 * 1024 * 1024)}))


def _partial_worker(sink, operation, arguments):
    Path(sink.result_path + ".partial").write_bytes(b"partial")
    time.sleep(30)


def _malformed_worker(sink, operation, arguments):
    path = Path(sink.result_path)
    path.write_bytes(b"not messagepack")
    path.chmod(0o600)


def _oversized_worker(sink, operation, arguments):
    path = Path(sink.result_path)
    path.touch(mode=0o600)
    with path.open("r+b") as stream:
        stream.truncate(sink.max_bytes + 1)


def test_large_result_does_not_wait_on_a_pipe(monkeypatch, tmp_path):
    monkeypatch.setattr(native_pdf_process, "_worker", _large_worker)
    monkeypatch.setattr(native_pdf_process.tempfile, "tempdir", str(tmp_path))
    assert ProcessNativePdf().inspect(b"input")["binary"] == b"x" * (8 * 1024 * 1024)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "worker,error",
    [
        (_partial_worker, "time limit"),
        (_malformed_worker, "could not be read"),
        (_oversized_worker, "byte limit"),
    ],
)
def test_failed_handoff_is_bounded_and_cleaned(monkeypatch, tmp_path, worker, error):
    monkeypatch.setattr(native_pdf_process, "_worker", worker)
    monkeypatch.setattr(native_pdf_process.tempfile, "tempdir", str(tmp_path))
    children = {p.pid for p in multiprocessing.active_children()}
    start = time.monotonic()
    with pytest.raises(ValueError, match=error):
        ProcessNativePdf(timeout=3).inspect(b"input")
    assert time.monotonic() - start < 7
    assert {p.pid for p in multiprocessing.active_children()} == children
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout_is_rejected(timeout):
    with pytest.raises(ValueError, match="finite and positive"):
        ProcessNativePdf(timeout=timeout)
