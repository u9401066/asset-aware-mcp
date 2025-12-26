"""
Domain Layer - Job Entities

ETL Job/Task entities for async document processing.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"  # Job created, waiting to start
    PROCESSING = "processing"  # Job is running
    COMPLETED = "completed"  # Job finished successfully
    FAILED = "failed"  # Job failed with error
    CANCELLED = "cancelled"  # Job was cancelled


class JobType(str, Enum):
    """Type of ETL job."""

    INGEST_PDF = "ingest_pdf"  # PDF document ingestion
    INGEST_BATCH = "ingest_batch"  # Multiple documents
    REINDEX = "reindex"  # Re-index existing document
    DELETE = "delete"  # Delete document


class JobProgress(BaseModel):
    """Progress information for a job."""

    current_step: int = Field(0, description="Current step number")
    total_steps: int = Field(0, description="Total number of steps")
    current_phase: str = Field("", description="Current phase name")
    message: str = Field("", description="Human-readable status message")
    percentage: float = Field(0.0, description="Completion percentage (0-100)")

    def update(
        self,
        step: int | None = None,
        phase: str | None = None,
        message: str | None = None,
    ) -> None:
        """Update progress."""
        if step is not None:
            self.current_step = step
        if phase is not None:
            self.current_phase = phase
        if message is not None:
            self.message = message
        if self.total_steps > 0:
            self.percentage = (self.current_step / self.total_steps) * 100


class Job(BaseModel):
    """
    ETL Job Entity.

    Represents an asynchronous document processing task.
    """

    job_id: str = Field(..., description="Unique job identifier")
    job_type: JobType = Field(..., description="Type of job")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current status")

    # Input
    input_files: list[str] = Field(default_factory=list, description="Input file paths")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Job parameters"
    )

    # Progress
    progress: JobProgress = Field(
        default_factory=lambda: JobProgress(), description="Progress info"
    )

    # Output
    output_doc_ids: list[str] = Field(
        default_factory=list, description="Output document IDs"
    )
    result: dict[str, Any] | None = Field(None, description="Final result data")
    error: str | None = Field(None, description="Error message if failed")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(None, description="When processing started")
    completed_at: datetime | None = Field(None, description="When job finished")

    # Metadata
    estimated_duration_seconds: int | None = Field(
        None, description="Estimated time to complete"
    )

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state (completed/failed/cancelled)."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    @property
    def duration_seconds(self) -> float | None:
        """Get job duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def start(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now()

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        self.progress.percentage = 100.0

    def fail(self, error: str) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now()

    def update_progress(
        self,
        step: int | None = None,
        total: int | None = None,
        phase: str | None = None,
        message: str | None = None,
    ) -> None:
        """Update job progress."""
        if total is not None:
            self.progress.total_steps = total
        self.progress.update(step=step, phase=phase, message=message)


class JobSummary(BaseModel):
    """Summary of a job for listing."""

    job_id: str
    job_type: JobType
    status: JobStatus
    progress_percentage: float = 0.0
    current_phase: str = ""
    message: str = ""
    input_file_count: int = 0
    output_doc_count: int = 0
    created_at: datetime
    duration_seconds: float | None = None
    error: str | None = None

    @classmethod
    def from_job(cls, job: Job) -> JobSummary:
        """Create summary from full job."""
        return cls(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            progress_percentage=job.progress.percentage,
            current_phase=job.progress.current_phase,
            message=job.progress.message,
            input_file_count=len(job.input_files),
            output_doc_count=len(job.output_doc_ids),
            created_at=job.created_at,
            duration_seconds=job.duration_seconds,
            error=job.error,
        )
