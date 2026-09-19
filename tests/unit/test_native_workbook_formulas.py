"""Keep formula spelling while changing only explicit local sheet qualifiers."""

import pytest

from src.domain.native_workbook import NativeWorksheetInsert, NativeWorksheetRename
from src.infrastructure.native_workbook_formulas import (
    formula_tokens,
    rename_sheet_references,
    sheet_references,
    table_references,
)


@pytest.mark.parametrize(
    "text,expected,count",
    [
        ("SUM(Data!A1:Data!B2)", "SUM('研究表'!A1:'研究表'!B2)", 2),
        ("Data!Table1[Other!Name]", "'研究表'!Table1[Other!Name]", 1),
        ("Table1[Data!Name]", "Table1[Data!Name]", 0),
        ("Data!A1 +  1", "'研究表'!A1 +  1", 1),
        ("Data!A1\t+\r\nOther!B1", "'研究表'!A1\t+\r\nOther!B1", 1),
        ("Table1[O'Brien]+Data!A1", "Table1[O'Brien]+'研究表'!A1", 1),
        ("  SUM(\nData!A1,  Data!B2 )", "  SUM(\n'研究表'!A1,  '研究表'!B2 )", 2),
        ("Data!A1#", "'研究表'!A1#", 1),
        ("@Data!A1", "@'研究表'!A1", 1),
        ("SUM(Data:Other!A1)", "SUM('研究表:Other'!A1)", 1),
        ("SUM('Data:Other'!A1)", "SUM('研究表:Other'!A1)", 1),
        ("SUM('Data':'Other'!A1)", "SUM('研究表:Other'!A1)", 1),
        ('INDIRECT("Data!A1") + Data!A1', "INDIRECT(\"Data!A1\") + '研究表'!A1", 1),
        ("[1]Data!A1 + '[book.xlsx]Data'!A1", "[1]Data!A1 + '[book.xlsx]Data'!A1", 0),
        ("Table1[Data!Name] + #REF!", "Table1[Data!Name] + #REF!", 0),
        ('IF(Data!A1=0,#N/A,"Data!")', "IF('研究表'!A1=0,#N/A,\"Data!\")", 1),
    ],
)
def test_lossless_local_qualifier_rewrites(text, expected, count):
    assert "".join(t[2] for t in formula_tokens(text)) == text
    assert rename_sheet_references(text, "Data", "研究表") == (expected, count)


def test_quoted_apostrophes_bangs_and_case_insensitive_names():
    text = "'o''brien!'!A1 + 'O''Brien!'!B2#"
    expected = "'New'' name'!A1 + 'New'' name'!B2#"
    assert rename_sheet_references(text, "O'Brien!", "New' name") == (expected, 2)
    refs = sheet_references("'A B:C D'!A1")
    assert refs[0].names == ("A B", "C D")


def test_table_dependency_names_exclude_external_book_references():
    assert table_references(
        "Table1[Count]+@Table2[Count]+'Data'!Table3[Count]+[1]Data!Table4[Count]"
    ) == {"table1", "table2", "table3"}


@pytest.mark.parametrize(
    "text", ["'missing!A1", 'IF("missing)', "Data:Other:Third!A1", "Data!", "x" * 65537]
)
def test_unhandled_or_ambiguous_formula_fails(text):
    with pytest.raises(ValueError):
        sheet_references(text)


@pytest.mark.parametrize(
    "name",
    ["History", "history", "bad\ud800", "bad\ufffe", "bad\n", "bad:name", "'bad"],
)
def test_native_structure_names_reject_invalid_xml_and_excel_names(name):
    with pytest.raises(ValueError):
        NativeWorksheetInsert(index=0, names=[name])
    with pytest.raises(ValueError):
        NativeWorksheetRename(
            key={"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"}, name=name
        )
