"""Independent LibreOffice/PyMuPDF replay of actual MCP-delivered slide pixels."""

from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pymupdf
from PIL import Image

from tests.codex_native_pdf.trace import digest, payload
from tests.codex_pdf.trace import require
from tests.codex_pptx_tables.slides import slide_keys


def replay(data, index, size):
    binary = os.environ.get("LIBREOFFICE_BIN") or shutil.which("libreoffice")
    require(binary, "Independent preview audit requires LibreOffice")
    with tempfile.TemporaryDirectory(prefix="codex-slide-audit-") as temp:
        directory = Path(temp)
        source = directory / "independent.pptx"
        source.write_bytes(data)
        profile = directory / "profile"
        (profile / "user").mkdir(parents=True)
        (profile / "user/registrymodifications.xcu").write_text(
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Filter/PDF/Export">'
            '<prop oor:name="ExportHiddenSlides" oor:op="fuse"><value>true</value></prop>'
            "</item></oor:items>",
            encoding="utf-8",
        )
        subprocess.run(
            [
                str(binary),
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--convert-to",
                "pdf:impress_pdf_Export",
                "--outdir",
                temp,
                str(source),
            ],
            check=True,
            timeout=60,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with pymupdf.open(directory / "independent.pdf") as pdf:
            require(len(pdf) == len(slide_keys(data)), "Independent PDF count differs")
            page = pdf[index]
            scale = size / max(page.rect.width, page.rect.height)
            image = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            return image.width, image.height, bytes(image.samples)


def validate_renders(workspace, deck, calls, final):
    seen, count = set(), 0
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != "render_pptx_slide":
            continue
        result = payload(call)
        revision = args["revision"]
        require(args["asset_id"] == deck["asset_id"], "Wrong rendered asset")
        data = (
            workspace / "data/native-assets" / deck["asset_id"] / "revisions" / revision
        ).read_bytes()
        require(
            digest(data) == revision == result["inspected_revision"],
            "Wrong preview revision",
        )
        keys = slide_keys(data)
        # The independent auditor retains original ZIP part names, not python-pptx aliases.
        selected = {k: args["pptx_slide_key"][k] for k in ("slide_id", "part")}
        index = keys.index(selected)
        require(
            result["pptx_slide_key"] == selected and result["slide_index"] == index,
            "Preview slide mapping differs",
        )
        images = [b for b in call["result"]["content"] if b["type"] == "image"]
        require(len(images) == 1, "Whole-slide actual image missing")
        png = base64.b64decode(images[0]["data"], validate=True)
        require(digest(png) == result["image_sha256"], "Slide image hash differs")
        width, height, pixels = replay(data, index, args.get("render_size", 1024))
        with Image.open(io.BytesIO(png)) as image:
            require(
                image.size == (width, height)
                and image.convert("RGB").tobytes() == pixels,
                "Slide preview pixels differ from independent rendering",
            )
        require(
            result["rendering_scope"] == "static_libreoffice_slide_preview",
            "Wrong preview scope",
        )
        require(
            result["renderer"]["name"] == "LibreOffice Impress",
            "Missing renderer identity",
        )
        (workspace.parent / f"reviewed-slide-{count}.png").write_bytes(png)
        seen.add(revision)
        count += 1
    require(
        len(seen) >= 2 and deck["revision"] in seen,
        "Current and historical slide review missing",
    )
    review = final.get("visual_review", {})
    require(
        review.get("scope") == "static_libreoffice_slide_preview"
        and review.get("powerpoint_checked") is False,
        "Unbounded visual review claim",
    )
    require(
        set(review.get("reviewed_revisions", [])) == seen,
        "Reported review differs from delivered images",
    )
    require(
        isinstance(review.get("findings"), list) and review["findings"],
        "Missing visual review findings",
    )
    return {
        "images": count,
        "revisions": len(seen),
        "independent_pixels_match": True,
        "agent_review": review,
        "scope": "Synthetic static slide preview; meaning remains agent judgment",
    }
