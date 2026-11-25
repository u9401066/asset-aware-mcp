"""Independent expected Word note CRUD and actual Writer page observations."""

import re
from copy import deepcopy
from dataclasses import dataclass

import pymupdf
from lxml import etree

from tests.native_docx_layout_helpers import independent_pdf
from tests.native_docx_notes_helpers import END, FOOT, W, digest, locator, parts

CORRECTED = " VERIFIED FOOTNOTE 007 µg -0.50 mg/L"


def edits(catalog, old):
    result = []
    for kind, part, identity, prefix, offset, text in [
        ("footnote", FOOT, 11, "Source", 10, "NEW FOOTNOTE 007 µg"),
        ("endnote", END, 12, "Second", 22, "NEW ENDNOTE -0.50 mg/L"),
    ]:
        node = next(
            n for n in catalog["body"]["text_nodes"] if n["text"].startswith(prefix)
        )
        assert node["text_sha256"] == digest(node["text"].encode())
        result.append(
            {
                "op": "create",
                "note_kind": kind,
                "part": part,
                "note_id": identity,
                "anchor": {
                    "text_path": node["path"],
                    "character_offset": len(node["text"])
                    if kind == "endnote"
                    else offset,
                    "expected_text_sha256": digest(node["text"].encode()),
                },
                "blocks": [
                    {
                        "kind": "paragraph",
                        "runs": [
                            {"text": text, "font_name": "Arial", "font_size_pt": 9}
                        ],
                    }
                ],
            }
        )
    result.append(
        {
            "op": "delete",
            "locator": locator(identity=8),
            "expected_note_sha256": old["note_xml_sha256"],
            "literal_body_text": "preserve",
        }
    )
    return result


def text_edit(record):
    node = next(n for n in record["text_nodes"] if "FOOTNOTE" in n["text"])
    return {
        "locator": locator(),
        "shared_scope": "all_native_references",
        "edits": [{"op": "set_text", "path": node["path"], "text": CORRECTED}],
    }


def id_correction():
    return [
        {
            "op": "remap_ids",
            "part": part,
            "note_kind": kind,
            "mappings": [{"note_id": old, "new_note_id": new} for old, new in pairs],
        }
        for part, kind, pairs in [
            (FOOT, "footnote", [(11, 1)]),
            (END, "endnote", [(12, 1), (5, 2)]),
        ]
    ]


def assert_native_id_correction(before, after):
    original, corrected = parts(before), parts(after)
    assert original.keys() == corrected.keys()
    assert {p for p in original if original[p] != corrected[p]} == {
        FOOT,
        END,
        "word/document.xml",
    }
    expected = {
        p: etree.fromstring(original[p]) for p in [FOOT, END, "word/document.xml"]
    }
    for part, kind, mapping in [
        (FOOT, "footnote", {11: 1}),
        (END, "endnote", {12: 1, 5: 2}),
    ]:
        for n in expected[part]:
            old = int(n.get(W + "id"))
            if old in mapping:
                n.set(W + "id", str(mapping[old]))
        for n in expected["word/document.xml"].iter(W + kind + "Reference"):
            old = int(n.get(W + "id"))
            if old in mapping:
                n.set(W + "id", str(mapping[old]))
    for part, root in expected.items():
        assert canonical(root) == canonical(etree.fromstring(corrected[part]))


def canonical(node):
    return etree.tostring(node, method="c14n", exclusive=True)


