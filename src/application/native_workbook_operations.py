"""Revision-pinned workbook structure and bounded complete read-back."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository, NativeDocumentRequest
    from src.domain.native_workbook import NativeWorkbookStructureAdapter


class NativeWorkbookOperations:
    def __init__(
        self, repository: NativeAssetRepository, adapter: NativeWorkbookStructureAdapter
    ):
        self.repository = repository
        self.adapter = adapter

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
        if request.op == "add_worksheets":
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
        else:
            updated, checks = self.adapter.delete(data, request.worksheet_keys)
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": native_asset_summary(committed, workbook_structure_enabled=True),
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


def _read_page(
    record: dict[str, Any], request: NativeDocumentRequest, revision: str
) -> dict[str, Any]:
    text = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    encoded = text.encode("utf-8")
    if len(encoded) > 16 * 1024 * 1024:
        raise ValueError("Workbook structure exceeds the read-back budget")
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
