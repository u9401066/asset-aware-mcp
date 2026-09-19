"""Managed grid edits retain historical evidence and never partially commit."""

import pytest

from tests.native_workbook_helpers import _call
from tests.unit.test_native_pptx_operations import read_shape
from tests.unit.test_native_pptx_table_operations import (
    add,
)
from tests.unit.test_native_pptx_table_operations import (
    managed as managed,
)


def request(managed):
    service, _, _, _ = managed
    result = add(managed)
    asset = result["asset"]
    locator = result["operation_result"]["changes"][0]["locator"]
    record = read_shape(service, asset, locator)
    return {
        "op": "update_pptx_table_grid",
        "asset_id": asset["asset_id"],
        "expected_revision": asset["revision"],
        "pptx_table_grid": {
            "reference": record["evidence"],
            "edits": [
                {"op": "insert", "axis": "column", "index": 1, "sizes": [300000]},
                {"op": "resize", "axis": "row", "index": 1, "sizes": [950000]},
            ],
        },
    }


def test_managed_grid_keeps_history_source_and_requires_new_references(managed):
    service, _, _, source = managed
    args = request(managed)
    original = source.read_bytes()
    result = _call(service, **args)
    assert result["success"] and not result["source_written"]
    assert source.read_bytes() == original
    record = read_shape(
        service, result["asset"], args["pptx_table_grid"]["reference"]["locator"]
    )
    assert len(record["table"]["rows"][0]["cells"]) == 4
    proof = _call(service, op="verify", reference=args["pptx_table_grid"]["reference"])
    assert proof["valid"] and not proof["is_current_managed_revision"]
    args["expected_revision"] = result["asset"]["revision"]
    with pytest.raises(ValueError, match="reference"):
        _call(service, **args)


@pytest.mark.parametrize(
    "failure", ["stale", "archived", "other_asset", "wrong_revision", "bad_second_edit"]
)
def test_failed_grid_edit_is_atomic(managed, failure):
    service, _, _, source = managed
    args = request(managed)
    if failure == "stale":
        args["expected_revision"] = "0" * 64
    elif failure == "archived":
        _call(
            service,
            op="archive",
            asset_id=args["asset_id"],
            expected_revision=args["expected_revision"],
        )
    elif failure == "other_asset":
        args["pptx_table_grid"]["reference"]["asset_id"] = "file_" + "0" * 32
    elif failure == "wrong_revision":
        args["pptx_table_grid"]["reference"]["revision"] = "0" * 64
    else:
        args["pptx_table_grid"]["edits"][1]["index"] = 99
    before = service.repository.load(args["asset_id"])
    source_before = source.read_bytes()
    with pytest.raises(ValueError):
        _call(service, **args)
    after = service.repository.load(args["asset_id"])
    assert after.revision == before.revision and after.history == before.history
    assert source.read_bytes() == source_before


def test_interleaved_grid_commit_retains_the_winning_revision(managed, monkeypatch):
    service, _, _, _ = managed
    args = request(managed)
    original = service.presentations.edit_table_grid

    def competing(data, grid):
        updated, checks = original(data, grid)
        service.repository.commit(
            args["asset_id"], args["expected_revision"], updated, checks
        )
        return updated, checks

    monkeypatch.setattr(service.presentations, "edit_table_grid", competing)
    with pytest.raises(ValueError, match=r"revision|changed|Stale|stale"):
        _call(service, **args)
    assert len(service.repository.load(args["asset_id"]).history) == 3