def assert_native_stages(original, intermediate, final):
    before, mid, after = map(parts, [original, intermediate, final])
    assert before.keys() == mid.keys() == after.keys()
    assert {k for k in before if before[k] != mid[k]} == {
        FOOT,
        END,
        "word/document.xml",
    }
    assert {k for k in mid if mid[k] != after[k]} == {FOOT}
    expected = etree.fromstring(mid[FOOT])
    node = next(n for n in expected if n.get(W + "id") == "2")
    next(n for n in node.iter(W + "t") if "FOOTNOTE" in n.text).text = CORRECTED
    assert canonical(expected) == canonical(etree.fromstring(after[FOOT]))
    for part, kind, old_ids, new_ids in [
        (FOOT, "footnote", {-1, 0, 2, 8}, {-1, 0, 2, 11}),
        (END, "endnote", {-1, 0, 5}, {-1, 0, 5, 12}),
    ]:
        old = {int(n.get(W + "id")): n for n in etree.fromstring(before[part])}
        new = {int(n.get(W + "id")): n for n in etree.fromstring(mid[part])}
        assert old.keys() == old_ids and new.keys() == new_ids
        for key in old_ids & new_ids:
            assert canonical(old[key]) == canonical(new[key])
        created = new[11 if kind == "footnote" else 12]
        assert len(list(created.iter(W + kind + "Ref"))) == 1
    old_main, new_main = (
        etree.fromstring(p["word/document.xml"]) for p in (before, after)
    )
    assert "".join(n.text or "" for n in old_main.iter(W + "t")) == "".join(
        n.text or "" for n in new_main.iter(W + "t")
    )
    assert [n.get(W + "id") for n in new_main.iter(W + "footnoteReference")] == [
        "11",
        "2",
    ]
    assert [n.get(W + "id") for n in new_main.iter(W + "endnoteReference")] == [
        "12",
        "5",
    ]

    def styles(root):
        return [
            (c, canonical(n.getparent().find(W + "rPr")))
            for n in root.iter(W + "t")
            for c in (n.text or "")
        ]

    assert styles(new_main) == styles(old_main)
    restored = deepcopy(new_main)
    assert len(list(restored.iter(W + "sectPr"))) == len(
        list(old_main.iter(W + "sectPr"))
    )


@dataclass(frozen=True)
class NoteLayout:
    """Writer pagination of the note fixture, as observed on ``baseline``."""

    baseline: str
    pages: int
    endnote_page: int
    continuous_endnotes: bool


# Writer 7.3 and 24.2.7.2 (ubuntu-24.04) start the endnotes on their own page.
SEPARATE_ENDNOTE_PAGE = NoteLayout(
    "LibreOffice 7.3 / 24.2.7.2: endnotes start a separate third page",
    pages=3,
    endnote_page=2,
    continuous_endnotes=False,
)
# Writer 26.2 (ubuntu-26.04, re-baselined on 26.2.7.3) lays DOCX endnotes out
# continuously, like Word: right after the last body line of page 2.
CONTINUOUS_ENDNOTES = NoteLayout(
    "LibreOffice 26.2.7.3: endnotes follow the last body line on page 2",
    pages=2,
    endnote_page=1,
    continuous_endnotes=True,
)


def note_layout(pdf):
    """Pick the layout baseline recorded for the Writer that produced ``pdf``."""
    producer = pdf.metadata.get("producer") or ""
    match = re.match(r"LibreOffice (\d+)\.(\d+)", producer)
    assert match, f"Independent replay was not produced by LibreOffice: {producer!r}"
    version = (int(match[1]), int(match[2]))
    if version <= (24, 2):
        return SEPARATE_ENDNOTE_PAGE
    if version >= (26, 2):
        return CONTINUOUS_ENDNOTES
    raise AssertionError(
        f"No recorded note layout baseline for {producer}; verify its pages and "
        "extend tests/native_docx_note_lifecycle_helpers.py"
    )


def flat(text):
    return " ".join(text.split())


