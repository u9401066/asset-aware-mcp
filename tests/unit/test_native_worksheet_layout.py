"""Layout corrections retain cell identity, native formatting and authored anchors."""

import hashlib
import io
import json
from copy import deepcopy

import pytest
import xlsxwriter
from lxml import etree

from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_layout import NativeLayoutUpdate
from src.domain.native_workbook import NativeWorksheetKey
from src.infrastructure.native_grid_metrics import EMU_PER_PIXEL
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_grid import NativeWorkbookGrid
from tests.native_grid_drawing_helpers import DRAWING_PART, SHEET_PART, drawing_workbook
from tests.native_workbook_helpers import _call, _parts, _replace
from tests.unit.test_native_grid_drawings import image_geometry, pictures
from tests.unit.test_native_grid_operations import service_at

KEY = {"sheet_id": "1", "part": SHEET_PART}


def request(*edits, **metrics):
    return NativeLayoutUpdate(
        worksheet=NativeWorksheetKey(**KEY), edits=list(edits), **metrics
    )


def fixture():
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        sheet = book.add_worksheet("Data")
        style = book.add_format({"num_format": "00000", "bg_color": "#FFDD77"})
        bold = book.add_format({"bold": True})
        sheet.set_column("A:E", 20, style, {"level": 2, "hidden": True})
        sheet.set_row(0, 25, style, {"level": 1})
        sheet.write_rich_string("A1", bold, "Rich", " text")
        sheet.write_formula("A2", '=CELL("width",A1)', style, 20)
        sheet.merge_range("C3:D4", "Merged", style)
        sheet.add_table(
            "A6:B8",
            {
                "columns": [{"header": "Name"}, {"header": "Value"}],
                "data": [["x", 1], ["y", 2]],
            },
        )
    source = output.getvalue()
    root = etree.fromstring(_parts(source)[SHEET_PART])
    col = root.find("s:cols/s:col", NS)
    col.set("{urn:retained}label", "foreign attribute")
    col.set("bestFit", "1")
    root.find("s:cols", NS).insert(0, etree.Comment("keep column note"))
    return _replace(
        source,
        {
            SHEET_PART: etree.tostring(root),
            "customXml/preserve.xml": b"<keep> original </keep>",
        },
    )


def layout(data):
    return NativeWorkbookGrid().read_layout(data, NativeWorksheetKey(**KEY))["layout"]


def test_split_intervals_preserves_format_and_reset_does_not_drop_metadata():
    original = fixture()
    data, result = NativeWorkbookGrid().update_layout(
        original,
        request(
            {
                "axis": "column",
                "at": 2,
                "count": 2,
                "width_ooxml": 32.5,
                "hidden": False,
            },
            {"axis": "row", "at": 1, "height_points": 42},
        ),
    )
    cols = layout(data)["columns"]
    assert [(c["min"], c["max"]) for c in cols] == [("1", "1"), ("2", "3"), ("4", "5")]
    original_col = layout(original)["columns"][0]
    for col in cols:
        assert col["style"] == original_col["style"]
        assert col["outlineLevel"] == "2"
        assert col["{urn:retained}label"] == "foreign attribute"
    assert cols[1]["width"] == "32.5" and cols[1]["hidden"] == "0"
    assert "bestFit" not in cols[1] and cols[0]["bestFit"] == "1"
    before, after = _parts(original), _parts(data)
    assert b"keep column note" in after[SHEET_PART]
    old = etree.fromstring(before[SHEET_PART])
    new = etree.fromstring(after[SHEET_PART])
    for address in ("A1", "C3", "D4", "A6", "B8"):
        path = f'.//s:c[@r="{address}"]'
        assert etree.tostring(old.find(path, NS), method="c14n") == etree.tostring(
            new.find(path, NS), method="c14n"
        )
    assert new.find('.//s:c[@r="A2"]/s:f', NS).text == 'CELL("width",A1)'
    assert new.find('.//s:c[@r="A2"]/s:v', NS) is None
    for part in before:
        if part not in result.changed_parts:
            assert before[part] == after[part]
    for part in (
        "xl/styles.xml",
        "xl/sharedStrings.xml",
        "xl/tables/table1.xml",
        "customXml/preserve.xml",
    ):
        assert before[part] == after[part]
    reset, _ = NativeWorkbookGrid().update_layout(
        data,
        request(
            {"axis": "column", "at": 2, "reset_size": True},
            {"axis": "row", "at": 1, "reset_size": True},
        ),
    )
    reset_col = next(c for c in layout(reset)["columns"] if c["min"] == "2")
    assert "width" not in reset_col and "customWidth" not in reset_col
    assert reset_col["style"] == original_col["style"] and reset_col["hidden"] == "0"
    row = layout(reset)["rows"][0]
    assert "ht" not in row and "customHeight" not in row
    assert row["outlineLevel"] == "1" and row["s"] == layout(original)["rows"][0]["s"]


@pytest.mark.parametrize(
    "edit",
    [
        {"axis": "row", "at": 1},
        {"axis": "row", "at": 1, "width_ooxml": 20},
        {"axis": "column", "at": 1, "height_points": 20},
        {"axis": "row", "at": 1, "height_points": 20, "reset_size": True},
        {"axis": "column", "at": 16_384, "count": 2, "hidden": True},
        {"axis": "row", "at": 1, "height_points": float("nan")},
        {"axis": "column", "at": 1, "width_ooxml": 256},
    ],
)
def test_layout_intent_rejects_wrong_units_ambiguous_or_unbounded_edits(edit):
    with pytest.raises(ValueError):
        request(edit)


