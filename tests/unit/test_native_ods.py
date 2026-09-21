"""Logical repetition, native values and structure-preserving ODS edits."""

import copy

import pytest
from lxml import etree
from pydantic import ValidationError

from src.domain.native_ods import NativeODSCreate, NativeODSValue
from src.infrastructure.native_odf_package import NS, NativeODFPackage, q, xml_bytes
from src.infrastructure.native_ods import NativeODS, create_native_ods
from tests.native_ods_helpers import edit, fixture, locator


def test_creation_is_deterministic_with_odf_names_not_excel_names():
    request = NativeODSCreate(
        tables=["History", "名字超過三十一字元" * 5, "Case", "case"]
    )
    data = create_native_ods(request)
    assert create_native_ods(request) == data
    listing = NativeODS(data).inspect()
    assert listing["odf_version"] == "1.3"
    assert [t["table_name"] for t in listing["tables"]] == request.tables
    assert listing["total_physical_records"] == 4


@pytest.mark.parametrize(
    ("kind", "value", "kwargs", "attribute", "expected"),
    [
        (
            "string",
            " =SUM([.A1])  繁體中文😀\t\n",
            {},
            "string-value",
            " =SUM([.A1])  繁體中文😀\t\n",
        ),
        (
            "float",
            "12345678901234567890.00100",
            {},
            "value",
            "12345678901234567890.00100",
        ),
        ("percentage", "0.125", {}, "value", "0.125"),
        ("currency", "3.43", {"currency": "USD"}, "currency", "USD"),
        ("boolean", False, {}, "boolean-value", "false"),
        ("date", "2026-09-21T12:30:00Z", {}, "date-value", "2026-09-21T12:30:00Z"),
        ("time", "PT26H15M0.50S", {}, "time-value", "PT26H15M0.50S"),
    ],
)
def test_authored_values_are_literal_and_lossless(
    kind, value, kwargs, attribute, expected
):
    original = create_native_ods(NativeODSCreate())
    changed, receipt = NativeODS(original).edit(
        [edit(value=value, kind=kind, **kwargs)]
    )
    record = NativeODS(changed).read_cell(locator())
    assert record["value_attributes"][attribute] == expected
    assert record["value_type"] == kind and record["formula"] is None
    assert receipt.changed_parts == ["content.xml"]
    again, noop = NativeODS(changed).edit([edit(value=value, kind=kind, **kwargs)])
    assert again == changed and not noop.changes
    if kind == "string":
        assert record["display_paragraphs"] == [value]


@pytest.mark.parametrize("prefix", ["formula", "公式", "á"])
def test_read_rich_text_whitespace_annotations_and_formula_namespace(prefix):
    data = fixture("""<table:table-row><table:table-cell table:style-name="money"
      office:value-type="float" office:value="999" table:formula="formula:=SUM([.B1:.B2])" xmlns:formula="urn:oasis:names:tc:opendocument:xmlns:of:1.2">
      <text:p>  A <text:span text:style-name="bold"> B</text:span><text:s text:c="3"/>C<text:tab/>D<text:line-break/>E </text:p>
      <office:annotation><text:p>NOT CELL DISPLAY</text:p></office:annotation>
      </table:table-cell></table:table-row>""")
    if prefix != "formula":
        package = NativeODFPackage(data)
        data = package.replace(
            {
                "content.xml": package.parts["content.xml"]
                .replace(b"formula:", (prefix + ":").encode())
                .replace(b"xmlns:formula=", ("xmlns:" + prefix + "=").encode())
            }
        )
    record = NativeODS(data).read_cell(locator())
    assert record["display_paragraphs"] == ["A B   C\tD\nE"]
    assert record["formula"]["namespace"] == NS["of"]
    assert record["formula"]["expression"] == "=SUM([.B1:.B2])"
    assert record["value_attributes"]["value"] == "999"
    assert record["cached_value_verified"] is False
    assert "NOT CELL DISPLAY" in record["native_xml"]


def test_repeated_grid_edit_splits_only_target_without_expanding():
    original = fixture(
        """<table:table-header-rows><table:table-row table:style-name="row" table:number-rows-repeated="1000000">
      <table:table-cell table:style-name="cell" table:number-columns-repeated="16000" office:value-type="string"><text:p>old</text:p></table:table-cell>
      </table:table-row></table:table-header-rows>""",
        extras={"Pictures/keep.bin": b"EXACT\x00PAYLOAD", "styles.xml": b"<styles/>"},
    )
    book = NativeODS(original)
    assert book.inspect()["total_physical_records"] == 1
    changed, receipt = book.edit(
        [edit(500000, 8000, "new"), edit(500000, 8001, "adjacent")]
    )
    updated = NativeODS(changed)
    assert len(changed) < 3000
    assert len(updated.root.findall(".//table:table-row", NS)) == 3
    for row, col, expected in [
        (0, 0, "old"),
        (499999, 8000, "old"),
        (500000, 7999, "old"),
        (500000, 8000, "new"),
        (500000, 8001, "adjacent"),
        (500000, 8002, "old"),
        (999999, 15999, "old"),
    ]:
        record = updated.read_cell(locator(row, col))
        assert record["display_paragraphs"] == [expected]
        assert record["attributes"][q("table", "style-name")] == "cell"
    for name, content in book.package.parts.items():
        if name != "content.xml":
            assert updated.package.parts[name] == content
    assert updated.package.comment == book.package.comment
    assert len([c for c in receipt.changes if c["operation"] == "set_cell_value"]) == 2
    assert receipt.changes[1]["before"]["repetition"]["row_count"] == 1000000


