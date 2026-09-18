"""Graph preservation across writer renumbering, cycles and page movement."""

from __future__ import annotations

import pytest

from src.infrastructure.native_pdf_graph import PdfObjectGraph
from src.infrastructure.native_pdf_package import NativePdfPackage, save_pdf
from tests.native_pdf_helpers import build_pdf, pixels


@pytest.mark.parametrize("feature", ["plain", "links", "forms", "labels"])
def test_native_pdf_roundtrip_graph_and_pixels(feature):
    data = build_pdf(**({feature: True} if feature != "plain" else {}))
    with NativePdfPackage(data) as before:
        records = [before.record(i) for i in range(3)]
        rewritten = save_pdf(before.pdf)
    with NativePdfPackage(rewritten) as after:
        for i, original in enumerate(records):
            changed = after.record(i)
            original.pop("locator")
            changed.pop("locator")
            assert changed == original
    assert pixels(rewritten) == pixels(data)


def test_pdf_page_reorder_keeps_reference_targets_and_graphs():
    data = build_pdf(links=True, forms=True)
    with NativePdfPackage(data) as package:
        mapping = package.page_map()
        expected = [
            PdfObjectGraph(mapping).describe(p.obj, root_page=True)
            for p in package.pdf.pages
        ]
        page = package.pdf.pages[0]
        identity = page.objgen
        del package.pdf.pages[0]
        package.pdf.pages.insert(2, page)
        assert package.pdf.pages[2].objgen == identity
        assert [
            PdfObjectGraph(mapping).describe(p.obj, root_page=True)
            for p in package.pdf.pages
        ] == [expected[1], expected[2], expected[0]]
        changed = save_pdf(package.pdf)
    assert pixels(changed) == [pixels(data)[i] for i in (1, 2, 0)]


def test_graph_rejects_surviving_reference_to_removed_page():
    with NativePdfPackage(build_pdf(links=True)) as package:
        mapping = package.page_map()
        del mapping[package.pdf.pages[1].objgen]
        with pytest.raises(ValueError, match="unselected page"):
            PdfObjectGraph(mapping).describe(package.pdf.pages[0].obj, root_page=True)
