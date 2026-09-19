"""Independent Writer/PyMuPDF replay of complete revision-bound page review."""

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


def replay(data, index, size, require_cjk=False):
    binary = os.environ.get("LIBREOFFICE_BIN") or shutil.which("libreoffice")
    require(binary, "Independent Word preview audit requires LibreOffice")
    with tempfile.TemporaryDirectory(prefix="codex-word-audit-") as temp:
        root = Path(temp)
        source = root / "independent.docx"
        source.write_bytes(data)
        profile = root / "profile"
        (profile / "user").mkdir(parents=True)
        values = {
            "UseLosslessCompression": "true",
            "IsSkipEmptyPages": "false",
            "ExportFormFields": "false",
            "ExportNotes": "false",
            "ExportNotesInMargin": "false",
        }
        settings = '<oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Filter/PDF/Export">'
        settings += "".join(
            f'<prop oor:name="{k}" oor:op="fuse"><value>{v}</value></prop>'
            for k, v in values.items()
        )
        (profile / "user/registrymodifications.xcu").write_text(
            settings + "</item></oor:items>", encoding="utf-8"
        )
        subprocess.run(
            [
                str(binary),
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--convert-to",
                "pdf:writer_pdf_Export",
                "--outdir",
                temp,
                str(source),
            ],
            check=True,
            timeout=60,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        require(source.read_bytes() == data, "Independent renderer changed source")
        with pymupdf.open(root / "independent.pdf") as pdf:
            page = pdf[index]
            if require_cjk:
                check_cjk(page)
            scale = size / max(page.rect.width, page.rect.height)
            image = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            return len(pdf), image.width, image.height, bytes(image.samples)


def check_cjk(page):
    """Mechanical signals accompany image review; they are not a visual verdict."""
    spans = page.get_texttrace()
    if page.number != 0:
        return
    text = "".join(chr(char[0]) for span in spans for char in span["chars"])
    # Painting order may put the Latin space before the CJK run. Native readback
    # checks the full heading; this check concerns its two Chinese codepoints.
    require("研究" in text, "Rendered Chinese heading differs or is missing")
    glyphs = [
        (span["font"], char[1])
        for span in spans
        for char in span["chars"]
        if char[0] in map(ord, "研究")
    ]
    require(
        len(glyphs) == 2
        and all("NotoSansTC" in font and glyph > 0 for font, glyph in glyphs)
        and glyphs[0] != glyphs[1],
        "Expected distinct CJK glyphs in the supplied Noto face",
    )


def validate_renders(
    workspace, asset, calls, final, historical_revisions, require_cjk=False
):
    seen, counts = set(), {}
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != "render_docx_page":
            continue
        result = payload(call)
        revision, index = args["revision"], args["docx_page_index"]
        require(args["asset_id"] == asset["asset_id"], "Wrong rendered Word asset")
        data = (root / revision).read_bytes()
        require(
            digest(data) == revision == result["inspected_revision"],
            "Wrong preview revision",
        )
        require(
            index == result["page_index"] == result["docx_page_index"],
            "Wrong rendered page index",
        )
        blocks = [b for b in call["result"]["content"] if b["type"] == "image"]
        require(len(blocks) == 1, "Actual Word page image missing")
        png = base64.b64decode(blocks[0]["data"], validate=True)
        require(digest(png) == result["image_sha256"], "Word PNG hash differs")
        count, width, height, pixels = replay(
            data, index, args.get("render_size", 1024), require_cjk
        )
        with Image.open(io.BytesIO(png)) as image:
            require(
                image.size == (width, height)
                and image.convert("RGB").tobytes() == pixels,
                "Word preview pixels differ from independent rendering",
            )
        require(result["page_count"] == count, "Rendered page count differs")
        require(
            result["next_page_index"] == (index + 1 if index + 1 < count else None),
            "Bad page continuation",
        )
        require(
            result["renderer"]["name"] == "LibreOffice Writer"
            and result["renderer"]["version"],
            "Missing Writer identity",
        )
        require(
            result["rendering_scope"] == "static_libreoffice_document_page_preview",
            "Wrong preview scope",
        )
        require(
            counts.setdefault(revision, count) == count, "Page count drift across reads"
        )
        (workspace.parent / f"reviewed-word-{len(seen)}.png").write_bytes(png)
        seen.add((revision, index))
    require(
        len(counts) >= 2 and asset["revision"] in counts,
        "Current/historical Word pages missing",
    )
    require(
        (set(counts) - {asset["revision"]}) & historical_revisions,
        "Temporary 008 revision was not visually reviewed",
    )
    require(
        seen
        == {(revision, i) for revision, count in counts.items() for i in range(count)},
        "Incomplete document page review",
    )
    review = final.get("visual_review", {})
    require(
        review.get("scope") == "static_libreoffice_document_page_preview"
        and review.get("word_checked") is False,
        "Unbounded Word fidelity claim",
    )
    require(
        {(p["revision"], p["page_index"]) for p in review.get("reviewed_pages", [])}
        == seen,
        "Claimed review differs from images delivered",
    )
    require(
        isinstance(review.get("findings"), list) and review["findings"],
        "Missing visual findings",
    )
    return {
        "images": len(seen),
        "revisions": len(counts),
        "independent_pixels_match": True,
        "cjk_text_and_font_checked": require_cjk,
        "agent_review": review,
        "scope": "Synthetic static Writer page review; meaning remains agent judgment",
    }
