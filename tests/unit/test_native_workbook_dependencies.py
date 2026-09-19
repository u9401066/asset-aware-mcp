"""Surviving cross-part references, external sources and structural guard cases."""

import io

import pytest
import xlsxwriter
from lxml import etree

from src.domain.native_workbook import NativeWorksheetInsert, NativeWorksheetRename
from src.infrastructure.native_ooxml import DOC_REL_NS, REL_NS, SHEET_NS, xml_bytes
from tests.native_workbook_helpers import _parts, _replace, build_workbook
from tests.unit.test_native_workbook_structure import ADAPTER, NS, keys


def with_pivot(source, *, attribute="sheet", value="Data", external=False):
    rels = etree.fromstring(_parts(source)["xl/_rels/workbook.xml.rels"])
    etree.SubElement(
        rels,
        f"{{{REL_NS}}}Relationship",
        Id="pivot",
        Type=f"{DOC_REL_NS}/pivotCacheDefinition",
        Target="pivotCache/test.xml",
    )
    root = etree.Element(
        f"{{{SHEET_NS}}}pivotCacheDefinition", nsmap={None: SHEET_NS, "r": DOC_REL_NS}
    )
    cache = etree.SubElement(root, f"{{{SHEET_NS}}}cacheSource", type="worksheet")
    node = etree.SubElement(
        cache, f"{{{SHEET_NS}}}worksheetSource", **{attribute: value}
    )
    replacements = {"xl/_rels/workbook.xml.rels": xml_bytes(rels)}
    if external:
        node.set(f"{{{DOC_REL_NS}}}id", "external")
        links = etree.Element(f"{{{REL_NS}}}Relationships", nsmap={None: REL_NS})
        etree.SubElement(
            links,
            f"{{{REL_NS}}}Relationship",
            Id="external",
            Type=f"{DOC_REL_NS}/externalLinkPath",
            Target="https://example.com/book.xlsx",
            TargetMode="External",
        )
        replacements["xl/pivotCache/_rels/test.xml.rels"] = xml_bytes(links)
    replacements["xl/pivotCache/test.xml"] = xml_bytes(root)
    return _replace(source, replacements)


def without_other_formula(source):
    root = etree.fromstring(_parts(source)["xl/worksheets/sheet2.xml"])
    formula = root.find(".//s:f", NS)
    formula.getparent().remove(formula)
    return _replace(source, {"xl/worksheets/sheet2.xml": xml_bytes(root)})


@pytest.mark.parametrize("attribute,value", [("sheet", "Data"), ("name", "Table1")])
def test_surviving_pivot_blocks_sheet_or_table_deletion(attribute, value):
    source = with_pivot(
        without_other_formula(build_workbook()), attribute=attribute, value=value
    )
    with pytest.raises(ValueError, match="pivot cache"):
        ADAPTER.delete(source, [keys(source)[0]])


def test_pivot_rename_updates_local_but_preserves_external_workbook():
    for external in (False, True):
        source = with_pivot(build_workbook(), external=external)
        updated, _ = ADAPTER.rename(
            source, NativeWorksheetRename(key=keys(source)[0], name="新表")
        )
        root = etree.fromstring(_parts(updated)["xl/pivotCache/test.xml"])
        assert root.find(".//s:worksheetSource", NS).get("sheet") == (
            "Data" if external else "新表"
        )


def test_consolidation_reference_is_renamed_and_blocks_deletion():
    source = without_other_formula(build_workbook())
    root = etree.fromstring(_parts(source)["xl/worksheets/sheet2.xml"])
    consolidate = etree.SubElement(root, f"{{{SHEET_NS}}}dataConsolidate")
    refs = etree.SubElement(consolidate, f"{{{SHEET_NS}}}dataRefs", count="1")
    etree.SubElement(refs, f"{{{SHEET_NS}}}dataRef", sheet="Data", ref="A1:A3")
    source = _replace(source, {"xl/worksheets/sheet2.xml": xml_bytes(root)})
    with pytest.raises(ValueError, match="consolidated range"):
        ADAPTER.delete(source, [keys(source)[0]])
    updated, _ = ADAPTER.rename(
        source, NativeWorksheetRename(key=keys(source)[0], name="新表")
    )
    inventory = ADAPTER.read(updated, references=True)["references"]
    assert any(
        item["kind"] == "consolidation_source" and item["text"] == "新表"
        for item in inventory
    )


