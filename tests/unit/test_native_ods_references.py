"""Static ODF reference grammar, structural mapping and exact literal preservation."""

from dataclasses import asdict

import pytest

from src.domain.native_ods_references import (
    OPENFORMULA,
    ODSAxisEdit,
    ODSSheetDelete,
    ODSSheetRename,
    map_ods_expression_references,
    parse_ods_reference,
    rewrite_ods_formula,
    rewrite_ods_reference,
)


@pytest.mark.parametrize(
    "expression,start",
    [
        ('SUM([Source.A1])+LEN("[Source.A1]")', 0),
        ("of:cell-content-is-in-list([Source.A1:.A3])", 3),
        ("is-true-formula([Source.A1]>0)", 0),
        ("formula-is([Source.A1]>0)", 0),
    ],
)
def test_native_owner_expressions_keep_original_spans_and_literals(expression, start):
    result, changes = map_ods_expression_references(
        expression,
        start=start,
        mapper=lambda ref: rewrite_ods_reference(
            ref, formula_sheet="Source", edit=ODSSheetRename("Source", "New 中文")
        ),
    )
    rebuilt, end = [], 0
    for change in changes:
        assert expression[change.start : change.end] == change.before
        rebuilt.extend((expression[end : change.start], change.after))
        end = change.end
    assert "".join([*rebuilt, expression[end:]]) == result
    assert "['New 中文'.A1" in result
    if '"[Source.A1]"' in expression:
        assert '"[Source.A1]"' in result


@pytest.mark.parametrize("replacement", [".A1]+1+[.B2", ".A1:.B2:.C3", "[.A1]", ""])
def test_expression_mapper_cannot_inject_formula_syntax(replacement):
    with pytest.raises(ValueError):
        map_ods_expression_references("[.A1]", start=0, mapper=lambda _: replacement)


@pytest.mark.parametrize("start", [-1, True, 7])
def test_expression_mapper_requires_valid_original_prefix_boundary(start):
    with pytest.raises(ValueError, match="prefix boundary"):
        map_ods_expression_references("[.A1]", start=start, mapper=lambda value: value)


def rewrite(text, edit=None, *, sheet="Source"):
    return rewrite_ods_reference(
        text,
        formula_sheet=sheet,
        edit=edit or ODSAxisEdit("Source", "rows", "insert", 2, 2),
    )


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (".A1", ".A1"),
        (".$B$3", ".$B$5"),
        ("Source.A1:.A5", "Source.A1:.A7"),
        ("Source.A3:.A5", "Source.A5:.A7"),
        ("Source.A1:.A3", "Source.A1:.A5"),
        ("Source.A3:.A3", "Source.A5:.A5"),
        ("Source.A5:.A1", "Source.A7:.A1"),
        ("Source.1:.3", "Source.1:.5"),
        ("Source.A:.C", "Source.A:.C"),
        ("Source.A$1:.A$1048576", "Source.A$1:.A$1048576"),
        ("Other.A3", "Other.A3"),
        ("#REF!", "#REF!"),
        ("'other.ods'#Source.A3", "'other.ods'#Source.A3"),
        (
            "'https://example.test/o''brien.ods'#Source.A3",
            "'https://example.test/o''brien.ods'#Source.A3",
        ),
    ],
)
def test_insert_rows_preserves_flags_scope_and_unaffected_bytes(before, after):
    assert rewrite(before) == after


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (".$B$3", "#REF!"),
        ("Source.A1:.A5", "Source.A1:.A4"),
        ("Source.A3:.A5", "Source.A3:.A4"),
        ("Source.A1:.A3", "Source.A1:.A2"),
        ("Source.A3:.A3", "#REF!"),
        ("Source.A5:.A1", "Source.A4:.A1"),
        ("Source.A1048575:.A1048576", "Source.A1048574:.A1048576"),
        ("Source.A3:.A1048576", "Source.A3:.A1048576"),
        ("Source.A1048576", "Source.A1048575"),
        ("Source.A1048576:.A1048576", "Source.A1048575:.A1048575"),
    ],
)
def test_delete_rows_contracts_survivors_and_keeps_open_grid_end(before, after):
    assert rewrite(before, ODSAxisEdit("Source", "rows", "delete", 2, 1)) == after


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("Source.A1", "Source.C1"),
        ("Source.$B$3", "Source.$D$3"),
        ("Source.A1:.C5", "Source.C1:.E5"),
        ("Source.A:.A", "Source.C:.C"),
        ("Source.1:.3", "Source.1:.3"),
    ],
)
def test_insert_columns_before_range_is_not_range_expansion(before, after):
    assert rewrite(before, ODSAxisEdit("Source", "columns", "insert", 0, 2)) == after


