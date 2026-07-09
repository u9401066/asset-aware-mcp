"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

# ============================================================================
# Docx Tools
# ============================================================================


class TestJobTools:
    """Tests for job_tools.py MCP functions."""

    async def test_get_job_status_not_found(self) -> None:
        """get_job_status returns error for unknown job."""
        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.get_job = AsyncMock(return_value=None)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_nonexistent")
            assert "❌" in result

    async def test_cancel_job_success(self) -> None:
        """cancel_job returns confirmation."""
        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.cancel_job = AsyncMock(return_value=True)
            from src.presentation.tools.job_tools import cancel_job

            result = await cancel_job("job_123")
            assert "🚫" in result

    async def test_cancel_job_not_found(self) -> None:
        """cancel_job returns error when job not found."""
        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.cancel_job = AsyncMock(return_value=False)
            from src.presentation.tools.job_tools import cancel_job

            result = await cancel_job("job_nonexistent")
            assert "❌" in result

    async def test_job_op_routes_existing_tools(self) -> None:
        """job(op, ...) provides one operation-based entrypoint for job CRUD."""
        with patch("src.presentation.tools.job_tools.get_job_status") as mock_status:
            mock_status.return_value = "job status"
            from src.presentation.tools.job_tools import job

            result = await job("get", job_id="job_123")

        assert result == "job status"
        mock_status.assert_awaited_once_with("job_123")

    async def test_job_op_rejects_unknown_operation(self) -> None:
        """job(op, ...) fails closed for unknown operations."""
        from src.presentation.tools.job_tools import job

        result = await job("archive", job_id="job_123")

        assert "Unsupported job op" in result

    async def test_job_op_rejects_missing_job_id_for_cancel(self) -> None:
        """job(op='cancel') requires a target job_id."""
        from src.presentation.tools.job_tools import job

        result = await job("cancel")

        assert "job_id is required" in result

    async def test_job_op_routes_cancel(self) -> None:
        """job(op='cancel') delegates to the legacy cancellation tool."""
        with patch("src.presentation.tools.job_tools.cancel_job") as mock_cancel:
            mock_cancel.return_value = "cancelled"
            from src.presentation.tools.job_tools import job

            result = await job("cancel", job_id="job_123")

        assert result == "cancelled"
        mock_cancel.assert_awaited_once_with("job_123")

    async def test_get_job_status_shows_backend_warnings_and_artifacts(self) -> None:
        """Completed jobs expose backend, warnings, artifacts, and next commands."""
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        job = Job(
            job_id="job_status_details",
            job_type=JobType.INGEST_PDF,
            status=JobStatus.COMPLETED,
            input_files=["paper.pdf"],
            output_doc_ids=["doc_123"],
            progress=JobProgress(total_steps=8, current_step=8, percentage=100),
            result={
                "documents": [
                    {
                        "file": "paper.pdf",
                        "doc_id": "doc_123",
                        "backend": "pymupdf_fallback",
                        "warnings": ["Marker was unavailable"],
                        "artifacts": {
                            "manifest": "data/doc_123/doc_123_manifest.json",
                            "markdown": "data/doc_123/doc_123_full.md",
                            "blocks": "data/doc_123/blocks.json",
                            "ai_safety_report": "data/doc_123/ai_safety_report.json",
                            "native_structure": "data/doc_123/native_structure.json",
                            "segmentation_coverage": "data/doc_123/segmentation_coverage.json",
                        },
                        "blocks_available": True,
                        "audit_artifacts_available": True,
                    }
                ],
                "warnings": ["Marker was unavailable"],
            },
        )

        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.get_job = AsyncMock(return_value=job)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_status_details")

        assert "pymupdf_fallback" in result
        assert "Marker was unavailable" in result
        assert "data/doc_123/blocks.json" in result
        assert "data/doc_123/ai_safety_report.json" in result
        assert 'document(op="prepare_ai", doc_id="doc_123")' in result
        assert 'document(op="audit", doc_id="doc_123")' in result
        assert 'export_document_segmentation("doc_123")' not in result

    async def test_get_job_status_docx_document_gets_docx_next_commands(self) -> None:
        """A DOCX entry in a mixed-batch job must not suggest PDF-only ops.

        Regression coverage: `document(op=...)` is the PDF facade; a DOCX
        doc_id has no manifest.json and would 404 there. Mixed-batch
        documents carry a `format` field precisely so this render can pick
        the correct facade (`docx(...)`) per entry.
        """
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        job = Job(
            job_id="job_mixed_batch",
            job_type=JobType.CONVERSION,
            status=JobStatus.COMPLETED,
            input_files=["paper.pdf", "summary.docx"],
            progress=JobProgress(total_steps=2, current_step=2, percentage=100),
            result={
                "conversion": {"operation": "ingest_mixed_batch"},
                "documents": [
                    {
                        "file": "paper.pdf",
                        "doc_id": "doc_pdf_1",
                        "backend": "pymupdf",
                        "format": "pdf",
                    },
                    {
                        "file": "summary.docx",
                        "doc_id": "docx_summary_1",
                        "backend": "docx",
                        "format": "docx",
                    },
                ],
                "failed_files": [],
            },
        )

        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.get_job = AsyncMock(return_value=job)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_mixed_batch")

        assert 'document(op="prepare_ai", doc_id="doc_pdf_1")' in result
        assert 'docx(op="get", doc_id="docx_summary_1")' in result
        assert 'docx(op="blocks", doc_id="docx_summary_1")' in result
        assert 'docx(op="validate", doc_id="docx_summary_1")' in result
        assert 'document(op="inspect", doc_id="docx_summary_1")' not in result

    async def test_get_job_status_refreshes_artifacts_created_after_ingest(
        self, tmp_path: Path
    ) -> None:
        """Job status should discover audit artifacts created after the job finished."""
        from src.domain.entities import DocumentManifest
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        doc_dir = tmp_path / "doc_123"
        doc_dir.mkdir()
        (doc_dir / "doc_123_manifest.json").write_text("{}", encoding="utf-8")
        (doc_dir / "ai_safety_report.json").write_text("{}", encoding="utf-8")
        (doc_dir / "native_structure.json").write_text("{}", encoding="utf-8")
        (doc_dir / "segmentation_coverage.json").write_text("{}", encoding="utf-8")
        manifest = DocumentManifest(
            doc_id="doc_123",
            filename="paper.pdf",
            page_count=1,
            manifest_path=str(doc_dir / "doc_123_manifest.json"),
        )
        job = Job(
            job_id="job_stale_artifacts",
            job_type=JobType.INGEST_PDF,
            status=JobStatus.COMPLETED,
            input_files=["paper.pdf"],
            output_doc_ids=["doc_123"],
            progress=JobProgress(total_steps=8, current_step=8, percentage=100),
            result={
                "documents": [
                    {
                        "file": "paper.pdf",
                        "doc_id": "doc_123",
                        "backend": "pymupdf",
                        "artifacts": {},
                    }
                ]
            },
        )

        with (
            patch("src.presentation.tools.job_tools.job_service") as mock_svc,
            patch("src.presentation.tools.job_tools.repository", create=True) as repo,
        ):
            mock_svc.get_job = AsyncMock(return_value=job)
            repo.load_manifest.return_value = manifest
            repo.get_doc_dir.side_effect = AssertionError(
                "job status artifact discovery must be read-only"
            )
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_stale_artifacts")

        assert str(doc_dir / "ai_safety_report.json") in result
        assert str(doc_dir / "native_structure.json") in result
        assert str(doc_dir / "segmentation_coverage.json") in result

    async def test_get_job_status_does_not_create_doc_dir_when_refreshing_artifacts(
        self, tmp_path: Path
    ) -> None:
        """Read-only job status must not create storage directories for old doc IDs."""
        from src.domain.job import Job, JobProgress, JobStatus, JobType
        from src.infrastructure.file_storage import FileStorage

        storage = FileStorage(tmp_path)
        job = Job(
            job_id="job_no_side_effects",
            job_type=JobType.INGEST_PDF,
            status=JobStatus.COMPLETED,
            input_files=["paper.pdf"],
            output_doc_ids=["doc_missing"],
            progress=JobProgress(total_steps=8, current_step=8, percentage=100),
            result={
                "documents": [
                    {
                        "file": "paper.pdf",
                        "doc_id": "doc_missing",
                        "backend": "pymupdf",
                        "artifacts": {},
                    }
                ]
            },
        )

        with (
            patch("src.presentation.tools.job_tools.job_service") as mock_svc,
            patch("src.presentation.tools.job_tools.repository", storage),
        ):
            mock_svc.get_job = AsyncMock(return_value=job)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_no_side_effects")

        assert "doc_missing" in result
        assert not (tmp_path / "doc_missing").exists()

    async def test_get_job_status_output_doc_ids_only_shows_facade_next_actions(
        self,
    ) -> None:
        """Old persisted jobs with only output_doc_ids still guide agents forward."""
        from src.domain.job import Job, JobProgress, JobStatus, JobType

        job = Job(
            job_id="job_old_schema",
            job_type=JobType.INGEST_PDF,
            status=JobStatus.COMPLETED,
            input_files=["paper.pdf"],
            output_doc_ids=["doc_old"],
            progress=JobProgress(total_steps=8, current_step=8, percentage=100),
            result={},
        )

        with patch("src.presentation.tools.job_tools.job_service") as mock_svc:
            mock_svc.get_job = AsyncMock(return_value=job)
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_old_schema")

        assert 'document(op="prepare_ai", doc_id="doc_old")' in result
        assert 'document(op="audit", doc_id="doc_old")' in result

    async def test_get_job_status_shows_stale_recovery_context(self) -> None:
        """Interrupted active jobs keep enough context to resume after restart."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobSummary, JobType

        class MemoryJobStore:
            def __init__(self) -> None:
                self.jobs: dict[str, Job] = {}

            async def create(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def get(self, job_id: str) -> Job | None:
                return self.jobs.get(job_id)

            async def update(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def list_active(self):
                return [
                    JobSummary.from_job(job)
                    for job in self.jobs.values()
                    if not job.is_terminal
                ]

            async def list_all(self, limit: int = 20):
                return [JobSummary.from_job(job) for job in self.jobs.values()]

        store = MemoryJobStore()
        job = Job(
            job_id="job_stale_context",
            job_type=JobType.INGEST_BATCH,
            status=JobStatus.PROCESSING,
            input_files=["/workspace/paper-a.pdf", "/workspace/paper-b.pdf"],
            output_doc_ids=["doc_partial"],
            progress=JobProgress(
                current_step=4,
                total_steps=16,
                current_phase="PDF Worker",
                message="[1/2] Running isolated PyMuPDF worker for paper-a.pdf",
                percentage=25,
            ),
            error="last visible worker error",
            result={
                "documents": [
                    {
                        "file": "/workspace/paper-a.pdf",
                        "doc_id": "doc_partial",
                        "backend": "pymupdf",
                    }
                ],
                "failed_files": [
                    {
                        "file": "/workspace/paper-b.pdf",
                        "error": "worker timeout before restart",
                    }
                ],
            },
        )
        await store.create(job)
        service = JobService(job_store=store)

        with patch("src.presentation.tools.job_tools.job_service", service):
            from src.presentation.tools.job_tools import get_job_status

            result = await get_job_status("job_stale_context")

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert "/workspace/paper-a.pdf" in result
        assert "/workspace/paper-b.pdf" in result
        assert "PDF Worker" in result
        assert "[1/2] Running isolated PyMuPDF worker" in result
        assert "last visible worker error" in result
        assert "worker timeout before restart" in result
        assert "doc_partial" in result
        assert "MCP server restarted before this job completed" in result

    async def test_list_jobs_shows_stale_recovery_context(self) -> None:
        """Recent job listing exposes stale-job recovery context, not just counts."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobSummary, JobType

        class MemoryJobStore:
            def __init__(self) -> None:
                self.jobs: dict[str, Job] = {}

            async def create(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def get(self, job_id: str) -> Job | None:
                return self.jobs.get(job_id)

            async def update(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def list_active(self):
                return [
                    JobSummary.from_job(job)
                    for job in self.jobs.values()
                    if not job.is_terminal
                ]

            async def list_all(self, limit: int = 20):
                return [JobSummary.from_job(job) for job in self.jobs.values()]

        store = MemoryJobStore()
        job = Job(
            job_id="job_stale_list_context",
            job_type=JobType.INGEST_PDF,
            status=JobStatus.PENDING,
            input_files=["/workspace/orphan.pdf"],
            output_doc_ids=["doc_orphan_partial"],
            progress=JobProgress(
                current_phase="Queued",
                message="Job created, waiting to start...",
            ),
            error="queue owner disappeared",
        )
        await store.create(job)
        service = JobService(job_store=store)

        with patch("src.presentation.tools.job_tools.job_service", service):
            from src.presentation.tools.job_tools import list_jobs

            result = await list_jobs(active_only=False)

        assert "job_stale_list_context" in result
        assert "failed" in result
        assert "/workspace/orphan.pdf" in result
        assert "Queued" in result
        assert "Job created, waiting to start" in result
        assert "queue owner disappeared" in result
        assert "doc_orphan_partial" in result


# ============================================================================
# Document Tools
# ============================================================================
