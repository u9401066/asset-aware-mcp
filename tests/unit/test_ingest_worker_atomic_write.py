"""Ingest worker JSON writes must survive Windows replace races.

On Windows os.replace() raises PermissionError (WinError 5) while the job runner
or antivirus holds progress.json open. A progress update must never fail the
ingestion, and result writes retry before giving up.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.application import ingest_worker


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(ingest_worker.time, "sleep", lambda _seconds: None)


def _flaky_replace(monkeypatch, failures: int) -> list[int]:
    real_replace = Path.replace
    calls = [0]

    def replace(self, target):
        calls[0] += 1
        if calls[0] <= failures:
            raise PermissionError(13, "Access is denied")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", replace)
    return calls


def _leftover_temps(directory: Path) -> list[Path]:
    return [p for p in directory.iterdir() if p.name.endswith(".tmp")]


def test_atomic_write_retries_a_locked_target(tmp_path, monkeypatch):
    calls = _flaky_replace(monkeypatch, failures=3)
    target = tmp_path / "result.json"

    ingest_worker._write_json_atomic(target, '{"ok": true}')

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert calls[0] == 4
    assert _leftover_temps(tmp_path) == []


def test_atomic_write_gives_up_after_its_attempts_and_cleans_up(tmp_path, monkeypatch):
    calls = _flaky_replace(monkeypatch, failures=10_000)
    target = tmp_path / "result.json"

    with pytest.raises(PermissionError):
        ingest_worker._write_json_atomic(target, "{}")

    assert calls[0] == ingest_worker._REPLACE_ATTEMPTS
    assert not target.exists()
    assert _leftover_temps(tmp_path) == []


def test_locked_progress_file_never_fails_the_ingestion(tmp_path, monkeypatch):
    calls = _flaky_replace(monkeypatch, failures=10_000)
    progress = tmp_path / "progress.json"
    callback = ingest_worker._make_progress_callback(progress)

    asyncio.run(callback(1, 3, "parse", "page 1"))

    assert calls[0] == ingest_worker._PROGRESS_REPLACE_ATTEMPTS
    assert not progress.exists()
    assert _leftover_temps(tmp_path) == []


def test_progress_update_lands_once_the_reader_lets_go(tmp_path, monkeypatch):
    _flaky_replace(monkeypatch, failures=1)
    progress = tmp_path / "progress.json"
    callback = ingest_worker._make_progress_callback(progress)

    asyncio.run(callback(2, 3, "chunk", "page 2"))

    data = json.loads(progress.read_text(encoding="utf-8"))
    assert (data["step"], data["total"], data["phase"]) == (2, 3, "chunk")
