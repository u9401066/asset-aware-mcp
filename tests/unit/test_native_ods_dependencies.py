"""Cross-part native dependency owners, exact plans and unresolved deletion policy."""

from dataclasses import replace

import pytest
from lxml import etree

from src.domain.native_ods import NativeODSTableRename
from src.domain.native_ods_references import ODSAxisEdit, ODSSheetDelete, ODSSheetRename
from src.infrastructure.native_odf_package import NS, q, xml_bytes
from src.infrastructure.native_ods_dependencies import ODSDependencies
from src.infrastructure.native_ods_reader import NativeODSReader
from src.infrastructure.native_ods_structure import rename_ods_table
from tests.native_ods_helpers import fixture


def source(
    *,
    chart_parent="..",
    formula="of:=SUM([Sheet1.A1:.A3])+LEN(&quot;[Sheet1.A1]&quot;)",
):
    declarations = " ".join(f'xmlns:{key}="{value}"' for key, value in NS.items())
    chart = f'''<office:document-content {declarations}
      xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0"
      xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
      xmlns:xlink="http://www.w3.org/1999/xlink">
      <office:body><office:chart><chart:chart xlink:href="{chart_parent}">
      <chart:plot-area table:cell-range-address="Sheet1.A1:Sheet1.B4">
      <chart:categories table:cell-range-address="Sheet1.A2:Sheet1.A4"/>
      <chart:series chart:values-cell-range-address="Sheet1.B2:Sheet1.B4"/></chart:plot-area>
      <table:table table:name="Sheet1"><table:table-row><table:table-cell table:formula="of:=[.A1]">
      <draw:g><svg:desc>Sheet1.B2:Sheet1.B4</svg:desc></draw:g>
      <text:p text:id="Sheet1.A1:Sheet1.A4">cached label</text:p>
      <draw:frame><svg:desc>Sheet1.A1 is a caption</svg:desc></draw:frame>
      </table:table-cell></table:table-row></table:table>
      </chart:chart></office:chart></office:body></office:document-content>'''
    styles = f"""<office:document-styles {declarations}><office:styles>
      <style:style style:name="conditional" style:family="table-cell">
      <style:map style:condition="is-true-formula([Sheet1.A1]&gt;0)" style:base-cell-address="Sheet1.A1"/>
      </style:style></office:styles></office:document-styles>"""
    settings = f"""<office:document-settings {declarations}><office:settings>
      <config:config-item-map-named config:name="Tables"><config:config-item-map-entry config:name="Sheet1"/></config:config-item-map-named>
      <config:config-item-map-named config:name="ScriptConfiguration"><config:config-item-map-entry config:name="Sheet1"><config:config-item config:name="CodeName" config:type="string">StableCodeName</config:config-item></config:config-item-map-entry></config:config-item-map-named>
      <config:config-item config:name="ActiveTable" config:type="string">Sheet1</config:config-item>
      <config:config-item-map-named config:name="Unrelated"><config:config-item-map-entry config:name="Sheet1"/></config:config-item-map-named>
      </office:settings></office:document-settings>"""
    data = fixture(
        f'''<table:table-row><table:table-cell table:formula="{formula}"/></table:table-row>
        <table:named-expressions><table:named-range table:name="Values" table:base-cell-address="$Sheet1.$A$1" table:cell-range-address="$Sheet1.$A$2:.$B$4"/>
        <table:named-expression table:name="Total" table:base-cell-address="$Sheet1.$A$1" table:expression="SUM([$Sheet1.$A$2:.$B$4])"/></table:named-expressions>
        <table:shapes><draw:frame><draw:object draw:notify-on-update-of-ranges="Sheet1.A1:Sheet1.A1  Sheet1.B2:Sheet1.B4"/></draw:frame></table:shapes>''',
        table_attributes='table:print-ranges="Sheet1.A1:Sheet1.B4"',
        extras={
            "styles.xml": styles.encode(),
            "settings.xml": settings.encode(),
            "Chart/content.xml": chart.encode(),
            "kept.bin": b"unchanged",
        },
    )
    book = NativeODSReader(data)
    manifest = book.package.xml("META-INF/manifest.xml")
    item = etree.SubElement(manifest, q("manifest", "file-entry"))
    item.set(q("manifest", "full-path"), "Chart/")
    item.set(q("manifest", "media-type"), "application/vnd.oasis.opendocument.chart")
    return NativeODSReader(
        book.package.replace({"META-INF/manifest.xml": xml_bytes(manifest)})
    )


