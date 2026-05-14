"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ============================================================================
# Docx Tools
# ============================================================================


class TestJobServiceConcurrency:
    """Tests for job concurrency limit."""

    async def test_concurrent_job_limit(self) -> None:
        """JobService raises RuntimeError when limit exceeded."""
        from src.application.job_service import JobService

        mock_store = AsyncMock()
        mock_store.create = AsyncMock()
        service = JobService(job_store=mock_store, max_concurrent_jobs=2)

        # Simulate 2 running tasks
        service._running_tasks = {"job_1": MagicMock(), "job_2": MagicMock()}

        with pytest.raises(RuntimeError, match="Too many concurrent jobs"):
            await service.create_ingest_job(["/test.pdf"])

    async def test_conversion_job_completes_with_artifact_payload(self) -> None:
        """JobService can run conversion handlers outside the MCP request path."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobStatus, JobSummary

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

            async def list_active(self) -> list[JobSummary]:
                return []

            async def list_all(self, _limit: int = 20) -> list[JobSummary]:
                return []

            async def cleanup_old(self, _max_age_hours: int) -> int:
                return 0

        async def handler(progress) -> dict:
            await progress.report(step=2, phase="Converting", message="running")
            return {
                "success": True,
                "operation": "pdf_to_docx",
                "output_path": "/workspace/out.docx",
            }

        store = MemoryJobStore()
        service = JobService(job_store=store)
        job = await service.create_conversion_job(
            operation="pdf_to_docx",
            handler=handler,
            parameters={"source": "doc_123"},
        )
        task = service._running_tasks[job.job_id]
        await asyncio.wait_for(task, timeout=1)

        stored = await store.get(job.job_id)
        assert stored.status == JobStatus.COMPLETED
        assert stored.result["conversion"]["output_path"] == "/workspace/out.docx"

    async def test_ingest_job_failure_is_not_marked_completed(self) -> None:
        """Failed file results must not be reported as a green completed job."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        class FailingDocumentService:
            async def ingest(self, *_args, **_kwargs):
                return [
                    IngestResult(
                        doc_id="",
                        filename="bad.pdf",
                        success=False,
                        error="bad pdf",
                    )
                ]

        store = MemoryJobStore()
        job = Job(
            job_id="job_test_failure",
            job_type=JobType.INGEST_PDF,
            input_files=["bad.pdf"],
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=FailingDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="",
                filename="bad.pdf",
                success=False,
                error="bad pdf",
                warnings=["Isolated ingest worker log: logs/bad.log"],
            )
        )

        await service._process_ingest_job(job.job_id)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert stored.error == "1/1 file(s) failed during ingestion"
        assert stored.result is not None
        assert stored.result["files_failed"] == 1
        assert stored.result["failed_files"] == [
            {
                "file": "bad.pdf",
                "error": "bad pdf",
                "warnings": ["Isolated ingest worker log: logs/bad.log"],
            }
        ]
        assert stored.result["warnings"] == ["Isolated ingest worker log: logs/bad.log"]

    async def test_pymupdf_job_uses_isolated_worker_not_event_loop_ingest(
        self, temp_dir: Path
    ) -> None:
        """Background PyMuPDF jobs also avoid blocking the MCP event loop."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        class EventLoopDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("PyMuPDF ingest should run in an isolated worker")

        doc_dir = temp_dir / "doc_pymupdf"
        doc_dir.mkdir()
        EventLoopDocumentService.repository.get_doc_dir.return_value = doc_dir

        store = MemoryJobStore()
        job = Job(
            job_id="job_pymupdf_worker",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": False},
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=EventLoopDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_pymupdf",
                filename="paper.pdf",
                success=True,
                backend="pymupdf",
            )
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_pymupdf"]
        service._run_isolated_ingest_worker.assert_awaited_once()

    async def test_marker_job_uses_isolated_worker_not_event_loop_ingest(
        self, temp_dir: Path
    ) -> None:
        """Marker jobs run through the subprocess worker path."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        class EventLoopDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("Marker ingest should run in an isolated worker")

        doc_dir = temp_dir / "doc_marker"
        doc_dir.mkdir()
        (doc_dir / "blocks.json").write_text("[]", encoding="utf-8")
        EventLoopDocumentService.repository.get_doc_dir.return_value = doc_dir

        store = MemoryJobStore()
        job = Job(
            job_id="job_marker_worker",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": True, "extract_figures": True},
            progress=JobProgress(total_steps=9),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=EventLoopDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_marker",
                filename="paper.pdf",
                success=True,
                backend="marker",
            )
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_marker"]
        assert stored.result is not None
        assert stored.result["documents"][0]["backend"] == "marker"
        assert stored.result["documents"][0]["blocks_available"] is True
        service._run_isolated_ingest_worker.assert_awaited_once()

    async def test_process_ingest_job_delegates_to_injected_worker_runner(
        self, temp_dir: Path
    ) -> None:
        """JobService should depend on an ingest worker runner port."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        class EventLoopDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("DocumentService.ingest must stay in the worker")

        class FakeIngestWorkerRunner:
            def __init__(self) -> None:
                self.requests = []

            async def run_ingest_worker(self, request):
                self.requests.append(request)
                return IngestResult(
                    doc_id="doc_runner",
                    filename="paper.pdf",
                    success=True,
                    backend="marker",
                )

        doc_dir = temp_dir / "doc_runner"
        doc_dir.mkdir()
        EventLoopDocumentService.repository.get_doc_dir.return_value = doc_dir
        runner = FakeIngestWorkerRunner()
        store = MemoryJobStore()
        job = Job(
            job_id="job_runner_port",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": True, "extract_figures": True},
            progress=JobProgress(total_steps=9),
        )
        await store.create(job)

        service = JobService(
            job_store=store,
            document_service=EventLoopDocumentService(),  # type: ignore[arg-type]
            ingest_worker_runner=runner,
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert len(runner.requests) == 1
        request = runner.requests[0]
        assert request.job_id == job.job_id
        assert request.file_path == "paper.pdf"
        assert request.parameters["use_marker"] is True
        assert request.progress_offset == 0
        assert request.progress_total_steps == 9
        assert request.progress_prefix == "[1/1] "
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_runner"]
        assert stored.result is not None
        assert stored.result["documents"][0]["backend"] == "marker"

    def test_isolated_ingest_worker_command_preserves_kg_index_flag(
        self,
        tmp_path: Path,
    ) -> None:
        """Worker CLI receives explicit KG indexing only when requested."""
        from src.infrastructure.subprocess_ingest_worker_runner import (
            SubprocessIngestWorkerRunner,
        )

        command_disabled = SubprocessIngestWorkerRunner._build_worker_command(
            "paper.pdf",
            {"index_knowledge_graph": False},
            tmp_path / "result.json",
            tmp_path / "progress.json",
        )
        command_enabled = SubprocessIngestWorkerRunner._build_worker_command(
            "paper.pdf",
            {"index_knowledge_graph": True},
            tmp_path / "result.json",
            tmp_path / "progress.json",
        )

        assert "--index-knowledge-graph" not in command_disabled
        assert "--index-knowledge-graph" in command_enabled

    def test_isolated_ingest_worker_env_disables_lightrag_when_kg_index_is_false(
        self,
        tmp_path: Path,
    ) -> None:
        """Worker composition root must not build LightRAG for PDF-only ingest."""
        from src.infrastructure.subprocess_ingest_worker_runner import (
            SubprocessIngestWorkerRunner,
        )

        env = SubprocessIngestWorkerRunner._worker_environment(
            tmp_path / "worker.log",
            {"index_knowledge_graph": False},
        )

        assert env["ENABLE_LIGHTRAG"] == "false"

    def test_isolated_ingest_worker_env_preserves_lightrag_for_explicit_kg_index(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit KG indexing keeps LightRAG enabled for the worker process."""
        from src.infrastructure import subprocess_ingest_worker_runner as runner_module
        from src.infrastructure.subprocess_ingest_worker_runner import (
            SubprocessIngestWorkerRunner,
        )

        monkeypatch.setattr(runner_module.settings, "enable_lightrag", True)

        env = SubprocessIngestWorkerRunner._worker_environment(
            tmp_path / "worker.log",
            {"index_knowledge_graph": True},
        )

        assert env["ENABLE_LIGHTRAG"] == "true"

    async def test_isolated_ingest_worker_reads_result_and_redirects_stdio_to_log(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The subprocess worker command returns JSON and keeps logs inspectable."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult

        created: dict[str, object] = {}

        class FakeProcess:
            returncode = 0

            async def wait(self) -> int:
                return 0

            def terminate(self) -> None:
                raise AssertionError("terminate should not be needed")

            def kill(self) -> None:
                raise AssertionError("kill should not be needed")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            created["cmd"] = cmd
            created["kwargs"] = kwargs
            kwargs["stdout"].write("worker booted\n")
            kwargs["stdout"].flush()
            result_path = Path(cmd[cmd.index("--result-json") + 1])
            result_path.write_text(
                IngestResult(
                    doc_id="doc_worker",
                    filename="paper.pdf",
                    backend="marker",
                ).model_dump_json(),
                encoding="utf-8",
            )
            return FakeProcess()

        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.tempfile.gettempdir",
            lambda: str(tmp_path),
        )
        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.asyncio.create_subprocess_exec",
            fake_create_subprocess_exec,
        )

        job_store = MagicMock()
        job_store.jobs_dir = tmp_path / "jobs"
        service = JobService(job_store=job_store)

        result = await service._run_isolated_ingest_worker(
            "job_worker",
            "paper.pdf",
            {
                "use_marker": True,
                "require_marker": True,
                "ocr_language": "eng",
                "marker_max_pages_per_chunk": 7,
                "page_ranges": ["1-2"],
                "extract_figures": True,
                "etl_profile": "arxiv",
            },
        )

        cmd = created["cmd"]
        kwargs = created["kwargs"]
        assert isinstance(cmd, tuple)
        assert "-m" in cmd
        assert "src.presentation.ingest_worker_main" in cmd
        assert "--use-marker" in cmd
        assert "--require-marker" in cmd
        assert "--extract-figures" in cmd
        assert "--etl-profile" in cmd
        assert "--progress-json" in cmd
        assert kwargs["stdin"] is asyncio.subprocess.DEVNULL
        assert kwargs["stdout"] is not asyncio.subprocess.DEVNULL
        assert kwargs["stderr"] is asyncio.subprocess.STDOUT
        assert kwargs["env"]["ETL_PROFILE"] == "arxiv"
        assert result.doc_id == "doc_worker"
        log_paths = list((tmp_path / "logs").glob("ingest_job_worker_paper_*.log"))
        assert len(log_paths) == 1
        log_path = log_paths[0]
        assert log_path.read_text(encoding="utf-8") == "worker booted\n"
        assert any(str(log_path) in warning for warning in result.warnings)

    async def test_isolated_ingest_worker_heartbeat_updates_job_from_progress_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Parent progress is refreshed while the isolated worker is still running."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobType

        class MemoryJobStore:
            def __init__(self) -> None:
                self.jobs: dict[str, Job] = {}
                self.jobs_dir = tmp_path / "jobs"

            async def create(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

            async def get(self, job_id: str) -> Job | None:
                return self.jobs.get(job_id)

            async def update(self, job: Job) -> Job:
                self.jobs[job.job_id] = job
                return job

        class FakeProcess:
            pid = 1234
            returncode: int | None = None

            async def wait(self) -> int:
                await asyncio.sleep(0.05)
                self.returncode = 0
                return 0

            def terminate(self) -> None:
                raise AssertionError("terminate should not be needed")

            def kill(self) -> None:
                raise AssertionError("kill should not be needed")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            kwargs["stdout"].write("marker log tail\n")
            kwargs["stdout"].flush()
            progress_path = Path(cmd[cmd.index("--progress-json") + 1])
            progress_path.write_text(
                json.dumps(
                    {
                        "step": 3,
                        "total": 9,
                        "phase": "Marker Parse",
                        "message": "Loading Marker models",
                    }
                ),
                encoding="utf-8",
            )
            result_path = Path(cmd[cmd.index("--result-json") + 1])
            result_path.write_text(
                IngestResult(
                    doc_id="doc_worker",
                    filename="paper.pdf",
                    backend="marker",
                ).model_dump_json(),
                encoding="utf-8",
            )
            return FakeProcess()

        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.asyncio.create_subprocess_exec",
            fake_create_subprocess_exec,
        )
        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.WORKER_HEARTBEAT_SECONDS",
            0.01,
            raising=False,
        )

        store = MemoryJobStore()
        job = Job(
            job_id="job_heartbeat",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=9),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)

        result = await service._run_isolated_ingest_worker(
            job.job_id,
            "paper.pdf",
            {"use_marker": True, "extract_figures": True},
        )

        stored = await store.get(job.job_id)
        assert result.success is True
        assert stored is not None
        assert stored.progress.current_phase == "Marker Parse"
        assert stored.progress.message == "Loading Marker models"
        assert stored.progress.current_step == 3
        assert stored.progress.percentage == pytest.approx(100 / 3)

    async def test_isolated_ingest_worker_invalid_result_returns_failure_with_log_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Partial worker JSON is reported as a failed result instead of escaping."""
        from src.application.job_service import JobService

        class FakeProcess:
            returncode = 0

            async def wait(self) -> int:
                return 0

            def terminate(self) -> None:
                raise AssertionError("terminate should not be needed")

            def kill(self) -> None:
                raise AssertionError("kill should not be needed")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            kwargs["stdout"].write("traceback line\n")
            kwargs["stdout"].flush()
            result_path = Path(cmd[cmd.index("--result-json") + 1])
            result_path.write_text('{"success": false', encoding="utf-8")
            return FakeProcess()

        monkeypatch.setattr(
            "src.infrastructure.subprocess_ingest_worker_runner.asyncio.create_subprocess_exec",
            fake_create_subprocess_exec,
        )
        job_store = MagicMock()
        job_store.jobs_dir = tmp_path / "jobs"
        service = JobService(job_store=job_store)

        result = await service._run_isolated_ingest_worker(
            "job_bad_result",
            "paper.pdf",
            {"use_marker": True},
        )

        log_paths = list((tmp_path / "logs").glob("ingest_job_bad_result_paper_*.log"))
        assert len(log_paths) == 1
        log_path = log_paths[0]
        assert result.success is False
        assert "Could not read isolated ingest worker result" in (result.error or "")
        assert str(log_path) in (result.error or "")
        assert log_path.read_text(encoding="utf-8") == "traceback line\n"

    async def test_ingest_worker_writes_result_and_progress_atomically(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Worker result/progress JSON writers preserve existing files on failure."""
        from src.application import ingest_worker
        from src.domain.entities import IngestResult

        result_path = tmp_path / "result.json"
        result_path.write_text(
            IngestResult(doc_id="old", filename="paper.pdf").model_dump_json(),
            encoding="utf-8",
        )

        original_write_text = Path.write_text

        def fail_after_partial_tmp_write(self: Path, *args, **kwargs) -> int:
            original_write_text(self, '{"partial"', encoding="utf-8")
            raise RuntimeError("disk full")

        monkeypatch.setattr(Path, "write_text", fail_after_partial_tmp_write)

        with pytest.raises(RuntimeError, match="disk full"):
            ingest_worker._write_result(
                result_path,
                IngestResult(doc_id="new", filename="paper.pdf"),
            )

        monkeypatch.setattr(Path, "write_text", original_write_text)
        assert json.loads(result_path.read_text(encoding="utf-8"))["doc_id"] == "old"
        assert not list(tmp_path.glob("*.tmp"))

        callback = ingest_worker._make_progress_callback(tmp_path / "progress.json")
        await callback(2, 9, "Marker Parse", "Loading Marker models")

        progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
        assert progress["step"] == 2
        assert progress["total"] == 9
        assert progress["phase"] == "Marker Parse"
        assert progress["message"] == "Loading Marker models"
        assert "ts" in progress
        assert not list(tmp_path.glob("*.tmp"))

    async def test_ingest_job_result_preserves_backend_warnings(self) -> None:
        """Background jobs keep degraded backend warnings in their final result."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        class FallbackDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                return [
                    IngestResult(
                        doc_id="doc_fallback",
                        filename="paper.pdf",
                        success=True,
                        backend="pymupdf_fallback",
                        warnings=["Marker requested; PyMuPDF fallback used"],
                    )
                ]

        FallbackDocumentService.repository.get_doc_dir.return_value = Path("data/doc")
        store = MemoryJobStore()
        job = Job(
            job_id="job_fallback",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": False},
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)
        service = JobService(
            job_store=store,
            document_service=FallbackDocumentService(),  # type: ignore[arg-type]
        )
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_fallback",
                filename="paper.pdf",
                success=True,
                backend="pymupdf_fallback",
                warnings=["Marker requested; PyMuPDF fallback used"],
            )
        )

        await service._process_ingest_job(job.job_id, service.document_service)

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.result is not None
        assert stored.result["degraded"] is True
        assert stored.result["warnings"] == ["Marker requested; PyMuPDF fallback used"]
        assert stored.result["documents"][0]["backend"] == "pymupdf_fallback"

    async def test_cancel_job_waits_for_running_task_cleanup(self) -> None:
        """cancel_job should not return while the task is still unwinding."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        cleanup_seen = False
        started = asyncio.Event()

        async def long_running() -> None:
            nonlocal cleanup_seen
            try:
                started.set()
                await asyncio.sleep(3600)
            finally:
                cleanup_seen = True

        store = MemoryJobStore()
        job = Job(
            job_id="job_cancel_wait",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=8),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)
        task = asyncio.create_task(long_running())
        await started.wait()
        service._running_tasks[job.job_id] = task

        assert await service.cancel_job(job.job_id) is True

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.CANCELLED
        assert task.done()
        assert cleanup_seen
        assert job.job_id not in service._running_tasks

    async def test_cancel_job_preserves_worker_cancellation_message(self) -> None:
        """cancel_job must not overwrite the worker's final cancellation update."""
        from src.application.job_service import JobService
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        store = MemoryJobStore()
        job = Job(
            job_id="job_cancel_message",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=8, message="worker started"),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)

        started = asyncio.Event()

        async def worker() -> None:
            try:
                started.set()
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                latest = await store.get(job.job_id)
                assert latest is not None
                latest.cancel()
                latest.progress.message = "Job cancelled by user"
                await store.update(latest)
                raise

        task = asyncio.create_task(worker())
        await started.wait()
        service._running_tasks[job.job_id] = task

        assert await service.cancel_job(job.job_id) is True

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.CANCELLED
        assert stored.progress.message == "Job cancelled by user"

    async def test_reconcile_stale_active_jobs_after_restart(self) -> None:
        """Persisted active jobs without in-memory tasks are failed on read/list."""
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
            job_id="job_stale",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            progress=JobProgress(total_steps=8),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)

        active = await service.list_active_jobs()
        stored = await store.get(job.job_id)

        assert active == []
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert "restarted" in (stored.error or "")

    async def test_reconcile_does_not_fail_other_live_owner_job(self) -> None:
        """Shared DATA_DIR instances must not fail jobs owned by a live process."""
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

        store = MemoryJobStore()
        job = Job(
            job_id="job_other_owner",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"job_owner_id": "other", "job_owner_pid": 12345},
            progress=JobProgress(total_steps=8),
        )
        job.start()
        await store.create(job)
        service = JobService(job_store=store)
        service._process_is_alive = MagicMock(return_value=True)  # type: ignore[method-assign]

        active = await service.list_active_jobs()
        stored = await store.get(job.job_id)

        assert len(active) == 1
        assert stored is not None
        assert stored.status == JobStatus.PROCESSING

    async def test_process_ingest_job_uses_captured_document_service(self) -> None:
        """Profile switches must not alter a job's already captured service."""
        from src.application.job_service import JobService
        from src.domain.entities import IngestResult
        from src.domain.job import Job, JobProgress, JobStatus, JobType

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

        class OriginalDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                return [
                    IngestResult(
                        doc_id="doc_original",
                        filename="paper.pdf",
                        success=True,
                    )
                ]

        class NewDocumentService:
            repository = MagicMock()

            async def ingest(self, *_args, **_kwargs):
                raise AssertionError("new service should not handle captured job")

        OriginalDocumentService.repository.get_doc_dir.return_value = Path("data/doc")
        store = MemoryJobStore()
        job = Job(
            job_id="job_profile_isolated",
            job_type=JobType.INGEST_PDF,
            input_files=["paper.pdf"],
            parameters={"use_marker": False},
            progress=JobProgress(total_steps=8),
        )
        await store.create(job)
        original = OriginalDocumentService()
        service = JobService(job_store=store, document_service=original)  # type: ignore[arg-type]
        service.set_document_service(NewDocumentService())  # type: ignore[arg-type]
        service._run_isolated_ingest_worker = AsyncMock(  # type: ignore[method-assign]
            return_value=IngestResult(
                doc_id="doc_original",
                filename="paper.pdf",
                success=True,
            )
        )

        await service._process_ingest_job(job.job_id, original)  # type: ignore[arg-type]

        stored = await store.get(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.output_doc_ids == ["doc_original"]

    async def test_process_ingest_job_cleans_running_task_when_job_missing(
        self,
    ) -> None:
        """A deleted/corrupt job file must not leak a concurrency slot."""
        from src.application.job_service import JobService

        class EmptyJobStore:
            async def get(self, _job_id: str):
                return None

        service = JobService(job_store=EmptyJobStore())  # type: ignore[arg-type]
        current_task = asyncio.current_task()
        assert current_task is not None
        service._running_tasks["job_missing"] = current_task  # type: ignore[assignment]

        await service._process_ingest_job("job_missing")

        assert "job_missing" not in service._running_tasks


# ============================================================================
# PDF Magic Byte Validation
# ============================================================================
