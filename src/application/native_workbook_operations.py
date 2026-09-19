"""Revision-pinned workbook structure and bounded complete read-back."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary

MAX_WORKBOOK_READ_BYTES = 16 * 1024 * 1024

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
    )
    from src.domain.native_grid import NativeGridAdapter
    from src.domain.native_table_edit import NativeTableEditAdapter
    from src.domain.native_workbook import NativeWorkbookStructureAdapter


class NativeWorkbookOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        adapter: NativeWorkbookStructureAdapter,
        grid: NativeGridAdapter | None = None,
        *,
        tables: NativeTableEditAdapter | None = None,
        summarize: Callable[[NativeFileAsset], dict[str, Any]] | None = None,
    ):
        self.repository = repository
        self.adapter = adapter
        self.grid = grid
        self.tables = tables
        self.summarize = summarize or (
            lambda asset: native_asset_summary(
                asset,
                workbook_structure_enabled=True,
                workbook_grid_enabled=grid is not None,
                workbook_table_edit_enabled=tables is not None,
            )
        )

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native workbook structure")
        if request.op == "read_workbook":
            revision = request.revision or asset.revision
            data = self.repository.read(asset.asset_id, revision)
            record = self.adapter.read(
                data, references=request.workbook_view == "references"
            )
            history = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            record.update(
                asset_id=asset.asset_id,
                revision=revision,
                operation_result=history.result.model_dump()
                if history.result
                else None,
            )
            return _read_page(record, request, revision)
        assert request.expected_revision is not None
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        data = self.repository.read(asset.asset_id, request.expected_revision)
        if request.op == "update_workbook_table":
            if self.tables is None:
                raise ValueError("Native Table editing adapter is not configured")
            assert request.table_update is not None
            updated, checks = self.tables.update(data, request.table_update)
            # Separate cell/reference budgets do not bound the combined public
            # representation. Reject before CAS if complete review is impossible.
            _record_text(
                {
                    **self.adapter.read(updated, references=True),
                    "asset_id": asset.asset_id,
                    "revision": hashlib.sha256(updated).hexdigest(),
                    "operation_result": checks.model_dump(),
                }
            )
        elif request.op == "update_worksheet_grid":
            if self.grid is None:
                raise ValueError("Native workbook grid adapter is not configured")
            assert request.worksheet_grid is not None
            updated, checks = self.grid.update(data, request.worksheet_grid)
        elif request.op == "add_worksheets":
            assert request.worksheet_insert is not None
            updated, checks = self.adapter.add(
                data, request.worksheet_insert, request.allow_3d_membership_change
            )
        elif request.op == "rename_worksheet":
            assert request.worksheet_rename is not None
            updated, checks = self.adapter.rename(data, request.worksheet_rename)
        elif request.op == "reorder_worksheets":
            updated, checks = self.adapter.reorder(
                data, request.worksheet_order, request.allow_3d_membership_change
            )
        elif request.op == "delete_worksheets":
            updated, checks = self.adapter.delete(data, request.worksheet_keys)
        else:
            raise ValueError("Unsupported native workbook operation")
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": self.summarize(committed),
            "source_written": False,
            "operation_result": {
                "changed_part_count": len(checks.changed_parts),
                "preserved_parts": checks.preserved_parts,
                "checks": checks.checks,
                "repairs": checks.repairs,
                "review_required": checks.review_required,
                "full_result_in": "read_workbook.operation_result",
            },
            "review_request": {
                "op": "read_workbook",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
                "workbook_view": "references",
            },
        }


def _record_text(record: dict[str, Any]) -> str:
    text = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(text.encode("utf-8")) > MAX_WORKBOOK_READ_BYTES:
        raise ValueError("Workbook structure exceeds the read-back budget")
    return text


def _read_page(
    record: dict[str, Any], request: NativeDocumentRequest, revision: str
) -> dict[str, Any]:
    text = _record_text(record)
    encoded = text.encode("utf-8")
    start = min(request.text_offset, len(text))
    end = min(start + request.text_limit, len(text))
    result: dict[str, Any] = {
        "success": True,
        "asset_id": request.asset_id,
        "inspected_revision": revision,
        "workbook_view": request.workbook_view,
        "text_sha256": hashlib.sha256(encoded).hexdigest(),
        "text_length": len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
        "source_written": False,
        "review_boundary": "Structure and explicit reference inventory do not cover every cell or prove meaning, rendering, dynamic references or calculated results. Use read_cell and Agent review.",
    }
    while True:
        result.update(
            text_excerpt=text[start:end],
            excerpt_char_range=[start, end],
            next_text_offset=end if end < len(text) else None,
            representation_complete=start == 0 and end == len(text),
        )
        if len(json.dumps(result, ensure_ascii=False, indent=2)) <= 10_000:
            return result
        end = start + (end - start) // 2
