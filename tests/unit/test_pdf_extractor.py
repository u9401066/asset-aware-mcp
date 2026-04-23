from __future__ import annotations

from pathlib import Path

from src.infrastructure.pdf_extractor import PyMuPDFExtractor


class _FakeQueue:
    def __init__(self, payload: tuple[str, object] | None = None):
        self._payload = payload

    def get_nowait(self) -> tuple[str, object]:
        if self._payload is None:
            raise RuntimeError("empty queue")
        return self._payload


class _FakeProcess:
    def __init__(self, *, alive_after_join: bool):
        self._alive_after_join = alive_after_join
        self.terminated = False
        self.join_calls: list[float] = []

    def start(self) -> None:
        return None

    def join(self, timeout: float | None = None) -> None:
        if timeout is not None:
            self.join_calls.append(timeout)

    def is_alive(self) -> bool:
        return self._alive_after_join

    def terminate(self) -> None:
        self.terminated = True


class _FakeContext:
    def __init__(self, queue: _FakeQueue, process: _FakeProcess):
        self._queue = queue
        self._process = process

    def Queue(self) -> _FakeQueue:
        return self._queue

    def Process(self, **_: object) -> _FakeProcess:
        return self._process


def test_extract_figure_captions_returns_worker_payload(monkeypatch) -> None:
    expected = {3: [{"number": "3", "caption": "Figure 3. Example caption"}]}
    queue = _FakeQueue(("ok", expected))
    process = _FakeProcess(alive_after_join=False)
    context = _FakeContext(queue, process)
    monkeypatch.setattr(
        "src.infrastructure.pdf_extractor.multiprocessing.get_context",
        lambda _method: context,
    )

    extractor = PyMuPDFExtractor()

    result = extractor.extract_figure_captions(Path("/tmp/test.pdf"))

    assert result == expected
    assert process.join_calls == [20.0]
    assert process.terminated is False


def test_extract_figure_captions_times_out_and_returns_empty(monkeypatch) -> None:
    queue = _FakeQueue()
    process = _FakeProcess(alive_after_join=True)
    context = _FakeContext(queue, process)
    monkeypatch.setattr(
        "src.infrastructure.pdf_extractor.multiprocessing.get_context",
        lambda _method: context,
    )

    extractor = PyMuPDFExtractor()

    result = extractor.extract_figure_captions(Path("/tmp/test.pdf"))

    assert result == {}
    assert process.join_calls == [20.0, 5]
    assert process.terminated is True
