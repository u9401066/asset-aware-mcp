"""Merge/split guards prevent implicit data hiding and ambiguous source conversion."""

import pytest
from lxml import etree

from src.domain.native_pptx import NativePptxShapeLocator
from src.domain.native_pptx_grid import NativePptxTableGridEdit
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_pptx_package import NS, NativePptxPackage
from tests.native_pptx_grid_helpers import edit, grid_fixture, reference, table
from tests.native_workbook_helpers import _call, _replace
from tests.unit.test_native_pptx_grid_operations import request
from tests.unit.test_native_pptx_merges import merge
from tests.unit.test_native_pptx_table_operations import managed as managed


@pytest.mark.parametrize(
    "failure",
    [
        "policy",
        "single",
        "reversed",
        "outside",
        "partial",
        "split_plain",
        "split_covered",
        "extra_axis",
        "nonempty",
    ],
)
def test_merge_and_split_refuse_ambiguous_requests(failure):
    data, ref, _ = grid_fixture()
    change = merge()
    if failure == "policy":
        change.pop("content_policy")
    elif failure == "single":
        change.update(end_row=1, end_column=0)
    elif failure == "reversed":
        change.update(end_row=0)
    elif failure == "outside":
        change.update(end_row=99)
    elif failure == "partial":
        change.update(row=0, column=1)
    elif failure.startswith("split_"):
        change = {
            "op": "split",
            "row": 1 if failure == "split_plain" else 0,
            "column": 1,
        }
    elif failure == "extra_axis":
        change["axis"] = "row"
    else:
        change["content_policy"] = "require_empty"
    with pytest.raises(ValueError):
        edit(data, ref, change)


@pytest.mark.parametrize(
    "content",
    [
        "text",
        "field",
        "break",
        "link",
        "foreign",
        "identity",
        "run_identity",
        "extension",
        "unknown_run",
        "bare_text",
    ],
)
def test_require_empty_detects_content_beyond_plain_visible_text(content):
    data, ref, _ = grid_fixture()
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    covered = package.locate(locator).findall(".//a:tbl/a:tr", NS)[0][1]
    p = covered.find("a:txBody/a:p", NS)
    if content == "text":
        run = etree.SubElement(p, f"{{{NS['a']}}}r")
        etree.SubElement(run, f"{{{NS['a']}}}t").text = " "
    elif content == "foreign":
        etree.SubElement(p, "{urn:custom}meaning")
    elif content == "identity":
        p.set("{urn:custom}id", "retain")
    elif content in {"unknown_run", "run_identity"}:
        run = etree.SubElement(p, f"{{{NS['a']}}}r")
        if content == "unknown_run":
            etree.SubElement(run, f"{{{NS['a']}}}unknown")
        else:
            run.set("{urn:custom}id", "retain")
    elif content == "bare_text":
        p.text = "unmodeled literal"
    else:
        tag = {
            "field": "fld",
            "break": "br",
            "link": "hlinkClick",
            "extension": "extLst",
        }[content]
        etree.SubElement(p, f"{{{NS['a']}}}{tag}")
    data = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    with pytest.raises(ValueError, match="hide"):
        edit(
            data,
            reference(data, locator),
            merge(row=0, end_row=0, content_policy="require_empty"),
        )
    appended, _ = edit(data, reference(data, locator), merge(row=0, end_row=0))
    assert len(table(appended).cell(0, 0).text_frame.paragraphs) == 2


@pytest.mark.parametrize(
    "failure",
    [
        "duplicate",
        "missing_body_properties",
        "no_paragraphs",
        "foreign_child",
        "bare_body_text",
    ],
)
def test_unsupported_text_bodies_are_not_silently_flattened(failure):
    from copy import deepcopy

    data, ref, _ = grid_fixture(merge=None)
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    cell = package.locate(locator).findall(".//a:tbl/a:tr", NS)[1][1]
    body = cell.find("a:txBody", NS)
    if failure == "duplicate":
        cell.insert(0, deepcopy(body))
    elif failure == "missing_body_properties":
        body.remove(body.find("a:bodyPr", NS))
    elif failure == "no_paragraphs":
        body.remove(body.find("a:p", NS))
    elif failure == "bare_body_text":
        body.text = "unmodeled data"
    else:
        etree.SubElement(body, "{urn:custom}extra").text = "must not be hidden"
    data = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    with pytest.raises(ValueError, match=r"structure|Ambiguous"):
        edit(data, reference(data, locator), merge())


def test_valid_merge_then_bad_split_never_commits_partial_state(managed):
    service, _, _, source = managed
    args = request(managed)
    args["pptx_table_grid"]["edits"] = [merge(), {"op": "split", "row": 1, "column": 1}]
    before = service.repository.load(args["asset_id"])
    original = source.read_bytes()
    with pytest.raises(ValueError, match="origin"):
        _call(service, **args)
    assert service.repository.load(args["asset_id"]) == before
    assert source.read_bytes() == original


def test_union_keeps_existing_grid_requests_and_requires_merge_policy():
    _, ref, _ = grid_fixture()
    value = NativePptxTableGridEdit(
        reference=ref,
        edits=[
            {"op": "split", "row": 0, "column": 0},
            {"op": "resize", "axis": "row", "index": 0, "sizes": [600000]},
            merge(),
        ],
    )
    assert [item.op for item in value.edits] == ["split", "resize", "merge"]
