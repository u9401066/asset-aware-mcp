"""Table creation dependency identity, source preservation and atomicity checks."""

import io

import pytest
from lxml import etree

from src.domain.native_assets import NativeCellEdit
from src.domain.native_table_edit import NativeTableUpdate
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet import NativeSpreadsheet
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_structure import NativeWorkbookStructure
from src.infrastructure.native_workbook_table_edit import NativeWorkbookTableEdit
from tests.native_workbook_helpers import _parts
from tests.unit.test_native_workbook_table_create import (
    ADAPTER,
    KEY,
    SHEET,
    request,
    source,
)
from tests.unit.test_native_workbook_table_edit import mutate


def test_retained_detached_table_parts_keep_ids_and_bytes_reserved():
    from src.infrastructure.native_ooxml import relationships_path

    original, _ = ADAPTER.create(source(), request())
    detached = mutate(
        original, SHEET, lambda root: root.remove(root.find("s:tableParts", NS))
    )
    detached = mutate(
        detached, relationships_path(SHEET), lambda root: root.remove(root[0])
    )
    output, result = ADAPTER.create(detached, request(name="NewRecords"))
    created = result.changes[0]["created_table"]
    assert created["id"] == "2" and created["part"] == "xl/tables/table2.xml"
    assert (
        _parts(output)["xl/tables/table1.xml"]
        == _parts(original)["xl/tables/table1.xml"]
    )
    assert len(NativeWorkbookStructure().read(output)["tables"]) == 1
    with pytest.raises(ValueError, match="name conflicts"):
        ADAPTER.create(detached, request())


def test_existing_registry_and_external_relationship_survive_second_table():
    output, _ = ADAPTER.create(source(), request())
    original = _parts(output)
    output, result = ADAPTER.create(
        output, request(ref="G1:G2", name="OutsideData", columns=[{"name": "Outside"}])
    )
    tables = NativeWorkbookStructure().read(output)["tables"]
    assert len(tables) == 2
    assert tables[0]["relationship_id"] != tables[1]["relationship_id"]
    assert _parts(output)["xl/tables/table1.xml"] == original["xl/tables/table1.xml"]
    assert result.changes[0]["created_table"]["id"] == "2"


def test_custom_style_and_shared_rich_headers_preserved():
    import xlsxwriter

    stream = io.BytesIO()
    with xlsxwriter.Workbook(stream, {"in_memory": True}) as book:
        sheet = book.add_worksheet("Data")
        sheet.write_rich_string("A1", book.add_format({"bold": True}), "Co", "de")
        sheet.write_row("B1", ["Count", "Double"])
        sheet.write_string("A2", "007")
        sheet.write_url("G2", "https://example.com", string="Reference")
    original = mutate(
        stream.getvalue(),
        "xl/styles.xml",
        lambda root: etree.SubElement(
            root.find("s:tableStyles", NS),
            tag("tableStyle"),
            name="CustomTable",
            table="1",
            count="0",
        ),
    )
    original = mutate(
        original,
        "xl/styles.xml",
        lambda root: root.find("s:tableStyles", NS).set("count", "1"),
    )
    output, result = ADAPTER.create(original, request(style={"name": "CustomTable"}))
    assert result.changes[0]["created_table"]["relationship_id"] == "rId2"
    assert (
        _parts(output)["xl/sharedStrings.xml"]
        == _parts(original)["xl/sharedStrings.xml"]
    )
    assert _parts(output)["xl/styles.xml"] == _parts(original)["xl/styles.xml"]
    assert NativeSpreadsheet(output).read_cell("Data", "A1")["rich_text"]
    assert (
        'name="CustomTable"'
        in NativeWorkbookStructure().read(output)["tables"][0]["xml"]
    )