def test_grid_overflow_invalidates_point_and_retains_surviving_range():
    edit = ODSAxisEdit("Source", "rows", "insert", 0, 1)
    assert rewrite(".A1048576", edit) == "#REF!"
    assert rewrite(".A1048575:.A1048576", edit) == ".A1048576:.A1048576"
    assert rewrite(".A1048574:.A1048575", edit) == ".A1048575:.A1048576"
    assert rewrite(".A1048575:.A1048576") == "#REF!"
    assert (
        rewrite(".A1:.A5", ODSAxisEdit("Source", "rows", "insert", 5, 1)) == ".A1:.A5"
    )


def test_explicit_older_editor_grid_is_not_inferred_from_odf_version():
    edit = ODSAxisEdit("Source", "columns", "delete", 0, 1, column_limit=1024)
    assert rewrite(".B1:.AMJ2", edit) == ".A1:.AMJ2"
    assert rewrite(".$A1:.$AMJ3", edit) == ".$A1:.$AMJ3"
    # On a larger grid AMJ is an ordinary endpoint, not the open right boundary.
    modern = ODSAxisEdit("Source", "columns", "delete", 0, 1)
    assert rewrite(".B1:.AMJ2", modern) == ".A1:.AMI2"


def test_rename_quotes_unicode_apostrophes_and_exact_absolute_sheet_flags():
    edit = ODSSheetRename("Source", "New 中文 O'Brien")
    assert rewrite("$Source.$A$1:.C3", edit) == "$'New 中文 O''Brien'.$A$1:.C3"
    assert rewrite("Source.A1:Other.C3", edit) == "'New 中文 O''Brien'.A1:Other.C3"
    assert rewrite("Other.A1:Source.C3", edit) == "Other.A1:'New 中文 O''Brien'.C3"
    assert rewrite(".A1", edit) == ".A1"
    assert rewrite("'Source'.A1", ODSSheetRename("Source", "New")) == "'New'.A1"
    assert rewrite("'Other'.A1", edit) == "'Other'.A1"


def test_delete_sheet_creates_error_only_for_target_and_keeps_external_source():
    edit = ODSSheetDelete("Source")
    assert rewrite("Source.A1:.C4", edit) == "#REF!"
    assert rewrite(".A1", edit) == "#REF!"
    assert rewrite("Other.A1", edit) == "Other.A1"
    assert rewrite("'elsewhere.ods'#Source.A1", edit) == "'elsewhere.ods'#Source.A1"


@pytest.mark.parametrize("reference", ["''#Source.A1", "'#fragment'#Source.A1"])
def test_same_document_source_requires_identity_resolution(reference):
    with pytest.raises(ValueError, match="source resolver"):
        rewrite(reference)


def test_read_nested_sheet_and_quoted_punctuation_without_flattening():
    ref = parse_ods_reference("$'名.前''[:]'.B2.'sub.table'.$AA$17")
    assert ref.start.sheet == "名.前'[:]"
    assert ref.start.subtable_tokens == ("B2", "'sub.table'")
    assert ref.start.column == 26 and ref.start.row == 16
    assert ref.start.render() == ref.lexical
    edit = ODSSheetRename("名.前'[:]", "new")
    assert rewrite(ref.lexical, edit) == "$'new'.B2.'sub.table'.$AA$17"


def test_dependent_reference_shapes_require_context_before_any_package_edit():
    with pytest.raises(ValueError, match="multi-sheet"):
        rewrite("Source.A1:Other.A3")
    with pytest.raises(ValueError, match="sheet order"):
        rewrite("Source.A1:Other.A3", ODSSheetDelete("Source"))
    with pytest.raises(ValueError, match="subtable"):
        rewrite("Source.A1.'nested'.B2")


