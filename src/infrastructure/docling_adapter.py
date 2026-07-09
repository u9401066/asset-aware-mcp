"""
Infrastructure Layer - Docling Adapter

High-fidelity structured PDF extraction via IBM Docling, exposed through the
same ``parse() -> MarkerParseResult`` contract as :class:`MarkerPDFExtractor`.
This lets Docling drop straight into the existing ``marker_extractor`` slot and
reuse the whole ``_ingest_single_with_marker`` asset pipeline (blocks.json,
section hierarchy, figure/table assets) with zero changes to the service layer.

Why Docling:
- MIT licensed (cleanest for this Apache-2.0 project).
- Page layout + reading order + table structure + formula + figure
  classification in one ``DoclingDocument``.
- Verified compatible with the secure ``Pillow>=12.2.0`` floor.
- Ships the lightweight GraniteDocling VLM, aligned with the granite backend.

The backend is heavy and optional, so every docling import is lazy and guarded;
the module always imports even when docling is not installed.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from src.infrastructure.marker_adapter import MarkerBlock, MarkerParseResult

logger = logging.getLogger(__name__)

DOCLING_INSTALL_HINT = (
    "Docling backend not available. Install the isolated engine with "
    "`python scripts/setup_docling.py` (cross-platform; see docs/docling-setup.md), "
    "or `uv pip install docling` into the main env, or set ETL_ENGINE=pymupdf. "
    "On pre-release Python without torch wheels, the isolated .venv-docling is required."
)

# Environment variables for the isolated-subprocess Docling bridge.
_DOCLING_PYTHON_ENV = "DOCLING_PYTHON_PATH"
_DOCLING_TIMEOUT_ENV = "DOCLING_TIMEOUT_SECONDS"
_DEFAULT_DOCLING_TIMEOUT = 900.0

# Docling ``DocItemLabel`` -> Marker block_type convention consumed downstream
# (annotate_marker_blocks / manifest generation). Unknown labels fall back to
# "Text" so no content is dropped.
_DOCLING_LABEL_MAP: dict[str, str] = {
    "section_header": "SectionHeader",
    "title": "SectionHeader",
    "table": "Table",
    "picture": "Figure",
    "chart": "Figure",
    "figure": "Figure",
    "caption": "Caption",
    "formula": "Equation",
    "equation": "Equation",
    "code": "Code",
    "footnote": "Footnote",
    "page_header": "PageHeader",
    "page_footer": "PageFooter",
    "list_item": "ListItem",
    "text": "Text",
    "paragraph": "Text",
}


class DoclingBackendUnavailable(RuntimeError):
    """Raised when the optional ``docling`` backend cannot be imported."""


class DoclingParseError(RuntimeError):
    """Raised when the Docling worker subprocess fails to parse a document."""


def _block_to_dict(block: MarkerBlock) -> dict[str, Any]:
    """Serialise a MarkerBlock (recursively) to a JSON-safe dict."""
    return {
        "block_id": block.block_id,
        "block_type": block.block_type,
        "page": block.page,
        "text": block.text,
        "bbox": block.bbox,
        "polygon": block.polygon,
        "section_hierarchy": {str(k): v for k, v in block.section_hierarchy.items()},
        "children": [_block_to_dict(child) for child in block.children],
        "metadata": block.metadata,
    }


def _block_from_dict(data: dict[str, Any]) -> MarkerBlock:
    """Rebuild a MarkerBlock (recursively) from a serialised dict."""
    return MarkerBlock(
        block_id=str(data.get("block_id", "")),
        block_type=str(data.get("block_type", "Text")),
        page=int(data.get("page", 1) or 1),
        text=str(data.get("text", "") or ""),
        bbox=list(data.get("bbox", []) or []),
        polygon=list(data.get("polygon", []) or []),
        section_hierarchy={
            str(k): str(v) for k, v in (data.get("section_hierarchy", {}) or {}).items()
        },
        children=[
            _block_from_dict(child) for child in (data.get("children", []) or [])
        ],
        metadata=dict(data.get("metadata", {}) or {}),
    )


def _serialize_result_to_dir(result: MarkerParseResult, out_dir: Path) -> None:
    """Serialise a MarkerParseResult to ``<out_dir>/result.json`` (+ images/).

    Image bytes are spilled to ``<out_dir>/images/`` and referenced by a
    manifest so the payload stays JSON-serialisable across the process boundary.
    """
    image_manifest: list[dict[str, str]] = []
    if result.images:
        image_dir = out_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        for index, (key, data) in enumerate(result.images.items()):
            filename = f"img_{index}.bin"
            (image_dir / filename).write_bytes(data)
            image_manifest.append({"key": key, "file": filename})
    payload = {
        "markdown": result.markdown,
        "blocks": [_block_to_dict(block) for block in result.blocks],
        "toc": result.toc,
        "metadata": result.metadata,
        "page_count": result.page_count,
        "images": image_manifest,
    }
    (out_dir / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _deserialize_result_from_dir(out_dir: Path) -> MarkerParseResult:
    """Rebuild a MarkerParseResult from ``<out_dir>/result.json`` (+ images/)."""
    payload = json.loads((out_dir / "result.json").read_text(encoding="utf-8"))
    images: dict[str, bytes] = {}
    for item in payload.get("images", []) or []:
        image_path = out_dir / "images" / item.get("file", "")
        if image_path.exists():
            images[str(item.get("key", ""))] = image_path.read_bytes()
    return MarkerParseResult(
        markdown=str(payload.get("markdown", "")),
        blocks=[_block_from_dict(b) for b in payload.get("blocks", []) or []],
        toc=list(payload.get("toc", []) or []),
        images=images,
        metadata=dict(payload.get("metadata", {}) or {}),
        page_count=int(payload.get("page_count", 0) or 0),
    )


class DoclingExtractor:
    """Docling structured parser emitting Marker-compatible results.

    Mirrors :class:`MarkerPDFExtractor`'s public surface
    (``require_backend_available`` + ``parse``) so it can be injected wherever a
    structured extractor is expected.
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        *,
        images_scale: float = 2.0,
    ) -> None:
        """Initialise the Docling extractor.

        Args:
            output_dir: Optional working directory for image spill-over.
            images_scale: Render scale for extracted page/figure images
                (2.0 ~= 144 DPI, a good quality/size trade-off).
        """
        self.output_dir = output_dir or Path("./temp_output")
        self.images_scale = images_scale

    @staticmethod
    def require_backend_available() -> None:
        """Preflight docling availability (in-process import OR isolated venv)."""
        try:
            from docling.document_converter import (  # type: ignore # noqa: F401
                DocumentConverter,
            )

            return
        except (ImportError, OSError):
            pass
        if DoclingExtractor._docling_python() is not None:
            return
        raise DoclingBackendUnavailable(DOCLING_INSTALL_HINT)

    @staticmethod
    def _venv_python(venv_dir: Path) -> Path:
        """Interpreter path inside a venv for the current OS (POSIX/Windows)."""
        if os.name == "nt":
            return venv_dir / "Scripts" / "python.exe"
        return venv_dir / "bin" / "python"

    @staticmethod
    def _docling_python() -> str | None:
        """Locate an isolated interpreter that has docling installed.

        Resolution order (cross-platform):
        1. ``DOCLING_PYTHON_PATH`` environment variable (explicit).
        2. ``Settings.docling_python_path`` (from .env / config).
        3. ``.venv-docling`` under the cwd or project root (``bin/python`` on
           POSIX, ``Scripts/python.exe`` on Windows).
        """
        explicit = os.environ.get(_DOCLING_PYTHON_ENV)
        if explicit and Path(explicit).exists():
            return explicit
        with contextlib.suppress(Exception):
            from src.infrastructure.config import Settings

            configured = Settings().docling_python_path
            if configured and Path(configured).exists():
                return configured
        for base in (Path.cwd(), Path(__file__).resolve().parents[2]):
            candidate = DoclingExtractor._venv_python(base / ".venv-docling")
            if candidate.exists():
                return str(candidate)
        return None

    @classmethod
    def _resolve_backend_mode(cls) -> str:
        """Return ``"direct"`` if docling is importable, else ``"subprocess"``.

        Raises DoclingBackendUnavailable when neither path is available.
        """
        try:
            import docling  # type: ignore # noqa: F401

            return "direct"
        except ImportError:
            pass
        if cls._docling_python() is not None:
            return "subprocess"
        raise DoclingBackendUnavailable(DOCLING_INSTALL_HINT)

    @staticmethod
    def _timeout_seconds() -> float:
        """Resolve the subprocess timeout budget (seconds)."""
        raw = os.environ.get(_DOCLING_TIMEOUT_ENV)
        if raw:
            with contextlib.suppress(ValueError, TypeError):
                return float(raw)
        return _DEFAULT_DOCLING_TIMEOUT

    def _parse_subprocess(
        self,
        pdf_path: Path,
        *,
        extract_images: bool = True,
        page_map: list[int] | None = None,
        reported_page_count: int | None = None,
    ) -> MarkerParseResult:
        """Parse via an isolated Python that has docling installed.

        Runs this module as a worker under the isolated interpreter, then
        rebuilds the MarkerParseResult from the worker's on-disk payload. Keeps
        heavy torch imports out of the MCP server process (OOM isolation).
        """
        import tempfile

        python_path = self._docling_python()
        if python_path is None:
            raise DoclingBackendUnavailable(DOCLING_INSTALL_HINT)

        with tempfile.TemporaryDirectory(prefix="docling_") as tmp:
            out_dir = Path(tmp)
            cmd = [
                python_path,
                "-m",
                "src.infrastructure.docling_adapter",
                str(pdf_path),
                str(out_dir),
            ]
            if not extract_images:
                cmd.append("--no-images")
            env = dict(os.environ)
            project_root = str(Path(__file__).resolve().parents[2])
            env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_seconds(),
                    env=env,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise DoclingBackendUnavailable(DOCLING_INSTALL_HINT) from exc
            except subprocess.TimeoutExpired as exc:
                raise DoclingParseError(
                    f"Docling worker timed out after {self._timeout_seconds()}s"
                ) from exc
            if proc.returncode != 0:
                raise DoclingParseError(
                    f"Docling worker failed (exit {proc.returncode}): "
                    f"{proc.stderr[:500]}"
                )
            result = _deserialize_result_from_dir(out_dir)

        if page_map:
            self._apply_page_map(result.blocks, page_map)
        if reported_page_count:
            result.page_count = reported_page_count
        result.metadata.setdefault("backend", "docling")
        result.metadata["docling_mode"] = "subprocess"
        return result

    def _build_converter(self, *, extract_images: bool) -> Any:
        """Create a DocumentConverter with picture generation toggled."""
        from docling.datamodel.base_models import InputFormat  # type: ignore
        from docling.datamodel.pipeline_options import (  # type: ignore
            PdfPipelineOptions,
        )
        from docling.document_converter import (  # type: ignore
            DocumentConverter,
            PdfFormatOption,
        )

        pipeline_options = PdfPipelineOptions()
        # Enable image byte generation only when figures are requested.
        for attr in ("generate_picture_images", "generate_page_images"):
            if hasattr(pipeline_options, attr):
                setattr(pipeline_options, attr, extract_images)
        if hasattr(pipeline_options, "images_scale"):
            pipeline_options.images_scale = self.images_scale
        if hasattr(pipeline_options, "do_table_structure"):
            pipeline_options.do_table_structure = True

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

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

        Dispatches to in-process Docling (``direct`` mode) when importable, or to
        an isolated Python via subprocess (``subprocess`` mode) when
        ``DOCLING_PYTHON_PATH`` / ``.venv-docling`` is available. This keeps the
        MCP server process free of heavy torch imports while still exposing a
        production-grade Docling path on runtimes where docling cannot be
        installed in-process (e.g. pre-release Python without torch wheels).
        """
        if self._resolve_backend_mode() == "subprocess":
            return self._parse_subprocess(
                pdf_path,
                extract_images=extract_images,
                page_map=page_map,
                reported_page_count=reported_page_count,
            )
        return self._parse_direct(
            pdf_path,
            extract_images=extract_images,
            max_pages_per_chunk=max_pages_per_chunk,
            page_map=page_map,
            reported_page_count=reported_page_count,
        )

    def _parse_direct(
        self,
        pdf_path: Path,
        *,
        extract_images: bool = True,
        max_pages_per_chunk: int | None = None,
        page_map: list[int] | None = None,
        reported_page_count: int | None = None,
    ) -> MarkerParseResult:
        """Parse in-process using an importable docling (heavy path)."""
        self.require_backend_available()
        converter = self._build_converter(extract_images=extract_images)
        result = converter.convert(str(pdf_path))
        document = getattr(result, "document", None)
        if document is None:
            raise DoclingBackendUnavailable(
                "Docling returned no document; the file may be unsupported."
            )

        markdown = self._export_markdown(document)
        blocks = self._extract_blocks(document)
        images = self._extract_images(document) if extract_images else {}
        page_count = self._resolve_page_count(document, reported_page_count)

        if page_map:
            self._apply_page_map(blocks, page_map)

        toc = self._extract_toc(blocks)
        metadata: dict[str, Any] = {
            "backend": "docling",
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

    @staticmethod
    def _export_markdown(document: Any) -> str:
        """Export DoclingDocument to Markdown, defensively."""
        exporter = getattr(document, "export_to_markdown", None)
        if callable(exporter):
            try:
                return str(exporter() or "")
            except Exception:
                logger.warning("Docling export_to_markdown failed", exc_info=True)
        return ""

    def _extract_blocks(self, document: Any) -> list[MarkerBlock]:
        """Map DoclingDocument items to Marker-compatible blocks."""
        blocks: list[MarkerBlock] = []
        try:
            iterator = document.iterate_items()
        except Exception:
            logger.warning("Docling iterate_items unavailable", exc_info=True)
            return blocks

        for counter, entry in enumerate(iterator, start=1):
            item = entry[0] if isinstance(entry, tuple) else entry
            label = str(getattr(item, "label", "") or "").lower()
            block_type = _DOCLING_LABEL_MAP.get(label, "Text")
            text = str(getattr(item, "text", "") or "")
            page, bbox = self._first_provenance(item)
            blocks.append(
                MarkerBlock(
                    block_id=f"docling_{counter}",
                    block_type=block_type,
                    page=page,
                    text=text,
                    bbox=bbox,
                    metadata={"docling_label": label},
                )
            )
        return blocks

    @staticmethod
    def _first_provenance(item: Any) -> tuple[int, list[float]]:
        """Extract (1-indexed page, [x0,y0,x1,y1] bbox) from a Docling item."""
        prov = getattr(item, "prov", None) or []
        if not prov:
            return 1, []
        first = prov[0]
        page = int(getattr(first, "page_no", 1) or 1)
        bbox: list[float] = []
        bb = getattr(first, "bbox", None)
        if bb is not None:
            try:
                bbox = [float(bb.l), float(bb.t), float(bb.r), float(bb.b)]
            except Exception:
                bbox = []
        return page, bbox

    def _extract_images(self, document: Any) -> dict[str, bytes]:
        """Render Docling picture items to PNG bytes keyed by a stable name."""
        images: dict[str, bytes] = {}
        pictures = getattr(document, "pictures", None) or []
        for idx, picture in enumerate(pictures):
            page, _bbox = self._first_provenance(picture)
            pil_image = self._picture_pil(picture, document)
            if pil_image is None:
                continue
            try:
                buffer = io.BytesIO()
                pil_image.save(buffer, format="PNG")
            except Exception:
                logger.debug("Docling picture %d not serialisable", idx, exc_info=True)
                continue
            # Marker-like key: ``_page_<0-indexed>_Figure_<n>.png``
            images[f"_page_{page - 1}_Figure_{idx}.png"] = buffer.getvalue()
        return images

    @staticmethod
    def _picture_pil(picture: Any, document: Any) -> Any:
        """Best-effort retrieval of a PIL image from a Docling picture item."""
        image_ref = getattr(picture, "image", None)
        pil_image = getattr(image_ref, "pil_image", None) if image_ref else None
        if pil_image is not None:
            return pil_image
        getter = getattr(picture, "get_image", None)
        if callable(getter):
            try:
                return getter(document)
            except Exception:
                return None
        return None

    @staticmethod
    def _apply_page_map(blocks: list[MarkerBlock], page_map: list[int]) -> None:
        """Remap subset-local page numbers back to original PDF pages in place."""
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
    def _resolve_page_count(document: Any, reported_page_count: int | None) -> int:
        """Resolve the reported page count."""
        if reported_page_count:
            return reported_page_count
        pages = getattr(document, "pages", None)
        if pages is not None:
            with contextlib.suppress(Exception):
                return len(pages)
        return 0


def _run_worker(argv: list[str]) -> int:
    """Worker entry point: parse a PDF with in-process docling and serialise.

    Invoked as ``python -m src.infrastructure.docling_adapter <pdf> <out_dir>
    [--no-images]`` under an isolated interpreter that has docling installed.
    The parent process (any Python) then rebuilds the result from the on-disk
    payload via :func:`_deserialize_result_from_dir`.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Docling isolated worker")
    parser.add_argument("pdf_path")
    parser.add_argument("output_dir")
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args(argv)

    extractor = DoclingExtractor()
    result = extractor._parse_direct(
        Path(args.pdf_path),
        extract_images=not args.no_images,
        page_map=None,
        reported_page_count=None,
    )
    _serialize_result_to_dir(result, Path(args.output_dir))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_run_worker(sys.argv[1:]))
