"""The note lifecycle render test picks its page baseline from the actual Writer."""

import pytest

from tests.native_docx_note_lifecycle_helpers import (
    CONTINUOUS_ENDNOTES,
    SEPARATE_ENDNOTE_PAGE,
    note_layout,
)


class _Pdf:
    def __init__(self, producer):
        self.metadata = {"producer": producer}


@pytest.mark.parametrize(
    ("producer", "expected"),
    [
        ("LibreOffice 7.3", SEPARATE_ENDNOTE_PAGE),
        ("LibreOffice 24.2.7.2 (X86_64)", SEPARATE_ENDNOTE_PAGE),
        ("LibreOffice 26.2.7.3 (X86_64)", CONTINUOUS_ENDNOTES),
        ("LibreOffice 26.8.0.1 (X86_64)", CONTINUOUS_ENDNOTES),
    ],
)
def test_recorded_writer_lines_map_to_their_baseline(producer, expected):
    assert note_layout(_Pdf(producer)) == expected


def test_baselines_keep_endnotes_on_the_last_page():
    assert (SEPARATE_ENDNOTE_PAGE.pages, SEPARATE_ENDNOTE_PAGE.endnote_page) == (3, 2)
    assert (CONTINUOUS_ENDNOTES.pages, CONTINUOUS_ENDNOTES.endnote_page) == (2, 1)
    assert CONTINUOUS_ENDNOTES.continuous_endnotes
    assert not SEPARATE_ENDNOTE_PAGE.continuous_endnotes


@pytest.mark.parametrize(
    "producer",
    ["LibreOffice 25.8.4.2 (X86_64)", "LibreOffice 24.8.0.3", "Skia/PDF m120", ""],
)
def test_unrecorded_writer_lines_fail_instead_of_guessing(producer):
    with pytest.raises(AssertionError):
        note_layout(_Pdf(producer))
