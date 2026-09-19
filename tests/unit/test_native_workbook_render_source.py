"""Preview guards distinguish actual resource operands from harmless content."""

import pytest

from src.infrastructure.native_workbook_render_source import (
    check_formula,
    rendering_source,
)
from tests.native_workbook_helpers import _parts, _replace, build_workbook
from tests.native_workbook_render_helpers import rendered_workbook


@pytest.mark.parametrize(
    "formula",
    [
        'WEBSERVICE("https://example.invalid")',
        '_xlfn.IMAGE("https://example.invalid")',
        'RTD("server",,"topic")',
        'DDE("cmd","x","y")',
        "_xll.addin(1)",
        "_xludf.run(1)",
        'CALL("lib","fn","J")',
        'EVALUATE("1+2")',
        "'[1]Sheet1'!A1",
        "[1]!Name",
        "cmd|'arg'!A0",
        "'[1]Sheet1'!custom(1)",
    ],
)
def test_resource_operands_reject(formula):
    with pytest.raises(ValueError):
        check_formula(formula, {"data", "other"})


@pytest.mark.parametrize(
    "formula",
    [
        '"WEBSERVICE( and [1]Sheet!A1 and cmd|x!y"',
        'HYPERLINK("https://example.invalid","link")',
        "SUM(Table1[A|B])",
        "SUM(Table1[A!B])",
        "'A|B'!A1",
        "@'A|B'!A1",
        "SUM(Data!A1:A9)",
        "_xlfn.XLOOKUP(A1,B1:B9,C1:C9)",
        "SUM(A1#)",
        "Table1[[#Data],[A]]",
        'IF(A1="cmd|x!y",1,2)',
    ],
)
def test_harmless_literals_local_references_and_hyperlinks_survive(formula):
    check_formula(formula, {"data", "a|b"})


def test_source_inventory_keeps_hidden_and_blank_sheets_and_package():
    data = rendered_workbook()
    inventory = rendering_source(data)
    assert [s["name"] for s in inventory] == ["First", "Blank", "Hidden", "Last"]
    assert inventory[2]["state"] == "hidden"
    assert inventory[3]["key"] == {"sheet_id": "4", "part": "xl/worksheets/sheet4.xml"}
    assert rendering_source(build_workbook())[0]["name"] == "Data"


@pytest.mark.parametrize(
    "fault",
    [
        "external",
        "ole",
        "svg",
        "vml",
        "macro_type",
        "query",
        "missing",
        "defined_name",
        "formula",
        "table_formula",
        "sheet_kind",
    ],
)
def test_known_dependencies_block_before_conversion(fault):
    data = rendered_workbook()
    parts = _parts(data)
    rel = b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="file:///outside.png" TargetMode="External"/></Relationships>'
    changed = {}
    if fault in {"external", "ole", "missing"}:
        if fault == "ole":
            rel = rel.replace(b"/image", b"/oleObject")
        if fault == "missing":
            rel = rel.replace(b"file:///outside.png", b"missing.png").replace(
                b' TargetMode="External"', b""
            )
        changed["xl/_rels/linked.xml.rels"] = rel
    elif fault == "svg":
        changed["xl/media/a.svg"] = b"<svg/>"
    elif fault == "vml":
        changed["xl/drawings/a.vml"] = (
            b'<v:shape xmlns:v="urn:schemas-microsoft-com:vml" src="file:///outside"/>'
        )
    elif fault == "macro_type":
        changed["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
            b"spreadsheetml.sheet.main+xml",
            b"spreadsheetml.sheet.macroEnabled.main+xml",
        )
    elif fault == "query":
        changed["xl/queryTables/a.xml"] = (
            b'<queryTable xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>'
        )
    elif fault == "defined_name":
        changed["xl/workbook.xml"] = parts["xl/workbook.xml"].replace(
            b"<definedNames>",
            b'<definedNames><definedName name="Remote">WEBSERVICE("https://example.invalid")</definedName>',
        )
    elif fault == "formula":
        changed["xl/worksheets/sheet1.xml"] = parts["xl/worksheets/sheet1.xml"].replace(
            b"<f>1+2</f>", b'<f>WEBSERVICE("https://example.invalid")</f>'
        )
    elif fault == "table_formula":
        changed["xl/tables/table1.xml"] = (
            b'<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><calculatedColumnFormula>WEBSERVICE("https://example.invalid")</calculatedColumnFormula></table>'
        )
    else:
        changed["xl/_rels/workbook.xml.rels"] = parts[
            "xl/_rels/workbook.xml.rels"
        ].replace(b"/worksheet", b"/chartsheet")
    with pytest.raises(ValueError):
        rendering_source(_replace(data, changed))
