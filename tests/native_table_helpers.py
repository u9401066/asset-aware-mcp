"""Real persisted native/A2T workspaces and complete readback helpers."""

import hashlib
import json

from src.application.native_document_service import NativeDocumentService
from src.application.table_service import TableService
from src.infrastructure.excel_renderer import ExcelRenderer
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_workbook_range import NativeWorkbookRange
from src.infrastructure.native_workbook_structure import NativeWorkbookStructure
from src.infrastructure.table_workspace_reader import FileTableWorkspaceReader
from src.presentation.response_limits import format_limited_json_response
from tests.native_workbook_helpers import _call, _edit, build_workbook


def service_at(root):
    tables = TableService(
        root / "tables",
        ExcelRenderer(root / "tables"),
        workspace_reader=FileTableWorkspaceReader(root / "tables"),
    )
    service = NativeDocumentService(
        FileNativeAssetRepository(root / "native"),
        SpreadsheetFileAdapter(),
        workbook_structure=NativeWorkbookStructure(),
        workbook_ranges=NativeWorkbookRange(),
        table_workspaces=tables,
    )
    return service, tables


def project(service, root, start="A1", end="E3"):
    data, _ = service.spreadsheets.edit(
        build_workbook(),
        [_edit("E1", "007"), _edit("E2", True, "boolean"), _edit("E3", "=SUM(A2)")],
    )
    source = root / "source.xlsx"
    source.write_bytes(data)
    asset = _call(service, op="register", source_path=str(source))["asset"]
    result = _call(
        service,
        op="project_workbook_table",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        table_projection={
            "worksheet": {"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
            "start_cell": start,
            "end_cell": end,
            "title": "原生表格",
        },
    )
    return asset, result


def read_workspace(service, table_id, limit=4000, **kwargs):
    chunks, offset, digest, text_digest = [], 0, None, None
    while True:
        result = _call(
            service,
            op="read_table_workspace",
            table_id=table_id,
            table_sha256=digest,
            text_offset=offset,
            text_limit=limit,
            **kwargs,
        )
        digest = digest or result["table_sha256"]
        text_digest = text_digest or result["text_sha256"]
        assert result["table_sha256"] == digest
        assert result["text_sha256"] == text_digest
        assert "response_truncated" not in format_limited_json_response(
            title="Workspace", payload=result
        )
        assert result["excerpt_char_range"][0] == offset
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    data = "".join(chunks).encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == text_digest
    return json.loads(data), digest


def apply(service, asset, table_id, digest):
    return _call(
        service,
        op="apply_table_workspace",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        table_id=table_id,
        expected_table_sha256=digest,
    )
