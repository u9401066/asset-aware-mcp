"""Unit tests for persistent job storage."""

from __future__ import annotations

import pytest

from src.domain.job import Job, JobProgress, JobType
from src.infrastructure.job_store import FileJobStore


@pytest.mark.asyncio
async def test_file_job_store_rejects_job_id_path_traversal(tmp_path) -> None:
    store = FileJobStore(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    assert await store.get("../outside") is None
    assert await store.delete("../outside") is False
    assert await store.get("/absolute/path") is None
    assert await store.delete("job_%2e%2e_outside") is False
    assert outside.exists()

    with pytest.raises(ValueError, match="Invalid job id"):
        await store.create(
            Job(
                job_id="../outside",
                job_type=JobType.INGEST_PDF,
                progress=JobProgress(total_steps=1),
            )
        )


@pytest.mark.asyncio
async def test_file_job_store_round_trips_valid_job(tmp_path) -> None:
    store = FileJobStore(tmp_path)
    job = Job(
        job_id="job_20260423_120000_abcdef12",
        job_type=JobType.INGEST_PDF,
        input_files=["paper.pdf"],
        progress=JobProgress(total_steps=8),
    )

    await store.create(job)

    loaded = await store.get(job.job_id)
    assert loaded is not None
    assert loaded.job_id == job.job_id
    assert loaded.input_files == ["paper.pdf"]
