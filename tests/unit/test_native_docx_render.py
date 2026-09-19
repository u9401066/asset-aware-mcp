"""DOCX preview identity, resource guards, bounded conversion and immutable source."""

from __future__ import annotations

import hashlib

import pytest
from docx.oxml.ns import qn
from lxml import etree

from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure import native_docx_render as rendering
from src.infrastructure.native_docx_render_source import check_fields, rendering_source
from src.infrastructure.native_ooxml import NativeOOXMLPackage, xml_bytes
from tests.native_docx_helpers import call, read_dfm
from tests.native_docx_helpers import native_docx as native_docx
from tests.native_docx_render_helpers import paged_docx
from tests.native_workbook_helpers import _replace


def test_explicit_revision_and_zero_based_page_required():
    args = {
        "op": "render_docx_page",
        "asset_id": "file_" + "a" * 32,
        "revision": "b" * 64,
        "docx_page_index": 0,
    }
    assert NativeDocumentRequest(**args).render_size == 1024
    for field in ("revision", "docx_page_index"):
        with pytest.raises(ValueError, match="Missing"):
            NativeDocumentRequest(**{k: v for k, v in args.items() if k != field})
    for index in (-1, 2000, True, "1"):
        with pytest.raises(ValueError):
            NativeDocumentRequest(**{**args, "docx_page_index": index})


def test_historical_render_uses_exact_managed_bytes(native_docx):
    service, asset, source = native_docx
    data, mtime = source.read_bytes(), source.stat().st_mtime_ns

    class Renderer:
        def render(self, actual, index, size):
            assert actual == data and index == 0 and size == 640
            return {"image_png": b"PNG"}

    service.docx_renderer = service.docx_operations.renderer = Renderer()
    contract = call(service, op="contract", for_op="render_docx_page")
    assert contract["docx_rendering"]["configured"]
    assert "render_docx_page" in contract["formats"]["docx"]
    call(
        service,
        op="update_docx",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        docx_edit={"dfm_text": read_dfm(service, asset).replace("原始段落", "UPDATED")},
    )
    result = call(
        service,
        op="render_docx_page",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        docx_page_index=0,
        render_size=640,
    )
    assert result["inspected_revision"] == hashlib.sha256(data).hexdigest()
    assert not result["source_written"]
    assert source.read_bytes() == data and source.stat().st_mtime_ns == mtime


def test_unconfigured_renderer_fails_explicitly(native_docx):
    service, asset, _ = native_docx
    contract = call(service, op="contract", for_op="render_docx_page")
    assert not contract["docx_rendering"]["configured"]
    assert "render_docx_page" not in contract["formats"]["docx"]
    with pytest.raises(ValueError, match="not configured"):
        call(
            service,
            op="render_docx_page",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            docx_page_index=0,
        )


@pytest.mark.parametrize(
    "instruction",
    [
        '<w:fldChar w:fldCharType="end"/>',
        "<w:instrText>PAGE</w:instrText>",
        '<w:fldChar w:fldCharType="begin"/>',
        '<w:fldChar w:fldCharType="begin"/><w:fldChar w:fldCharType="separate"/><w:fldChar w:fldCharType="separate"/>',
        '<w:fldChar w:fldCharType="begin"/><w:fldChar w:fldCharType="separate"/><w:instrText>PAGE</w:instrText>',
    ],
)
def test_ambiguous_field_instructions_are_not_rendered(instruction):
    root = etree.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        + instruction
        + "</w:p>"
    )
    with pytest.raises(ValueError, match="field"):
        check_fields(root)


@pytest.mark.parametrize("fault", [None, "missing", "traversal"])
def test_relationships_allow_hyperlinks_but_require_internal_parts(fault):
    target, mode, kind = (
        "https://example.invalid/reference",
        ' TargetMode="External"',
        "hyperlink",
    )
    if fault:
        target, mode, kind = (
            ("missing.png" if fault == "missing" else "../../../../outside.png"),
            "",
            "image",
        )
    relationships = f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{kind}" Target="{target}"{mode}/></Relationships>'
    data = _replace(
        paged_docx(), {"word/_rels/linked.xml.rels": relationships.encode()}
    )
    if fault:
        with pytest.raises(ValueError):
            rendering_source(data)
    else:
        rendering_source(data)


