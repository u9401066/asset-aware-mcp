"""Slide structure fails atomically on stale state, dependencies and malformed layouts."""

from copy import deepcopy

import pytest
from lxml import etree

from src.domain.native_pptx_slides import NativePptxSlideInsert
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    relationships_path,
    xml_bytes,
)
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_pptx_package import NS, NativePptxPackage
from tests.native_pptx_helpers import build_presentation
from tests.native_workbook_helpers import _call, _replace
from tests.unit.test_native_pptx_operations import managed as managed
from tests.unit.test_native_pptx_slides import insert_request, keys


def presentation_change(data, change):
    package = NativePptxPackage(data)
    change(package.presentation)
    return _replace(data, {package.main_part: xml_bytes(package.presentation)})


@pytest.mark.parametrize("fault", ["duplicate", "missing", "wrong_part", "wrong_id"])
def test_invalid_order_and_deletion_keys_are_rejected(fault):
    adapter, data = NativePresentation(), build_presentation()
    selected = keys(data)
    if fault == "duplicate":
        selected[1] = selected[0]
    elif fault == "missing":
        selected = selected[:1]
    elif fault == "wrong_part":
        selected[0].part = selected[1].part
    else:
        selected[0].slide_id = "999999"
    with pytest.raises(ValueError, match=r"identities|permutation"):
        adapter.reorder_slides(data, selected)
    if fault != "missing":
        with pytest.raises(ValueError, match="identities"):
            adapter.delete_slides(data, selected)


@pytest.mark.parametrize("fault", ["bounds", "layout", "identity_exhaustion"])
def test_insertion_requires_existing_layout_boundary_and_id_capacity(fault):
    adapter, data = NativePresentation(), build_presentation()
    request = insert_request(adapter, data)
    if fault == "bounds":
        request.index = 3
    elif fault == "layout":
        request.slides[0].layout_part = "ppt/slideLayouts/missing.xml"
    else:
        data = presentation_change(
            data,
            lambda root: root.find("p:sldIdLst/p:sldId", NS).set("id", "2147483647"),
        )
    with pytest.raises(ValueError):
        adapter.add_slides(data, request)


@pytest.mark.parametrize("operation", ["add", "delete", "reorder"])
@pytest.mark.parametrize("dependency", ["sections", "range", "protected"])
def test_structure_edits_reject_known_index_dependencies_and_protection(
    operation, dependency
):
    adapter, data = NativePresentation(), build_presentation()

    def change(root):
        tag = {
            "sections": "{http://schemas.microsoft.com/office/powerpoint/2010/main}sectionLst",
            "range": f"{{{NS['p']}}}sldRg",
            "protected": f"{{{NS['p']}}}modifyVerifier",
        }[dependency]
        etree.SubElement(root, tag)

    data = presentation_change(data, change)
    with pytest.raises(ValueError, match=r"Sections|Protected"):
        if operation == "add":
            adapter.add_slides(data, insert_request(adapter, data))
        elif operation == "delete":
            adapter.delete_slides(data, keys(data)[:1])
        else:
            adapter.reorder_slides(data, list(reversed(keys(data))))


def custom_show(data):
    def change(root):
        selected = root.find("p:sldIdLst/p:sldId", NS)
        show = etree.SubElement(
            etree.SubElement(root, f"{{{NS['p']}}}custShowLst"),
            f"{{{NS['p']}}}custShow",
            name="Keep ordering",
            id="0",
        )
        entry = etree.SubElement(
            etree.SubElement(show, f"{{{NS['p']}}}sldLst"), f"{{{NS['p']}}}sld"
        )
        entry.set(f"{{{DOC_REL_NS}}}id", selected.get(f"{{{DOC_REL_NS}}}id"))

    return presentation_change(data, change)


def test_custom_show_blocks_delete_but_keeps_its_independent_order_on_reorder():
    adapter, data = NativePresentation(), custom_show(build_presentation())
    with pytest.raises(ValueError, match="custom show"):
        adapter.delete_slides(data, keys(data)[:1])
    updated, _ = adapter.reorder_slides(data, list(reversed(keys(data))))
    for data_value in (data, updated):
        root = NativePptxPackage(data_value).presentation
        node = root.find("p:custShowLst", NS)
        value = etree.tostring(node, method="c14n")
        if data_value == data:
            expected = value
        else:
            assert value == expected


@pytest.mark.parametrize("kind", ["slide", "hyperlink", "custom"])
def test_incoming_internal_links_from_retained_parts_block_slide_deletion(kind):
    adapter, data = NativePresentation(), build_presentation()
    package = NativePptxPackage(data)
    owner = package.slides[1]["part"]
    rels = package.xml(relationships_path(owner))
    etree.SubElement(
        rels,
        f"{{{REL_NS}}}Relationship",
        Id="rIdIncoming",
        Type=f"{DOC_REL_NS}/{kind}",
        Target="slide1.xml",
    )
    data = _replace(data, {relationships_path(owner): xml_bytes(rels)})
    with pytest.raises(ValueError, match="incoming"):
        adapter.delete_slides(data, keys(data)[:1])