@pytest.mark.parametrize(
    "formula", ["SUM(Table1[First])", "SUM(Table1)", "Table1[#All]"]
)
def test_whole_table_and_column_dependencies_block_deletion(formula):
    source = build_workbook()
    root = etree.fromstring(_parts(source)["xl/worksheets/sheet2.xml"])
    root.find(".//s:f", NS).text = formula
    source = _replace(source, {"xl/worksheets/sheet2.xml": xml_bytes(root)})
    with pytest.raises(ValueError, match="structured reference"):
        ADAPTER.delete(source, [keys(source)[0]])


def test_rename_rewrites_names_hyperlinks_validation_and_conditional_formats():
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        data, other = book.add_worksheet("Data"), book.add_worksheet("Other")
        data.write("A1", 7)
        book.define_name("Named", "=Data!$A$1")
        other.write_url("A1", "internal:Data!A1")
        other.data_validation("A2", {"validate": "list", "source": "=Data!$A$1:$A$2"})
        other.conditional_format(
            "A3",
            {
                "type": "formula",
                "criteria": "=Data!A1>0",
                "format": book.add_format({"bold": True}),
            },
        )
        other.write_formula("A4", '=INDIRECT("Data!A1")')
        other.write_formula("A5", "='[outside.xlsx]Data'!A1")
    source = output.getvalue()
    updated, _ = ADAPTER.rename(
        source, NativeWorksheetRename(key=keys(source)[0], name="O'Brien")
    )
    refs = ADAPTER.read(updated, references=True)["references"]
    texts = {item["text"] for item in refs}
    assert {
        "'O''Brien'!$A$1",
        "'O''Brien'!A1",
        "'O''Brien'!$A$1:$A$2",
        "'O''Brien'!A1>0",
        'INDIRECT("Data!A1")',
        "'[outside.xlsx]Data'!A1",
    } <= texts


def test_delete_last_visible_and_identity_mismatch_fail():
    source = without_other_formula(build_workbook())
    root = etree.fromstring(_parts(source)["xl/workbook.xml"])
    root.find("s:sheets", NS)[1].set("state", "hidden")
    source = _replace(source, {"xl/workbook.xml": xml_bytes(root)})
    with pytest.raises(ValueError, match="visible worksheet"):
        ADAPTER.delete(source, [keys(source)[0]])
    wrong = keys(source)[0].model_copy(update={"part": keys(source)[1].part})
    with pytest.raises(ValueError, match="exact workbook revision"):
        ADAPTER.rename(source, NativeWorksheetRename(key=wrong, name="Renamed"))
    with pytest.raises(ValueError, match="all current keys"):
        ADAPTER.reorder(source, [keys(source)[0]])
    with pytest.raises(ValueError, match="already exists"):
        ADAPTER.add(source, NativeWorksheetInsert(index=0, names=["DATA"]))


@pytest.mark.parametrize(
    "relation",
    ["vbaProject", "revisionLog", "activeXControl", "digital-signature/signature"],
)
def test_unsupported_relationship_guards(relation):
    source = build_workbook()
    root = etree.fromstring(_parts(source)["xl/_rels/workbook.xml.rels"])
    etree.SubElement(
        root,
        f"{{{REL_NS}}}Relationship",
        Id="unsupported",
        Type=f"{DOC_REL_NS}/{relation}",
        Target="unsupported.bin",
    )
    source = _replace(
        source,
        {
            "xl/_rels/workbook.xml.rels": xml_bytes(root),
            "xl/unsupported.bin": b"preserve",
        },
    )
    with pytest.raises(ValueError, match="block sheet structure"):
        ADAPTER.add(source, NativeWorksheetInsert(index=0, names=["Added"]))
