"""Independent source streams, underlying pixels and authored annotation checks."""

import io

import pikepdf
import pymupdf

from src.infrastructure.native_pdf_graph import PdfObjectGraph
from tests.codex_pdf.trace import require


def streams(page):
    value = page.obj.get("/Contents", pikepdf.Array())
    parts = [value] if isinstance(value, pikepdf.Stream) else list(value)
    return [part.read_raw_bytes() for part in parts]


def original_annotations(pdf):
    pages = {p.obj.objgen: str(i) for i, p in enumerate(pdf.pages)}
    return [
        [PdfObjectGraph(pages).describe(a) for a in p.obj.get("/Annots", [])]
        for p in pdf.pages
    ]


def preserve_body(original, changed, changed_page):
    with (
        pikepdf.Pdf.open(io.BytesIO(original)) as a,
        pikepdf.Pdf.open(io.BytesIO(changed)) as b,
    ):
        require(len(a.pages) == len(b.pages), "Page count changed")
        require(
            [streams(p) for p in a.pages] == [streams(p) for p in b.pages],
            "Body streams changed",
        )
        old, new = original_annotations(a), original_annotations(b)
        for i, entries in enumerate(old):
            require(
                new[i][: len(entries)] == entries, "Original annotation graph changed"
            )
            if i != changed_page:
                require(new[i] == entries, "Unrequested annotation was added")
    with (
        pymupdf.open(stream=original, filetype="pdf") as a,
        pymupdf.open(stream=changed, filetype="pdf") as b,
    ):
        for i, (left, right) in enumerate(zip(a, b, strict=True)):
            require(
                (left.rect, left.rotation, left.cropbox, left.mediabox)
                == (right.rect, right.rotation, right.cropbox, right.mediabox),
                "Page geometry changed",
            )
            scale = 700 / max(left.rect.width, left.rect.height)
            if i != changed_page:
                one = left.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale), annots=True, alpha=False
                )
                two = right.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale), annots=True, alpha=False
                )
                require(
                    (one.width, one.height, one.samples)
                    == (two.width, two.height, two.samples),
                    "Untouched annotated page pixels changed",
                )
    # Independent reader copies: remove page Annots using MuPDF xrefs and reload
    # to avoid annotation transparency changing the body's compositing path.
    bodies = []
    for data in (original, changed):
        with pymupdf.open(stream=data, filetype="pdf") as reader:
            for page in reader:
                reader.xref_set_key(page.xref, "Annots", "null")
            bodies.append(reader.tobytes())
    with (
        pymupdf.open(stream=bodies[0], filetype="pdf") as a,
        pymupdf.open(stream=bodies[1], filetype="pdf") as b,
    ):
        for left, right in zip(a, b, strict=True):
            require(left.get_text() == right.get_text(), "Native body text changed")
            scale = 700 / max(left.rect.width, left.rect.height)
            one = left.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), annots=False, alpha=False
            )
            two = right.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), annots=False, alpha=False
            )
            require(
                (one.width, one.height, one.samples)
                == (two.width, two.height, two.samples),
                "Underlying body pixels changed",
            )


def authored(data, page_index):
    with pikepdf.Pdf.open(io.BytesIO(data)) as pdf:
        return [
            (str(a.get("/Subtype")), str(a.get("/Contents", "")))
            for a in pdf.pages[page_index].obj.get("/Annots", [])
            if a.get("/Subtype") in {pikepdf.Name.FreeText, pikepdf.Name.Highlight}
        ]


def check_stages(data, case):
    require(len(data) == 4, "Expected register/create/update/delete history")
    index = case["pages"][0]["index"]
    line = " | ".join(case["rows"][0])
    require(authored(data[0], index) == [], "Corpus has unexpected authored markup")
    require(
        authored(data[1], index)
        == [("/Highlight", "First data row"), ("/FreeText", line)],
        "Created annotations differ",
    )
    require(
        authored(data[2], index)
        == [("/Highlight", "First data row"), ("/FreeText", "VERIFIED: " + line)],
        "Updated annotations differ",
    )
    require(
        authored(data[3], index) == [("/FreeText", "VERIFIED: " + line)],
        "Final annotations differ",
    )
    for changed in data[1:]:
        preserve_body(data[0], changed, index)