def rename_request(book, **changes):
    return NativeODSTableRename(
        **{
            "table_index": 0,
            "table_name": "Sheet1",
            "new_name": "New 中文 O'Brien",
            "dependencies_sha256": ODSDependencies(book).catalog()["inventory_sha256"],
            **changes,
        }
    )


def test_transaction_preserves_repetition_style_package_and_scopes_cache_receipts():
    book = source()
    row = book.tables[0].find(q("table", "table-row"))
    row.set(q("table", "number-rows-repeated"), "1000")
    cell = row.find(q("table", "table-cell"))
    cell.set(q("table", "number-columns-repeated"), "200")
    cell.set(q("table", "style-name"), "conditional")
    cell.set(q("office", "value-type"), "float")
    cell.set(q("office", "value"), "42")
    etree.SubElement(cell, q("text", "p")).text = "42"
    original = book.package.replace({"content.xml": xml_bytes(book.root)})
    book = NativeODSReader(original)
    changed, report = rename_ods_table(original, rename_request(book))
    output = NativeODSReader(changed)
    assert report.changed_parts == [
        "Chart/content.xml",
        "content.xml",
        "settings.xml",
        "styles.xml",
    ]
    for part in set(book.package.parts) - set(report.changed_parts):
        assert output.package.parts[part] == book.package.parts[part]
    assert output.tables[0].get(q("table", "name")) == "New 中文 O'Brien"
    row_after = output.tables[0].find(q("table", "table-row"))
    assert dict(row_after.attrib) == dict(row.attrib) and len(row_after) == 1
    cell_after = row_after[0]
    assert cell_after.get(q("table", "number-columns-repeated")) == "200"
    assert cell_after.get(q("table", "style-name")) == "conditional"
    assert cell_after.get(q("office", "value")) is None
    assert cell_after.find(q("text", "p")).text == "42"  # Unverified display.
    assert cell_after.get(q("table", "formula")) == (
        "of:=SUM(['New 中文 O''Brien'.A1:.A3])+LEN(\"[Sheet1.A1]\")"
    )
    cache = report.changes[-1]
    assert cache["operation"] == "invalidate_typed_formula_cache"
    assert cache["record_scope"] == "after_dependency_mapping_and_table_rename"
    assert cache["locator"]["table_name"] == "New 中文 O'Brien"
    assert cache["before"]["value_attributes"]["value"] == "42"
    assert cache["after"]["value_attributes"] == {}
    assert cache["before"]["repetition"] == cache["after"]["repetition"]
    assert book.package.original == original
    assert (
        report.changes[0]["dependencies_after_sha256"]
        == (ODSDependencies(output).catalog()["inventory_sha256"])
    )


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"table_index": 1}, "index is absent"),
        ({"table_name": "wrong"}, "original index"),
        ({"dependencies_sha256": "0" * 64}, "inventory changed"),
    ],
)
def test_transaction_checks_original_identity_and_inventory(changes, error):
    book = source()
    original = book.package.original
    with pytest.raises(ValueError, match=error):
        rename_ods_table(original, rename_request(book, **changes))
    assert book.package.original == original


@pytest.mark.parametrize(
    "guard", ["structure", "table", "dependent", "opaque", "collision"]
)
def test_transaction_protection_and_unresolved_owners_fail_without_returning_output(
    guard,
):
    book = source()
    if guard == "structure":
        book.body.set(q("table", "structure-protected"), "true")
    elif guard == "table":
        book.tables[0].set(q("table", "protected"), "1")
    elif guard == "dependent":
        book.tables[0].find(".//table:table-cell", NS).set(
            q("table", "protected"), "true"
        )
    elif guard == "opaque":
        etree.SubElement(book.tables[0], q("draw", "object-ole"))
    else:
        etree.SubElement(
            book.body, q("table", "table"), {q("table", "name"): "NEW 中文 O'BRIEN"}
        )
    data = book.package.replace({"content.xml": xml_bytes(book.root)})
    with pytest.raises(ValueError, match=r"Protected|unresolved|collides"):
        rename_ods_table(data, rename_request(NativeODSReader(data)))


