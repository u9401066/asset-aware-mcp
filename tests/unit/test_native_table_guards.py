"""Reject stale, ambiguous and unsupported native/A2T writes without mutation."""

import json

import pytest
from lxml import etree

from src.application.native_document_service import NativeDocumentService
from src.application.native_table_projection import canonical_table
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_table_workspace import (
    NativeTableCellValue,
    NativeTableProjection,
)
from src.infrastructure.table_workspace_reader import FileTableWorkspaceReader
from tests.native_table_helpers import apply, project, read_workspace, service_at
from tests.native_workbook_helpers import _call, _parts, _replace, build_workbook


@pytest.mark.parametrize(
    "start,end", [("B2", "A1"), ("A0", "B2"), ("A1", "XFE1"), ("A1", "A20001")]
)
def test_projection_rejects_bad_or_oversize_ranges(start, end):
    with pytest.raises(ValueError):
        NativeTableProjection(
            worksheet={"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
            start_cell=start,
            end_cell=end,
        )


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "number", "value": True},
        {"kind": "string", "value": 7},
        {"kind": "boolean", "value": "true"},
        {"kind": "formula", "value": "A1"},
        {"kind": "blank", "value": ""},
        {"kind": "number", "value": float("nan")},
        {"kind": "string", "value": "ok", "extra": "ignored?"},
    ],
)
def test_tagged_values_are_strict(value):
    with pytest.raises(ValueError):
        NativeTableCellValue.model_validate(value)


@pytest.mark.parametrize(
    "start,end,row,column,match",
    [
        ("A5", "D6", 1, "B", "merged"),
        ("A1", "E3", 1, "D", "Rich"),
        ("A8", "B10", 0, "A", "table"),
    ],
)
def test_native_editor_guards_remain_in_force(tmp_path, start, end, row, column, match):
    service, tables = service_at(tmp_path)
    asset, projection = project(service, tmp_path, start, end)
    table_id = projection["table_id"]
    tables.update_cell(table_id, row, column, {"kind": "string", "value": "unsafe"})
    _, digest = read_workspace(service, table_id)
    count = len(service.repository.list_assets(0, 100))
    with pytest.raises(ValueError, match=match):
        apply(service, asset, table_id, digest)
    assert service.repository.load(asset["asset_id"]).revision == asset["revision"]
    assert len(service.repository.list_assets(0, 100)) == count


def test_fresh_disk_snapshot_prevents_stale_cache_and_page_mix(tmp_path):
    service, _ = service_at(tmp_path)
    asset, projection = project(service, tmp_path)
    table_id, old_hash = projection["table_id"], projection["table_sha256"]
    _, another = service_at(tmp_path)
    another.update_cell(table_id, 0, "E", {"kind": "string", "value": "009"})
    with pytest.raises(ValueError, match="workspace changed"):
        apply(service, asset, table_id, old_hash)
    with pytest.raises(ValueError, match="workspace changed"):
        _call(
            service,
            op="read_table_workspace",
            table_id=table_id,
            table_sha256=old_hash,
            text_offset=100,
        )
    with pytest.raises(ValueError, match="table_sha256"):
        NativeDocumentRequest(
            op="read_table_workspace", table_id=table_id, text_offset=100
        )
    record, _ = read_workspace(service, table_id)
    assert record["table"]["rows"][0]["E"]["value"] == "009"
    with pytest.raises(ValueError, match="offset"):
        _call(
            service,
            op="read_table_workspace",
            table_id=table_id,
            table_sha256=read_workspace(service, table_id)[1],
            text_offset=10_000_000,
        )


def test_binding_keys_archive_and_snapshot_identity_are_checked(tmp_path):
    service, tables = service_at(tmp_path)
    asset, projection = project(service, tmp_path)
    table_id = projection["table_id"]
    context = tables.get_table_context(table_id)
    binding = context.native_binding
    assert binding is not None
    invalid_projection = binding.projection.model_dump()
    invalid_projection["worksheet"]["sheet_id"] = "77"
    with pytest.raises(ValueError, match="key"):
        _call(
            service,
            op="project_workbook_table",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            table_projection=invalid_projection,
        )
    with pytest.raises(ValueError, match="A2T snapshot"):
        read_workspace(
            service, table_id, workspace_reference=binding.source.model_dump()
        )
    made = _call(
        service,
        op="create_workbook_from_table",
        table_id=table_id,
        expected_table_sha256=projection["table_sha256"],
        table_workbook={},
    )
    with pytest.raises(ValueError, match="different table identity"):
        read_workspace(
            service, "tbl_different", workspace_reference=made["workspace_reference"]
        )
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
    )
    with pytest.raises(ValueError, match="Archived"):
        apply(service, asset, table_id, projection["table_sha256"])


