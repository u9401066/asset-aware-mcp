"""Independent expected Word note CRUD and actual Writer page observations."""

from copy import deepcopy

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


def inspect_pages(data, *, final):
    pdf_data = independent_pdf(data)
    with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
        texts = [p.get_text() for p in pdf]
        assert len(texts) == 3, texts
        assert "Source 007" in texts[0] and "Second value -0.50 mg/L" in texts[1]
        assert "FOOTNOTE 007 µg -0.50 mg/L" in texts[0]
        assert "ENDNOTE 1,234.50" in texts[2]
        assert (
            "KEEP SECOND PARAGRAPH" in texts[0] and "KEEP SECOND PARAGRAPH" in texts[2]
        )
        if final:
            assert "VERIFIED FOOTNOTE" in texts[0] and "NEW FOOTNOTE 007 µg" in texts[0]
            assert "NEW ENDNOTE -0.50 mg/L" in texts[2]
            assert "REMOVE OLD FOOTNOTE" not in "".join(texts)
            assert "ii ENDNOTE" in texts[2]
            assert texts[0].index("NEW FOOTNOTE") < texts[0].index("VERIFIED FOOTNOTE")
            assert texts[2].index("NEW ENDNOTE") < texts[2].index("ENDNOTE 1,234.50")
        else:
            assert "REMOVE OLD FOOTNOTE" in texts[1]
            assert "NEW FOOTNOTE" not in "".join(texts)
        assert pdf[0].search_for("FOOTNOTE")[0].y0 > pdf[0].rect.height / 2
    return pdf_data, texts


def inspect_id_mismatch(data):
    """Retain the actual Writer24 failure before the explicit corrective edit."""
    pdf_data = independent_pdf(data)
    with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
        texts = [page.get_text() for page in pdf]
        assert len(texts) == 3, texts
        assert "1 VERIFIED FOOTNOTE" in texts[0], texts[0]
        assert "i ENDNOTE 1,234.50" in texts[2], texts[2]
        assert texts[0].index("VERIFIED FOOTNOTE") < texts[0].index("NEW FOOTNOTE")
        assert texts[2].index("ENDNOTE 1,234.50") < texts[2].index("NEW ENDNOTE")
    return pdf_data, texts
