"""
Application Layer - Job Service

ETL Job management service with background task execution.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.job import Job, JobProgress, JobStatus, JobSummary, JobType

if TYPE_CHECKING:
    from src.application.document_service import DocumentService
    from src.infrastructure.job_store import JobStoreInterface

logger = logging.getLogger(__name__)


class JobService:
    """
    Application service for ETL job management.

    Handles:
    - Job creation and tracking
    - Background task execution
    - Progress updates
    - Job lifecycle management
    """

    def __init__(
        self,
        job_store: JobStoreInterface,
        document_service: DocumentService | None = None,
    ) -> None:
        """
        Initialize job service.

        Args:
            job_store: Job storage implementation
            document_service: Document processing service
        """
        self.job_store = job_store
        self.document_service = document_service
        self._running_tasks: dict[str, asyncio.Task[None]] = {}

    def set_document_service(self, document_service: DocumentService) -> None:
        """Set document service (for late binding)."""
        self.document_service = document_service

    async def create_ingest_job(
        self,
        file_paths: list[str],
        parameters: dict[str, Any] | None = None,
    ) -> Job:
        """
        Create a new document ingestion job.

        Args:
            file_paths: List of PDF file paths to process
            parameters: Optional processing parameters

        Returns:
            Created job with ID for tracking
        """
        # Generate unique job ID
        job_id = (
            f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # Estimate duration (rough: 10s per file)
        estimated_duration = len(file_paths) * 10

        # Create job
        job = Job(
            job_id=job_id,
            job_type=JobType.INGEST_PDF
            if len(file_paths) == 1
            else JobType.INGEST_BATCH,
            status=JobStatus.PENDING,
            input_files=file_paths,
            parameters=parameters or {},
            progress=JobProgress(
                total_steps=len(file_paths) * 5,  # 5 steps per file
                message="Job created, waiting to start...",
            ),
            estimated_duration_seconds=estimated_duration,
        )

        # Save job
        await self.job_store.create(job)

        # Start background processing
        task = asyncio.create_task(self._process_ingest_job(job_id))
        self._running_tasks[job_id] = task

        logger.info(f"Created ingest job {job_id} for {len(file_paths)} file(s)")
        return job

    async def get_job(self, job_id: str) -> Job | None:
        """Get job by ID."""
        return await self.job_store.get(job_id)

    async def get_job_status(self, job_id: str) -> JobSummary | None:
        """Get job status summary."""
        job = await self.job_store.get(job_id)
        if job is None:
            return None
        return JobSummary.from_job(job)

    async def list_jobs(self, limit: int = 20) -> list[JobSummary]:
        """List all jobs."""
        return await self.job_store.list_all(limit)

    async def list_active_jobs(self) -> list[JobSummary]:
        """List active (running) jobs."""
        return await self.job_store.list_active()

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Returns:
            True if job was cancelled, False if not found or already terminal
        """
        job = await self.job_store.get(job_id)
        if job is None or job.is_terminal:
            return False

        # Cancel the task
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            del self._running_tasks[job_id]

        # Update job status
        job.cancel()
        await self.job_store.update(job)

        logger.info(f"Cancelled job {job_id}")
        return True

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs."""
        return await self.job_store.cleanup_old(max_age_hours)

    # ========================================================================
    # Background Processing
    # ========================================================================

    async def _process_ingest_job(self, job_id: str) -> None:
        """
        Background task to process an ingestion job.

        This runs asynchronously and updates job status as it progresses.
        """
        job = await self.job_store.get(job_id)
        if job is None:
            logger.error(f"Job {job_id} not found")
            return

        try:
            # Start job
            job.start()
            job.progress.current_phase = "Starting"
            job.progress.message = "Initializing document processing..."
            await self.job_store.update(job)

            if self.document_service is None:
                raise RuntimeError("Document service not configured")

            total_files = len(job.input_files)
            step = 0

            for i, file_path in enumerate(job.input_files):
                filename = Path(file_path).name

                # Phase 1: Extract
                step += 1
                job.update_progress(
                    step=step,
                    phase="Extracting",
                    message=f"[{i + 1}/{total_files}] Extracting text from {filename}...",
                )
                await self.job_store.update(job)

                # Actually process the document (ingest() takes a list)
                try:
                    results = await self.document_service.ingest([file_path])
                    result = results[0] if results else None

                    if result is not None and result.success:
                        job.output_doc_ids.append(result.doc_id)

                        # Update progress through phases
                        phases = [
                            "Converting",
                            "Indexing",
                            "Generating Manifest",
                            "Finalizing",
                        ]
                        for phase in phases:
                            step += 1
                            job.update_progress(
                                step=step,
                                phase=phase,
                                message=f"[{i + 1}/{total_files}] {phase} {filename}...",
                            )
                            await self.job_store.update(job)
                            # Small delay to show progress
                            await asyncio.sleep(0.1)
                    else:
                        # File failed but continue with others
                        step += 4  # Skip remaining phases for this file
                        error_msg = result.error if result else "No result returned"
                        logger.warning(f"Failed to process {filename}: {error_msg}")

                except asyncio.CancelledError:
                    raise  # Re-raise cancellation
                except Exception as e:
                    step += 4
                    logger.error(f"Error processing {filename}: {e}")

            # Complete job
            job.complete(
                result={
                    "files_processed": total_files,
                    "documents_created": len(job.output_doc_ids),
                    "doc_ids": job.output_doc_ids,
                }
            )
            job.progress.message = (
                f"Completed! Created {len(job.output_doc_ids)} document(s)"
            )
            await self.job_store.update(job)

            logger.info(
                f"Job {job_id} completed: {len(job.output_doc_ids)}/{total_files} files processed"
            )

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            job.cancel()
            job.progress.message = "Job cancelled by user"
            await self.job_store.update(job)

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.fail(str(e))
            job.progress.message = f"Failed: {e}"
            await self.job_store.update(job)

        finally:
            # Clean up task reference
            if job_id in self._running_tasks:
                del self._running_tasks[job_id]


# ============================================================================
# Progress Reporter for Document Service Integration
# ============================================================================


class JobProgressReporter:
    """
    Progress reporter that integrates with job service.

    Can be passed to document service to update job progress.
    """

    def __init__(self, job_service: JobService, job_id: str) -> None:
        """Initialize reporter."""
        self.job_service = job_service
        self.job_id = job_id

    async def report(
        self,
        step: int | None = None,
        phase: str | None = None,
        message: str | None = None,
    ) -> None:
        """Report progress update."""
        job = await self.job_service.get_job(self.job_id)
        if job and not job.is_terminal:
            job.update_progress(step=step, phase=phase, message=message)
            await self.job_service.job_store.update(job)