def test_sparse_creation_clear_and_historical_input_bytes():
    original = create_native_ods(NativeODSCreate())
    book = NativeODS(original)
    changed, _ = book.edit([edit(100000, 15000, "far away")])
    assert len(changed) < 2000
    assert NativeODS(changed).read_cell(locator(100000, 15000))[
        "display_paragraphs"
    ] == ["far away"]
    assert not book.read_cell(locator(100000, 15000))["present"]
    cleared, receipt = NativeODS(changed).edit([edit(100000, 15000, None, "blank")])
    assert not NativeODS(cleared).read_cell(locator(100000, 15000))["value_attributes"]
    assert receipt.review_required and book.package.original == original


def test_rich_replacement_preserves_annotation_cell_style_and_other_cell_xml():
    data = fixture("""<table:table-row><table:table-cell table:style-name="money">
      <text:p><text:span text:style-name="bold">old</text:span></text:p>
      <office:annotation><text:p>keep comment</text:p></office:annotation></table:table-cell>
      <table:table-cell office:value-type="string"><text:p><text:span text:style-name="italic">untouched</text:span></text:p></table:table-cell>
      </table:table-row>""")
    original = NativeODS(data)
    comment = etree.tostring(original.root.find(".//office:annotation", NS))
    other = original.read_cell(locator(0, 1))
    changed, _ = original.edit([edit(value="new")])
    updated = NativeODS(changed)
    assert updated.read_cell(locator(0, 1)) == other
    assert etree.tostring(updated.root.find(".//office:annotation", NS)) == comment
    assert (
        updated.read_cell(locator())["attributes"][q("table", "style-name")] == "money"
    )


def test_formula_authoring_has_no_fabricated_result_and_clear_removes_formula():
    original = create_native_ods(NativeODSCreate())
    changed, _ = NativeODS(original).edit(
        [edit(value="=SUM([.A2:.A3])", kind="formula")]
    )
    record = NativeODS(changed).read_cell(locator())
    assert record["formula"]["namespace"] == NS["of"]
    assert not record["value_attributes"] and not record["display_paragraphs"]
    cleared, _ = NativeODS(changed).edit([edit(value=None, kind="blank")])
    assert NativeODS(cleared).read_cell(locator())["formula"] is None


@pytest.mark.parametrize(
    ("attrs", "row", "reason"),
    [
        (
            'table:protected="true"',
            "<table:table-row><table:table-cell/></table:table-row>",
            "Protected",
        ),
        (
            "",
            "<table:table-row><table:covered-table-cell/></table:table-row>",
            "Covered",
        ),
        (
            "",
            '<table:table-row><table:table-cell table:number-matrix-rows-spanned="2" table:number-matrix-columns-spanned="2"/></table:table-row>',
            "matrix",
        ),
        (
            "",
            '<table:table-row table:number-rows-repeated="2"><table:table-cell table:formula="of:=1+1"/></table:table-row>',
            "mapping-aware",
        ),
        (
            "",
            '<table:table-row table:number-rows-repeated="2"><table:table-cell xml:id="id1"/></table:table-row>',
            "mapping-aware",
        ),
        (
            "",
            '<table:table-row><table:table-cell><text:p><text:bookmark text:name="b"/>old</text:p></table:table-cell></table:table-row>',
            "text-aware",
        ),
    ],
)
def test_dependent_edits_reject_without_mutating_source(attrs, row, reason):
    original = fixture(row, table_attributes=attrs)
    book = NativeODS(original)
    with pytest.raises(ValueError, match=reason):
        book.edit([edit()])
    assert book.package.original == original


def test_wrong_locator_duplicates_and_late_failure_are_atomic():
    data = create_native_ods(NativeODSCreate())
    with pytest.raises(ValueError, match="name"):
        NativeODS(data).read_cell(locator(name="wrong"))
    with pytest.raises(ValueError, match="same cell"):
        NativeODS(data).edit([edit(), edit()])
    before = NativeODS(data).inspect()
    with pytest.raises(ValueError, match="name"):
        NativeODS(data).edit([edit(), edit(1, name="wrong")])
    assert NativeODS(data).inspect() == before


@pytest.mark.parametrize("value", ["0", "-1", "1000000000000000", "x"])
def test_invalid_repetitions_fail_bounded(value):
    data = fixture(
        f'<table:table-row table:number-rows-repeated="{value}"><table:table-cell/></table:table-row>'
    )
    with pytest.raises(ValueError, match="repetition"):
        NativeODS(data)


