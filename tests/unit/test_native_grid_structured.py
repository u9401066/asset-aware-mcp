"""Structured references preserve source column identity through native grid edits."""

import pytest

from src.domain.native_grid_tables import GridTableChange, GridTableColumn
from src.infrastructure.native_grid_selectors import rewrite_selector
from src.infrastructure.native_grid_structured import rewrite_structured_formula


def change(
    after=((2, "Second"), (3, "Third")),
    before=((1, "First"), (2, "Second"), (3, "Third")),
):
    return GridTableChange(
        "Table1",
        tuple(GridTableColumn(*col) for col in before),
        tuple(GridTableColumn(*col) for col in after) if after is not None else None,
    )


def rewrite(text, table=None, context=None):
    return rewrite_structured_formula(text, [table or change()], table_context=context)


@pytest.mark.parametrize(
    "source,expected",
    [
        ("SUM(Table1[First])", "SUM(#REF!)"),
        ("SUM(Table1[[First]:[Third]])", "SUM(Table1[[Second]:[Third]])"),
        ("SUM(Table1[[Third]:[First]])", "SUM(Table1[[Third]:[Second]])"),
        ("SUM(Table1[ [First]:[Third] ])", "SUM(Table1[ [Second]:[Third] ])"),
        (
            "SUM(Table1[[#Data],[First]:[Third]])",
            "SUM(Table1[[#Data],[Second]:[Third]])",
        ),
        ("SUM(Table1[First]:Table1[Third])", "SUM(Table1[Second]:Table1[Third])"),
        (
            "SUM(Data!Table1[First] : Data!Table1[Third])",
            "SUM(Data!Table1[Second] : Data!Table1[Third])",
        ),
        ("SUM(Table1[First]: Table1[Second])", "SUM(Table1[Second]: Table1[Second])"),
        ("SUM(Table1[[First],[Third]])", "SUM(#REF!)"),
        (
            "Table1[Second]+Table1[#Headers]+Table1",
            "Table1[Second]+Table1[#Headers]+Table1",
        ),
        ("SUM(Table1[[SECOND]:[THIRD]])", "SUM(Table1[[SECOND]:[THIRD]])"),
    ],
)
def test_deleted_column_and_surviving_interval_references(source, expected):
    assert rewrite(source)[0] == expected


@pytest.mark.parametrize(
    "source,expected",
    [
        ("[@First]", "[@Renamed]"),
        ("[@[First]]", "[@[Renamed]]"),
        ("[First]", "[Renamed]"),
        ("[[#This Row],[First]]", "[[#This Row],[Renamed]]"),
        ("[[#This Row],First]", "[[#This Row],Renamed]"),
    ],
)
def test_implicit_selectors_use_current_table_context(source, expected):
    renamed = change(after=((1, "Renamed"), (2, "Second"), (3, "Third")))
    assert rewrite(source, renamed, "Table1")[0] == expected
    assert rewrite(source, renamed, "Unrelated")[0] == source
    with pytest.raises(ValueError, match="table context"):
        rewrite(source, renamed)


def test_new_column_reusing_deleted_name_does_not_capture_old_reference():
    table = change(after=((4, "First"), (2, "Second"), (3, "Third")))
    assert rewrite("Table1[First]", table)[0] == "#REF!"
    assert rewrite("Table1[[First]:[Third]]", table)[0] == "Table1[[Second]:[Third]]"


def test_new_columns_inside_interval_are_included_without_changing_original_spelling():
    table = change(after=((1, "First"), (4, "Inserted"), (2, "Second"), (3, "Third")))
    source = 'SUM( Table1[[FIRST]:[Third]] ,  "Table1[First]" )'
    assert rewrite(source, table) == (source, 0)


def test_renaming_escapes_headers_and_adds_required_nested_brackets():
    table = change(after=((1, "A] B2,#@'"), (2, "Second"), (3, "Third")))
    encoded = "A'] B2,'#'@''"
    assert rewrite("Table1[First]", table)[0] == "Table1[[" + encoded + "]]"
    assert rewrite("Table1[@First]", table)[0] == "Table1[@[" + encoded + "]]"
    assert (
        rewrite("Table1[[#This Row],First]", table)[0]
        == "Table1[[#This Row],[" + encoded + "]]"
    )
    assert (
        rewrite("Table1[[#Data],[First]:[Third]]", table)[0]
        == "Table1[[#Data],[" + encoded + "]:[Third]]"
    )
    escaped = change(
        before=((1, "A] B2,#@'"), (2, "Second")), after=((1, "Restored"), (2, "Second"))
    )
    assert rewrite("Table1[[" + encoded + "]]", escaped)[0] == "Table1[[Restored]]"


def test_escape_literals_items_and_whitespace_are_distinct():
    table = change(
        before=((1, "#All"), (2, " First "), (3, "First")),
        after=((1, "All"), (2, "Spaced"), (3, "First")),
    )
    assert (
        rewrite("Table1['#All]+Table1[#All]+Table1[ First ]", table)[0]
        == "Table1[All]+Table1[#All]+Table1[Spaced]"
    )
    assert rewrite("Table1[First]", table)[0] == "Table1[First]"


def test_external_workbook_qualifiers_and_literal_strings_remain_exact():
    source = "SUM('[outside.xlsx]Data'!Table1[First], [1]Data!Table1[First]:Table1[Third], Other!Table1[First], \"Table1[First]\")"
    expected = "SUM('[outside.xlsx]Data'!Table1[First], [1]Data!Table1[First]:Table1[Third], #REF!, \"Table1[First]\")"
    assert rewrite(source)[0] == expected
    assert rewrite("[1]Other!Table2[A]:Data!Table1[First]")[0] == "#REF!"


def test_removed_table_invalidates_whole_column_item_and_implicit_refs():
    source = "SUM(Table1,Table1[#All],Table1[First],[@First],Table2[First])"
    assert (
        rewrite(source, change(after=None), "Table1")[0]
        == "SUM(#REF!,#REF!,#REF!,#REF!,Table2[First])"
    )


@pytest.mark.parametrize(
    "spec",
    [
        "[Missing]",
        "[[First][Second]]",
        "[[#Data]:[First]]",
        "[[First]:[Second]:[Third]]",
        "[[[First]]]",
    ],
)
def test_ambiguous_or_unknown_affected_selectors_fail(spec):
    with pytest.raises(ValueError):
        rewrite_selector(spec, change())


def test_duplicate_ids_names_and_reordering_require_explicit_reconciliation():
    for after in (
        ((1, "First"), (1, "Second")),
        ((1, "First"), (2, "FIRST")),
        ((2, "Second"), (1, "First")),
    ):
        with pytest.raises(ValueError):
            change(after=after)
