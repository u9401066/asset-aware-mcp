"""Grid transforms preserve literal formula syntax and adjust exact dependencies."""

import pytest

from src.domain.native_grid import GridTransform, NativeGridEdit, NativeGridUpdate
from src.domain.native_grid_address import transform_reference
from src.infrastructure.native_grid_formulas import (
    rewrite_grid_formula,
    translate_shared_formula,
)


def transform(axis="row", operation="insert", at=2, count=1):
    return GridTransform(
        NativeGridEdit(axis=axis, operation=operation, at=at, count=count)
    )


@pytest.mark.parametrize(
    "source,expected",
    [
        ("A1", "A1"),
        ("$A$2", "$A$3"),
        ("aA2", "aA3"),
        ("A1:B3", "A1:B4"),
        ("3:5", "4:6"),
        ("$1:$3", "$1:$4"),
        ("A:C", "A:C"),
        ("MyName", None),
        ("XFE1", None),
        ("B5:A2", "B6:A3"),
    ],
)
def test_insert_references(source, expected):
    assert transform_reference(source, transform()) == expected


@pytest.mark.parametrize(
    "source,expected",
    [
        ("A2", "#REF!"),
        ("A3:B4", "A2:B2"),
        ("A1:B2", "A1:B1"),
        ("A2:B3", "#REF!"),
        ("A1:B6", "A1:B4"),
        ("3:5", "2:3"),
    ],
)
def test_delete_shrinks_ranges_instead_of_deleting_surviving_endpoints(
    source, expected
):
    assert (
        transform_reference(source, transform(operation="delete", count=2)) == expected
    )


def test_whole_columns_mixed_absolute_case_and_storage_overflow():
    shift = transform(axis="column", at=2)
    assert transform_reference("$B1:c$4", shift) == "$C1:d$4"
    assert transform_reference("$A:$C", shift) == "$A:$D"
    assert transform_reference("1:3", shift) == "1:3"
    assert transform_reference("XFD1", shift) == "#REF!"
    with pytest.raises(ValueError, match="outside"):
        shift.point(16384)
    with pytest.raises(ValueError, match="outside"):
        shift.span(16383, 16384)
    assert (
        transform(operation="delete", at=1048576).point(1048576, clamp=True) == 1048576
    )


def rewrite(text, shift=None, owner="Data"):
    return rewrite_grid_formula(
        text,
        shift or transform(),
        owner=owner,
        target="Data",
        sheets=["First", "Data", "Other"],
    )


def test_formula_literals_names_external_references_and_whitespace_are_exact():
    source = "=SUM(  $A$2 , Data!B3, Other!C3,\t'Data'!D4, \"Data!A2\", Named, [Book.xlsx]Data!A2, @A2#)"
    expected = "=SUM(  $A$3 , Data!B4, Other!C3,\t'Data'!D5, \"Data!A2\", Named, [Book.xlsx]Data!A2, @A3#)"
    assert rewrite(source) == (expected, 4)
    assert rewrite("SUM(A2,Data!B2)", owner="Other") == ("SUM(A2,Data!B3)", 1)
    assert rewrite("SUM(A2,Data!B2)", owner="Data") == ("SUM(A3,Data!B3)", 2)


@pytest.mark.parametrize(
    "source,expected",
    [
        ("SUM(A2:A4)", "SUM(A2:A2)"),
        ("SUM(A2 : A4)", "SUM(A2 : A2)"),
        ("SUM(A2: A4)", "SUM(A2: A2)"),
        ("SUM(A2 :A4)", "SUM(A2 :A2)"),
        ("SUM(Data!A2:Data!A4)", "SUM(Data!A2:Data!A2)"),
        ("SUM(Data!A2 : Data!A4)", "SUM(Data!A2 : Data!A2)"),
        ("SUM(Data!A2: Data!A4)", "SUM(Data!A2: Data!A2)"),
        ("SUM(Data!A2 :Data!A4)", "SUM(Data!A2 :Data!A2)"),
        ("Data!A2+@A3#", "#REF!+#REF!"),
    ],
)
def test_range_deletion_including_spaced_and_qualified_endpoints(source, expected):
    assert rewrite(source, transform(operation="delete", count=2))[0] == expected


def test_3d_coordinate_divergence_and_ambiguous_names_fail():
    with pytest.raises(ValueError, match="3D"):
        rewrite("SUM(First:Other!A2)")
    assert rewrite("SUM(First:Other!A1)")[0] == "SUM(First:Other!A1)"
    with pytest.raises(ValueError, match="context"):
        rewrite("A2", owner=None)
    with pytest.raises(ValueError, match="different coordinate"):
        rewrite("Data!A2:Other!A4")
    assert rewrite("SUM(Table1[Column A],First!A2)")[1] == 0


def test_shared_formulas_translate_relative_coordinates_only():
    source = 'SUM($A1,B$2,$C$3,Data!D4,A:C,1:$2,@E5#,"A1",Name)'
    assert (
        translate_shared_formula(source, 2, 1)
        == 'SUM($A3,C$2,$C$3,Data!E6,B:D,3:$2,@F7#,"A1",Name)'
    )
    assert translate_shared_formula("A1+$A$1", -1, 0) == "#REF!+$A$1"


def test_edit_request_roundtrip_and_axis_boundaries():
    value = NativeGridUpdate(
        worksheet={"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
        edits=[{"axis": "row", "operation": "delete", "at": 3}],
    )
    assert NativeGridUpdate.model_validate(value.model_dump()) == value
    for edit in (
        {"axis": "column", "operation": "insert", "at": 16384, "count": 2},
        {"axis": "row", "operation": "delete", "at": 1, "inherit_format": "before"},
    ):
        with pytest.raises(ValueError):
            NativeGridEdit.model_validate(edit)


@pytest.mark.parametrize("reference", ["A2:NamedRange", "NamedRange:A2", "A2:B4:C6"])
def test_unresolved_ranges_containing_coordinates_are_not_silently_left_stale(
    reference,
):
    with pytest.raises(ValueError, match="range resolver"):
        rewrite(f"SUM({reference})")
    with pytest.raises(ValueError, match="range resolver"):
        translate_shared_formula(reference, 1, 1)
    assert rewrite(f"SUM(Other!{reference})")[0] == f"SUM(Other!{reference})"
    assert rewrite(f"SUM({reference})", owner="Other")[0] == f"SUM({reference})"


def test_small_coordinate_space_matches_surviving_cells_for_every_delete_interval():
    for at in range(1, 9):
        for count in range(1, 4):
            change = transform(operation="delete", at=at, count=count)
            for first in range(1, 9):
                for last in range(first, 10):
                    survivors = [
                        value if value < at else value - count
                        for value in range(first, last + 1)
                        if not at <= value < at + count
                    ]
                    expected = (min(survivors), max(survivors)) if survivors else None
                    assert change.span(first, last) == expected


@pytest.mark.parametrize(
    "reference",
    [
        "Table1[[A'] B2,C]]",
        "Table1[[A'[ B2]]",
        "Table1[[A'] Data!A2]]",
        "Table1['#One]",
        "Table1[O''Brien]",
        "Table1[ [One]:[Two] ]",
    ],
)
def test_escaped_structured_column_headers_are_never_rewritten_as_coordinates(
    reference,
):
    source = f"SUM({reference},A2)"
    assert rewrite(source) == (f"SUM({reference},A3)", 1)
    assert translate_shared_formula(source, 1, 0) == f"SUM({reference},A3)"