def test_formula_changes_have_original_unicode_spans_and_leave_literals_exact():
    formula = '公式:=IF("中文😀[Source.A3]"="a""[.A3]";[Source.$B$3]+[.A5];\'標籤[.A3]\')+INDIRECT("Source.A3")'
    changed, events = rewrite_ods_formula(
        formula,
        formula_sheet="Source",
        edit=ODSAxisEdit("Source", "rows", "insert", 2, 2),
        namespaces={"公式": OPENFORMULA},
    )
    assert changed == formula.replace("[Source.$B$3]", "[Source.$B$5]").replace(
        "[.A5]", "[.A7]"
    )
    assert len(events) == 2
    for event in events:
        assert formula[event.start : event.end] == event.before
        assert set(asdict(event)) == {"start", "end", "before", "after"}
    restored = changed
    for event in reversed(events):
        restored = restored.replace(event.after, event.before, 1)
    assert restored == formula


def test_formula_preserves_namespace_spelling_whitespace_and_quoted_sheet_brackets():
    formula = "of:= SUM( ['A]B'.A3] ;  [#REF!] )"
    actual, events = rewrite_ods_formula(
        formula,
        formula_sheet="Other",
        edit=ODSAxisEdit("A]B", "rows", "insert", 0, 1),
        namespaces={"of": OPENFORMULA},
    )
    assert actual == "of:= SUM( ['A]B'.A4] ;  [#REF!] )"
    assert len(events) == 1
    assert rewrite_ods_formula(
        "=1+2", formula_sheet="Source", edit=ODSSheetDelete("Source"), namespaces={}
    ) == ("=1+2", [])


@pytest.mark.parametrize(
    "text",
    [
        "",
        "A1",
        ".A0",
        ".a1",
        ".1",
        ".A",
        ".$",
        ".A1:.2",
        ".A1:.A2:.A3",
        "'bad.A1",
        "'''.A1",
        "Sheet name.A1",
        ".A1]",
        ".A1\x00",
        ".'nested'.A1",
    ],
)
def test_reject_ambiguous_or_malformed_reference(text):
    with pytest.raises(ValueError):
        parse_ods_reference(text)


@pytest.mark.parametrize(
    "formula",
    [
        "",
        "=",
        "of:1+2",
        "of:=",
        "foreign:=[.A1]",
        "of:=[.A1",
        "of:=[[.A1]]",
        "of:=[.A1]]",
        'of:="unclosed',
        "of:='unclosed",
        'of:=["A1"]',
    ],
)
def test_reject_unknown_namespace_and_unbalanced_formula_tokens(formula):
    with pytest.raises(ValueError):
        rewrite_ods_formula(
            formula,
            formula_sheet="Source",
            edit=ODSSheetDelete("Source"),
            namespaces={"of": OPENFORMULA},
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"index": -1},
        {"index": True},
        {"count": 0},
        {"count": True},
        {"count": 1_048_577},
        {"row_limit": 0},
        {"column_limit": 16_385},
        {"sheet": ""},
        {"axis": "sheets"},
        {"operation": "move"},
    ],
)
def test_validate_edit_before_mapping(kwargs):
    with pytest.raises(ValueError):
        ODSAxisEdit(
            **{
                "sheet": "Source",
                "axis": "rows",
                "operation": "insert",
                "index": 0,
                "count": 1,
                **kwargs,
            }
        )


def test_budgets_reject_excessive_formula_and_reference_without_expansion():
    with pytest.raises(ValueError, match="budget"):
        parse_ods_reference("A" * 65_537)
    with pytest.raises(ValueError, match="budget"):
        rewrite_ods_formula(
            "=" + "1" * 65_536,
            formula_sheet="Source",
            edit=ODSSheetDelete("Source"),
            namespaces={},
        )
    with pytest.raises(ValueError, match="grid"):
        rewrite(".A1048577")
    with pytest.raises(ValueError, match="budget"):
        rewrite_ods_formula(
            "=" + "+".join(["[Source.A1]"] * 100),
            formula_sheet="Observer",
            edit=ODSSheetRename("Source", "n" * 1024),
            namespaces={},
        )
