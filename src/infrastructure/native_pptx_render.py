"""Render an exact PPTX revision through an optional LibreOffice installation."""

from __future__ import annotations

import hashlib
import math
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.native_assets import MAX_NATIVE_BYTES
from src.domain.native_pdf import NativePdfPageLocator
from src.infrastructure.native_office_process import (
    office_binary,
    prepare_profile,
    run_office,
)
from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_pdf_process import ProcessNativePdf
from src.infrastructure.native_pptx_package import NS, NativePptxPackage

if TYPE_CHECKING:
    from src.domain.native_pptx_slides import NativePptxSlideKey

MAX_RENDER_SLIDES = 100


def rendering_source(data: bytes, slide: NativePptxSlideKey) -> tuple[int, int, bool]:
    package = NativePptxPackage(data)
    if not 1 <= len(package.slides) <= MAX_RENDER_SLIDES:
        raise ValueError("Presentation preview supports 1..100 slides per file")
    try:
        index = package.slides.index(slide.model_dump())
    except ValueError as exc:
        raise ValueError("Slide identity does not resolve in this revision") from exc
    # Full-deck export keeps slide number fields and layout inheritance intact.
    # Reject alternative show selections rather than guessing PDF page identity.
    if package.presentation.find("p:custShowLst", NS) is not None:
        raise ValueError("Custom slide shows require a show-aware rendering workflow")
    for name in package.parts:
        if name.endswith(".rels"):
            for item in package.xml(name):
                if (
                    item.get("TargetMode") == "External"
                    and item.get("Type", "") != f"{DOC_REL_NS}/hyperlink"
                ):
                    raise ValueError(
                        "Linked external content is unsupported in slide previews"
                    )
        elif name.endswith(".xml"):
            root = package.xml(name)
            if root.xpath(
                ".//p:showPr/p:sldRg | .//p:showPr/p:custShow", namespaces=NS
            ):
                raise ValueError(
                    "Slide show ranges require a show-aware rendering workflow"
                )
        elif name.lower().endswith((".svg", ".svgz")):
            raise ValueError("SVG media requires a resource-aware rendering workflow")
    root = package.shape_root(slide.part, "slide")
    return index, len(package.slides), root.get("show", "1") in {"0", "false"}


class LibreOfficePresentationRenderer:
    def __init__(self, timeout: float = 60):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Presentation render timeout must be finite and positive")
        self.timeout = timeout

    def render(
        self, data: bytes, slide: NativePptxSlideKey, render_size: int
    ) -> dict[str, Any]:
        if not 64 <= render_size <= 2048:
            raise ValueError("Presentation render dimension must be 64..2048 pixels")
        index, count, hidden = rendering_source(data, slide)
        binary = office_binary()
        deadline = time.monotonic() + self.timeout
        with tempfile.TemporaryDirectory(prefix="native-pptx-render-") as directory:
            root = Path(directory)
            profile = prepare_profile(root)
            version = run_office(
                [binary, profile, "--headless", "--version"],
                root,
                deadline - time.monotonic(),
            )
            if "LibreOffice" not in version:
                raise ValueError("Could not identify the LibreOffice renderer version")
            source = root / "source.pptx"
            source.write_bytes(data)
            run_office(
                [
                    binary,
                    profile,
                    "--headless",
                    "--norestore",
                    "--nodefault",
                    "--convert-to",
                    "pdf:impress_pdf_Export",
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
                    "LibreOffice produced no slide PDF; check that Impress is installed and can open this PPTX"
                )
            if not 0 < pdf.stat().st_size <= MAX_NATIVE_BYTES:
                raise ValueError("Rendered presentation PDF exceeds the byte limit")
            with pdf.open("rb") as handle:
                converted = handle.read(MAX_NATIVE_BYTES + 1)
            if len(converted) > MAX_NATIVE_BYTES:
                raise ValueError("Rendered presentation PDF exceeds the byte limit")
            if (
                source.is_symlink()
                or source.stat().st_size != len(data)
                or source.read_bytes() != data
            ):
                raise ValueError("Renderer changed its temporary source copy")
            parser = ProcessNativePdf(timeout=deadline - time.monotonic())
            metadata = parser.inspect(converted)
            if metadata["page_count"] != count:
                raise ValueError(
                    "Rendered page count differs from the pinned slide list"
                )
            locator = NativePdfPageLocator.model_validate(
                metadata["pages"][index]["locator"]
            )
            parser = ProcessNativePdf(timeout=deadline - time.monotonic())
            png = parser.render(converted, locator, render_size)
        return {
            "image_png": png,
            "image_sha256": hashlib.sha256(png).hexdigest(),
            "rendered_pdf_sha256": hashlib.sha256(converted).hexdigest(),
            "slide_index": index,
            "slide_count": count,
            "hidden": hidden,
            "renderer": {"name": "LibreOffice Impress", "version": version[:256]},
            "render_size": render_size,
            "rendering_scope": "static_libreoffice_slide_preview",
            "limitations": [
                "Installed fonts and LibreOffice may differ from Microsoft PowerPoint.",
                "Animations, transitions and media playback are not represented.",
                "A preview is not a semantic or visual verification verdict.",
            ],
        }
