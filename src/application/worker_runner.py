"""Application ports for isolated ingest worker execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.domain.entities import IngestResult


@dataclass(frozen=True, slots=True)
class IngestWorkerRequest:
    """Request passed from job orchestration to an ingest worker runner."""

    job_id: str
    file_path: str
    parameters: dict[str, Any]
    progress_offset: int = 0
    progress_total_steps: int | None = None
    progress_prefix: str = ""


class IngestWorkerRunner(Protocol):
    """Port for running one ingest worker outside the MCP request loop."""

    async def run_ingest_worker(
        self,
        request: IngestWorkerRequest,
    ) -> IngestResult:
        """Run one isolated ingest worker and return its result."""