def assert_continuous_endnotes(pdf, texts, *, final):
    """Re-baselined on LibreOffice 26.2.7.3: numbering and placement per page."""
    first, last = (flat(text) for text in texts)
    page = pdf[1]
    body = page.search_for("Second value -0.50 mg/L")
    endnotes = page.search_for("ENDNOTE")
    page_footnotes = page.search_for("FOOTNOTE")
    assert len(body) == 1 and endnotes, texts
    # Endnotes run on directly below the last body line, in the top half of the
    # page; footnotes stay in the bottom area of the page that references them.
    assert all(body[0].y1 < r.y0 < page.rect.height / 2 for r in endnotes), texts
    assert all(
        r.y0 > p.rect.height / 2 for p in pdf for r in p.search_for("FOOTNOTE")
    ), texts
    assert all(e.y1 < f.y0 for e in endnotes for f in page_footnotes), texts
    # Automatic numbering stays separate: body marks and note areas agree on
    # footnotes 1, 2 and endnotes i, ii.
    if final:
        assert first.startswith("Source 0071 µg and preserved run.2"), texts
        assert "1 NEW FOOTNOTE 007 µg 2 VERIFIED FOOTNOTE" in first, texts
        assert last.startswith("Second value -0.50 mg/L.iii"), texts
        assert "i NEW ENDNOTE -0.50 mg/L ii ENDNOTE 1,234.50" in last, texts
        assert not page_footnotes and texts[1].count("KEEP SECOND PARAGRAPH") == 1
    else:
        assert first.startswith("Source 007 µg and preserved run.1"), texts
        assert "1 FOOTNOTE 007 µg -0.50 mg/L" in first, texts
        assert last.startswith("Second value -0.50 mg/L.2i"), texts
        assert "i ENDNOTE 1,234.50" in last and "2 REMOVE OLD FOOTNOTE" in last
        assert texts[1].count("KEEP SECOND PARAGRAPH") == 2, texts


def inspect_pages(data, *, final):
    pdf_data = independent_pdf(data)
    with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
        layout = note_layout(pdf)
        texts = [p.get_text() for p in pdf]
        end = layout.endnote_page
        assert len(texts) == layout.pages, (layout.baseline, texts)
        assert "Source 007" in texts[0] and "Second value -0.50 mg/L" in texts[1]
        assert "FOOTNOTE 007 µg -0.50 mg/L" in texts[0]
        assert "ENDNOTE 1,234.50" in texts[end]
        assert (
            "KEEP SECOND PARAGRAPH" in texts[0]
            and "KEEP SECOND PARAGRAPH" in texts[end]
        )
        if final:
            assert "VERIFIED FOOTNOTE" in texts[0] and "NEW FOOTNOTE 007 µg" in texts[0]
            assert "NEW ENDNOTE -0.50 mg/L" in texts[end]
            assert "REMOVE OLD FOOTNOTE" not in "".join(texts)
            assert "ii ENDNOTE" in texts[end]
            assert texts[0].index("NEW FOOTNOTE") < texts[0].index("VERIFIED FOOTNOTE")
            assert texts[end].index("NEW ENDNOTE") < texts[end].index(
                "ENDNOTE 1,234.50"
            )
        else:
            assert "REMOVE OLD FOOTNOTE" in texts[1]
            assert "NEW FOOTNOTE" not in "".join(texts)
        assert pdf[0].search_for("FOOTNOTE")[0].y0 > pdf[0].rect.height / 2
        if layout.continuous_endnotes:
            assert_continuous_endnotes(pdf, texts, final=final)
    return pdf_data, texts


def inspect_id_mismatch(data):
    """Retain the actual Writer failure before the explicit corrective edit.

    Seen on Writer 24.2.7.2 and unchanged on 26.2.7.3: the note areas follow the
    definition order, so the first body mark points at the wrong note text.
    """
    pdf_data = independent_pdf(data)
    with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
        layout = note_layout(pdf)
        texts = [page.get_text() for page in pdf]
        end = layout.endnote_page
        assert len(texts) == layout.pages, (layout.baseline, texts)
        assert "1 VERIFIED FOOTNOTE" in texts[0], texts[0]
        assert "i ENDNOTE 1,234.50" in texts[end], texts[end]
        assert texts[0].index("VERIFIED FOOTNOTE") < texts[0].index("NEW FOOTNOTE")
        assert texts[end].index("ENDNOTE 1,234.50") < texts[end].index("NEW ENDNOTE")
    return pdf_data, texts
