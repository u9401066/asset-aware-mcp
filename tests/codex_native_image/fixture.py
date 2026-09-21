"""Build an explicitly derived EXIF-oriented PNG from the pinned NIST original."""

import io
import shutil

import pymupdf
from PIL import Image, ImageOps

from tests.codex_native_pdf.trace import digest
from tests.codex_pdf.trace import require
from tests.real_pdf.corpus import cases, check_source


def prepare(corpus, workspace):
    case = next(c for c in cases() if c["id"] == "nist-1648a")
    original = corpus / case["filename"]
    check_source(original, case)
    pdf_path = workspace / "source.pdf"
    shutil.copyfile(original, pdf_path)
    with pymupdf.open(pdf_path) as pdf:
        page = pdf[4]
        scale = 1400 / max(page.rect.width, page.rect.height)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        upright = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        words = page.get_text("words")
        anchor = next(w for w in words if w[4] == "Aluminum")
        row = [w for w in words if abs(w[1] - anchor[1]) < 2]
        require(
            [w[4] for w in row] == ["Aluminum", "(Al)(a,b)", "3.43", "±", "0.13", "%"],
            "Pinned first-row text geometry changed",
        )
        bounds = [
            min(w[0] for w in row) / page.rect.width,
            min(w[1] for w in row) / page.rect.height,
            max(w[2] for w in row) / page.rect.width,
            max(w[3] for w in row) / page.rect.height,
        ]
    upright.save(workspace / "upright-oracle.png")
    stored = upright.transpose(Image.Transpose.ROTATE_90)
    exif = Image.Exif()
    exif[274] = 6
    output = io.BytesIO()
    stored.save(output, format="PNG", exif=exif)
    source = workspace / "source.png"
    source.write_bytes(output.getvalue())
    with Image.open(source) as decoded:
        require(
            ImageOps.exif_transpose(decoded).tobytes() == upright.tobytes(),
            "Fixture orientation round trip differs",
        )
    return {
        "case": case,
        "source_sha256": digest(source.read_bytes()),
        "source_mtime_ns": source.stat().st_mtime_ns,
        "pdf_mtime_ns": pdf_path.stat().st_mtime_ns,
        "derivation": {
            "kind": "benchmark rasterization; not a NIST-published PNG",
            "pdf_sha256": case["sha256"],
            "page_index": 4,
            "renderer": "PyMuPDF " + pymupdf.VersionBind,
            "size_px": list(upright.size),
            "upright_rgb_sha256": digest(upright.tobytes()),
            "source_orientation": 6,
            "first_row_text_bounds": bounds,
        },
    }