def test_transaction_noop_keeps_original_zip_bytes_and_no_cache_change():
    book = source()
    changed, report = rename_ods_table(
        book.package.original, rename_request(book, new_name="Sheet1")
    )
    assert changed == book.package.original
    assert not report.changes and not report.changed_parts and not report.repairs


def test_rename_maps_all_native_parts_and_keeps_chart_local_coordinates():
    book = source()
    dependencies = ODSDependencies(book)
    plan = dependencies.plan(ODSSheetRename("Sheet1", "New 中文 O'Brien"))
    assert not plan.unresolved
    assert {c.dependency.part for c in plan.changes} == {
        "content.xml",
        "styles.xml",
        "settings.xml",
        "Chart/content.xml",
    }
    records = dependencies.apply(plan)
    assert records and all(record["original_unicode_spans"] for record in records)
    for record in records:
        before = record["before"]["value"]
        for span in record["original_unicode_spans"]:
            assert before[span["start"] : span["end"]] == span["before"]
    chart = dependencies.roots["Chart/content.xml"]
    local = chart.find(".//table:table-cell", NS)
    assert local is not None and local.get(q("table", "formula")) == "of:=[.A1]"
    desc = local.find(
        "draw:g/{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}desc", NS
    )
    assert (
        desc is not None
        and desc.text == "'New 中文 O''Brien'.B2:'New 中文 O''Brien'.B4"
    )
    paragraph = local.find(q("text", "p"))
    assert (
        paragraph is not None
        and paragraph.get(q("text", "id"))
        == "'New 中文 O''Brien'.A1:'New 中文 O''Brien'.A4"
    )
    caption = local.find(
        "draw:frame/{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}desc", NS
    )
    assert caption is not None and caption.text == "Sheet1.A1 is a caption"
    assert 'LEN("[Sheet1.A1]")' in book.tables[0].find(".//table:table-cell", NS).get(
        q("table", "formula")
    )
    settings = dependencies.roots["settings.xml"]
    unrelated = settings.xpath(
        "//config:config-item-map-named[@config:name='Unrelated']/config:config-item-map-entry",
        namespaces=NS,
    )[0]
    assert unrelated.get(q("config", "name")) == "Sheet1"
    script_entry = settings.xpath(
        "//config:config-item-map-named[@config:name='ScriptConfiguration']/config:config-item-map-entry",
        namespaces=NS,
    )[0]
    assert script_entry.get(q("config", "name")) == "New 中文 O'Brien"
    assert script_entry[0].text == "StableCodeName"
    book.tables[0].set(q("table", "name"), "New 中文 O'Brien")
    replacements = dependencies.replacements()
    reopened = NativeODSReader(book.package.replace(replacements))
    assert reopened.tables[0].get(q("table", "name")) == "New 中文 O'Brien"
    assert reopened.package.parts["kept.bin"] == b"unchanged"
    assert (
        not ODSDependencies(reopened)
        .plan(ODSSheetRename("New 中文 O'Brien", "Next"))
        .unresolved
    )


@pytest.mark.parametrize("chart_parent", ["", ".", "./"])
def test_embedded_chart_without_parent_data_is_a_separate_coordinate_space(
    chart_parent,
):
    book = source(chart_parent=chart_parent)
    dependencies = ODSDependencies(book)
    plan = dependencies.plan(ODSSheetRename("Sheet1", "Renamed"))
    assert not plan.unresolved
    assert not any(c.dependency.part == "Chart/content.xml" for c in plan.changes)
    dependencies.apply(plan)
    assert "Chart/content.xml" not in dependencies.replacements()


def test_deletion_reports_owners_instead_of_rebinding_chart_to_another_sheet():
    book = source()
    dependencies = ODSDependencies(book)
    before = {name: xml_bytes(root) for name, root in dependencies.roots.items()}
    plan = dependencies.plan(ODSSheetDelete("Sheet1"))
    assert any(
        issue.get("dependency", {}).get("part") == "Chart/content.xml"
        for issue in plan.unresolved
    )
    with pytest.raises(ValueError, match="every ODS dependency"):
        dependencies.apply(plan)
    assert before == {
        name: xml_bytes(root) for name, root in dependencies.roots.items()
    }


