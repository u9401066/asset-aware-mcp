"""Named pivot sources and chart caches are dependencies even without changed A1 text."""

import pytest
from lxml import etree

from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_ooxml import DOC_REL_NS, REL_NS, TYPE_NS
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_grid import NativeWorkbookGrid
from tests.native_grid_helpers import table_workbook
from tests.native_workbook_helpers import _parts, _replace, build_workbook
from tests.unit.test_native_workbook_grid import request, root

CACHE = "xl/pivotCache/pivotCacheDefinition1.xml"
LOCATION = "xl/pivotTables/pivotTable1.xml"


def with_pivot_source(source, *, external=False):
    workbook = root(source, "xl/workbook.xml")
    container = etree.SubElement(workbook, tag("pivotCaches"))
    etree.SubElement(
        container,
        tag("pivotCache"),
        cacheId="1",
        **{f"{{{DOC_REL_NS}}}id": "gridPivot"},
    )
    relationships = root(source, "xl/_rels/workbook.xml.rels")
    etree.SubElement(
        relationships,
        f"{{{REL_NS}}}Relationship",
        Id="gridPivot",
        Type=DOC_REL_NS + "/pivotCacheDefinition",
        Target="pivotCache/pivotCacheDefinition1.xml",
    )
    cache = etree.Element(
        tag("pivotCacheDefinition"),
        nsmap={None: NS["s"]},
        refreshOnLoad="0",
        invalid="0",
    )
    cache_source = etree.SubElement(cache, tag("cacheSource"), type="worksheet")
    worksheet = etree.SubElement(cache_source, tag("worksheetSource"), name="Table1")
    fields = etree.SubElement(cache, tag("cacheFields"), count="3")
    for name in ("Input", "Calc", "Label"):
        etree.SubElement(fields, tag("cacheField"), name=name)
    types = root(source, "[Content_Types].xml")
    etree.SubElement(
        types,
        f"{{{TYPE_NS}}}Override",
        PartName="/" + CACHE,
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheDefinition+xml",
    )
    replacements = {
        "xl/workbook.xml": etree.tostring(workbook),
        "xl/_rels/workbook.xml.rels": etree.tostring(relationships),
        "[Content_Types].xml": etree.tostring(types),
    }
    if external:
        worksheet.set(f"{{{DOC_REL_NS}}}id", "outside")
        rels = etree.Element(f"{{{REL_NS}}}Relationships", nsmap={None: REL_NS})
        etree.SubElement(
            rels,
            f"{{{REL_NS}}}Relationship",
            Id="outside",
            Type=DOC_REL_NS + "/externalLinkPath",
            Target="file:///outside.xlsx",
            TargetMode="External",
        )
        replacements["xl/pivotCache/_rels/pivotCacheDefinition1.xml.rels"] = (
            etree.tostring(rels)
        )
    replacements[CACHE] = etree.tostring(cache)
    return _replace(source, replacements)


def test_named_table_row_change_invalidates_pivot_cache_even_without_changed_source_text():
    updated, result = NativeWorkbookGrid().update(
        with_pivot_source(table_workbook()),
        request({"axis": "row", "operation": "insert", "at": 4}),
    )
    cache = root(updated, CACHE)
    assert cache.get("invalid") == cache.get("refreshOnLoad") == "1"
    assert cache.find("s:cacheSource/s:worksheetSource", NS).get("name") == "Table1"
    assert result.changes[0]["edits"][0]["invalidated_named_source_caches"] == [CACHE]


def test_pivot_backed_table_columns_require_coordinated_cache_fields():
    with pytest.raises(ValueError, match="cache field identities"):
        NativeWorkbookGrid().update(
            with_pivot_source(table_workbook()),
            request({"axis": "column", "operation": "delete", "at": 1}),
        )


def test_external_same_named_table_does_not_block_local_deletion_or_invalidate_external_cache():
    source = with_pivot_source(table_workbook(), external=True)
    updated, _ = NativeWorkbookGrid().update(
        source, request({"axis": "row", "operation": "delete", "at": 2, "count": 4})
    )
    assert _parts(updated)[CACHE] == _parts(source)[CACHE]
    assert root(updated).find("s:tableParts", NS) is None


def test_chart_table_reference_clears_cached_values_when_table_grows():
    source = build_workbook()
    chart = root(source, "xl/charts/chart1.xml")
    ns = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
    chart.find(".//c:f", ns).text = "Table1[First]"
    source = _replace(source, {"xl/charts/chart1.xml": etree.tostring(chart)})
    updated, result = NativeWorkbookGrid().update(
        source, request({"axis": "row", "operation": "insert", "at": 9})
    )
    after = root(updated, "xl/charts/chart1.xml")
    assert after.find(".//c:f", ns).text == "Table1[First]"
    assert not after.findall(".//c:numCache", ns)
    assert result.changes[0]["cleared_remaining_chart_caches"] >= 1


def with_pivot_location():
    source = table_workbook()
    rels = root(source, "xl/worksheets/_rels/sheet1.xml.rels")
    etree.SubElement(
        rels,
        f"{{{REL_NS}}}Relationship",
        Id="pivotResult",
        Type=DOC_REL_NS + "/pivotTable",
        Target="../pivotTables/pivotTable1.xml",
    )
    pivot = etree.Element(
        tag("pivotTableDefinition"),
        nsmap={None: NS["s"]},
        name="Pivot1",
        cacheId="1",
        dataCaption="Values",
    )
    etree.SubElement(
        pivot,
        tag("location"),
        ref="H10:J14",
        firstHeaderRow="1",
        firstDataRow="2",
        firstDataCol="1",
    )
    return _replace(
        source,
        {
            "xl/worksheets/_rels/sheet1.xml.rels": etree.tostring(rels),
            LOCATION: etree.tostring(pivot),
        },
    )


def test_whole_pivot_location_moves_without_reinterpreting_relative_result_offsets():
    updated, _ = NativeWorkbookGrid().update(with_pivot_location(), request())
    location = root(updated, LOCATION).find("s:location", NS)
    assert dict(location.attrib) == {
        "ref": "H11:J15",
        "firstHeaderRow": "1",
        "firstDataRow": "2",
        "firstDataCol": "1",
    }
    with pytest.raises(ValueError, match="pivot result"):
        NativeWorkbookGrid().update(
            with_pivot_location(),
            request({"axis": "row", "operation": "delete", "at": 12}),
        )
