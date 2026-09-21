"""Independent audit rejects body drift and missing/tampered continuation pages."""

import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_pdf_annotations.audit import read_page
from tests.codex_pdf_annotations.checks import check_stages, preserve_body
from tests.native_pdf_helpers import build_pdf, page_reference, rewrite
from tests.unit.test_native_pdf_annotation_edits import reference, update


def stages():
    data = [build_pdf()]
    created, _ = update(
        data[-1],
        [
            {
                "op": "create",
                "page_reference": page_reference(data[-1], 0).model_dump(),
                "appearance": {
                    "kind": "Highlight",
                    "quads": [[0.1, 0.1, 0.8, 0.1, 0.1, 0.2, 0.8, 0.2]],
                },
                "metadata": {"contents": "First data row"},
            },
            {
                "op": "create",
                "page_reference": page_reference(data[-1], 0).model_dump(),
                "appearance": {
                    "kind": "FreeText",
                    "rect": [0.1, 0.7, 0.8, 0.9],
                    "text": "007 | µg",
                },
            },
        ],
    )
    data.append(created)
    changed, _ = update(
        data[-1],
        [
            {
                "op": "update",
                "reference": reference(data[-1], "007 | µg"),
                "replace_appearance": {
                    "kind": "FreeText",
                    "rect": [0.1, 0.7, 0.8, 0.9],
                    "text": "VERIFIED: 007 | µg",
                },
            }
        ],
    )
    data.append(changed)
    deleted, _ = update(
        data[-1],
        [
            {
                "op": "delete",
                "reference": reference(data[-1], "First data row"),
                "scope": "annotation_and_owned_popup",
            }
        ],
    )
    data.append(deleted)
    return data


def test_independent_body_and_authored_stage_checks():
    data = stages()
    check_stages(data, {"pages": [{"index": 0}], "rows": [["007", "µg"]]})
    changed = rewrite(
        data[-1],
        lambda pdf: (
            pdf.pages[1].obj.Contents[0].write(b"BT /F1 12 Tf (tampered) Tj ET")
        ),
    )
    with pytest.raises(ValueError, match="Body streams"):
        preserve_body(data[0], changed, 0)
    with pytest.raises(ValueError, match="Created annotations"):
        check_stages(data, {"pages": [{"index": 0}], "rows": [["008", "µg"]]})


@pytest.mark.parametrize("fault", [None, "skip", "hash", "offset", "continuation"])
def test_complete_read_audit_never_accepts_partial_or_tampered_json(fault):
    value = {"contents": "007 µg"}
    text = canonical(value).decode()
    buffers = {}
    first = {
        "text_excerpt": text[:7],
        "text_sha256": digest(text.encode()),
        "excerpt_char_range": [0, 7],
        "next_text_offset": 7,
    }
    assert read_page(buffers, {"op": "read_pdf_annotation"}, first) is None
    last = {
        "text_excerpt": text[7:],
        "text_sha256": first["text_sha256"],
        "excerpt_char_range": [7, len(text)],
        "next_text_offset": None,
    }
    args = {"op": "read_pdf_annotation", "text_offset": 7}
    if fault == "skip":
        buffers.clear()
    elif fault == "hash":
        last["text_excerpt"] = last["text_excerpt"].replace("007", "008")
    elif fault == "offset":
        args["text_offset"] = 8
    elif fault == "continuation":
        last["next_text_offset"] = len(text) + 1
    if fault:
        with pytest.raises(ValueError):
            read_page(buffers, args, last)
    else:
        assert read_page(buffers, args, last) == value
