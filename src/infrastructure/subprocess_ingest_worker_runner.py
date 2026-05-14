"""Subprocess implementation of the isolated ingest worker runner port."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.entities import IngestResult
from src.domain.job import Job
from src.infrastructure.config import settings

if TYPE_CHECKING:
    from src.application.worker_runner import IngestWorkerRequest
    from src.domain.repositories import JobStoreInterface

logger = logging.getLogger(__name__)

WORKER_HEARTBEAT_SECONDS = 5.0


class SubprocessIngestWorkerRunner:
    """Run PDF ingestion in a subprocess so stdio MCP remains responsive."""

    def __init__(self, job_store: JobStoreInterface) -> None:
        self.job_store = job_store
        self._worker_processes: dict[str, asyncio.subprocess.Process] = {}

    async def run_ingest_worker(self, request: IngestWorkerRequest) -> IngestResult:
        logs_dir = self._worker_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = "".join(
            char if char.isalnum() or char in "-_." else "_"
            for char in Path(request.file_path).stem
        )[:40]
        safe_stem = safe_stem or "document"
        log_path = (
            logs_dir / f"ingest_{request.job_id}_{safe_stem}_{uuid.uuid4().hex[:8]}.log"
        )
        worker_temp_dir = Path(
            tempfile.mkdtemp(prefix=f"asset_aware_{request.job_id}_")
        )
        result_path = worker_temp_dir / "result.json"
        progress_path = worker_temp_dir / "progress.json"
        cmd = self._build_worker_command(
            request.file_path,
            request.parameters,
            result_path,
            progress_path,
        )
        env = self._worker_environment(log_path, request.parameters)
        if profile_name := request.parameters.get("etl_profile"):
            env["ETL_PROFILE"] = str(profile_name)

        log_file = log_path.open("w", encoding="utf-8")
        heartbeat_task: asyncio.Task[None] | None = None
        return_code: int | None = None
        spawn_error: Exception | None = None
        try:
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(Path.cwd()),
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env,
                )
            except Exception as exc:
                spawn_error = exc
                return_code = None
            else:
                self._worker_processes[request.job_id] = process
                try:
                    await self._persist_worker_process_metadata(
                        request.job_id,
                        getattr(process, "pid", None),
                        log_path,
                    )
                except Exception:
                    logger.warning(
                        "Failed to persist worker process metadata for %s",
                        request.job_id,
                        exc_info=True,
                    )
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_isolated_worker(
                        request.job_id,
                        process,
                        progress_path,
                        log_path,
                        progress_offset=request.progress_offset,
                        progress_total_steps=request.progress_total_steps,
                        progress_prefix=request.progress_prefix,
                    )
                )
                try:
                    return_code = await process.wait()
                except asyncio.CancelledError:
                    await self._terminate_worker_process(process)
                    raise
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat_task
            log_file.close()
            self._worker_processes.pop(request.job_id, None)

        if spawn_error is not None:
            shutil.rmtree(worker_temp_dir, ignore_errors=True)
            return IngestResult(
                doc_id="",
                filename=Path(request.file_path).name,
                success=False,
                error=(
                    "Could not start isolated ingest worker: "
                    f"{spawn_error}. See {log_path}"
                ),
            )

        try:
            if result_path.exists():
                data = json.loads(result_path.read_text(encoding="utf-8"))
                result = IngestResult.model_validate(data)
                self._append_worker_log_warning(result, log_path)
                return result
        except Exception as exc:
            return IngestResult(
                doc_id="",
                filename=Path(request.file_path).name,
                success=False,
                error=(
                    "Could not read isolated ingest worker result: "
                    f"{exc}. See {log_path}"
                ),
            )
        finally:
            shutil.rmtree(worker_temp_dir, ignore_errors=True)

        return IngestResult(
            doc_id="",
            filename=Path(request.file_path).name,
            success=False,
            error=f"Isolated ingest worker exited with code {return_code}. See {log_path}",
        )

    @staticmethod
    def _build_worker_command(
        file_path: str,
        parameters: dict[str, Any],
        result_path: Path,
        progress_path: Path,
    ) -> list[str]:
        cmd = [
            sys.executable,
            "-m",
            "src.presentation.ingest_worker_main",
            "--file",
            file_path,
            "--result-json",
            str(result_path),
            "--progress-json",
            str(progress_path),
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
            ("index_knowledge_graph", "--index-knowledge-graph"),
        ]:
            if parameters.get(flag):
                cmd.append(name)

        if profile_name := parameters.get("etl_profile"):
            cmd.extend(["--etl-profile", str(profile_name)])
        return cmd

    def _worker_logs_dir(self) -> Path:
        jobs_dir = getattr(self.job_store, "jobs_dir", None)
        if jobs_dir is not None:
            return Path(jobs_dir).parent / "logs"
        return Path.cwd() / "data" / "logs"

    @staticmethod
    def _worker_environment(
        log_path: Path,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        parameters = parameters or {}
        env = os.environ.copy()
        env["DATA_DIR"] = str(settings.data_dir.resolve())
        env["TABLE_OUTPUT_DIR"] = str(settings.table_output_dir.resolve())
        env["LIGHTRAG_WORKING_DIR"] = str(settings.lightrag_working_dir.resolve())
        env["ETL_PROFILE"] = settings.etl_profile
        index_knowledge_graph = bool(parameters.get("index_knowledge_graph", False))
        enable_lightrag = settings.enable_lightrag and index_knowledge_graph
        env["ENABLE_LIGHTRAG"] = "true" if enable_lightrag else "false"
        env["ENABLE_MISTRAL_OCR"] = "true" if settings.enable_mistral_ocr else "false"
        env["ASSET_AWARE_SUPPRESS_MARKER_OUTPUT"] = "true"
        env["ASSET_AWARE_MARKER_OUTPUT_LOG"] = str(log_path)
        if settings.etl_profile_json is not None:
            env["ETL_PROFILE_JSON"] = str(settings.etl_profile_json.resolve())
        if settings.mistral_api_key:
            env["MISTRAL_API_KEY"] = settings.mistral_api_key
        if settings.openai_api_key:
            env["OPENAI_API_KEY"] = settings.openai_api_key
        return env

    @staticmethod
    def _append_worker_log_warning(result: IngestResult, log_path: Path) -> None:
        warning = f"Isolated ingest worker log: {log_path}"
        if warning not in result.warnings:
            result.warnings.append(warning)

    async def _persist_worker_process_metadata(
        self,
        job_id: str,
        worker_pid: int | None,
        log_path: Path,
    ) -> None:
        maybe_job = self.job_store.get(job_id)
        job = await maybe_job if inspect.isawaitable(maybe_job) else maybe_job
        if not isinstance(job, Job) or job.is_terminal:
            return
        if worker_pid is not None:
            job.parameters["worker_pid"] = worker_pid
        job.parameters["worker_started_at"] = datetime.now().isoformat()
        job.parameters["worker_log_path"] = str(log_path)
        await self.job_store.update(job)

    async def _heartbeat_isolated_worker(
        self,
        job_id: str,
        process: asyncio.subprocess.Process,
        progress_path: Path,
        log_path: Path,
        *,
        progress_offset: int = 0,
        progress_total_steps: int | None = None,
        progress_prefix: str = "",
    ) -> None:
        while process.returncode is None:
            try:
                await self._refresh_worker_progress(
                    job_id,
                    progress_path,
                    log_path,
                    progress_offset=progress_offset,
                    progress_total_steps=progress_total_steps,
                    progress_prefix=progress_prefix,
                )
            except Exception:
                logger.warning(
                    "Failed to refresh worker progress for %s",
                    job_id,
                    exc_info=True,
                )
            await asyncio.sleep(WORKER_HEARTBEAT_SECONDS)

    async def _refresh_worker_progress(
        self,
        job_id: str,
        progress_path: Path,
        log_path: Path,
        *,
        progress_offset: int = 0,
        progress_total_steps: int | None = None,
        progress_prefix: str = "",
    ) -> None:
        job = await self.job_store.get(job_id)
        if job is None or job.is_terminal:
            return

        progress_data = self._read_worker_progress(progress_path)
        if progress_data is not None:
            step = self._coerce_progress_int(progress_data.get("step"))
            total = self._coerce_progress_int(progress_data.get("total"))
            phase = str(progress_data.get("phase") or "Ingest Worker")
            message = str(progress_data.get("message") or "Ingest worker is running")
            if step is not None:
                job.progress.current_step = progress_offset + step
            if total is not None and total > 0:
                mapped_total = (
                    progress_total_steps if progress_total_steps is not None else total
                )
                job.progress.total_steps = max(job.progress.total_steps, mapped_total)
            job.progress.current_phase = phase
            job.progress.message = f"{progress_prefix}{message}"
            if job.progress.total_steps > 0:
                job.progress.percentage = (
                    job.progress.current_step / job.progress.total_steps
                ) * 100
        else:
            tail = self._tail_log_line(log_path)
            job.progress.current_phase = "Ingest Worker"
            job.progress.message = (
                f"{progress_prefix}Ingest worker is running. Last log: {tail}"
                if tail
                else f"{progress_prefix}Ingest worker is running. Log: {log_path}"
            )
        await self.job_store.update(job)

    @staticmethod
    def _read_worker_progress(progress_path: Path) -> dict[str, Any] | None:
        if not progress_path.exists():
            return None
        try:
            data = json.loads(progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _coerce_progress_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return None

    @staticmethod
    def _tail_log_line(log_path: Path) -> str:
        try:
            with log_path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(size - 8192, 0))
                chunk = handle.read().decode("utf-8", errors="replace")
        except OSError:
            return ""
        lines = chunk.splitlines()
        return next((line.strip() for line in reversed(lines) if line.strip()), "")

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
