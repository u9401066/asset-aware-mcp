"""Cache receipts require bounded physical traversal and retain every native value."""

import hashlib
import json

import pytest

from src.infrastructure import native_ods_editor, native_ods_grid, native_ods_reader
from src.infrastructure.native_ods import NativeODS
from tests.native_ods_helpers import edit, fixture
from tests.native_operation_results_artifact_smoke import formula_source


@pytest.mark.parametrize(
    "formula_count,output_sha,receipt_sha",
    [
        (
            200,
            "56d077c861b2b1b982c61d4be7496d5e9308fa7c660b292881860a264eb3a33f",
            "447e3e2576fb490dd3d98d429dce78104bc80f68736b45c64aa9bbb158ff0f36",
        ),
        (
            400,
            "a1bfebed1a53ae11db39ded59395a32bfe01540eaf34c64ffc43107d4055d0af",
            "5a18c4ac12de83e2a70a8a7dbe4ecb8d2ab4e122d63c90d14b9f976e875f0436",
        ),
    ],
)
def test_cache_receipts_do_not_rescan_the_prefix_for_every_formula(
    formula_count, output_sha, receipt_sha, monkeypatch
):
    original = formula_source(formula_count)
    visits = 0
    walk = native_ods_reader.rows

    def measured(table):
        nonlocal visits
        for record in walk(table):
            visits += 1
            yield record

    for module in (native_ods_reader, native_ods_editor, native_ods_grid):
        monkeypatch.setattr(module, "rows", measured)
    changed, receipt = NativeODS(original).edit([edit(value="3", kind="float")])
    caches = [
        c for c in receipt.changes if c["operation"] == "invalidate_typed_formula_cache"
    ]
    assert len(caches) == formula_count
    assert changed != original
    canonical = json.dumps(
        receipt.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    # Captured from published 5093031 before changing traversal. These pin every
    # output byte and complete receipt field, not a shortened performance summary.
    assert hashlib.sha256(changed).hexdigest() == output_sha
    assert hashlib.sha256(canonical).hexdigest() == receipt_sha
    for row, cache in enumerate(caches, 1):
        assert cache["locator"]["row"] == row
        assert cache["before"]["value_attributes"]["value"] == "2"
        assert cache["after"]["value_attributes"] == {}
        assert cache["before"]["formula"] == cache["after"]["formula"]
    # Count real physical records visited, not elapsed time or function-call
    # counts. Repeated prefix scans violate this bound even on fast CI machines.
    assert visits <= 24 * (formula_count + 1), visits


def test_grouped_repeated_formula_ranges_keep_exact_locators_and_namespaces():
    original = fixture("""
      <table:table-header-rows><table:table-row><table:table-cell office:value-type="float" office:value="1"><text:p>1</text:p></table:table-cell></table:table-row></table:table-header-rows>
      <table:table-row-group>
        <table:table-row table:number-rows-repeated="1000">
          <table:table-cell table:number-columns-repeated="300" table:style-name="keep" office:value-type="float" office:value="2" table:formula="計算:=[.A1]*2" xmlns:計算="urn:oasis:names:tc:opendocument:xmlns:of:1.2"><text:p><text:span text:style-name="rich">cached 中文😀</text:span></text:p></table:table-cell>
          <table:table-cell office:value-type="boolean" office:boolean-value="true" table:formula="of:=[.A1]&gt;0"><text:p>TRUE</text:p></table:table-cell>
        </table:table-row>
        <table:table-rows><table:table-row><table:table-cell table:number-columns-repeated="299"/><table:table-cell office:value-type="string" office:string-value="old" table:formula="of:=IF([.A1]&gt;0;&quot;old&quot;;&quot;new&quot;)"><text:p>old</text:p></table:table-cell></table:table-row></table:table-rows>
      </table:table-row-group>""")
    changed, result = NativeODS(original).edit([edit(value="3", kind="float")])
    before, after = NativeODS(original), NativeODS(changed)
    caches = [
        c for c in result.changes if c["operation"] == "invalidate_typed_formula_cache"
    ]
    assert len(caches) == 3
    expected = [(1, 0, 1000, 300), (1, 300, 1000, 1), (1001, 299, 1, 1)]
    for change, (row, column, height, width) in zip(caches, expected, strict=True):
        locator = edit(row, column).locator
        assert change["locator"] == locator.model_dump()
        assert change["before"] == before.read_cell(locator)
        assert change["after"] == after.read_cell(locator)
        assert (
            change["before"]["repetition"]
            == change["after"]["repetition"]
            == {
                "row_start": row,
                "row_count": height,
                "column_start": column,
                "column_count": width,
            }
        )
        assert change["before"]["formula"] == change["after"]["formula"]
        assert (
            change["before"]["display_paragraphs"]
            == change["after"]["display_paragraphs"]
        )
    assert caches[0]["after"]["formula"]["lexical"].startswith("計算:")
    assert caches[0]["after"]["display_paragraphs"] == ["cached 中文😀"]
    assert after.inspect()["total_physical_records"] == 5