@pytest.mark.parametrize(
    "fault",
    ["duplicate_master", "wrong_master", "unsupported_placeholder", "duplicate_shapes"],
)
def test_malformed_layouts_cannot_be_used_for_new_slides(fault):
    adapter, data = NativePresentation(), build_presentation()
    request = insert_request(adapter, data, layout_type="title")
    package = NativePptxPackage(data)
    part = request.slides[0].layout_part
    if fault == "duplicate_master":
        root = package.presentation
        master_ids = root.find("p:sldMasterIdLst", NS)
        master_ids.append(deepcopy(master_ids[0]))
        part = package.main_part
    elif fault == "wrong_master":
        part = relationships_path(part)
        root = package.xml(part)
        root[0].set("Target", "../slideMasters/missing.xml")
    else:
        root = package.xml(part)
        tree = root.find("p:cSld/p:spTree", NS)
        if fault == "unsupported_placeholder":
            tree[2].tag = f"{{{NS['p']}}}pic"
        else:
            tree.append(deepcopy(tree[2]))
    data = _replace(data, {part: xml_bytes(root)})
    with pytest.raises(ValueError):
        adapter.add_slides(data, request)


def test_new_part_names_reserve_even_detached_content_type_declarations():
    adapter, data = NativePresentation(), build_presentation()
    package = NativePptxPackage(data)
    root = package.xml("[Content_Types].xml")
    etree.SubElement(
        root,
        "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
        PartName="/ppt/slides/nativeSlide1.xml",
        ContentType="application/xml",
    )
    data = _replace(data, {"[Content_Types].xml": xml_bytes(root)})
    updated, result = adapter.add_slides(data, insert_request(adapter, data))
    assert result.changes[0]["slides"][0]["part"].endswith("nativeSlide2.xml")
    assert "ppt/slides/nativeSlide1.xml" not in NativePptxPackage(updated).parts


def test_bad_second_insert_keeps_managed_revision_and_source_unchanged(managed):
    service, asset, source = managed
    before = service.repository.load(asset["asset_id"])
    data = source.read_bytes()
    request = insert_request(service.presentations, data)
    request.slides.append(deepcopy(request.slides[0]))
    request.slides[1].layout_part = "missing.xml"
    with pytest.raises(ValueError):
        _call(
            service,
            op="add_pptx_slides",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pptx_slide_insert=request.model_dump(),
        )
    assert service.repository.load(asset["asset_id"]) == before
    assert source.read_bytes() == data


def test_stale_and_archived_slide_mutations_fail_without_source_changes(managed):
    service, asset, source = managed
    data = source.read_bytes()
    args = {
        "op": "reorder_pptx_slides",
        "asset_id": asset["asset_id"],
        "expected_revision": asset["revision"],
        "pptx_slide_order": [k.model_dump() for k in reversed(keys(data))],
    }
    changed = _call(service, **args)["asset"]
    with pytest.raises(ValueError, match="stale"):
        _call(service, **args)
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=changed["revision"],
    )
    with pytest.raises(ValueError, match="Archived"):
        _call(service, **{**args, "expected_revision": changed["revision"]})
    assert source.read_bytes() == data


def test_concurrent_slide_edit_cannot_publish_over_another_revision(
    managed, monkeypatch
):
    service, asset, source = managed
    original = service.presentations.add_slides

    def interleave(data, request):
        _call(
            service,
            op="reorder_pptx_slides",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pptx_slide_order=[k.model_dump() for k in reversed(keys(data))],
        )
        return original(data, request)

    monkeypatch.setattr(service.presentations, "add_slides", interleave)
    with pytest.raises(ValueError):
        _call(
            service,
            op="add_pptx_slides",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pptx_slide_insert=insert_request(
                service.presentations, source.read_bytes()
            ).model_dump(),
        )
    current = service.repository.load(asset["asset_id"])
    assert NativePptxPackage(
        service.repository.read(asset["asset_id"], current.revision)
    ).slides == [k.model_dump() for k in reversed(keys(source.read_bytes()))]


def test_slide_input_budget_prevents_unbounded_runs():
    with pytest.raises(ValueError, match="20,000"):
        NativePptxSlideInsert(
            index=0,
            slides=[
                {
                    "layout_part": "layout.xml",
                    "textboxes": [{"paragraphs": [[{"text": "x"}] * 100] * 100}] * 3,
                }
            ],
        )
