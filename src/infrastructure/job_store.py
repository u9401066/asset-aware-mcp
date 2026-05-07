"""
Infrastructure Layer - Job Store

Persistent storage for ETL jobs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.repositories import JobStoreInterface

if TYPE_CHECKING:
    from src.domain.job import Job, JobSummary

logger = logging.getLogger(__name__)

_JOB_ID_RE = re.compile(r"^job_[A-Za-z0-9_-]+$")


class FileJobStore(JobStoreInterface):
    """
    File-based job store.

    Stores each job as a JSON file for persistence across restarts.
    """

    def __init__(self, data_dir: str | Path) -> None:
        """
        Initialize file job store.

        Args:
            data_dir: Base data directory
        """
        self.jobs_dir = (Path(data_dir) / "jobs").resolve()
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _job_path(self, job_id: str) -> Path:
        """Get file path for a job while preventing path traversal."""
        if not _JOB_ID_RE.fullmatch(job_id):
            raise ValueError(f"Invalid job id: {job_id}")

        path = (self.jobs_dir / f"{job_id}.json").resolve()
        try:
            path.relative_to(self.jobs_dir)
        except ValueError as exc:
            raise ValueError(f"Job path escapes storage root: {job_id}") from exc
        return path

    def _atomic_write_job(self, path: Path, job: Job) -> None:
        """Write a job JSON file without exposing partial contents."""
        tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(job.model_dump(mode="json"), f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            tmp_path.replace(path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    async def create(self, job: Job) -> Job:
        """Create a new job."""
        path = self._job_path(job.job_id)
        if path.exists():
            raise ValueError(f"Job {job.job_id} already exists")

        self._atomic_write_job(path, job)

        logger.info(f"Created job: {job.job_id}")
        return job

    async def get(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        from src.domain.job import Job

        try:
            path = self._job_path(job_id)
        except ValueError:
            return None
        if not path.exists():
            return None

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            return Job.model_validate(data)
        except Exception as e:
            logger.error(f"Error loading job {job_id}: {e}")
            return None

    async def update(self, job: Job) -> Job:
        """Update an existing job."""
        path = self._job_path(job.job_id)

        self._atomic_write_job(path, job)

        return job

    async def delete(self, job_id: str) -> bool:
        """Delete a job."""
        try:
            path = self._job_path(job_id)
        except ValueError:
            return False
        if path.exists():
            path.unlink()
            logger.info(f"Deleted job: {job_id}")
            return True
        return False

    async def list_all(self, limit: int = 50) -> list[JobSummary]:
        """List all jobs (most recent first)."""
        from src.domain.job import Job, JobSummary

        jobs: list[tuple[datetime, JobSummary]] = []

        for path in self.jobs_dir.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as f:
                    data = json.load(f)
                job = Job.model_validate(data)
                jobs.append((job.created_at, JobSummary.from_job(job)))
            except Exception as e:
                logger.warning(f"Error loading job {path.stem}: {e}")

        # Sort by created_at descending
        jobs.sort(key=lambda x: x[0], reverse=True)

        return [summary for _, summary in jobs[:limit]]

    async def list_active(self) -> list[JobSummary]:
        """List active (non-terminal) jobs."""
        from src.domain.job import Job, JobSummary

        active: list[JobSummary] = []

        for path in self.jobs_dir.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as f:
                    data = json.load(f)
                job = Job.model_validate(data)
                if not job.is_terminal:
                    active.append(JobSummary.from_job(job))
            except Exception as e:
                logger.warning(f"Error loading job {path.stem}: {e}")

        return active

    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Delete old completed/failed jobs."""
        from src.domain.job import Job

        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted = 0

        for path in self.jobs_dir.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as f:
                    data = json.load(f)
                job = Job.model_validate(data)

                if job.is_terminal and job.created_at.timestamp() < cutoff:
                    path.unlink()
                    deleted += 1
                    logger.info(f"Cleaned up old job: {job.job_id}")
            except Exception as e:
                logger.warning(f"Error checking job {path.stem}: {e}")

        return deleted


class InMemoryJobStore(JobStoreInterface):
    """
    In-memory job store (for testing or single-session use).
    """

    def __init__(self) -> None:
        """Initialize in-memory store."""
        self._jobs: dict[str, Job] = {}

    async def create(self, job: Job) -> Job:
        """Create a new job."""
        if job.job_id in self._jobs:
            raise ValueError(f"Job {job.job_id} already exists")
        self._jobs[job.job_id] = job
        return job

    async def get(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def update(self, job: Job) -> Job:
        """Update an existing job."""
        self._jobs[job.job_id] = job
        return job

    async def delete(self, job_id: str) -> bool:
        """Delete a job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    async def list_all(self, limit: int = 50) -> list[JobSummary]:
        """List all jobs."""
        from src.domain.job import JobSummary

        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [JobSummary.from_job(job) for job in jobs[:limit]]

    async def list_active(self) -> list[JobSummary]:
        """List active jobs."""
        from src.domain.job import JobSummary

        return [
            JobSummary.from_job(job)
            for job in self._jobs.values()
            if not job.is_terminal
        ]

    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Delete old jobs."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_delete = [
            job_id
            for job_id, job in self._jobs.items()
            if job.is_terminal and job.created_at.timestamp() < cutoff
        ]

        for job_id in to_delete:
            del self._jobs[job_id]

        return len(to_delete)
