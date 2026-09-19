"""Preview original DOCX bytes through optional Writer, without DFM reconstruction."""

from __future__ import annotations

import hashlib
import math
import tempfile
import time
from pathlib import Path
from typing import Any

from src.domain.native_assets import MAX_NATIVE_BYTES
from src.domain.native_pdf import MAX_PDF_PAGES, NativePdfPageLocator
from src.infrastructure.native_docx_render_source import rendering_source
from src.infrastructure.native_office_process import (
    office_binary,
    prepare_profile,
    run_office,
)
from src.infrastructure.native_pdf_process import ProcessNativePdf


class LibreOfficeWordRenderer:
    def __init__(self, timeout: float = 60):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("DOCX render timeout must be finite and positive")
        self.timeout = timeout

    def render(self, data: bytes, page_index: int, render_size: int) -> dict[str, Any]:
        if type(page_index) is not int or not 0 <= page_index < MAX_PDF_PAGES:
            raise ValueError("DOCX preview index must be zero-based and below 2000")
        if not 64 <= render_size <= 2048:
            raise ValueError("DOCX render dimension must be 64..2048 pixels")
        rendering_source(data)
        binary = office_binary("Writer")
        deadline = time.monotonic() + self.timeout
        with tempfile.TemporaryDirectory(prefix="native-docx-render-") as directory:
            root = Path(directory)
            profile = prepare_profile(root, writer=True)
            version = run_office(
                [binary, profile, "--headless", "--version"],
                root,
                deadline - time.monotonic(),
            )
            if "LibreOffice" not in version:
                raise ValueError("Could not identify the LibreOffice renderer version")
            source = root / "source.docx"
            source.write_bytes(data)
            run_office(
                [
                    binary,
                    profile,
                    "--headless",
                    "--norestore",
                    "--nodefault",
                    "--convert-to",
                    "pdf:writer_pdf_Export",
                    "--outdir",
                    str(root),
                    str(source),
                ],
                root,
                deadline - time.monotonic(),
            )
            pdf = root / "source.pdf"
            if not pdf.is_file() or pdf.is_symlink():
                raise ValueError(
                    "LibreOffice produced no document PDF; check that Writer is installed and can open this DOCX"
                )
            if not 0 < pdf.stat().st_size <= MAX_NATIVE_BYTES:
                raise ValueError("Rendered DOCX PDF exceeds the byte limit")
            with pdf.open("rb") as handle:
                converted = handle.read(MAX_NATIVE_BYTES + 1)
            if len(converted) > MAX_NATIVE_BYTES:
                raise ValueError("Rendered DOCX PDF exceeds the byte limit")
            if (
                source.is_symlink()
                or source.stat().st_size != len(data)
                or source.read_bytes() != data
            ):
                raise ValueError("Renderer changed its temporary source copy")
            metadata = ProcessNativePdf(timeout=deadline - time.monotonic()).inspect(
                converted
            )
            count = metadata["page_count"]
            if not 1 <= count <= MAX_PDF_PAGES or page_index >= count:
                raise ValueError(
                    f"DOCX preview page {page_index} is outside rendered page count {count}"
                )
            page = metadata["pages"][page_index]
            locator = NativePdfPageLocator.model_validate(page["locator"])
            png = ProcessNativePdf(timeout=deadline - time.monotonic()).render(
                converted, locator, render_size
            )
        return {
            "image_png": png,
            "image_sha256": hashlib.sha256(png).hexdigest(),
            "rendered_pdf_sha256": hashlib.sha256(converted).hexdigest(),
            "page_index": page_index,
            "page_count": count,
            "next_page_index": page_index + 1 if page_index + 1 < count else None,
            "page_geometry": {
                key: page[key] for key in ("media_box", "crop_box", "rotation")
            },
            "renderer": {"name": "LibreOffice Writer", "version": version[:256]},
            "render_size": render_size,
            "rendering_scope": "static_libreoffice_document_page_preview",
            "limitations": [
                "Installed fonts and LibreOffice pagination may differ from Microsoft Word.",
                "Each request creates a fresh rendition; fields can recalculate and page indices are rendition-local.",
                "Comments, revision display and interactive objects require separate review; form fields use static print output.",
                "A preview is not a semantic or visual verification verdict.",
            ],
        }