def test_escaped_column_names_remain_exact_in_headers_and_formulas():
    name = "A]#'_x0041_"
    original, _ = NativeSpreadsheet(source(rich=False)).edit(
        [NativeCellEdit(sheet="Data", cell="A1", kind="string", value=name)]
    )
    output, _ = ADAPTER.create(
        original,
        request(
            ref="A1:C4",
            totals_row=True,
            columns=[
                {"name": name, "totals": {"kind": "function", "value": "count"}},
                {"name": "Count"},
                {"name": "Double"},
            ],
        ),
    )
    assert NativeSpreadsheet(output).read_cell("Data", "A1")["value"] == name
    assert "_x005F_x0041_" in NativeWorkbookStructure().read(output)["tables"][0]["xml"]
    table = NativeWorkbookStructure().read(output)["tables"][0]
    updated, _ = NativeWorkbookTableEdit().update(
        output,
        NativeTableUpdate(
            worksheet=KEY,
            part=table["part"],
            expected_ref="A1:C4",
            columns=[{"column_id": 1, "expected_name": name, "name": "Code"}],
        ),
    )
    assert (
        NativeSpreadsheet(updated).read_cell("Data", "A4")["value"]
        == "=SUBTOTAL(103,[Code])"
    )


def test_pivot_source_header_change_requires_coordinated_field_identity():
    from tests.unit.test_native_grid_metadata import CACHE, with_pivot_source

    original = mutate(
        source(),
        SHEET,
        lambda root: root.find("s:sheetData/s:row", NS).remove(
            root.find("s:sheetData/s:row/s:c", NS)
        ),
    )
    original = with_pivot_source(original)

    def locate(root):
        node = root.find("s:cacheSource/s:worksheetSource", NS)
        node.attrib.clear()
        node.set("sheet", "Data")
        node.set("ref", "A1:C3")

    original = mutate(original, CACHE, locate)
    with pytest.raises(ValueError, match="Pivot source header changes"):
        ADAPTER.create(original, request(header_policy="fill_blank"))


def test_public_review_budget_rejects_creation_before_cas(tmp_path, monkeypatch):
    from src.application import native_workbook_operations as operations
    from src.application.native_document_service import NativeDocumentService
    from src.infrastructure.native_asset_store import FileNativeAssetRepository
    from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
    from tests.native_workbook_helpers import _call

    repository = FileNativeAssetRepository(tmp_path / "store")
    adapter = NativeWorkbookStructure()
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        workbook_structure=adapter,
        workbook_table_creation=ADAPTER,
    )
    path = tmp_path / "source.xlsx"
    path.write_bytes(source())
    asset = _call(service, op="register", source_path=str(path))["asset"]
    baseline = {
        **adapter.read(path.read_bytes(), references=True),
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "operation_result": None,
    }
    monkeypatch.setattr(
        operations,
        "MAX_WORKBOOK_READ_BYTES",
        len(operations._record_text(baseline).encode()) + 100,
    )
    with pytest.raises(ValueError, match="read-back budget"):
        _call(
            service,
            op="add_workbook_table",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            table_create=request().model_dump(),
        )
    current = repository.load(asset["asset_id"])
    assert current.revision == asset["revision"] and len(current.history) == 1


def test_concurrent_commit_retains_competitor_without_partial_table(tmp_path):
    from src.application.native_document_service import NativeDocumentService
    from src.infrastructure.native_asset_store import FileNativeAssetRepository
    from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
    from tests.native_workbook_helpers import _call

    repository = FileNativeAssetRepository(tmp_path / "store")

    class ConcurrentCreate:
        def create(self, data, intent):
            output, result = ADAPTER.create(data, intent)
            other, receipt = NativeSpreadsheet(data).edit(
                [NativeCellEdit(sheet="Data", cell="G1", kind="string", value="Human")]
            )
            repository.commit(asset["asset_id"], asset["revision"], other, receipt)
            return output, result

    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        workbook_structure=NativeWorkbookStructure(),
        workbook_table_creation=ConcurrentCreate(),
    )
    path = tmp_path / "source.xlsx"
    path.write_bytes(source())
    asset = _call(service, op="register", source_path=str(path))["asset"]
    with pytest.raises(ValueError):
        _call(
            service,
            op="add_workbook_table",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            table_create=request().model_dump(),
        )
    current = repository.load(asset["asset_id"])
    output = repository.read(current.asset_id, current.revision)
    assert len(current.history) == 2
    assert NativeWorkbookStructure().read(output)["tables"] == []
    assert NativeSpreadsheet(output).read_cell("Data", "G1")["value"] == "Human"
