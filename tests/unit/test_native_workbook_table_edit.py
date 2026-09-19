"""Native Table metadata, values, formatting and dependency edits stay coordinated."""

import io
from copy import deepcopy

import openpyxl
import pytest
from lxml import etree

from src.domain.native_assets import NativeCellEdit
from src.domain.native_table_edit import NativeTableUpdate
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet import NativeSpreadsheet
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_structure import NativeWorkbookStructure
from src.infrastructure.native_workbook_table_edit import NativeWorkbookTableEdit
from tests.native_grid_helpers import table_workbook
from tests.native_workbook_helpers import _parts, _replace
from tests.unit.test_native_grid_metadata import CACHE, with_pivot_source
from tests.unit.test_native_grid_named_sources import named_source
from tests.unit.test_native_grid_tables import read, table


def request(*columns, ref="A2:C5", **kwargs):
    return NativeTableUpdate(
        worksheet={"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
        part="xl/tables/table1.xml",
        expected_ref=ref,
        columns=list(columns),
        **kwargs,
    )


def column(identity=1, expected="Input", **changes):
    return {"column_id": identity, "expected_name": expected, **changes}


def mutate(source, part, action):
    root = etree.fromstring(_parts(source)[part])
    action(root)
    return _replace(source, {part: etree.tostring(root)})


def test_rename_calculated_and_totals_commit_consistent_native_parts():
    original = table_workbook(totals=True, formula="=A3*2")
    updated, result = NativeWorkbookTableEdit().update(
        original,
        request(
            column(name="Amount"),
            column(
                2,
                "Calc",
                name="Doubled",
                calculated={"formula": "=A3*3", "policy": "require_matching"},
                totals={"kind": "function", "value": "average"},
            ),
            column(3, "Label", totals={"kind": "label", "value": "平均"}),
            ref="A2:C6",
        ),
    )
    book = openpyxl.load_workbook(io.BytesIO(updated))
    try:
        native = book["Data"].tables["Table1"]
        assert native.ref == "A2:C6" and native.autoFilter.ref == "A2:C5"
        assert [(c.id, c.name) for c in native.tableColumns] == [
            (1, "Amount"),
            (2, "Doubled"),
            (3, "Label"),
        ]
        assert [book["Data"][f"B{row}"].value for row in (3, 4, 5)] == [
            "=A3*3",
            "=A4*3",
            "=A5*3",
        ]
        assert book["Data"]["B6"].value == "=SUBTOTAL(101,[Doubled])"
        assert book["Data"]["C6"].value == "平均"
        assert book["Other"]["A2"].value == "=SUM(Table1[Amount])"
        assert native.tableColumns[1].calculatedColumnFormula.text == "A3*3"
        assert native.tableColumns[1].totalsRowFunction == "average"
    finally:
        book.close()
    for part in ("xl/styles.xml", "customXml/unchanged.xml"):
        assert _parts(updated)[part] == _parts(original)[part]
    for address in ("A3", "B3", "B6", "C6"):
        assert (
            read(updated, address)["style_index"]
            == read(original, address)["style_index"]
        )
    assert "xl/worksheets/sheet2.xml" in result.changes[0]["structured_references"]
    assert all(read(updated, f"B{row}")["cached_value"] is None for row in (3, 4, 5, 6))


def test_rename_rewrites_existing_calculated_and_defined_references():
    source = table_workbook()
    source = mutate(
        source,
        "xl/workbook.xml",
        lambda root: setattr(
            root.find("s:definedNames/s:definedName", NS), "text", "Table1[Input]"
        ),
    )
    updated, _ = NativeWorkbookTableEdit().update(
        source, request(column(name="Price [net]"))
    )
    assert read(updated, "B3")["value"] == "=[[#This Row],[Price '[net']]]*2"
    assert (
        "Price '[net']"
        in table(updated)
        .find("s:tableColumns/s:tableColumn/s:calculatedColumnFormula", NS)
        .text
    )
    names = etree.fromstring(_parts(updated)["xl/workbook.xml"]).find(
        "s:definedNames/s:definedName", NS
    )
    assert names.text == "Table1[[Price '[net']]]"


def test_calculated_exceptions_require_explicit_replacement_and_removal_keeps_cells():
    source = table_workbook(formula="=A3*2", expand_a1=False)
    with pytest.raises(ValueError, match="exception at B4"):
        NativeWorkbookTableEdit().update(
            source,
            request(
                column(
                    2,
                    "Calc",
                    calculated={"formula": "=A3*3", "policy": "require_matching"},
                )
            ),
        )
    updated, _ = NativeWorkbookTableEdit().update(
        source,
        request(
            column(2, "Calc", calculated={"formula": "=A3*3", "policy": "replace_all"})
        ),
    )
    removed, result = NativeWorkbookTableEdit().update(
        updated,
        request(
            column(2, "Calc", calculated={"formula": None, "policy": "keep_cells"})
        ),
    )
    assert (
        table(removed).find(
            "s:tableColumns/s:tableColumn/s:calculatedColumnFormula", NS
        )
        is None
    )
    assert read(removed, "B5")["value"] == "=A5*3"
    assert result.changes[0]["request"]["columns"][0]["calculated"]["formula"] is None
    final, _ = NativeSpreadsheet(removed).edit(
        [NativeCellEdit(sheet="Data", cell="B5", kind="number", value=11)]
    )
    assert read(final, "B5")["value"] == 11


def rich_source():
    source = table_workbook()
    sheet = etree.fromstring(_parts(source)["xl/worksheets/sheet1.xml"])
    index = sheet.find(".//s:c[@r='A2']/s:v", NS).text
    strings = etree.fromstring(_parts(source)["xl/sharedStrings.xml"])
    item = strings.findall("s:si", NS)[int(index)]
    item[:] = []
    for text, prop in (("In", "b"), ("put", "i")):
        run = etree.SubElement(item, tag("r"))
        etree.SubElement(etree.SubElement(run, tag("rPr")), tag(prop))
        etree.SubElement(run, tag("t")).text = text
    other = etree.fromstring(_parts(source)["xl/worksheets/sheet2.xml"])
    etree.SubElement(
        other.find("s:sheetData/s:row", NS), tag("c"), r="B1", t="s"
    ).append(etree.Element(tag("v")))
    other.find(".//s:c[@r='B1']/s:v", NS).text = index
    return _replace(
        source,
        {
            "xl/sharedStrings.xml": etree.tostring(strings),
            "xl/worksheets/sheet2.xml": etree.tostring(other),
        },
    )


def test_shared_rich_header_requires_exact_runs_and_never_changes_other_users():
    source = rich_source()
    inventory = NativeWorkbookStructure().read(source)["tables"][0]["header_cells"][0]
    assert inventory["column_id"] == "1" and inventory["cell"] == "A2"
    assert inventory["value"]["rich_text"] and ">In<" in inventory["shared_string_xml"]
    with pytest.raises(ValueError, match="run-aware"):
        NativeWorkbookTableEdit().update(source, request(column(name="Output")))
    updated, _ = NativeWorkbookTableEdit().update(
        source, request(column(name="Output", header_runs=["Out", "put"]))
    )
    assert read(updated, "A2")["value"] == "Output" and read(updated, "A2")["rich_text"]
    old_sst = etree.fromstring(_parts(source)["xl/sharedStrings.xml"])
    new_sst = etree.fromstring(_parts(updated)["xl/sharedStrings.xml"])
    assert [etree.tostring(n) for n in old_sst] == [etree.tostring(n) for n in new_sst]
    sheet = etree.fromstring(_parts(updated)["xl/worksheets/sheet1.xml"])
    content = sheet.find(".//s:c[@r='A2']/s:is", NS)
    assert content.find("s:r/s:rPr/s:b", NS) is not None
    assert content.findall("s:r", NS)[1].find("s:rPr/s:i", NS) is not None
    assert NativeSpreadsheet(updated).read_cell("Other", "B1")["value"] == "Input"
    current = NativeWorkbookStructure().read(updated)["tables"][0]["header_cells"][0]
    assert current["shared_string_xml"] is None and ">Out<" in current["cell_xml"]
    with pytest.raises(ValueError, match="run count"):
        NativeWorkbookTableEdit().update(
            source, request(column(name="Output", header_runs=["Output"]))
        )


@pytest.mark.parametrize(
    "changes,match",
    [
        ([column(name="Calc")], "Duplicate"),
        ([column(expected="wrong", name="X")], "expected_name"),
        ([column(99, "Input", name="X")], "unknown column"),
        ([column(totals={"kind": "blank"})], "existing totals"),
        (
            [
                column(
                    2,
                    "Calc",
                    calculated={"formula": "=[@Missing]", "policy": "replace_all"},
                )
            ],
            "unknown source column",
        ),
    ],
)
def test_invalid_table_intent_rejects(changes, match):
    with pytest.raises(ValueError, match=match):
        NativeWorkbookTableEdit().update(table_workbook(), request(*changes))


@pytest.mark.parametrize(
    "damage,match",
    [
        (lambda root: etree.SubElement(root, tag("sheetProtection")), "Protected"),
        (lambda root: root.find(".//s:c[@r='A2']", NS).set("cm", "1"), "metadata"),
        (
            lambda root: etree.SubElement(
                etree.SubElement(root, tag("mergeCells")), tag("mergeCell"), ref="A2:B2"
            ),
            "Merged",
        ),
        (
            lambda root: root.find(".//s:c[@r='B3']/s:f", NS).set("t", "shared"),
            "Shared/array",
        ),
    ],
)
def test_native_guards_stay_active_for_specialized_edits(damage, match):
    source = mutate(table_workbook(), "xl/worksheets/sheet1.xml", damage)
    with pytest.raises(ValueError, match=match):
        NativeWorkbookTableEdit().update(
            source,
            request(
                column(name="X"),
                column(
                    2, "Calc", calculated={"formula": "=A3", "policy": "replace_all"}
                ),
            ),
        )


@pytest.mark.parametrize(
    "source",
    [
        table_workbook,
        lambda: named_source(("Proxy", "AllData", None)),
        lambda: with_pivot_source(table_workbook()),
    ],
)
def test_pivot_headers_block_rename_but_data_formula_changes_invalidate_cache(source):
    original = source()
    if CACHE not in _parts(original):
        original = with_pivot_source(original)
    with pytest.raises(ValueError, match="cache field identities"):
        NativeWorkbookTableEdit().update(original, request(column(name="X")))
    updated, result = NativeWorkbookTableEdit().update(
        original,
        request(
            column(
                2, "Calc", calculated={"formula": "=A3*3", "policy": "require_matching"}
            )
        ),
    )
    cache = etree.fromstring(_parts(updated)[CACHE])
    assert cache.get("invalid") == "1" and cache.get("refreshOnLoad") == "1"
    assert result.changes[0]["invalidated_pivot_caches"] == [CACHE]


@pytest.mark.parametrize(
    "totals,expected",
    [
        ({"kind": "blank"}, None),
        ({"kind": "formula", "value": "=SUM(Table1[Input])"}, "=SUM(Table1[Input])"),
    ],
)
def test_totals_replacement_clears_obsolete_attributes(totals, expected):
    source = table_workbook(totals=True)
    updated, _ = NativeWorkbookTableEdit().update(
        source, request(column(2, "Calc", totals=totals), ref="A2:C6")
    )
    assert read(updated, "B6")["value"] == expected
    node = table(updated).findall("s:tableColumns/s:tableColumn", NS)[1]
    assert node.get("totalsRowLabel") is None
    assert node.get("totalsRowFunction") == ("custom" if expected else None)


def test_schema_validates_policy_and_identity_without_io():
    good = request(column(name="New")).model_dump()
    bads = []
    for replacement in (
        {"formula": None, "policy": "replace_all"},
        {"formula": "A3", "policy": "require_matching"},
        {"formula": "=A3", "policy": "keep_cells"},
    ):
        value = deepcopy(good)
        value["columns"][0]["calculated"] = replacement
        bads.append(value)
    duplicate = deepcopy(good)
    duplicate["columns"] *= 2
    bads.append(duplicate)
    for bad in bads:
        with pytest.raises(ValueError):
            NativeTableUpdate.model_validate(bad)


@pytest.mark.parametrize(
    "attribute,value", [("tableType", "queryTable"), ("tableType", "xml")]
)
def test_bound_source_tables_require_coordinated_schema_edits(attribute, value):
    source = mutate(
        table_workbook(),
        "xl/tables/table1.xml",
        lambda node: node.set(attribute, value),
    )
    with pytest.raises(ValueError, match="source field identities"):
        NativeWorkbookTableEdit().update(source, request(column(name="X")))


def test_metadata_only_edit_still_checks_protection():
    source = mutate(
        table_workbook(),
        "xl/worksheets/sheet1.xml",
        lambda root: etree.SubElement(root, tag("sheetProtection")),
    )
    with pytest.raises(ValueError, match="Protected"):
        NativeWorkbookTableEdit().update(
            source,
            request(
                column(2, "Calc", calculated={"formula": None, "policy": "keep_cells"})
            ),
        )


def test_wrong_table_range_and_worksheet_identity_reject():
    source = table_workbook()
    for update in (
        request(column(name="X"), ref="A1:C5"),
        request(column(name="X")).model_copy(update={"part": "xl/tables/missing.xml"}),
    ):
        with pytest.raises(ValueError):
            NativeWorkbookTableEdit().update(source, update)


def test_phonetic_header_requires_explicit_correspondence():
    source = rich_source()
    source = mutate(
        source,
        "xl/sharedStrings.xml",
        lambda root: etree.SubElement(
            root.find("s:si[s:r]", NS), tag("phoneticPr"), fontId="0"
        ),
    )
    with pytest.raises(ValueError, match="Phonetic"):
        NativeWorkbookTableEdit().update(
            source, request(column(name="Output", header_runs=["Out", "put"]))
        )


def test_swapping_names_retains_original_column_identity():
    updated, _ = NativeWorkbookTableEdit().update(
        table_workbook(),
        request(column(name="Label"), column(3, "Label", name="Input")),
    )
    assert (
        read(updated, "A2")["value"] == "Label"
        and read(updated, "C2")["value"] == "Input"
    )
    assert (
        NativeSpreadsheet(updated).read_cell("Other", "A2")["value"]
        == "=SUM(Table1[Label])"
    )
    assert read(updated, "B3")["value"] == "=[[#This Row],Label]*2"


@pytest.mark.parametrize("totals", [False, True])
def test_late_cas_conflict_keeps_concurrent_revision_without_table_partial_write(
    tmp_path,
    totals,
):
    from src.application.native_document_service import NativeDocumentService
    from src.infrastructure.native_asset_store import FileNativeAssetRepository
    from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
    from tests.native_workbook_helpers import _call

    repository = FileNativeAssetRepository(tmp_path / "store")
    source = tmp_path / "source.xlsx"
    source.write_bytes(table_workbook())

    class ConcurrentEdit:
        def update(self, data, change):
            updated, receipt = NativeWorkbookTableEdit().update(data, change)
            competitor, result = NativeSpreadsheet(data).edit(
                [NativeCellEdit(sheet="Data", cell="C3", kind="string", value="human")]
            )
            repository.commit(asset["asset_id"], asset["revision"], competitor, result)
            return updated, receipt

    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        workbook_structure=NativeWorkbookStructure(),
        workbook_tables=ConcurrentEdit(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    with pytest.raises(ValueError):
        _call(
            service,
            op="update_workbook_table",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            table_update=(
                request(totals_row={"action": "add"})
                if totals
                else request(column(name="Amount"))
            ).model_dump(),
        )
    current = repository.load(asset["asset_id"])
    assert len(current.history) == 2
    output = repository.read(current.asset_id, current.revision)
    assert read(output, "C3")["value"] == "human"
    assert read(output, "A2")["value"] == "Input"
    assert source.read_bytes() == repository.read(asset["asset_id"], asset["revision"])


@pytest.mark.parametrize("totals", [False, True])
def test_combined_public_readback_budget_rejects_before_commit(
    tmp_path, monkeypatch, totals
):
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
        workbook_tables=NativeWorkbookTableEdit(),
    )
    source = tmp_path / "source.xlsx"
    source.write_bytes(table_workbook())
    asset = _call(service, op="register", source_path=str(source))["asset"]
    baseline = {
        **adapter.read(source.read_bytes(), references=True),
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "operation_result": None,
    }
    limit = len(operations._record_text(baseline).encode("utf-8")) + 100
    monkeypatch.setattr(operations, "MAX_WORKBOOK_READ_BYTES", limit)
    assert operations._record_text(baseline)
    with pytest.raises(ValueError, match="read-back budget"):
        _call(
            service,
            op="update_workbook_table",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            table_update=(
                request(totals_row={"action": "add"})
                if totals
                else request(column(name="Amount"))
            ).model_dump(),
        )
    current = repository.load(asset["asset_id"])
    assert current.revision == asset["revision"] and len(current.history) == 1


def test_receipt_before_formula_is_the_original_revision_not_renamed_intermediate():
    source = table_workbook()
    _, result = NativeWorkbookTableEdit().update(
        source,
        request(
            column(name="Amount"),
            column(
                2,
                "Calc",
                calculated={"formula": "=[@Amount]*3", "policy": "require_matching"},
            ),
        ),
    )
    cell = result.changes[0]["cells"]["B3"]
    assert cell["before"]["value"] == read(source, "B3")["value"]
    assert cell["after"]["value"] == "=[@Amount]*3"
