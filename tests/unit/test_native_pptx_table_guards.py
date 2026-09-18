"""Reject table data loss, unsupported source state and corrupted builder results."""

from __future__ import annotations

import pytest

from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure import native_pptx_tables
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_pptx_package import NS
from tests.native_pptx_helpers import build_presentation
from tests.native_pptx_table_helpers import table_addition
from tests.native_workbook_helpers import _replace


@pytest.mark.parametrize(
    "failure",
    [
        "ragged",
        "covered_text",
        "covered_format",
        "overlap",
        "out_of_grid",
        "reversed",
        "single",
        "zero_width",
        "total_extent",
        "xml_text",
        "color",
        "cell_budget",
        "run_budget",
    ],
)
def test_table_request_guards(failure):
    data = build_presentation()
    item = table_addition(data).model_dump()
    table = item["table"]
    if failure == "ragged":
        table["cells"][1].pop()
    elif failure == "covered_text":
        table["cells"][0][1]["paragraphs"][0][0]["text"] = "must not disappear"
    elif failure == "covered_format":
        table["cells"][0][1]["fill_rgb"] = "ABCDEF"
    elif failure == "overlap":
        table["merges"] *= 2
    elif failure == "out_of_grid":
        table["merges"][0]["end_row"] = 99
    elif failure == "reversed":
        table["merges"][0]["row"] = 1
    elif failure == "single":
        table["merges"][0]["end_column"] = 0
    elif failure == "zero_width":
        table["column_widths"][0] = 0
    elif failure == "total_extent":
        table["column_widths"] = [100_000_000] * 3
    elif failure == "xml_text":
        table["cells"][1][1]["paragraphs"][0][0]["text"] = "\x01"
    elif failure == "color":
        table["cells"][1][1]["fill_rgb"] = "red"
    elif failure == "cell_budget":
        table.update(
            column_widths=[100] * 100,
            row_heights=[100] * 100,
            cells=[[{}] * 100] * 100,
            merges=[],
        )
    elif failure == "run_budget":
        table["cells"][1][1]["paragraphs"] = [[{"text": "a"}] * 100] * 100
    batch = [item] * 3 if failure.endswith("budget") else [item]
    with pytest.raises(ValueError):
        NativeDocumentRequest(
            op="add_pptx_tables",
            asset_id="file_" + "a" * 32,
            expected_revision="b" * 64,
            pptx_tables=batch,
        )


@pytest.mark.parametrize(
    "failure", ["text", "width", "margin", "merge", "color", "style", "position"]
)
def test_new_node_is_compared_to_requested_data(failure, monkeypatch):
    data = build_presentation()
    original = native_pptx_tables.build_table

    def broken(*args):
        node = original(*args)
        if failure == "text":
            node.find(".//a:t", NS).text = "wrong"
        elif failure == "width":
            node.find(".//a:gridCol", NS).set("w", "9")
        elif failure == "margin":
            node.find(".//a:tcPr", NS).set("marL", "9")
        elif failure == "merge":
            node.find(".//a:tc", NS).set("gridSpan", "3")
        elif failure == "color":
            node.find(".//a:srgbClr", NS).set("val", "112233")
        elif failure == "style":
            node.find(
                ".//a:tableStyleId", NS
            ).text = "{00000000-0000-0000-0000-000000000000}"
        else:
            node.find("p:xfrm/a:off", NS).set("x", "9")
        return node

    monkeypatch.setattr(native_pptx_tables, "build_table", broken)
    with pytest.raises(ValueError, match="Table read-back"):
        NativePresentation().add_tables(data, [table_addition(data)])


def test_signature_prevents_table_insertion():
    data = build_presentation()
    signed = _replace(data, {"_xmlsignatures/test.xml": b"<signature/>"})
    with pytest.raises(ValueError, match=r"signature|signed"):
        NativePresentation().add_tables(signed, [table_addition(data)])


@pytest.mark.parametrize(
    "failure", ["missing_part", "invalid_default", "external", "duplicate"]
)
def test_destination_style_relationship_is_checked(failure):
    from lxml import etree

    from src.infrastructure.native_ooxml import DOC_REL_NS, REL_NS, xml_bytes
    from src.infrastructure.native_pptx_package import NativePptxPackage

    data = build_presentation()
    package = NativePptxPackage(data)
    rels = package.xml("ppt/_rels/presentation.xml.rels")
    style = next(r for r in rels if r.get("Type") == f"{DOC_REL_NS}/tableStyles")
    replacements = {}
    if failure == "missing_part":
        style.set("Target", "missing.xml")
    elif failure == "external":
        style.set("Target", "https://example.com/styles.xml")
        style.set("TargetMode", "External")
    elif failure == "duplicate":
        etree.SubElement(
            rels,
            f"{{{REL_NS}}}Relationship",
            Id="extraStyle",
            Type=style.get("Type"),
            Target=style.get("Target"),
        )
    else:
        styles = package.xml("ppt/tableStyles.xml")
        styles.set("def", "not-a-guid")
        replacements["ppt/tableStyles.xml"] = xml_bytes(styles)
    replacements["ppt/_rels/presentation.xml.rels"] = xml_bytes(rels)
    broken = _replace(data, replacements)
    with pytest.raises(ValueError, match="table style"):
        NativePresentation().add_tables(broken, [table_addition(data)])


def test_absent_destination_style_does_not_import_scratch_style():
    from src.infrastructure.native_ooxml import DOC_REL_NS, xml_bytes
    from src.infrastructure.native_pptx_package import NativePptxPackage

    data = build_presentation()
    package = NativePptxPackage(data)
    rels = package.xml("ppt/_rels/presentation.xml.rels")
    style = next(r for r in rels if r.get("Type") == f"{DOC_REL_NS}/tableStyles")
    rels.remove(style)
    data = _replace(data, {"ppt/_rels/presentation.xml.rels": xml_bytes(rels)})
    updated, result = NativePresentation().add_tables(data, [table_addition(data)])
    assert result.changes[0]["table_style_id"] is None
    assert set(NativePptxPackage(updated).parts) == set(NativePptxPackage(data).parts)