def test_workspace_persistence_failure_and_unsafe_read_paths(tmp_path, monkeypatch):
    service, tables = service_at(tmp_path)
    _, projection = project(service, tmp_path)
    context = tables.read_workspace(projection["table_id"])
    with pytest.raises(ValueError, match="already exists"):
        tables.create_workspace(context)
    context.id = "tbl_failed"

    def fail(*_args):
        raise OSError("disk failure")

    monkeypatch.setattr(tables, "_write_json_temp", fail)
    with pytest.raises(OSError, match="disk failure"):
        tables.create_workspace(context)
    assert context.id not in tables._tables
    assert not (tables.storage_dir / f"{context.id}.json").exists()
    reader = FileTableWorkspaceReader(tables.storage_dir)
    for table_id in ("..", "../escape", str(tmp_path / "escape"), "x\\y"):
        with pytest.raises(ValueError, match="Invalid"):
            reader.read_workspace(table_id)
    path = tables.storage_dir / "alias.json"
    try:
        path.symlink_to(tables.storage_dir / f"{projection['table_id']}.json")
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")
    with pytest.raises((ValueError, OSError)):
        reader.read_workspace("alias")


def test_workspace_file_identity_and_byte_budget(tmp_path):
    service, tables = service_at(tmp_path)
    _, projection = project(service, tmp_path)
    path = tables.storage_dir / f"{projection['table_id']}.json"
    state = json.loads(path.read_text("utf-8"))
    state["id"] = "wrong"
    path.write_text(json.dumps(state), "utf-8")
    with pytest.raises(ValueError, match="identity mismatch"):
        tables.read_workspace(projection["table_id"])
    with path.open("wb") as handle:
        handle.truncate(16 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="byte limit"):
        tables.read_workspace(projection["table_id"])
    with pytest.raises(ValueError, match="finite UTF-8"):
        canonical_table({"invalid": float("inf")})


async def test_discovery_reports_adapter_availability_and_export_guard(tmp_path):
    service, tables = service_at(tmp_path)
    _, projection = project(service, tmp_path)
    contract = _call(service, op="contract", for_op="apply_table_workspace")
    assert contract["table_workspaces_enabled"]
    assert "read_table_workspace" in contract["formats"]["xlsx"]
    basic = NativeDocumentService(service.repository, service.spreadsheets)
    assert not _call(basic, op="contract")["table_workspaces_enabled"]
    with pytest.raises(ValueError, match="configured"):
        _call(basic, op="read_table_workspace", table_id=projection["table_id"])
    with pytest.raises(ValueError, match="create_workbook_from_table"):
        await tables.render_table(projection["table_id"], "excel")


def test_error_cells_remain_readonly_until_an_explicit_writable_type(tmp_path):
    service, tables = service_at(tmp_path)
    data = build_workbook()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    root = etree.fromstring(_parts(data)["xl/worksheets/sheet1.xml"])
    row = root.find(f"{{{ns}}}sheetData/{{{ns}}}row")
    cell = etree.SubElement(row, f"{{{ns}}}c", r="E1", t="e")
    etree.SubElement(cell, f"{{{ns}}}v").text = "#N/A"
    data = _replace(data, {"xl/worksheets/sheet1.xml": etree.tostring(root)})
    source = tmp_path / "errors.xlsx"
    source.write_bytes(data)
    asset = _call(service, op="register", source_path=str(source))["asset"]
    projection = _call(
        service,
        op="project_workbook_table",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        table_projection={
            "worksheet": {"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
            "start_cell": "E1",
            "end_cell": "E1",
        },
    )
    table_id = projection["table_id"]
    record, digest = read_workspace(service, table_id)
    assert record["table"]["rows"] == [{"E": {"kind": "source_only", "value": "#N/A"}}]
    assert not apply(service, asset, table_id, digest)["changed"]
    count = len(service.repository.list_assets(0, 100))
    with pytest.raises(ValueError, match="kind"):
        _call(
            service,
            op="create_workbook_from_table",
            table_id=table_id,
            expected_table_sha256=digest,
            table_workbook={},
        )
    assert len(service.repository.list_assets(0, 100)) == count
    tables.update_cell(table_id, 0, "E", {"kind": "string", "value": "#N/A"})
    _, digest = read_workspace(service, table_id)
    changed = apply(service, asset, table_id, digest)
    assert changed["changed"]
    current = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Data", cell="E1"
    )["cell"]
    assert current["kind"] == "string" and current["value_excerpt"] == "#N/A"
    assert current["representation_complete"]
    assert source.read_bytes() == data
