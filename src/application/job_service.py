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
    from src.domain.repositories import JobStoreInterface

logger = logging.getLogger(__name__)


# Maximum concurrent ETL jobs to prevent resource exhaustion
MAX_CONCURRENT_JOBS = 5


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
        max_concurrent_jobs: int = MAX_CONCURRENT_JOBS,
    ) -> None:
        """
        Initialize job service.

        Args:
            job_store: Job storage implementation
            document_service: Document processing service
            max_concurrent_jobs: Maximum number of concurrent jobs
        """
        self.job_store = job_store
        self.document_service = document_service
        self.max_concurrent_jobs = max_concurrent_jobs
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._quota_lock = asyncio.Lock()

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
        async with self._quota_lock:
            # Check concurrent job limit while holding the slot reservation lock.
            active_count = len(self._running_tasks)
            if active_count >= self.max_concurrent_jobs:
                msg = (
                    f"Too many concurrent jobs ({active_count}/{self.max_concurrent_jobs}). "
                    "Wait for existing jobs to finish or cancel some."
                )
                raise RuntimeError(msg)

            # Generate unique job ID
            job_id = (
                f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            )

            # Estimate duration (rough: 10s per file)
            estimated_duration = len(file_paths) * 10
            job_parameters = parameters or {}
            base_steps = 9 if job_parameters.get("use_marker") else 8
            steps_per_file = base_steps + (
                1 if job_parameters.get("ocr_enabled") else 0
            )

            # Create job
            job = Job(
                job_id=job_id,
                job_type=JobType.INGEST_PDF
                if len(file_paths) == 1
                else JobType.INGEST_BATCH,
                status=JobStatus.PENDING,
                input_files=file_paths,
                parameters=job_parameters,
                progress=JobProgress(
                    total_steps=len(file_paths) * steps_per_file,
                    message="Job created, waiting to start...",
                ),
                estimated_duration_seconds=estimated_duration,
            )

            # Save job
            await self.job_store.create(job)

            # Start background processing
            task = asyncio.create_task(self._process_ingest_job(job_id))
            self._running_tasks[job_id] = task

            def forget_task(
                _task: asyncio.Task[None], task_job_id: str = job_id
            ) -> None:
                self._running_tasks.pop(task_job_id, None)

            task.add_done_callback(forget_task)

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
        task = self._running_tasks.pop(job_id, None)
        if task is not None:
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=5)
            except asyncio.CancelledError:
                pass
            except TimeoutError:
                logger.warning(
                    "Timed out waiting for job task cancellation: %s", job_id
                )

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
        job: Job | None = None
        try:
            job = await self.job_store.get(job_id)
            if job is None:
                logger.error(f"Job {job_id} not found")
                return

            # Start job
            job.start()
            job.progress.current_phase = "Starting"
            job.progress.message = "Initializing document processing..."
            await self.job_store.update(job)

            if self.document_service is None:
                raise RuntimeError("Document service not configured")

            total_files = len(job.input_files)
            base_steps = 9 if job.parameters.get("use_marker") else 8
            steps_per_file = base_steps + (
                1 if job.parameters.get("ocr_enabled") else 0
            )
            total_steps = max(total_files, 1) * steps_per_file
            job.update_progress(total=total_steps)
            await self.job_store.update(job)
            failed_files: list[dict[str, str]] = []

            for i, file_path in enumerate(job.input_files):
                filename = Path(file_path).name
                base_step = i * steps_per_file

                async def report_job_progress(
                    step: int,
                    _ignored_total: int,
                    phase: str,
                    message: str,
                    *,
                    _base_step: int = base_step,
                ) -> None:
                    current_job = await self.job_store.get(job_id)
                    if current_job is None or current_job.is_terminal:
                        return
                    current_job.update_progress(
                        step=_base_step + step,
                        total=total_steps,
                        phase=phase,
                        message=message,
                    )
                    await self.job_store.update(current_job)

                # Actually process the document (ingest() takes a list)
                try:
                    use_marker = job.parameters.get("use_marker", False)
                    if use_marker:
                        self._ensure_marker_extractor_for_job()
                    results = await self.document_service.ingest(
                        [file_path],
                        use_marker=use_marker,
                        progress_callback=report_job_progress,
                        ocr_enabled=job.parameters.get("ocr_enabled", False),
                        ocr_language=job.parameters.get("ocr_language", "eng"),
                        rotate_pages=job.parameters.get("rotate_pages", False),
                        deskew=job.parameters.get("deskew", False),
                        marker_max_pages_per_chunk=job.parameters.get(
                            "marker_max_pages_per_chunk",
                            0,
                        ),
                        extract_figures=job.parameters.get("extract_figures", True),
                        page_ranges=job.parameters.get("page_ranges") or None,
                    )
                    result = results[0] if results else None

                    if result is not None and result.success:
                        job.output_doc_ids.append(result.doc_id)
                    else:
                        error_msg = (
                            result.error
                            if result is not None and result.error is not None
                            else "No result returned"
                        )
                        failed_files.append({"file": file_path, "error": error_msg})
                        logger.warning(f"Failed to process {filename}: {error_msg}")
                        job.update_progress(
                            step=base_step + steps_per_file,
                            total=total_steps,
                            phase="Failed",
                            message=f"[{i + 1}/{total_files}] Failed processing {filename}: {error_msg}",
                        )
                        await self.job_store.update(job)

                except asyncio.CancelledError:
                    raise  # Re-raise cancellation
                except Exception as e:
                    error_msg = str(e)
                    failed_files.append({"file": file_path, "error": error_msg})
                    logger.error(f"Error processing {filename}: {e}")
                    job.update_progress(
                        step=base_step + steps_per_file,
                        total=total_steps,
                        phase="Failed",
                        message=f"[{i + 1}/{total_files}] Error processing {filename}: {error_msg}",
                    )
                    await self.job_store.update(job)

            result_payload = {
                "files_processed": total_files,
                "files_failed": len(failed_files),
                "documents_created": len(job.output_doc_ids),
                "doc_ids": job.output_doc_ids,
                "failed_files": failed_files,
            }
            if failed_files:
                error_msg = (
                    f"{len(failed_files)}/{total_files} file(s) failed during ingestion"
                )
                job.fail(error_msg)
                job.result = result_payload
                job.update_progress(
                    step=total_steps,
                    total=total_steps,
                    phase="Failed",
                    message=error_msg,
                )
            else:
                # Complete job only when every input file succeeded.
                job.complete(result=result_payload)
                job.update_progress(
                    step=total_steps,
                    total=total_steps,
                    phase="Completed",
                    message=f"Completed! Created {len(job.output_doc_ids)} document(s)",
                )
            await self.job_store.update(job)

            logger.info(
                "Job %s finished with status=%s: %d/%d files processed",
                job_id,
                job.status.value,
                len(job.output_doc_ids),
                total_files,
            )

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            if job is not None:
                job.cancel()
                job.progress.message = "Job cancelled by user"
                await self.job_store.update(job)

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            if job is not None:
                job.fail(str(e))
                job.progress.message = f"Failed: {e}"
                await self.job_store.update(job)

        finally:
            self._running_tasks.pop(job_id, None)

    def _ensure_marker_extractor_for_job(self) -> None:
        """Load the Marker extractor inside the background worker when requested."""
        if self.document_service is None:
            return
        if getattr(self.document_service, "marker_extractor", None) is not None:
            return
        try:
            from src.infrastructure.marker_adapter import MarkerPDFExtractor

            MarkerPDFExtractor.require_backend_available()
            self.document_service.marker_extractor = MarkerPDFExtractor()
        except Exception as exc:
            logger.warning(
                "Marker requested for background job but is unavailable: %s",
                exc,
                exc_info=True,
            )


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
