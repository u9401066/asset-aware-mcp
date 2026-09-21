"""Native ODS render inputs, resource boundaries and immutable PDF provenance."""

import hashlib
import io
import json
import struct
from pathlib import Path

import pymupdf
import pytest
from lxml import etree
from PIL import Image

from src.application.native_document_service import NativeDocumentService
from src.domain.native_ods import NativeODSCreate
from src.domain.native_pdf import NativePdfCreate
from src.domain.native_rendition import NativeWorkbookRendition
from src.infrastructure import native_workbook_render as rendering
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_odf_package import NS, NativeODFPackage, q, xml_bytes
from src.infrastructure.native_ods import (
    NativeODS,
    NativeODSFileAdapter,
    create_native_ods,
)
from src.infrastructure.native_ods_render_source import rendering_source
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_ods_helpers import edit, fixture, repack
from tests.native_workbook_helpers import _call
from tests.unit.test_native_ods_service import cell, update
from tests.unit.test_native_workbook_rendition import create, read


def formula_source(expression, *, alias="of", namespace=None):
    root = etree.Element("root", nsmap={**NS, alias: namespace or NS["of"]})
    row = etree.SubElement(root, q("table", "table-row"))
    value = etree.SubElement(row, q("table", "table-cell"))
    value.set(q("table", "formula"), f"{alias}:={expression}")
    return fixture(etree.tostring(row, encoding="unicode"))


@pytest.mark.parametrize(
    "expression",
    [
        "[.A1]*2",
        "ISERROR([.#REF!])",
        'IF([.A1]>4;"high";"low")',
        "SUM(['sheet#1'.A1:.A2])",
        '"DDE(""file:///tmp/x"")"',
        "COM.MICROSOFT.XLOOKUP([.A1];[.B1:.B4];[.C1:.C4])",
        "INDIRECT(\"'sheet#1'.A1\")",
    ],
)
def test_local_openformula_keeps_quoted_data_and_names_distinct(expression):
    source = formula_source(expression)
    records = rendering_source(source)
    assert records[0]["key"] == {
        "part": "content.xml",
        "table_index": 0,
        "table_name": "Sheet1",
    }
    assert records[0]["name"] == "Sheet1"


def test_formula_namespace_alias_is_resolved_not_guessed():
    assert rendering_source(formula_source("[.A1]*2", alias="公式"))
    with pytest.raises(ValueError, match="namespace"):
        rendering_source(
            formula_source("[.A1]*2", namespace="urn:unrecognized:formula")
        )