def test_malformed_intervals_and_stale_sheet_keys_are_rejected():
    original = fixture()
    root = etree.fromstring(_parts(original)[SHEET_PART])
    root.find("s:cols", NS).append(deepcopy(root.find("s:cols/s:col", NS)))
    source = _replace(original, {SHEET_PART: etree.tostring(root)})
    with pytest.raises(ValueError, match="Overlapping"):
        NativeWorkbookGrid().update_layout(
            source, request({"axis": "row", "at": 1, "height_points": 30})
        )
    bad = request({"axis": "row", "at": 1, "height_points": 30})
    bad.worksheet.sheet_id = "99"
    with pytest.raises(ValueError):
        NativeWorkbookGrid().update_layout(original, bad)


def test_sheet_protection_permissions_are_honored_without_unlocking():
    source = fixture()
    root = etree.fromstring(_parts(source)[SHEET_PART])
    protection = etree.SubElement(
        root, tag("sheetProtection"), sheet="1", formatRows="0", password="ABCD"
    )
    source = _replace(source, {SHEET_PART: etree.tostring(root)})
    data, _ = NativeWorkbookGrid().update_layout(
        source, request({"axis": "row", "at": 1, "height_points": 30})
    )
    assert layout(data)["protection"] == dict(protection.attrib)
    with pytest.raises(ValueError, match="does not permit"):
        NativeWorkbookGrid().update_layout(
            source, request({"axis": "column", "at": 1, "width_ooxml": 30})
        )


@pytest.mark.parametrize(
    "edit,expected",
    [
        (
            {"axis": "row", "at": 1, "height_points": 30},
            [(69, 43, 64, 40), (69, 43, 64, 40), (69, 23, 64, 40)],
        ),
        (
            {"axis": "row", "at": 2, "height_points": 45},
            [(69, 23, 64, 60), (69, 23, 64, 40), (69, 23, 64, 40)],
        ),
        (
            {"axis": "column", "at": 2, "width_ooxml": 18.28515625},
            [(69, 23, 128, 40), (69, 23, 64, 40), (69, 23, 64, 40)],
        ),
    ],
)
def test_dimensions_follow_authored_anchor_modes_and_preserve_media_notes(
    edit, expected
):
    source = drawing_workbook()
    updated, result = NativeWorkbookGrid().update_layout(source, request(edit))
    assert [
        tuple(v // EMU_PER_PIXEL for v in image_geometry(node))
        for node in pictures(updated)
    ] == expected
    old, new = _parts(source), _parts(updated)
    for part in (
        "xl/media/image1.png",
        "xl/comments1.xml",
        "xl/styles.xml",
        "customXml/grid.xml",
    ):
        assert old[part] == new[part]
    assert result.changes[0]["edits"][0]["objects"]["drawings"][DRAWING_PART]
    assert result.changes[0]["edits"][0]["objects"]["comments"] == []


def test_layout_history_source_and_complete_receipt_budget(tmp_path, monkeypatch):
    service = service_at(tmp_path / "store")
    path = tmp_path / "original.xlsx"
    original = fixture()
    path.write_bytes(original)
    mtime = path.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(path))["asset"]
    ref = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Data", cell="A1"
    )["cell"]["evidence"]
    payload = {
        "op": "update_worksheet_layout",
        "asset_id": asset["asset_id"],
        "expected_revision": asset["revision"],
        "worksheet_layout": request(
            {"axis": "column", "at": 2, "width_ooxml": 40}
        ).model_dump(),
    }
    changed = _call(service, **payload)
    assert changed["asset"]["capabilities"]["update_worksheet_layout"]
    chunks, offset, sha = [], 0, None
    while True:
        page = _call(
            service, **changed["review_request"], text_offset=offset, text_limit=139
        )
        sha = sha or page["text_sha256"]
        assert page["text_sha256"] == sha
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    record = json.loads(text)
    receipt = record["operation_result"]["changes"][0]
    assert (
        receipt["before"] == layout(original) and receipt["after"] == record["layout"]
    )
    assert _call(service, op="verify", reference=ref)["valid"]
    with pytest.raises(ValueError, match="stale"):
        _call(service, **payload)
    monkeypatch.setattr(
        "src.application.native_workbook_operations.MAX_WORKBOOK_READ_BYTES", 100
    )
    payload["expected_revision"] = changed["asset"]["revision"]
    with pytest.raises(ValueError, match="read-back budget"):
        _call(service, **payload)
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert service.repository.read(asset["asset_id"], asset["revision"]) == original
    assert path.read_bytes() == original and path.stat().st_mtime_ns == mtime


def test_layout_contract_required_revision_and_disabled_adapter(tmp_path):
    enabled = _call(
        service_at(tmp_path / "yes"), op="contract", for_op="update_worksheet_layout"
    )
    assert enabled["worksheet_layout_enabled"]
    assert "read_worksheet_layout" in enabled["formats"]["xlsx"]
    disabled = _call(service_at(tmp_path / "no", enabled=False), op="contract")
    assert not disabled["worksheet_layout_enabled"]
    assert "update_worksheet_layout" not in disabled["formats"]["xlsx"]
    with pytest.raises(ValueError, match="revision"):
        NativeDocumentRequest(
            op="read_worksheet_layout", asset_id="file_" + "a" * 32, worksheet_key=KEY
        )