def test_paging_preserves_compressed_ranges_and_source_version():
    data = fixture(
        "<table:table-row>" + "<table:table-cell/>" * 5 + "</table:table-row>"
    )
    package = NativeODFPackage(data)
    root = package.xml("content.xml")
    root.set(q("office", "version"), "1.2")
    data = package.replace({"content.xml": xml_bytes(root)})
    book = NativeODS(data)
    assert book.inspect(limit=2)["next_offset"] == 2
    assert book.inspect(offset=4, limit=2)["next_offset"] is None
    changed, _ = book.edit([edit()])
    assert NativeODS(changed).inspect()["odf_version"] == "1.2"


@pytest.mark.parametrize(
    ("kind", "value", "kwargs"),
    [
        ("float", "NaN", {}),
        ("float", "inf", {}),
        ("float", 1.2, {}),
        ("boolean", "false", {}),
        ("blank", "", {}),
        ("currency", "1", {}),
        ("string", "x", {"currency": "USD"}),
        ("string", "bad\x00", {}),
        ("date", "2026-02-30", {}),
        ("time", "PT", {}),
        ("formula", "of:=1+1", {}),
    ],
)
def test_invalid_authored_values_are_not_coerced(kind, value, kwargs):
    with pytest.raises(ValidationError):
        NativeODSValue(kind=kind, value=value, **kwargs)


def test_byte_limit_prevents_xml_preservation_from_inflating_unbounded_evidence():
    data = fixture(
        '<table:table-row><table:table-cell><text:p><text:s text:c="999999999"/></text:p></table:table-cell></table:table-row>'
    )
    with pytest.raises(ValueError, match="space count"):
        NativeODS(data).read_cell(locator())


def test_existing_rich_value_noop_does_not_flatten_runs():
    data = fixture(
        '<table:table-row><table:table-cell office:value-type="string"><text:p><text:span text:style-name="bold">old</text:span></text:p></table:table-cell></table:table-row>'
    )
    before = copy.deepcopy(NativeODS(data).read_cell(locator()))
    result, receipt = NativeODS(data).edit([edit(value="old")])
    assert result == data and not receipt.changes
    assert NativeODS(result).read_cell(locator()) == before


def test_formula_cache_invalidation_preserves_expression_display_and_style():
    data = fixture("""<table:table-row><table:table-cell office:value-type="float" office:value="3.43"/>
      <table:table-cell office:value-type="float" office:value="6.86" table:style-name="currency" table:formula="local:=[.A1]*2" xmlns:local="urn:oasis:names:tc:opendocument:xmlns:of:1.2"><text:p text:style-name="keep"><text:span text:style-name="bold">6.86</text:span></text:p></table:table-cell></table:table-row>""")
    before = NativeODS(data).read_cell(locator(0, 1))
    changed, receipt = NativeODS(data).edit([edit(value="5.75", kind="float")])
    after = NativeODS(changed).read_cell(locator(0, 1))
    assert after["formula"] == before["formula"]
    assert not after["value_attributes"] and not after["cached_value_verified"]
    assert after["display_paragraphs"] == before["display_paragraphs"]
    assert 'text:style-name="bold"' in after["native_xml"]
    assert after["attributes"][q("table", "style-name")] == "currency"
    assert receipt.repairs == [
        "invalidated_typed_formula_caches",
        "extended_column_declarations",
    ]
    assert len(receipt.changes) == 3
    assert receipt.changes[1]["operation"] == "invalidate_typed_formula_cache"
    noop, result = NativeODS(data).edit([edit(value="3.43", kind="float")])
    assert noop == data and not result.repairs


def test_merge_coordinates_cannot_be_created_when_covered_elements_are_missing():
    data = fixture(
        '<table:table-row><table:table-cell table:number-columns-spanned="2" table:number-rows-spanned="2"/></table:table-row>'
    )
    for row, column in [(0, 1), (1, 0), (1, 1)]:
        with pytest.raises(ValueError, match="Covered"):
            NativeODS(data).edit([edit(row, column)])
    changed, _ = NativeODS(data).edit([edit()])
    assert (
        NativeODS(changed).read_cell(locator())["attributes"][
            q("table", "number-columns-spanned")
        ]
        == "2"
    )


@pytest.mark.parametrize("inherited", [False, True])
def test_alias_used_inside_repeated_attribute_is_never_silently_dropped(inherited):
    data = fixture(
        '<table:table-row table:number-rows-repeated="2"><table:table-cell xmlns:alias="urn:oasis:names:tc:opendocument:xmlns:of:1.2" xmlns:custom="urn:test" custom:binding="alias:value"/></table:table-row>'
    )
    if inherited:
        package = NativeODFPackage(data)
        binding = b'xmlns:alias="urn:oasis:names:tc:opendocument:xmlns:of:1.2"'
        content = (
            package.parts["content.xml"]
            .replace(binding, b"")
            .replace(
                b"<office:document-content ",
                b"<office:document-content " + binding + b" ",
            )
        )
        data = package.replace({"content.xml": content})
    try:
        result, _ = NativeODS(data).edit([edit()])
    except ValueError as exc:
        assert "namespace binding" in str(exc)
    else:
        for cell in NativeODS(result).root.findall(".//table:table-cell", NS):
            assert cell.nsmap.get("alias") == NS["of"]