@pytest.mark.parametrize("change", ["after", "missing", "duplicate"])
def test_forged_or_partial_plans_fail_before_any_native_edit(change):
    dependencies = ODSDependencies(source())
    plan = dependencies.plan(ODSSheetRename("Sheet1", "New"))
    before = {name: xml_bytes(root) for name, root in dependencies.roots.items()}
    if change == "after":
        plan = replace(
            plan, changes=(replace(plan.changes[0], after="forged"), *plan.changes[1:])
        )
    elif change == "missing":
        plan = replace(plan, changes=plan.changes[1:])
    else:
        plan = replace(plan, changes=(*plan.changes, plan.changes[0]))
    with pytest.raises(ValueError, match=r"modified|duplicate"):
        dependencies.apply(plan)
    assert before == {
        name: xml_bytes(root) for name, root in dependencies.roots.items()
    }


def test_unrelated_xml_changes_also_stale_a_dependency_plan():
    book = source()
    dependencies = ODSDependencies(book)
    plan = dependencies.plan(ODSSheetRename("Sheet1", "New"))
    book.tables[0].set(q("table", "style-name"), "edited-after-inspection")
    with pytest.raises(ValueError, match="XML changed"):
        dependencies.apply(plan)
    assert (
        book.tables[0]
        .find(".//table:table-cell", NS)
        .get(q("table", "formula"))
        .startswith("of:=SUM([Sheet1.")
    )


def test_relative_named_ranges_require_base_and_usage_context_for_axis_edits():
    book = source()
    target = book.root.find(".//table:named-range", NS)
    assert target is not None
    target.set(q("table", "cell-range-address"), "Sheet1.A2:.B4")
    dependencies = ODSDependencies(book)
    plan = dependencies.plan(ODSAxisEdit("Sheet1", "rows", "delete", 1, 3))
    assert any("base/usage-aware" in issue["reason"] for issue in plan.unresolved)


def test_literal_and_external_references_are_not_replaced():
    book = source(
        formula="of:=[&apos;other.ods&apos;#Sheet1.A1]+LEN(&quot;Sheet1.A1&quot;)"
    )
    dependencies = ODSDependencies(book)
    plan = dependencies.plan(ODSSheetRename("Sheet1", "New"))
    assert not plan.unresolved
    assert not any(c.dependency.kind == "formula" for c in plan.changes)


@pytest.mark.parametrize(
    "formula,reason",
    [
        ("other:=[Sheet1.A1]", "namespace"),
        ("of:=[sheet1.A1]", "alias/identity"),
        ("of:=[&apos;&apos;#Sheet1.A1]", "source resolver"),
    ],
)
def test_unresolved_namespace_alias_and_same_source_are_explicit(formula, reason):
    plan = ODSDependencies(source(formula=formula)).plan(
        ODSSheetRename("Sheet1", "New")
    )
    assert any(reason in item["reason"] for item in plan.unresolved)


def test_unknown_dependency_namespace_is_not_silently_retained():
    book = source()
    book.tables[0].set("{urn:unmodeled}cell-range-address", "Sheet1.A1")
    plan = ODSDependencies(book).plan(ODSSheetRename("Sheet1", "New"))
    assert any("Unknown dependency" in item["reason"] for item in plan.unresolved)


def test_quoted_address_lists_keep_exact_whitespace_and_original_spans():
    book = source()
    dependencies = ODSDependencies(book)
    first = dependencies.plan(ODSSheetRename("Sheet1", "A B"))
    dependencies.apply(first)
    book.tables[0].set(q("table", "name"), "A B")
    data = book.package.replace(dependencies.replacements())
    second = ODSDependencies(NativeODSReader(data)).plan(ODSSheetRename("A B", "C D"))
    change = next(
        c
        for c in second.changes
        if c.dependency.kind == "addresses"
        and c.dependency.attribute == q("draw", "notify-on-update-of-ranges")
    )
    assert change.after == "'C D'.A1:'C D'.A1  'C D'.B2:'C D'.B4"
    assert len(change.spans) == 2
