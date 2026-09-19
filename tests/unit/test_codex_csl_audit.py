"""Actual-CSL audits must inspect nested PDF records and reject forged chunks."""

import pytest

from tests.codex_csl.audit import readback
from tests.codex_native_pdf.trace import canonical, digest


def page_record(value):
    text = canonical(value).decode("utf-8")
    return {
        "text_excerpt": text,
        "text_sha256": digest(text.encode()),
        "text_length": len(text),
        "excerpt_char_range": [0, len(text)],
        "next_text_offset": None,
    }


def test_nested_native_pdf_page_is_a_complete_hashed_record():
    value = {
        "evidence": {"revision": "original", "locator": {"page_index": 1}},
        "text": "Unicode 中文",
    }
    page = page_record(value)
    result = readback({"page": page}, "read_pdf_page", "document", {}, {})
    assert result == ("read_pdf_page", page["text_sha256"], value)


def test_edited_excerpt_with_unchanged_hash_is_rejected():
    page = page_record({"title": "Alpha"})
    page["text_excerpt"] = page["text_excerpt"].replace("Alpha", "Omega")
    with pytest.raises(ValueError, match="changed result hash"):
        readback(page, "render_citations", "evidence", {}, {})


def test_missing_initial_chunks_cannot_count_as_complete_read():
    page = page_record({"title": "Alpha"})
    page["excerpt_char_range"][0] = 4
    page["text_excerpt"] = page["text_excerpt"][4:]
    with pytest.raises(ValueError, match="Noncontiguous"):
        readback(page, "render_citations", "evidence", {"text_offset": 4}, {})
