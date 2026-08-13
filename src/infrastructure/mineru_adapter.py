"""
Infrastructure Layer - MinerU Adapter

Highest-accuracy structured PDF extraction via OpenDataLab MinerU, exposed
through the same ``parse() -> MarkerParseResult`` contract as
:class:`MarkerPDFExtractor` so it drops into the existing ``marker_extractor``
slot without service-layer changes.

Design choices:
- Uses the stable MinerU **CLI** (``mineru -p <pdf> -o <out> -b pipeline``) and
  reads the well-defined ``*_content_list.json`` output, rather than the
  fast-moving Python API. This is version-robust across MinerU 2.x/3.x.
- Runs in a subprocess with a timeout, matching the project's existing OOM
  isolation strategy (MinerU pulls torch/onnxruntime and can be memory-hungry).
- The ``pipeline`` backend runs on pure CPU by default.

The backend is heavy and optional; every MinerU touchpoint is lazy and guarded.
The packaged ``[mineru]`` extra is intentionally empty while MinerU's
``transformers<5`` cap excludes currently patched releases. The adapter remains
available for isolated upstream evaluation, but production installs should use
PyMuPDF4LLM or Docling.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.domain.marker_errors import MINERU_INSTALL_HINT
from src.infrastructure.marker_adapter import MarkerBlock, MarkerParseResult

logger = logging.getLogger(__name__)

DEFAULT_MINERU_TIMEOUT_SECONDS = 900.0

# MinerU content_list ``type`` -> Marker block_type convention.
_MINERU_TYPE_MAP: dict[str, str] = {
    "title": "SectionHeader",
    "image": "Figure",
    "table": "Table",
    "equation": "Equation",
    "text": "Text",
    "list": "ListItem",
}


class MinerUBackendUnavailable(RuntimeError):
    """Raised when the optional ``mineru`` backend is not importable/on PATH."""


class MinerUExtractor:
    """MinerU structured parser emitting Marker-compatible results.

    Mirrors :class:`MarkerPDFExtractor`'s public surface
    (``require_backend_available`` + ``parse``).
    """

    ENGINE_NAME = "mineru"

    def __init__(
        self,
        output_dir: Path | None = None,
        *,
        backend: str = "pipeline",
        timeout_seconds: float | None = None,
    ) -> None:
        """Initialise the MinerU extractor.

        Args:
            output_dir: Optional working directory (unused; MinerU writes to a
                private temp dir per parse).
            backend: MinerU backend. ``pipeline`` runs on pure CPU (default);
                ``vlm-*`` variants need a GPU/inference server.
            timeout_seconds: Hard wall-clock cap for the MinerU subprocess.
        """
        self.output_dir = output_dir or Path("./temp_output")
        self.backend = backend
        raw_timeout = os.environ.get("MINERU_DOCUMENT_TIMEOUT_SECONDS")
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else _coerce_float(raw_timeout, DEFAULT_MINERU_TIMEOUT_SECONDS)
        )

    @staticmethod
    def require_backend_available() -> None:
        """Preflight the MinerU import / CLI availability."""
        try:
            import mineru  # type: ignore # noqa: F401

            return
        except ImportError:
            pass
        if shutil.which("mineru") is None:
            raise MinerUBackendUnavailable(MINERU_INSTALL_HINT)

    def parse(
        self,
        pdf_path: Path,
        *,
        extract_images: bool = True,
        max_pages_per_chunk: int | None = None,
        page_map: list[int] | None = None,
        reported_page_count: int | None = None,
    ) -> MarkerParseResult:
        """Parse a PDF into a Marker-compatible structured result.

        Signature mirrors :meth:`MarkerPDFExtractor.parse`. ``max_pages_per_chunk``
        is accepted for parity; MinerU manages long documents internally.
        """
        self.require_backend_available()
        with tempfile.TemporaryDirectory(prefix="mineru_out_") as tmp_name:
            out_dir = Path(tmp_name)
            self._run_cli(pdf_path, out_dir)

            content_list = self._read_content_list(out_dir)
            markdown = self._read_markdown(out_dir)
            blocks = self._blocks_from_content_list(content_list)
            images = self._load_images(out_dir, content_list) if extract_images else {}

        if page_map:
            self._apply_page_map(blocks, page_map)

        toc = self._extract_toc(blocks)
        page_count = reported_page_count or self._max_page(blocks)
        metadata: dict[str, Any] = {
            "backend": f"mineru:{self.backend}",
            "block_count": len(blocks),
            "image_count": len(images),
        }
        return MarkerParseResult(
            markdown=markdown,
            blocks=blocks,
            toc=toc,
            images=images,
            metadata=metadata,
            page_count=page_count,
        )

    def _run_cli(self, pdf_path: Path, out_dir: Path) -> None:
        """Invoke the MinerU CLI in a subprocess with a timeout."""
        mineru_bin = shutil.which("mineru")
        if mineru_bin is None:
            raise MinerUBackendUnavailable(MINERU_INSTALL_HINT)
        cmd = [
            mineru_bin,
            "-p",
            str(pdf_path),
            "-o",
            str(out_dir),
            "-b",
            self.backend,
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise MinerUBackendUnavailable(
                f"MinerU timed out after {self.timeout_seconds:.0f}s parsing "
                f"{pdf_path.name}. Reduce the document or raise "
                "MINERU_DOCUMENT_TIMEOUT_SECONDS."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", "replace")[:500]
            raise MinerUBackendUnavailable(
                f"MinerU CLI failed for {pdf_path.name}: {stderr}"
            ) from exc

    @staticmethod
    def _read_content_list(out_dir: Path) -> list[dict[str, Any]]:
        """Load the first ``*_content_list.json`` MinerU emitted."""
        matches = sorted(out_dir.rglob("*_content_list.json"))
        if not matches:
            return []
        try:
            data = json.loads(matches[0].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("MinerU content_list unreadable", exc_info=True)
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _read_markdown(out_dir: Path) -> str:
        """Load the first Markdown file MinerU emitted."""
        matches = sorted(out_dir.rglob("*.md"))
        for candidate in matches:
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError:
                continue
            if text.strip():
                return text
        return ""

    def _blocks_from_content_list(
        self, content_list: list[dict[str, Any]]
    ) -> list[MarkerBlock]:
        """Map MinerU content_list entries to Marker-compatible blocks."""
        blocks: list[MarkerBlock] = []
        for idx, item in enumerate(content_list):
            item_type = str(item.get("type", "text") or "text")
            block_type = _MINERU_TYPE_MAP.get(item_type, "Text")
            page = int(item.get("page_idx", 0) or 0) + 1  # 0-indexed -> 1-indexed
            text = self._item_text(item, item_type)
            bbox = self._coerce_bbox(item.get("bbox"))
            blocks.append(
                MarkerBlock(
                    block_id=f"mineru_{idx}",
                    block_type=block_type,
                    page=page,
                    text=text,
                    bbox=bbox,
                    metadata={
                        "mineru_type": item_type,
                        "img_path": str(item.get("img_path", "") or ""),
                    },
                )
            )
        return blocks

    @staticmethod
    def _item_text(item: dict[str, Any], item_type: str) -> str:
        """Pick the most meaningful text field for a MinerU item."""
        if item_type == "table":
            return str(item.get("table_body", "") or item.get("text", "") or "")
        if item_type == "image":
            caption = item.get("image_caption", "")
            if isinstance(caption, list):
                return " ".join(str(part) for part in caption)
            return str(caption or "")
        return str(item.get("text", "") or "")

    @staticmethod
    def _coerce_bbox(raw: Any) -> list[float]:
        """Coerce a MinerU bbox to ``[x0, y0, x1, y1]`` floats."""
        if not isinstance(raw, (list, tuple)) or len(raw) < 4:
            return []
        try:
            return [float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])]
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _load_images(
        out_dir: Path, content_list: list[dict[str, Any]]
    ) -> dict[str, bytes]:
        """Load image bytes referenced by ``img_path`` in the content list."""
        images: dict[str, bytes] = {}
        for idx, item in enumerate(content_list):
            if item.get("type") != "image":
                continue
            img_path = str(item.get("img_path", "") or "")
            if not img_path:
                continue
            matches = sorted(out_dir.rglob(Path(img_path).name))
            if not matches:
                continue
            try:
                payload = matches[0].read_bytes()
            except OSError:
                continue
            page = int(item.get("page_idx", 0) or 0)
            ext = matches[0].suffix.lstrip(".") or "jpg"
            images[f"_page_{page}_Figure_{idx}.{ext}"] = payload
        return images

    @staticmethod
    def _apply_page_map(blocks: list[MarkerBlock], page_map: list[int]) -> None:
        """Remap subset-local page numbers back to original pages in place."""
        for block in blocks:
            if 1 <= block.page <= len(page_map):
                block.page = page_map[block.page - 1]

    @staticmethod
    def _extract_toc(blocks: list[MarkerBlock]) -> list[dict[str, Any]]:
        """Derive a simple TOC from section-header blocks."""
        toc: list[dict[str, Any]] = []
        for block in blocks:
            if block.block_type == "SectionHeader" and block.text.strip():
                toc.append(
                    {"title": block.text.strip(), "page": block.page, "level": 1}
                )
        return toc

    @staticmethod
    def _max_page(blocks: list[MarkerBlock]) -> int:
        """Infer page count from the highest block page number."""
        return max((block.page for block in blocks), default=0)


def _coerce_float(raw: str | None, default: float) -> float:
    """Parse a float env value with a fallback."""
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
