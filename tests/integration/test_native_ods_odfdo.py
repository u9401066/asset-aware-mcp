"""Optional independent upstream ODF reader, without adding a runtime dependency."""

import importlib
import os
from decimal import Decimal

import pytest

from src.domain.native_ods import NativeODSCreate
from src.infrastructure.native_ods import NativeODS, create_native_ods
from tests.native_ods_helpers import edit, fixture

pytestmark = pytest.mark.skipif(
    os.environ.get("NATIVE_ODS_ODFDO_TEST") != "1",
    reason="Set NATIVE_ODS_ODFDO_TEST=1 with isolated odfdo installed",
)


def test_odfdo_reads_native_creation_and_compressed_edits(tmp_path):
    Document = importlib.import_module("odfdo").Document
    original = create_native_ods(NativeODSCreate())
    data, _ = NativeODS(original).edit(
        [
            edit(value=" literal =SUM(A1)  中文😀\t\n"),
            edit(1, 1, "3.43", "float"),
            edit(2, 0, False, "boolean"),
        ]
    )
    source = tmp_path / "created.ods"
    source.write_bytes(data)
    sheet = Document(source).body.get_sheet(0)
    assert sheet.get_cell("A1").value == " literal =SUM(A1)  中文😀\t\n"
    assert sheet.get_cell("B2").value == Decimal("3.43")
    assert sheet.width == 2
    assert sheet.get_cell("A3").value is False
    compressed = fixture(
        '<table:table-column table:number-columns-repeated="10"/><table:table-row table:number-rows-repeated="20"><table:table-cell table:number-columns-repeated="10" office:value-type="string"><text:p>old</text:p></table:table-cell></table:table-row>'
    )
    changed, _ = NativeODS(compressed).edit([edit(10, 5, "new")])
    source = tmp_path / "repeated.ods"
    source.write_bytes(changed)
    sheet = Document(source).body.get_sheet(0)
    assert sheet.get_cell("F11").value == "new"
    for position in ("E11", "G11", "F10", "F12", "J20"):
        assert sheet.get_cell(position).value == "old"
