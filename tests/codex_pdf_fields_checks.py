"""Independent low-level form values, source streams, native states and body pixels."""

import io

import pikepdf
import pymupdf

from src.infrastructure.native_pdf_graph import PdfObjectGraph
from tests.codex_pdf.trace import require
from tests.codex_pdf_annotations.checks import streams
from tests.codex_pdf_fields import VALUE


def roots(pdf):
    fields = list(pdf.Root.AcroForm.Fields)
    names = [str(field.get("/T", "")) for field in fields]
    require(len(set(names)) == len(names), "Pinned-case root names are not unique")
    return dict(zip(names, fields, strict=True))


def preserve_body(original, changed):
    with (
        pikepdf.Pdf.open(io.BytesIO(original)) as a,
        pikepdf.Pdf.open(io.BytesIO(changed)) as b,
    ):
        require(len(a.pages) == len(b.pages), "Page count changed")
        require(
            [streams(p) for p in a.pages] == [streams(p) for p in b.pages],
            "Body streams changed",
        )
        left, right = roots(a), roots(b)
        graphs = [
            PdfObjectGraph({p.obj.objgen: str(i) for i, p in enumerate(pdf.pages)})
            for pdf in (a, b)
        ]
        require(
            graphs[0].describe(left["Button2"]) == graphs[1].describe(right["Button2"]),
            "Untouched pushbutton changed",
        )
        for name in ("Check Box3", "Group4"):
            old = list(left[name].get("/Kids", [left[name]]))
            new = list(right[name].get("/Kids", [right[name]]))
            require(len(old) == len(new), "Native button widgets changed")
            for first, second in zip(old, new, strict=True):
                require(
                    graphs[0].describe(first.get("/AP"))
                    == graphs[1].describe(second.get("/AP")),
                    "Native button appearance changed",
                )
    bodies = []
    for data in (original, changed):
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                doc.xref_set_key(page.xref, "Annots", "null")
            bodies.append(doc.tobytes())
    with (
        pymupdf.open(stream=bodies[0], filetype="pdf") as a,
        pymupdf.open(stream=bodies[1], filetype="pdf") as b,
    ):
        for left, right in zip(a, b, strict=True):
            require(
                (left.rect, left.rotation, left.cropbox, left.mediabox)
                == (right.rect, right.rotation, right.cropbox, right.mediabox),
                "Page geometry changed",
            )
            require(left.get_text() == right.get_text(), "Body text changed")
            scale = 900 / max(left.rect.width, left.rect.height)
            one = left.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            two = right.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            require(
                (one.width, one.height, one.samples)
                == (two.width, two.height, two.samples),
                "Underlying body pixels changed",
            )


def check_states(data):
    require(len(data) >= 4, "Missing update/create/delete revisions")
    stages = []
    for raw in data:
        with pikepdf.Pdf.open(io.BytesIO(raw)) as pdf:
            fields = roots(pdf)
            stages.append(
                {name: str(field.get("/V", "")) for name, field in fields.items()}
            )
            if stages[-1].get("Check Box3") == "/Yes":
                require(
                    str(fields["Check Box3"].AS) == "/Yes",
                    "Checkbox appearance state differs",
                )
            if stages[-1].get("Group4") == "/Choice2":
                require(
                    [str(w.AS) for w in fields["Group4"].Kids] == ["/Off", "/Choice2"],
                    "Radio appearance states differ",
                )
    require(
        set(stages[0]) == {"Text1", "Button2", "Check Box3", "Group4"},
        "Unexpected original fields",
    )
    require(
        any(s.get("Text1") == VALUE and "ReviewCopy" not in s for s in stages[1:]),
        "Missing requested Text1 update before creation",
    )
    require(
        any(s.get("Text1") == s.get("ReviewCopy") == VALUE for s in stages[1:]),
        "Missing copied value before deletion",
    )
    require(
        stages[-1]
        == {
            "Button2": stages[0]["Button2"],
            "Check Box3": "/Yes",
            "Group4": "/Choice2",
            "ReviewCopy": VALUE,
        },
        "Final native field values differ",
    )
    for changed in data[1:]:
        preserve_body(data[0], changed)
