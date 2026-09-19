"""Reject lossy grid changes, inconsistent merges and corrupted serialized output."""

import pytest
from lxml import etree

from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_pptx import NativePptxShapeLocator
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_pptx_package import NS, NativePptxPackage
from tests.native_pptx_grid_helpers import edit, grid_fixture, reference
from tests.native_workbook_helpers import _replace


@pytest.mark.parametrize(
    "failure",
    [
        "empty_grid",
        "outside",
        "too_many",
        "zero",
        "total",
        "ragged",
        "covered_text",
        "covered_style",
        "stale_hash",
        "wrong_shape",
        "missing_ref",
        "extra_field",
    ],
)
def test_bad_requests_do_not_produce_a_document(failure):
    data, ref, _ = grid_fixture(merge="rectangle")
    item = {"op": "insert", "axis": "row", "index": 1, "sizes": [100000]}
    if failure == "empty_grid":
        item = {"op": "delete", "axis": "row", "index": 0, "count": 3}
    elif failure == "outside":
        item["index"] = 4
    elif failure == "too_many":
        item["sizes"] *= 100
    elif failure == "zero":
        item["sizes"] = [0]
    elif failure == "total":
        item["sizes"] = [100000000]
    elif failure == "ragged":
        item["cells"] = [[{}]]
    elif failure.startswith("covered_"):
        item["cells"] = [[{}, {}, {}]]
        item["cells"][0][0] = (
            {"fill_rgb": "123456"}
            if failure == "covered_style"
            else {"paragraphs": [[{"text": "do not hide"}]]}
        )
    elif failure == "stale_hash":
        ref["value_sha256"] = "0" * 64
    elif failure == "wrong_shape":
        ref["locator"]["shape_id"] = "999999"
    elif failure == "missing_ref":
        ref.pop("value_sha256")
    else:
        item["unknown"] = True
    with pytest.raises(ValueError):
        edit(data, ref, item)


@pytest.mark.parametrize(
    "failure",
    [
        "orphan",
        "overlap",
        "span_bounds",
        "ragged",
        "hidden_text",
        "hidden_field",
        "hidden_extension",
        "hidden_id",
        "hidden_foreign",
        "hidden_relation",
        "signature",
        "protection",
        "zero_extent",
    ],
)
def test_malformed_or_lossy_source_state_is_rejected(failure):
    data, ref, _ = grid_fixture(merge="rectangle")
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    shape = package.locate(locator)
    rows = shape.findall(".//a:tbl/a:tr", NS)
    covered = rows[1].findall("a:tc", NS)[0]
    if failure == "orphan":
        rows[2].findall("a:tc", NS)[2].set("vMerge", "1")
    elif failure == "overlap":
        covered.attrib.clear()
        covered.set("gridSpan", "3")
    elif failure == "span_bounds":
        rows[0][0].set("rowSpan", "100")
    elif failure == "ragged":
        rows[2].remove(rows[2][0])
    elif failure == "hidden_text":
        run = etree.SubElement(covered.find("a:txBody/a:p", NS), f"{{{NS['a']}}}r")
        etree.SubElement(run, f"{{{NS['a']}}}t").text = "hidden evidence"
    elif failure == "hidden_field":
        etree.SubElement(
            covered.find("a:txBody/a:p", NS), f"{{{NS['a']}}}fld", id="keep"
        )
    elif failure == "hidden_extension":
        etree.SubElement(covered, f"{{{NS['a']}}}extLst")
    elif failure == "hidden_id":
        covered.set("id", "keep")
    elif failure == "hidden_foreign":
        etree.SubElement(covered, "{urn:custom}evidence")
    elif failure == "hidden_relation":
        covered.find("a:tcPr", NS).set("{" + NS["r"] + "}embed", "rId9")
    elif failure == "zero_extent":
        shape.find("p:xfrm/a:ext", NS).set("cy", "0")
    replacements = {locator.part: xml_bytes(package.roots[locator.part])}
    if failure == "signature":
        replacements["_xmlsignatures/proof.xml"] = b"<signature/>"
    elif failure == "protection":
        etree.SubElement(package.presentation, f"{{{NS['p']}}}modifyVerifier")
        replacements[package.main_part] = xml_bytes(package.presentation)
    data = _replace(data, replacements)
    with pytest.raises(ValueError):
        edit(
            data,
            reference(data, locator),
            {"op": "delete", "axis": "row", "index": 0, "count": 1},
        )


@pytest.mark.parametrize("target", ["shape", "surrounding_xml", "unrelated_part"])
def test_serialized_corruption_is_detected_independently(target, monkeypatch):
    data, ref, _ = grid_fixture()
    original = NativePptxPackage.replace

    def broken(self, replacements, removed=None):
        result = original(self, replacements, removed)
        package = NativePptxPackage(result)
        locator = NativePptxShapeLocator(**ref["locator"])
        if target == "unrelated_part":
            return _replace(result, {"docProps/core.xml": b"<bad/>"})
        root = package.shape_root(locator.part, locator.region)
        if target == "shape":
            package.locate(locator).find(".//a:tblGrid/a:gridCol", NS).set("w", "9")
        else:
            root.find(".//a:t", NS).text = "changed unrelated text"
        return _replace(result, {locator.part: xml_bytes(root)})

    monkeypatch.setattr(NativePptxPackage, "replace", broken)
    with pytest.raises(ValueError, match=r"read-back|outside|unrelated"):
        edit(data, ref, {"op": "resize", "axis": "row", "index": 0, "sizes": [900000]})


def test_typed_contract_rejects_missing_and_unused_fields():
    _data, ref, _ = grid_fixture()
    request = {
        "op": "update_pptx_table_grid",
        "asset_id": ref["asset_id"],
        "expected_revision": ref["revision"],
        "pptx_table_grid": {
            "reference": ref,
            "edits": [{"op": "resize", "axis": "row", "index": 0, "sizes": [100000]}],
        },
    }
    assert NativeDocumentRequest(**request).pptx_table_grid
    with pytest.raises(ValueError):
        NativeDocumentRequest(**{**request, "pptx_tables": []})
    request.pop("pptx_table_grid")
    with pytest.raises(ValueError):
        NativeDocumentRequest(**request)
