"""Revision-bound ODF reads and cell transactions with complete native receipts."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_operation_results import revision_result_dict
from src.domain.native_asset_models import NativeEditResult
from src.domain.native_ods import ODS_REVIEW, NativeODSCellEdit, attach_ods_evidence

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
    )
    from src.domain.native_ods import NativeODSAdapter


def ods_record_text(record: dict[str, Any]) -> str:
    text = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    # A complete 128 MiB operation envelope plus a bounded 16 MiB listing.
    if len(text.encode("utf-8")) > 144 * 1024 * 1024:
        raise ValueError("ODS representation exceeds the complete read budget")
    return text


def _page(record: dict[str, Any], request: NativeDocumentRequest) -> dict[str, Any]:
    text = ods_record_text(record)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if request.ods_text_sha256 is not None and request.ods_text_sha256 != sha:
        raise ValueError("ODS representation changed; restart the complete read")
    start = min(request.text_offset, len(text))
    end = min(start + request.text_limit, len(text))
    result = {
        "success": True,
        "asset_id": request.asset_id,
        "inspected_revision": request.revision,
        "representation": record["schema_version"],
        "text_sha256": sha,
        "text_length": len(text),
        "serialization": "canonical-json; UTF-8 SHA-256; Unicode character offsets",
        "source_written": False,
        "review_required": ODS_REVIEW,
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
        if end <= start:
            raise ValueError("ODS response exceeds the MCP budget")
        end = start + (end - start) // 2


class NativeODSOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        adapter: NativeODSAdapter,
        summarize: Callable[[NativeFileAsset], dict[str, Any]],
    ):
        self.repository = repository
        self.adapter = adapter
        self.summarize = summarize

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if request.op == "create_ods":
            assert request.ods_create is not None
            data = self.adapter.create(request.ods_create)
            structure = self.adapter.inspect(data, offset=0, limit=1)
            report = NativeEditResult(
                changed_parts=["mimetype", "META-INF/manifest.xml", "content.xml"],
                preserved_parts=0,
                changes=[{"operation": "create_ods", "tables": structure["tables"]}],
                checks=["native_package_reopened", "explicit_blank_tables"],
                review_required=list(ODS_REVIEW),
            )
            asset = self.repository.create(
                request.ods_create.name,
                data,
                "ods",
                "application/vnd.oasis.opendocument.spreadsheet",
                result=report,
            )
            return self._result(asset, report, True)
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "ods":
            raise ValueError("ODS operations require an ODS asset")
        if request.op in {"read_ods", "read_ods_cell"}:
            assert request.revision is not None
            data = self.repository.read(asset.asset_id, request.revision)
            payload: dict[str, Any]
            if request.op == "read_ods_cell":
                assert request.ods_locator is not None
                record = self.adapter.read_cell(data, request.ods_locator)
                attach_ods_evidence(record, asset.asset_id, request.revision)
                # The envelope is deliberately outside the canonical cell record.
                payload = {"schema_version": "native-ods-cell-v1", "cell": record}
            else:
                payload = self.adapter.inspect(
                    data, offset=request.offset, limit=request.limit
                )
                history = next(
                    h for h in reversed(asset.history) if h.sha256 == request.revision
                )
                payload.update(
                    schema_version="native-ods-ranges-v1",
                    record_scope="physical_repetition_ranges; anchors are logical coordinates, not coverage verification",
                    operation_result=revision_result_dict(
                        self.repository, asset, history
                    ),
                )
            return _page(payload, request)
        if request.op != "update_ods":
            raise ValueError("Unknown ODS operation")
        assert request.expected_revision is not None and request.ods_update is not None
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale ODS asset; inspect before editing")
        data = self.repository.read(asset.asset_id, request.expected_revision)
        edits = []
        for update in request.ods_update.cells:
            ref = update.reference
            if (ref.asset_id, ref.revision) != (
                asset.asset_id,
                request.expected_revision,
            ):
                raise ValueError(
                    "ODS references must identify the target asset and expected revision"
                )
            record = self.adapter.read_cell(data, ref.locator)
            attach_ods_evidence(record, asset.asset_id, request.expected_revision)
            if record["evidence"] != ref.model_dump(mode="json"):
                raise ValueError("ODS cell reference failed integrity verification")
            edits.append(
                NativeODSCellEdit(
                    locator=ref.locator,
                    value=update.value,
                    display_policy=update.display_policy,
                )
            )
        changed, report = self.adapter.edit(data, edits)
        report.checks.append("all_original_logical_cell_references_verified")
        # Reject unreadable reports before publishing a managed revision.
        ods_record_text(
            {
                **self.adapter.inspect(changed, offset=0, limit=1),
                "operation_result": report.model_dump(mode="json"),
            }
        )
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, changed, report
        )
        return self._result(committed, report, changed != data)

    def _result(
        self, asset: NativeFileAsset, report: NativeEditResult, changed: bool
    ) -> dict[str, Any]:
        return {
            "success": True,
            "asset": self.summarize(asset),
            "source_written": False,
            "new_revision_created": changed,
            "operation_result": report.model_dump(mode="json")
            if not changed
            else {
                "changed_parts": report.changed_parts,
                "checks": report.checks,
                "repairs": report.repairs,
                "review_required": report.review_required,
                "full_result_in": "read_ods.operation_result",
            },
            "review_request": {
                "op": "read_ods",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
            },
        }
