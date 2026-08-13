"""Application service for safe PDF preflight operations."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.pdf_preflight import PDFPreflightReport
    from src.domain.repositories import PDFPreflightInterface


class PDFPreflightService:
    """Run a synchronous PDF inspector without blocking the MCP event loop."""

    def __init__(self, inspector: PDFPreflightInterface):
        self.inspector = inspector

    async def inspect(self, pdf_path: str | Path) -> PDFPreflightReport:
        """Inspect one source path and return its normalized routing report."""
        return await asyncio.to_thread(self.inspector.inspect, Path(pdf_path))
