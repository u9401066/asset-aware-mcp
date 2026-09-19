"""Ports for revision-bound static document previews, without visual judgments."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.domain.native_pptx_slides import NativePptxSlideKey


class NativePresentationRenderer(Protocol):
    def render(
        self, data: bytes, slide: NativePptxSlideKey, render_size: int
    ) -> dict[str, Any]: ...
