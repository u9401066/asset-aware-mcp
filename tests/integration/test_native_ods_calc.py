"""Independent Calc import, native ODS edits, formula results and actual PDF layout."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import openpyxl
import pymupdf
import pytest
import xlsxwriter
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from src.domain.native_ods import NativeODSCreate
from src.domain.native_rendition import NativeWorkbookRendition
from src.infrastructure.native_odf_package import q, xml_bytes
from src.infrastructure.native_ods import NativeODS, create_native_ods
from src.infrastructure.native_office_process import (
    office_binary,
    prepare_profile,
    run_office,
)
from src.infrastructure.native_workbook_render import LibreOfficeODSRenderer
from tests.integration.test_native_ods_stdio import cell as read_ods_cell
from tests.integration.test_native_pdf_regions_stdio import native
from tests.integration.test_native_workbook_rendition_stdio import (
    read_receipt,
    render_page,
)
from tests.native_ods_helpers import edit, locator
from tests.native_workbook_render_helpers import rendered_workbook

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("NATIVE_ODS_RENDER_TEST") != "1",
        reason="Set NATIVE_ODS_RENDER_TEST=1 with LibreOffice Calc installed",
    ),
    pytest.mark.timeout(180),
]


def convert(source, destination, output_format, *, whole_sheet=False, calculation=None):
    destination.mkdir()
    profile = prepare_profile(destination)
    if whole_sheet or calculation is not None:
        # Independent command-line control, without the production renderer or
        # its profile builder. Explicitly request the same documented policies.
        settings = destination / "profile/user/registrymodifications.xcu"
        extra = f'<item oor:path="/org.openoffice.Office.Common/Filter/PDF/Export"><prop oor:name="SinglePageSheets" oor:op="fuse"><value>{str(whole_sheet).lower()}</value></prop></item>'
        if calculation is not None:
            extra += f'<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>{0 if calculation == "recalculate" else 1}</value></prop></item>'
        settings.write_text(
            settings.read_text().replace("</oor:items>", extra + "</oor:items>")
        )
    log = run_office(
        [
            os.environ.get("NATIVE_ODS_CALC_BIN") or office_binary("Calc"),
            profile,
            "--headless",
            "--norestore",
            "--convert-to",
            output_format,
            "--outdir",
            str(destination),
            str(source),
        ],
        destination,
        45,
    )
    suffix = output_format.split(":", 1)[0]
    result = destination / (source.stem + "." + suffix)
    assert result.is_file(), log
    return result


def write_fixture(source, title, amount):
    """Author source and expected state independently of our ODS editor."""
    with xlsxwriter.Workbook(source) as book:
        sheet = book.add_worksheet("Sheet1")
        red = book.add_format({"font_color": "#FF0000", "font_size": 20, "bold": True})
        number = book.add_format({"num_format": "0.00", "font_color": "#0000FF"})
        sheet.write("A1", title, red)
        sheet.write_number("A2", amount, number)
        sheet.write_formula("B2", "=A2*2", number, amount * 2)
        sheet.write_formula("B3", "=A2>4", None, amount > 4)
        sheet.write_formula(
            "B4", '=IF(A2>4,"high","low")', None, "high" if amount > 4 else "low"
        )
        sheet.write("A4", "UNCHANGED")
        sheet.set_column("A:B", 25)
        sheet.print_area("A1:B4")


def test_real_calc_creation_native_read_edit_and_render(tmp_path):
    source = tmp_path / "original.xlsx"
    write_fixture(source, "OLD TITLE", 3.43)
    expected_source = tmp_path / "expected.xlsx"
    write_fixture(expected_source, "NEW TITLE", 5.75)
    expected_ods = convert(expected_source, tmp_path / "expected-ods", "ods")
    expected_independent = convert(expected_ods, tmp_path / "expected-readback", "xlsx")
    expected_readback = openpyxl.load_workbook(expected_independent, data_only=True)
    original_ods = convert(source, tmp_path / "source-ods", "ods")
    original = original_ods.read_bytes()
    mtime = original_ods.stat().st_mtime_ns
    book = NativeODS(original)
    old_style = book.read_cell(locator())["attributes"][q("table", "style-name")]
    changed, receipt = book.edit([edit(value="NEW TITLE"), edit(1, 0, "5.75", "float")])
    edited = tmp_path / "edited.ods"
    edited.write_bytes(changed)
    assert (
        NativeODS(changed).read_cell(locator())["attributes"][q("table", "style-name")]
        == old_style
    )
    assert (
        original_ods.read_bytes() == original
        and original_ods.stat().st_mtime_ns == mtime
    )
    for name, content in book.package.parts.items():
        if name != "content.xml":
            assert NativeODS(changed).package.parts[name] == content
    independent = convert(edited, tmp_path / "readback", "xlsx")
    readback = openpyxl.load_workbook(independent, data_only=True)
    assert readback.active["A1"].value == "NEW TITLE"
    assert readback.active["A2"].value == 5.75
    assert readback.active["B2"].value == 11.5
    # Calc 7.3 exports this predicate as Boolean; 24.2 may export numeric 1.
    # Require the independent same-version expected state, including its type.
    assert expected_readback.active["B3"].value == 1
    assert expected_readback.active["B3"].data_type in {"b", "n"}
    for address in ("A1", "A2", "B2", "B3", "B4", "A4"):
        actual, expected = readback.active[address], expected_readback.active[address]
        assert (actual.value, actual.data_type) == (expected.value, expected.data_type)
    assert readback.active["B4"].value == "high"
    assert readback.active["A2"].number_format == "0.00"
    assert readback.active["A1"].font.bold
    # Compare exported font metadata with Calc's independent expected state.
    # The actual red glyphs and complete rendered page are checked below.
    assert readback.active["A1"].font.color == expected_readback.active["A1"].font.color
    assert readback.active["A4"].value == "UNCHANGED"
    pdf = convert(edited, tmp_path / "render", "pdf:calc_pdf_Export")
    original_pdf = convert(
        original_ods, tmp_path / "before-render", "pdf:calc_pdf_Export"
    )
    expected_pdf = convert(
        expected_ods, tmp_path / "expected-render", "pdf:calc_pdf_Export"
    )
    with pymupdf.open(pdf) as rendered, pymupdf.open(expected_pdf) as expected_render:
        assert len(rendered) == len(expected_render) == 1
        assert rendered[0].rect == expected_render[0].rect
        assert rendered[0].get_text() == expected_render[0].get_text()
        assert (
            rendered[0].get_pixmap().samples == expected_render[0].get_pixmap().samples
        )
        expected_render[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
            tmp_path / "expected-preview.png"
        )
        text = rendered[0].get_text()
        assert all(
            item in text for item in ("NEW TITLE", "5.75", "11.50", "UNCHANGED", "high")
        )
        spans = [
            span
            for block in rendered[0].get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
            for span in line["spans"]
        ]
        title = next(span for span in spans if "NEW TITLE" in span["text"])
        assert title["color"] == 0xFF0000 and title["size"] >= 19
        rendered[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
            tmp_path / "edited-preview.png"
        )
        with pymupdf.open(original_pdf) as old_render:
            old_rect = old_render[0].search_for("UNCHANGED")[0]
            assert rendered[0].search_for("UNCHANGED")[0] == old_rect
            assert (
                rendered[0].get_pixmap(clip=old_rect).samples
                == old_render[0].get_pixmap(clip=old_rect).samples
            )
            old_render[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
                tmp_path / "original-preview.png"
            )
    assert receipt.changed_parts == ["content.xml"]
    assert receipt.repairs == ["invalidated_typed_formula_caches"]
    assert (
        original_ods.read_bytes() == original
        and original_ods.stat().st_mtime_ns == mtime
    )
    if output := os.environ.get("NATIVE_ODS_ARTIFACTS"):
        root = Path(output)
        root.mkdir(parents=True, exist_ok=False)
        files = [
            original_ods,
            edited,
            independent,
            pdf,
            original_pdf,
            tmp_path / "edited-preview.png",
            tmp_path / "original-preview.png",
            expected_ods,
            expected_independent,
            expected_pdf,
            tmp_path / "expected-preview.png",
        ]
        hashes = {}
        for file in files:
            data = file.read_bytes()
            (root / file.name).write_bytes(data)
            hashes[file.name] = hashlib.sha256(data).hexdigest()
        (root / "receipt.json").write_text(receipt.model_dump_json(indent=2))
        (root / "proof.json").write_text(
            json.dumps(
                {
                    "sha256": hashes,
                    "renderer": os.environ.get("NATIVE_ODS_CALC_BIN")
                    or office_binary("Calc"),
                    "source_unchanged": True,
                    "independent_formula_value": readback.active["B2"].value,
                    "predicate_export": {
                        "actual_value": readback.active["B3"].value,
                        "actual_type": readback.active["B3"].data_type,
                        "expected_value": expected_readback.active["B3"].value,
                        "expected_type": expected_readback.active["B3"].data_type,
                    },
                    "full_page_matches_independent_expected": True,
                },
                indent=2,
            )
        )


def test_native_created_ods_is_readable_by_calc_including_uncached_formula(tmp_path):
    original = create_native_ods(NativeODSCreate())
    data, _ = NativeODS(original).edit(
        [
            edit(value="literal =1+1"),
            edit(1, 0, "3.43", "float"),
            edit(1, 1, "=[.A2]*2", "formula"),
            edit(2, 0, True, "boolean"),
        ]
    )
    source = tmp_path / "created.ods"
    source.write_bytes(data)
    result = convert(source, tmp_path / "converted", "xlsx")
    readback = openpyxl.load_workbook(result, data_only=True)
    assert readback.active["A1"].value == "literal =1+1"
    assert readback.active["A2"].value == 3.43
    assert readback.active["B2"].value == 6.86
    assert readback.active["A3"].value is True


async def test_real_ods_renditions_preserve_native_source_pages_and_wiki_on_restart(
    tmp_path,
):
    fixture_path = tmp_path / "fixture.xlsx"
    fixture_path.write_bytes(rendered_workbook())
    imported = convert(fixture_path, tmp_path / "ods-fixture", "ods")
    book = NativeODS(imported.read_bytes())
    _, cached, _ = book.locate(locator(1, 1, "First"))
    assert cached is not None and cached.get(q("table", "formula"))
    # Without an explicit style Calc can recalculate solely to determine the
    # number format, even with ODFRecalcMode=never. Keep this cache-policy fixture
    # unambiguous; the separate unstyled regression exercises that behavior.
    cached.set(q("table", "style-name"), "Default")
    cached.set(q("office", "value-type"), "float")
    cached.set(q("office", "value"), "999")
    for paragraph in cached.findall(q("text", "p")):
        paragraph.text = "999"
    source = tmp_path / "source.ods"
    original = book.package.replace({"content.xml": xml_bytes(book.root)})
    source.write_bytes(original)
    mtime = source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "LIBREOFFICE_BIN": os.environ.get("NATIVE_ODS_CALC_BIN")
            or office_binary("Calc"),
        },
    )
    saved = []
    async with Client(stdio_client(params)) as client:
        contract = await native(
            client, op="contract", for_op="create_workbook_rendition"
        )
        assert contract["workbook_rendering"]["source_formats"] == ["xlsx", "ods"]
        assert "create_workbook_rendition" in contract["formats"]["ods"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        old = await read_ods_cell(client, asset, name="First")
        changed = await native(
            client,
            op="update_ods",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            ods_update={
                "cells": [
                    {
                        "reference": old["evidence"],
                        "value": {"kind": "string", "value": "NEW WORKBOOK CONTENT"},
                        "display_policy": "replace_paragraphs_preserve_cell_style",
                    }
                ]
            },
        )
        assert changed["success"] and changed["asset"]["revision"] != asset["revision"]
        for mode in ("print", "whole_sheet"):
            for calculation in ("prefer_cache", "recalculate"):
                control = convert(
                    source,
                    tmp_path / f"control-{mode}-{calculation}",
                    "pdf:calc_pdf_Export",
                    whole_sheet=mode == "whole_sheet",
                    calculation=calculation,
                )
                created = await native(
                    client,
                    op="create_workbook_rendition",
                    asset_id=asset["asset_id"],
                    revision=asset["revision"],
                    workbook_rendition={"mode": mode, "calculation": calculation},
                )
                assert created["success"], created
                pdf_asset = created["asset"]
                receipt = await read_receipt(client, pdf_asset)
                conversion = receipt["changes"][0]
                assert conversion["source_reference"] == asset["file_reference"]
                rendering = conversion["rendering"]
                assert rendering["calculation_requested"] == calculation
                assert [w["key"]["table_name"] for w in rendering["worksheets"]] == [
                    "First",
                    "Blank",
                    "Hidden",
                    "Last",
                ]
                path = tmp_path / f"{mode}-{calculation}.pdf"
                published = await native(
                    client,
                    op="publish",
                    asset_id=pdf_asset["asset_id"],
                    expected_revision=pdf_asset["revision"],
                    output_path=str(path),
                )
                assert published["success"], published
                with pymupdf.open(path) as pdf, pymupdf.open(control) as expected:
                    text = [p.get_text() for p in pdf]
                    assert text == [p.get_text() for p in expected]
                    assert [p.get_pixmap().samples for p in pdf] == [
                        p.get_pixmap().samples for p in expected
                    ]
                    assert len(pdf) == (2 if mode == "print" else 4)
                    assert ("999" if calculation == "prefer_cache" else "3") in text[
                        0
                    ].splitlines()
                    assert "FIRST PRINT" in text[0] and "NEW WORKBOOK" not in text[0]
                    if mode == "whole_sheet":
                        assert "OUTSIDE PRINT RANGE" in text[0] and not text[1]
                        # Whole-sheet bounds can clip overflowing text in the
                        # narrow hidden column; its entire image matches Calc.
                        assert text[2].startswith("HIDDEN") and "LAST PRINT" in text[3]
                        assert [
                            m["page_index"] for m in rendering["sheet_page_mapping"]
                        ] == [0, 1, 2, 3]
                    else:
                        assert "OUTSIDE PRINT RANGE" not in "".join(text)
                        assert (
                            "HIDDEN CONTENT" not in "".join(text)
                            and "LAST PRINT" in text[1]
                        )
                        assert rendering["sheet_page_mapping"] is None
                    spans = [
                        s
                        for b in pdf[0].get_text("dict")["blocks"]
                        if "lines" in b
                        for line in b["lines"]
                        for s in line["spans"]
                    ]
                    title = next(s for s in spans if "FIRST PRINT" in s["text"])
                    assert title["color"] == 0xFF0000 and title["size"] >= 23
                catalog = await native(
                    client,
                    op="read_pdf",
                    asset_id=pdf_asset["asset_id"],
                    revision=pdf_asset["revision"],
                )
                images = []
                for index, page in enumerate(catalog["pages"]):
                    png = await render_page(client, pdf_asset, page["locator"])
                    (tmp_path / f"{mode}-{calculation}-{index}.png").write_bytes(png)
                    images.append((page["locator"], png))
                wiki_request = {
                    "op": "export_wiki",
                    "asset_id": pdf_asset["asset_id"],
                    "revision": pdf_asset["revision"],
                    "output_dir": str(tmp_path / "wiki"),
                }
                wiki = await native(client, **wiki_request)
                assert wiki["success"], wiki
                root = Path(wiki["output_dir"])
                manifest = json.loads((root / "manifest.json").read_text())
                attachment = manifest["rendition"]["source_attachment"]
                assert (
                    attachment.endswith(".ods")
                    and (root / attachment).read_bytes() == original
                )
                snapshot = {
                    str(p.relative_to(root)): p.read_bytes()
                    for p in root.rglob("*")
                    if p.is_file()
                }
                saved.append((pdf_asset, receipt, images, wiki_request, root, snapshot))
    async with Client(stdio_client(params)) as client:
        for pdf_asset, receipt, images, wiki_request, root, snapshot in saved:
            assert await read_receipt(client, pdf_asset) == receipt
            for position, png in images:
                assert await render_page(client, pdf_asset, position) == png
            assert (await native(client, **wiki_request))["reused"]
            assert {
                str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob("*")
                if p.is_file()
            } == snapshot
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
    assert (
        NativeODS(original).read_cell(locator(1, 1, "First"))["value_attributes"][
            "value"
        ]
        == "999"
    )
    if target := os.environ.get("NATIVE_ODS_RENDITION_ARTIFACTS"):
        shutil.copytree(tmp_path, Path(target))


def test_unstyled_ods_cache_policy_matches_independent_calc(tmp_path, monkeypatch):
    # Calc can recompute an unstyled formula to determine its number format.
    # Compare actual output with a direct Calc conversion, independently of the
    # renderer; do not promise that prefer_cache freezes cached values.
    xlsx = tmp_path / "unstyled.xlsx"
    with xlsxwriter.Workbook(xlsx) as book:
        book.add_worksheet().write_formula("A1", "=1+2", None, 999)
    imported = convert(xlsx, tmp_path / "imported", "ods")
    book = NativeODS(imported.read_bytes())
    _, cell, _ = book.locate(locator())
    assert cell is not None and q("table", "style-name") not in cell.attrib
    cell.set(q("office", "value"), "999")
    for paragraph in cell.findall(q("text", "p")):
        paragraph.text = "999"
    source = tmp_path / "source.ods"
    data = book.package.replace({"content.xml": xml_bytes(book.root)})
    source.write_bytes(data)
    control = convert(source, tmp_path / "control", "pdf:calc_pdf_Export")
    monkeypatch.setenv(
        "LIBREOFFICE_BIN",
        os.environ.get("NATIVE_ODS_CALC_BIN") or office_binary("Calc"),
    )
    output, receipt = LibreOfficeODSRenderer().convert(
        data, NativeWorkbookRendition(mode="print", calculation="prefer_cache")
    )
    with (
        pymupdf.open(control) as expected,
        pymupdf.open(stream=output, filetype="pdf") as actual,
    ):
        assert len(actual) == len(expected) == 1
        assert actual[0].get_text() == expected[0].get_text() == "3\n"
        assert actual[0].get_pixmap().samples == expected[0].get_pixmap().samples
    assert receipt["calculation_requested"] == "prefer_cache"
    assert source.read_bytes() == data


def test_real_ods_chart_and_raster_match_independent_calc_conversion(
    tmp_path, monkeypatch
):
    image = tmp_path / "local.png"
    Image.new("RGB", (30, 20), "red").save(image)
    source = tmp_path / "chart.xlsx"
    with xlsxwriter.Workbook(source) as book:
        sheet = book.add_worksheet("Chart")
        sheet.write_column("A1", [1, 2, 3])
        sheet.write_column("B1", [2, 4, 3])
        sheet.insert_image("D1", str(image))
        chart = book.add_chart({"type": "column"})
        chart.add_series(
            {"values": "=Chart!$B$1:$B$3", "categories": "=Chart!$A$1:$A$3"}
        )
        chart.set_title({"name": "LOCAL CHART"})
        sheet.insert_chart("A5", chart)
        sheet.print_area("A1:L23")
    ods = convert(source, tmp_path / "native", "ods")
    data, mtime = ods.read_bytes(), ods.stat().st_mtime_ns
    expected_path = convert(ods, tmp_path / "independent", "pdf:calc_pdf_Export")
    monkeypatch.setenv(
        "LIBREOFFICE_BIN",
        os.environ.get("NATIVE_ODS_CALC_BIN") or office_binary("Calc"),
    )
    output, receipt = LibreOfficeODSRenderer().convert(
        data, NativeWorkbookRendition(mode="print", calculation="recalculate")
    )
    with (
        pymupdf.open(stream=output, filetype="pdf") as actual,
        pymupdf.open(expected_path) as expected,
    ):
        assert len(actual) == len(expected) == 1
        assert "LOCAL CHART" in actual[0].get_text()
        assert actual[0].get_image_info()
        assert actual[0].get_text() == expected[0].get_text()
        assert actual[0].get_pixmap().samples == expected[0].get_pixmap().samples
        if target := os.environ.get("NATIVE_ODS_CHART_ARTIFACTS"):
            root = Path(target)
            root.mkdir(parents=True, exist_ok=False)
            (root / "source.ods").write_bytes(data)
            (root / "actual.pdf").write_bytes(output)
            (root / "expected.pdf").write_bytes(expected_path.read_bytes())
            actual[0].get_pixmap().save(root / "actual.png")
            (root / "receipt.json").write_text(json.dumps(receipt, indent=2))
    assert ods.read_bytes() == data and ods.stat().st_mtime_ns == mtime
