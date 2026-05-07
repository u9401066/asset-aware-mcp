"""
Application Layer - Job Service

ETL Job management service with background task execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.entities import IngestResult
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
        self._worker_processes: dict[str, asyncio.subprocess.Process] = {}
        self._quota_lock = asyncio.Lock()
        self._instance_id = uuid.uuid4().hex
        self._started_at = datetime.now()

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
            job_parameters = dict(parameters or {})
            job_parameters.setdefault("job_owner_id", self._instance_id)
            job_parameters.setdefault("job_owner_pid", os.getpid())
            job_parameters.setdefault(
                "job_owner_started_at", self._started_at.isoformat()
            )
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
            task = asyncio.create_task(
                self._process_ingest_job(job_id, self.document_service)
            )
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
        job = await self.job_store.get(job_id)
        if job is not None:
            job = await self._mark_stale_if_untracked(job)
        return job

    async def get_job_status(self, job_id: str) -> JobSummary | None:
        """Get job status summary."""
        job = await self.get_job(job_id)
        if job is None:
            return None
        return JobSummary.from_job(job)

    async def list_jobs(self, limit: int = 20) -> list[JobSummary]:
        """List all jobs."""
        await self.reconcile_stale_active_jobs()
        return await self.job_store.list_all(limit)

    async def list_active_jobs(self) -> list[JobSummary]:
        """List active (running) jobs."""
        await self.reconcile_stale_active_jobs()
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

        # Cancel the task. The worker owns the final status update, so reload the
        # job after the task unwinds instead of writing a stale object back.
        task = self._running_tasks.get(job_id)
        if task is not None:
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=15)
            except asyncio.CancelledError:
                pass
            except TimeoutError:
                logger.warning(
                    "Timed out waiting for job task cancellation: %s", job_id
                )
                current = await self.job_store.get(job_id)
                if current is not None and not current.is_terminal:
                    current.progress.message = (
                        "Cancellation requested; worker is still stopping"
                    )
                    await self.job_store.update(current)
                return True
            if task.done():
                self._running_tasks.pop(job_id, None)

        latest = await self.job_store.get(job_id)
        if latest is None:
            return False
        if latest.is_terminal:
            logger.info(f"Cancelled job {job_id}")
            return True

        latest.cancel()
        latest.progress.message = "Job cancelled by user"
        await self.job_store.update(latest)

        logger.info(f"Cancelled job {job_id}")
        return True

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs."""
        return await self.job_store.cleanup_old(max_age_hours)

    async def reconcile_stale_active_jobs(self) -> int:
        """Fail persisted active jobs that no longer have an in-memory worker."""
        stale_count = 0
        for summary in await self.job_store.list_active():
            job = await self.job_store.get(summary.job_id)
            if job is None:
                continue
            was_terminal = job.is_terminal
            updated = await self._mark_stale_if_untracked(job)
            if not was_terminal and updated.is_terminal:
                stale_count += 1
        return stale_count

    # ========================================================================
    # Background Processing
    # ========================================================================

    async def _process_ingest_job(
        self,
        job_id: str,
        document_service: DocumentService | None = None,
    ) -> None:
        """
        Background task to process an ingestion job.

        This runs asynchronously and updates job status as it progresses.
        """
        job: Job | None = None
        document_service = document_service or self.document_service
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

            if document_service is None:
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
            documents: list[dict[str, Any]] = []
            all_warnings: list[str] = []

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
                    result: IngestResult | None
                    if use_marker:
                        job.update_progress(
                            step=base_step + 1,
                            total=total_steps,
                            phase="Marker Worker",
                            message=(
                                f"[{i + 1}/{total_files}] Running isolated Marker "
                                f"worker for {filename}"
                            ),
                        )
                        await self.job_store.update(job)
                        result = await self._run_isolated_ingest_worker(
                            job_id,
                            file_path,
                            job.parameters,
                        )
                    else:
                        results = await document_service.ingest(
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
                            require_marker=job.parameters.get("require_marker", False),
                        )
                        result = results[0] if results else None

                    if result is not None and result.success:
                        if (
                            job.parameters.get("require_marker")
                            and result.backend != "marker"
                        ):
                            error_msg = (
                                "Marker structure parse was required, but ingestion "
                                f"completed with backend={result.backend!r}."
                            )
                            failed_files.append({"file": file_path, "error": error_msg})
                            logger.warning(
                                "Failed strict Marker job for %s: %s",
                                filename,
                                error_msg,
                            )
                            continue
                        job.output_doc_ids.append(result.doc_id)
                        documents.append(
                            self._document_result_payload(
                                file_path,
                                result,
                                document_service=document_service,
                            )
                        )
                        all_warnings.extend(result.warnings)
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
                "documents": documents,
                "failed_files": failed_files,
                "warnings": all_warnings,
                "degraded": any(
                    item.get("backend") == "pymupdf_fallback" for item in documents
                ),
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
            self._worker_processes.pop(job_id, None)

    async def _mark_stale_if_untracked(self, job: Job) -> Job:
        """Mark persisted active jobs as failed after a server restart."""
        if job.is_terminal or job.job_id in self._running_tasks:
            return job
        owner_id = job.parameters.get("job_owner_id")
        if owner_id and owner_id != self._instance_id:
            owner_pid = job.parameters.get("job_owner_pid")
            if isinstance(owner_pid, int) and self._process_is_alive(owner_pid):
                return job

        job.fail("MCP server restarted before this job completed")
        job.progress.current_phase = "Interrupted"
        job.progress.message = (
            "This job was still active when the MCP server restarted. "
            "Start a new ingest job to continue."
        )
        await self.job_store.update(job)
        return job

    async def _run_isolated_ingest_worker(
        self,
        job_id: str,
        file_path: str,
        parameters: dict[str, Any],
    ) -> IngestResult:
        """Run Marker ingestion in a subprocess so stdio MCP remains responsive."""
        result_path = (
            Path(tempfile.gettempdir())
            / f"asset_aware_{job_id}_{uuid.uuid4().hex}_result.json"
        )
        cmd = [
            sys.executable,
            "-m",
            "src.application.ingest_worker",
            "--file",
            file_path,
            "--result-json",
            str(result_path),
            "--ocr-language",
            str(parameters.get("ocr_language", "eng")),
            "--marker-max-pages-per-chunk",
            str(parameters.get("marker_max_pages_per_chunk", 0)),
            "--page-ranges-json",
            json.dumps(parameters.get("page_ranges") or []),
        ]
        for flag, name in [
            ("use_marker", "--use-marker"),
            ("require_marker", "--require-marker"),
            ("ocr_enabled", "--ocr-enabled"),
            ("rotate_pages", "--rotate-pages"),
            ("deskew", "--deskew"),
            ("extract_figures", "--extract-figures"),
        ]:
            if parameters.get(flag):
                cmd.append(name)

        if profile_name := parameters.get("etl_profile"):
            cmd.extend(["--etl-profile", str(profile_name)])

        env = os.environ.copy()
        if profile_name := parameters.get("etl_profile"):
            env["ETL_PROFILE"] = str(profile_name)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(Path(__file__).resolve().parents[2]),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        self._worker_processes[job_id] = process
        try:
            return_code = await process.wait()
        except asyncio.CancelledError:
            await self._terminate_worker_process(process)
            raise
        finally:
            self._worker_processes.pop(job_id, None)

        if result_path.exists():
            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
                return IngestResult.model_validate(data)
            except Exception as exc:
                return IngestResult(
                    doc_id="",
                    filename=Path(file_path).name,
                    success=False,
                    error=f"Could not read isolated ingest worker result: {exc}",
                )
            finally:
                result_path.unlink(missing_ok=True)

        return IngestResult(
            doc_id="",
            filename=Path(file_path).name,
            success=False,
            error=f"Isolated ingest worker exited with code {return_code}",
        )

    async def _terminate_worker_process(
        self, process: asyncio.subprocess.Process
    ) -> None:
        """Terminate a subprocess worker with a bounded kill fallback."""
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()
            await process.wait()

    def _process_is_alive(self, pid: int) -> bool:
        """Best-effort owner liveness check for stale job reconciliation."""
        if pid <= 0:
            return False
        if pid == os.getpid():
            return True
        if os.name == "nt":
            return self._windows_process_is_alive(pid)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _windows_process_is_alive(self, pid: int) -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return str(pid) in result.stdout

    def _document_result_payload(
        self,
        file_path: str,
        result: IngestResult,
        *,
        document_service: DocumentService,
    ) -> dict[str, Any]:
        """Build a compact, citation-ready job result for a successful ingest."""
        payload: dict[str, Any] = {
            "file": file_path,
            "doc_id": result.doc_id,
            "backend": result.backend,
            "warnings": result.warnings,
            "pages_processed": result.pages_processed,
            "tables_found": result.tables_found,
            "figures_found": result.figures_found,
            "sections_found": result.sections_found,
        }
        if result.manifest is not None:
            payload["manifest_path"] = result.manifest.manifest_path
            payload["markdown_path"] = result.manifest.markdown_path

        try:
            doc_dir = document_service.repository.get_doc_dir(result.doc_id)
        except Exception:
            return payload

        artifact_candidates = {
            "manifest": doc_dir / f"{result.doc_id}_manifest.json",
            "markdown": doc_dir / f"{result.doc_id}_full.md",
            "blocks": doc_dir / "blocks.json",
            "segmentation": doc_dir / "segmentation.json",
        }
        artifacts = {
            name: str(path)
            for name, path in artifact_candidates.items()
            if path.exists()
        }
        payload["artifacts"] = artifacts
        payload["blocks_available"] = "blocks" in artifacts
        payload["segmentation_available"] = "segmentation" in artifacts
        return payload


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