@pytest.mark.parametrize("axis", ["rows", "columns"])
def test_real_drawing_namespace_blocks_repetition_split_without_optional_ids(axis):
    drawing = '<actual:frame xmlns:actual="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"/>'
    row_repeat = ' table:number-rows-repeated="3"' if axis == "rows" else ""
    cell_repeat = ' table:number-columns-repeated="3"' if axis == "columns" else ""
    source = fixture(
        f"<table:table-row{row_repeat}><table:table-cell{cell_repeat}>{drawing}</table:table-cell></table:table-row>"
    )
    with pytest.raises(ValueError, match="mapping-aware"):
        NativeODS(source).edit(
            [edit(row=1 if axis == "rows" else 0, column=1 if axis == "columns" else 0)]
        )
    assert (
        NativeODS(create_native_ods(NativeODSCreate())).root.nsmap["draw"]
        == "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    )


def test_real_drawing_namespace_is_checked_even_with_an_unrelated_prefix():
    source = fixture(
        '<table:table-row><table:table-cell><actual:plugin xmlns:actual="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"/></table:table-cell></table:table-row>'
    )
    with pytest.raises(ValueError, match="resource-aware"):
        rendering_source(source)


def test_repeated_package_images_are_verified_once_per_resource(monkeypatch):
    from src.infrastructure import native_ods_render_source

    output = io.BytesIO()
    Image.new("RGB", (2, 3), "red").save(output, format="PNG")
    source = resource_source(
        "./Pictures/red.png", extra={"Pictures/red.png": output.getvalue()}
    )
    package = NativeODFPackage(source)
    root = package.xml("content.xml")
    node = root.find(".//" + q("draw", "image"))
    assert node is not None
    parent = node.getparent()
    assert parent is not None
    for _ in range(100):
        parent.append(etree.fromstring(etree.tostring(node)))
    count = []
    check = native_ods_render_source._image

    def inspected(data):
        count.append(len(data))
        check(data)

    monkeypatch.setattr(native_ods_render_source, "_image", inspected)
    assert rendering_source(package.replace({"content.xml": xml_bytes(root)}))
    assert count == [len(output.getvalue())]


@pytest.mark.parametrize(
    "expression",
    [
        'WEBSERVICE("https://example.invalid")',
        'ORG.OPENOFFICE.DDE("app";"topic";"item")',
        'COM.MICROSOFT.REGISTER.ID("library";"entry")',
        "COM.EXAMPLE.ADDIN(1)",
        "['file:///tmp/external.ods'#$Sheet1.A1]",
        "INDIRECT([.A1])",
        'INDIRECT("file:///tmp/external.ods#$Sheet1.A1")',
        'INDIRECT("file"&[.A1])',
        "SUM([.A1)",
        '"unterminated',
    ],
)
def test_formula_resources_and_ambiguous_syntax_fail_before_office(
    monkeypatch, expression
):
    calls = []
    monkeypatch.setattr(rendering, "office_binary", lambda *_: calls.append("office"))
    with pytest.raises(ValueError):
        rendering.LibreOfficeODSRenderer().convert(
            formula_source(expression),
            NativeWorkbookRendition(mode="print", calculation="recalculate"),
        )
    assert calls == []


def resource_source(href, *, extra=None, tag="image"):
    row = etree.Element(
        q("table", "table-row"), nsmap={**NS, "xlink": "http://www.w3.org/1999/xlink"}
    )
    cell = etree.SubElement(row, q("table", "table-cell"))
    node = etree.SubElement(cell, q("draw", tag))
    node.set("{http://www.w3.org/1999/xlink}href", href)
    return fixture(etree.tostring(row, encoding="unicode"), extras=extra)


@pytest.mark.parametrize(
    "href",
    [
        "https://example.invalid/x.png",
        "file:///tmp/x.png",
        "../x.png",
        "%2e%2e/x.png",
        "Pictures/missing.png",
    ],
)
def test_external_escaping_and_missing_resources_are_rejected(href):
    with pytest.raises(ValueError):
        rendering_source(resource_source(href))


@pytest.mark.parametrize("href", ["..", "."])
def test_embedded_chart_data_reference_resolves_within_the_package(href):
    chart = f'<office:document-content xmlns:office="{NS["office"]}" xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" xmlns:xlink="http://www.w3.org/1999/xlink"><office:body><office:chart><chart:chart xlink:href="{href}"/></office:chart></office:body></office:document-content>'.encode()
    book = NativeODFPackage(
        resource_source("./Object1", tag="object", extra={"Object1/content.xml": chart})
    )
    manifest = book.xml("META-INF/manifest.xml")
    item = etree.SubElement(manifest, q("manifest", "file-entry"))
    item.set(q("manifest", "full-path"), "Object1/")
    item.set(q("manifest", "media-type"), "application/vnd.oasis.opendocument.chart")
    parts = {**book.parts, "META-INF/manifest.xml": xml_bytes(manifest)}
    assert rendering_source(repack(parts))
    for external in ("../..", "https://example.invalid/", "../missing"):
        with pytest.raises(ValueError):
            rendering_source(
                repack(
                    {
                        **parts,
                        "Object1/content.xml": chart.replace(
                            f'href="{href}"'.encode(), f'href="{external}"'.encode()
                        ),
                    }
                )
            )


def test_chart_metafile_framing_rejects_truncation_and_foreign_records():
    from src.infrastructure.native_ods_render_source import _metafile

    # Native VersionCompat header and one LINECOLOR action. Actual Calc chart
    # decoding and pixel equivalence are tested with an independently authored file.
    header = b"VCLMTF" + struct.pack("<HI", 1, 49) + bytes(45) + struct.pack("<I", 1)
    record = struct.pack("<HHII", 132, 1, 4, 0xFF0000)
    _metafile(header + record)
    for invalid in (
        header + record[:-1],
        header + record + b"extra",
        b"wrong" + record,
        header + struct.pack("<HHI", 143, 1, 0),
        header + struct.pack("<HHI", 147, 1, 0),
        header + struct.pack("<HHI", 512, 1, 10) + bytes(10),
    ):
        with pytest.raises(ValueError):
            _metafile(invalid)


def test_local_raster_and_embedded_chart_are_inspected_without_conversion():
    output = io.BytesIO()
    Image.new("RGB", (2, 3), "red").save(output, format="PNG")
    source = resource_source(
        "./Pictures/red%20one.png", extra={"Pictures/red one.png": output.getvalue()}
    )
    assert len(rendering_source(source)) == 1
    with pytest.raises(ValueError, match="raster"):
        rendering_source(
            resource_source(
                "Pictures/fake.png",
                extra={
                    "Pictures/fake.png": b'<svg xmlns="http://www.w3.org/2000/svg"/>'
                },
            )
        )
    chart = f'<office:document-content xmlns:office="{NS["office"]}"><office:body><office:chart/></office:body></office:document-content>'.encode()
    book = NativeODFPackage(
        resource_source("./Object1", tag="object", extra={"Object1/content.xml": chart})
    )
    manifest = book.xml("META-INF/manifest.xml")
    item = etree.SubElement(manifest, q("manifest", "file-entry"))
    item.set(q("manifest", "full-path"), "Object1/")
    item.set(q("manifest", "media-type"), "application/vnd.oasis.opendocument.chart")
    assert rendering_source(
        repack({**book.parts, "META-INF/manifest.xml": xml_bytes(manifest)})
    )
    with pytest.raises(ValueError, match="identity"):
        rendering_source(
            repack(
                {
                    **book.parts,
                    "META-INF/manifest.xml": xml_bytes(manifest),
                    "Object1/content.xml": b"<wrong/>",
                }
            )
        )


@pytest.mark.parametrize(
    "xml",
    [
        "<draw:plugin/>",
        "<draw:object-ole/>",
        "<table:table-source/>",
        "<office:script/>",
        '<text:p xml:base="https://example.invalid/"/>',
    ],
)
def test_active_source_nodes_and_base_remapping_are_explicit_limits(xml):
    with pytest.raises(ValueError):
        rendering_source(
            fixture(
                "<table:table-row><table:table-cell>"
                + xml
                + "</table:table-cell></table:table-row>"
            )
        )


@pytest.mark.parametrize(
    "mode,calculation", [("print", "prefer_cache"), ("whole_sheet", "recalculate")]
)
def test_ods_renderer_uses_native_bytes_odf_policy_and_exact_pdf(
    monkeypatch, mode, calculation
):
    source = create_native_ods(NativeODSCreate(tables=["First", "Blank"]))
    roots = []

    def office(command, root, timeout):
        roots.append(root)
        text = (root / "profile/user/registrymodifications.xcu").read_text()
        assert (
            f'oor:name="ODFRecalcMode" oor:op="fuse"><value>{0 if calculation == "recalculate" else 1}</value>'
            in text
        )
        assert "OOXMLRecalcMode" not in text and "DisableMacrosExecution" in text
        assert 'oor:name="Link" oor:op="fuse"><value>1</value>' in text
        if "--version" in command:
            return "LibreOffice fixture"
        assert (root / "source.ods").read_bytes() == source
        assert not (root / "source.xlsx").exists()
        with pymupdf.open() as pdf:
            for _ in range(2 if mode == "whole_sheet" else 1):
                pdf.new_page()
            pdf.save(root / "source.pdf")
        return "converted"

    monkeypatch.setattr(rendering, "office_binary", lambda *_: "fixture-office")
    monkeypatch.setattr(rendering, "run_office", office)
    monkeypatch.setattr(rendering, "ProcessNativePdf", lambda **_: NativePdf())
    pdf, receipt = rendering.LibreOfficeODSRenderer().convert(
        source, NativeWorkbookRendition(mode=mode, calculation=calculation)
    )
    assert receipt["rendered_pdf_sha256"] == hashlib.sha256(pdf).hexdigest()
    assert receipt["source_copy_unchanged"] and all(not r.exists() for r in roots)
    if mode == "whole_sheet":
        assert [
            r["worksheet"]["table_name"] for r in receipt["sheet_page_mapping"]
        ] == ["First", "Blank"]
    else:
        assert receipt["sheet_page_mapping"] is None


def test_ods_rendition_discovery_history_wiki_and_renderer_boundaries(tmp_path):
    repository = FileNativeAssetRepository(tmp_path / "store")
    pdfs = NativePdf()
    pdf, _ = pdfs.create(NativePdfCreate(name="a.pdf", pages=[{"blank": {}}]), {})
    seen = []

    class Renderer:
        def convert(self, data, request):
            seen.append(data)
            return pdf, {
                "rendered_pdf_sha256": hashlib.sha256(pdf).hexdigest(),
                "page_count": 1,
                "source_copy_unchanged": True,
            }

    def context(renderer=None):
        return NativeDocumentService(
            repository,
            SpreadsheetFileAdapter(),
            FileNativeWikiPublisher((tmp_path / "store",)),
            pdfs=pdfs,
            ods=NativeODSFileAdapter(),
            ods_renderer=renderer,
        )

    with pytest.raises(ValueError, match="PDF"):
        NativeDocumentService(
            repository, SpreadsheetFileAdapter(), ods_renderer=Renderer()
        )
    service = context(Renderer())
    contract = _call(service, op="contract", for_op="create_workbook_rendition")
    assert contract["workbook_rendering"]["source_formats"] == ["ods"]
    assert "create_workbook_rendition" in contract["formats"]["ods"]
    assert "create_workbook_rendition" not in contract["formats"]["xlsx"]
    source = tmp_path / "original.ods"
    source.write_bytes(create_native_ods(NativeODSCreate()))
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(source))["asset"]
    update(service, asset, cell(service, asset)["evidence"], "CHANGED")
    current = repository.load(asset["asset_id"]).model_dump()
    result = create(service, asset)
    assert (
        seen == [original]
        and repository.load(asset["asset_id"]).model_dump() == current
    )
    receipt = read(service, result["asset"])
    assert receipt["changes"][0]["source_reference"] == asset["file_reference"]
    request = {
        "op": "export_wiki",
        "asset_id": result["asset"]["asset_id"],
        "revision": result["asset"]["revision"],
        "output_dir": str(tmp_path / "wiki"),
    }
    published = _call(service, **request)
    root = Path(published["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    attachment = manifest["rendition"]["source_attachment"]
    assert attachment.endswith(".ods") and (root / attachment).read_bytes() == original
    restored = context()
    assert read(restored, result["asset"]) == receipt
    assert _call(restored, **request)["reused"]
    with pytest.raises(ValueError, match="not configured"):
        create(restored, asset)
    assert _call(restored, op="contract")["workbook_rendering"]["source_formats"] == []
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