@pytest.mark.parametrize(
    "fault", ["external", "svg", "ole", "altChunk", "vml", "vml_part"]
)
def test_preview_rejects_known_resource_loading_paths(fault):
    data = paged_docx()
    if fault == "external":
        changed = {
            "word/_rels/linked.xml.rels": b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="file:///private/image.png" TargetMode="External"/></Relationships>'
        }
    elif fault == "svg":
        changed = {"word/media/danger.svg": b"<svg/>"}
    elif fault == "vml_part":
        changed = {
            "word/drawings/linked.vml": b'<v:imagedata xmlns:v="urn:schemas-microsoft-com:vml" src="file:///private/image.png"/>'
        }
    else:
        package = NativeOOXMLPackage(data)
        root = package.xml("word/document.xml")
        body = root.find(qn("w:body"))
        xml = {
            "ole": '<o:OLEObject xmlns:o="urn:schemas-microsoft-com:office:office"/>',
            "altChunk": '<w:altChunk xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
            "vml": '<v:imagedata xmlns:v="urn:schemas-microsoft-com:vml" src="https://example.invalid/image.png"/>',
        }[fault]
        body.insert(0, etree.fromstring(xml))
        changed = {"word/document.xml": xml_bytes(root)}
    with pytest.raises(ValueError, match=r"external|SVG|embedded|VML"):
        rendering_source(_replace(data, changed))


@pytest.mark.parametrize(
    "instruction",
    ["INCLUDETEXT", "INCLUDEPICTURE", "DDEAUTO", "DATABASE", "LINK", "RD", "PAGE"],
)
@pytest.mark.parametrize("complex_field", [False, True])
def test_fields_are_checked_across_instruction_runs(instruction, complex_field):
    data = paged_docx()
    package = NativeOOXMLPackage(data)
    root = package.xml("word/document.xml")
    paragraph = root.find(".//" + qn("w:p"))
    if complex_field:
        for kind in ("begin", "separate", "end"):
            run = etree.SubElement(paragraph, qn("w:r"))
            field = etree.SubElement(run, qn("w:fldChar"))
            field.set(qn("w:fldCharType"), kind)
            if kind == "begin":
                for text in (
                    instruction[:3],
                    instruction[3:] + ' "file:///private/doc"',
                ):
                    etree.SubElement(
                        etree.SubElement(paragraph, qn("w:r")), qn("w:instrText")
                    ).text = text
    else:
        field = etree.SubElement(paragraph, qn("w:fldSimple"))
        field.set(qn("w:instr"), instruction + ' "file:///private/doc"')
    updated = _replace(data, {"word/document.xml": xml_bytes(root)})
    if instruction == "PAGE":
        rendering_source(updated)
    else:
        with pytest.raises(ValueError, match="Resource-loading"):
            rendering_source(updated)


@pytest.fixture
def fake_conversion(monkeypatch):
    monkeypatch.setattr(rendering, "office_binary", lambda component: "office")
    calls = []

    def run(command, directory, timeout):
        calls.append((command, directory))
        assert timeout > 0
        if "--version" in command:
            return "LibreOffice test-renderer"
        (directory / "source.pdf").write_bytes(b"%PDF-placeholder")
        return ""

    monkeypatch.setattr(rendering, "run_office", run)

    class Pdf:
        def __init__(self, timeout):
            assert timeout > 0

        def inspect(self, data):
            return {
                "page_count": 2,
                "pages": [
                    {
                        "locator": {
                            "page_index": i,
                            "object_id": i + 3,
                            "generation": 0,
                        },
                        "media_box": [0, 0, 612, 792],
                        "crop_box": [0, 0, 612, 792],
                        "rotation": 0,
                    }
                    for i in range(2)
                ],
            }

        def render(self, data, locator, size):
            assert locator.page_index == 1 and size == 640
            return b"PNG"

    monkeypatch.setattr(rendering, "ProcessNativePdf", Pdf)
    return calls, run, Pdf


def test_preview_metadata_and_private_cleanup(fake_conversion):
    calls, _, _ = fake_conversion
    result = rendering.LibreOfficeWordRenderer().render(paged_docx(), 1, 640)
    assert result["page_count"] == 2 and result["next_page_index"] is None
    assert result["image_sha256"] == hashlib.sha256(b"PNG").hexdigest()
    assert result["renderer"]["name"] == "LibreOffice Writer"
    assert all(not directory.exists() for _, directory in calls)


@pytest.mark.parametrize(
    "fault,pattern",
    [
        ("missing", "no document PDF"),
        ("count", "page count"),
        ("large", "byte limit"),
        ("source", "temporary source"),
        ("version", "renderer version"),
    ],
)
def test_bad_converter_output_cannot_return_preview(
    fake_conversion, monkeypatch, fault, pattern
):
    calls, run, pdf = fake_conversion

    def broken(command, directory, timeout):
        output = run(command, directory, timeout)
        if "--version" in command:
            return "unknown" if fault == "version" else output
        if fault == "missing":
            (directory / "source.pdf").unlink()
        if fault == "source":
            (directory / "source.docx").write_bytes(b"changed")
        return output

    monkeypatch.setattr(rendering, "run_office", broken)
    if fault == "count":
        monkeypatch.setattr(pdf, "inspect", lambda *_: {"page_count": 1})
    if fault == "large":
        monkeypatch.setattr(rendering, "MAX_NATIVE_BYTES", 1)
    with pytest.raises(ValueError, match=pattern):
        rendering.LibreOfficeWordRenderer().render(paged_docx(), 1, 640)
    assert all(not directory.exists() for _, directory in calls)
