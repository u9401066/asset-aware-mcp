"""Bridge complete A2T workspaces and versioned native workbook operations."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_evidence_service import attach_native_evidence
from src.application.native_table_projection import (
    canonical_table,
    matching_grid,
    projected_context,
    projection_edits,
    workbook_from_context,
    workspace_bytes,
    workspace_hash,
)
from src.domain.native_asset_models import NativeEditResult
from src.domain.native_file_reference import NativeFileReference
from src.domain.table_state import table_from_state, table_state

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
        NativeSpreadsheetAdapter,
    )
    from src.domain.native_table_workspace import (
        NativeTableRangeReader,
        NativeTableWorkspaces,
    )
    from src.domain.table_entities import TableContext

WORKSPACE_MEDIA_TYPE = "application/vnd.asset-aware.a2t+json"


class NativeTableOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        spreadsheets: NativeSpreadsheetAdapter,
        ranges: NativeTableRangeReader,
        workspaces: NativeTableWorkspaces,
        summarize: Callable[[NativeFileAsset], dict[str, Any]] = native_asset_summary,
    ):
        self.repository, self.spreadsheets = repository, spreadsheets
        self.ranges, self.workspaces = ranges, workspaces
        self.summarize = summarize

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if request.op == "project_workbook_table":
            return self._project(request)
        assert request.table_id is not None
        if request.workspace_reference is not None:
            reference = request.workspace_reference
            snapshot = self.repository.load(reference.asset_id)
            if snapshot.format != "a2t" or snapshot.media_type != WORKSPACE_MEDIA_TYPE:
                raise ValueError(
                    "Workspace reference does not identify an A2T snapshot"
                )
            context = table_from_state(
                json.loads(self.repository.read(reference.asset_id, reference.revision))
            )
            if context.id != request.table_id:
                raise ValueError("Workspace reference has a different table identity")
        else:
            context = self.workspaces.read_workspace(request.table_id)
        digest = workspace_hash(context)
        expected = (
            request.table_sha256
            if request.op == "read_table_workspace"
            else request.expected_table_sha256
        )
        if expected and expected != digest:
            raise ValueError(
                "Table workspace changed; read the complete snapshot again"
            )
        if request.op == "read_table_workspace":
            return _page(self._record(context), request, digest)
        if request.op == "create_workbook_from_table":
            return self._create(context, request)
        return self._apply(context, request)

    def _source_records(self, context: TableContext) -> list[list[dict[str, Any]]]:
        binding = context.native_binding
        if binding is None:
            return []
        source = self.repository.load(binding.source.asset_id)
        if source.format not in {"xlsx", "xlsm"}:
            raise ValueError("Workspace source is not a native workbook")
        return self.ranges.read_range(
            self.repository.read(source.asset_id, binding.source.revision),
            binding.projection,
        )

    def _record(self, context: TableContext) -> dict[str, Any]:
        source_cells = []
        binding = context.native_binding
        if binding is not None:
            for row_id, row in zip(
                binding.row_ids, self._source_records(context), strict=True
            ):
                for column, record in zip(binding.columns, row, strict=True):
                    attach_native_evidence(
                        record, binding.source.asset_id, binding.source.revision
                    )
                    source_cells.append(
                        {"row_id": row_id, "column_name": column, "source": record}
                    )
        return {
            "schema_version": "native-table-workspace-v1",
            "table": table_state(context),
            "source_cells": source_cells,
            "source_correspondence_unchanged": matching_grid(context),
            "binding_scope": "Extraction origin only; original source references do not assert semantic support for edited values. Styles and raw source details remain in the immutable workbook.",
        }

    def _project(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.revision is not None
        assert request.table_projection is not None
        asset = self.repository.load(request.asset_id)
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native table projection")
        records = self.ranges.read_range(
            self.repository.read(asset.asset_id, request.revision),
            request.table_projection,
        )
        context = projected_context(
            asset.asset_id, request.revision, request.table_projection, records
        )
        canonical_table(
            self._record(context)
        )  # Never create a projection too large to read completely.
        self.workspaces.create_workspace(context)
        stored = self.workspaces.read_workspace(context.id)
        return {
            "success": True,
            "table_id": context.id,
            "table_sha256": workspace_hash(stored),
            "rows": context.row_count,
            "columns": len(context.columns),
            "source_written": False,
            "read_request": {"op": "read_table_workspace", "table_id": context.id},
        }

    def _freeze(self, context: TableContext) -> NativeFileReference:
        asset = self.repository.create(
            f"{context.id}.json", workspace_bytes(context), "a2t", WORKSPACE_MEDIA_TYPE
        )
        return NativeFileReference(asset_id=asset.asset_id, revision=asset.revision)

    def _apply(
        self, context: TableContext, request: NativeDocumentRequest
    ) -> dict[str, Any]:
        assert request.asset_id is not None and request.expected_revision is not None
        binding = context.native_binding
        if (
            binding is None
            or binding.source.asset_id != request.asset_id
            or binding.source.revision != request.expected_revision
        ):
            raise ValueError(
                "Workspace binding does not match the target asset and expected revision"
            )
        asset = self.repository.load(request.asset_id)
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError(
                "Archived or stale native asset; reconcile before applying the workspace"
            )
        edits = projection_edits(context, self._source_records(context))
        if not edits:
            return {
                "success": True,
                "changed": False,
                "asset": self.summarize(asset),
                "table_sha256": workspace_hash(context),
                "source_written": False,
            }
        updated, result = self.spreadsheets.edit(
            self.repository.read(asset.asset_id, request.expected_revision), edits
        )
        reference = self._freeze(context)
        result.changes.append(
            {
                "operation": "apply_table_workspace",
                "table_id": context.id,
                "table_sha256": reference.revision,
                "workspace_reference": reference.model_dump(),
                "source_binding": binding.model_dump(),
                "edited_cell_count": len(edits),
            }
        )
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, result
        )
        return self._result(committed, context, reference, result)

    def _create(
        self, context: TableContext, request: NativeDocumentRequest
    ) -> dict[str, Any]:
        assert request.table_workbook is not None
        workbook, mapping = workbook_from_context(context, request.table_workbook)
        data = self.spreadsheets.create(workbook)
        reference = self._freeze(context)
        result = NativeEditResult(
            changed_parts=[],
            preserved_parts=0,
            changes=[
                {
                    "operation": "create_workbook_from_table",
                    "table_id": context.id,
                    "table_sha256": reference.revision,
                    "workspace_reference": reference.model_dump(),
                    "mapping": mapping,
                }
            ],
            checks=["tagged_cell_types_checked", "new_native_workbook_created"],
            review_required=[
                "semantic_accuracy",
                "new_workbook_layout",
                "formula_results",
            ],
        )
        asset = self.repository.create(
            workbook.name,
            data,
            "xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            result=result,
        )
        return self._result(asset, context, reference, result)

    def _result(
        self,
        asset: NativeFileAsset,
        context: TableContext,
        reference: NativeFileReference,
        result: NativeEditResult,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "changed": True,
            "asset": self.summarize(asset),
            "table_id": context.id,
            "table_sha256": reference.revision,
            "workspace_reference": reference.model_dump(),
            "source_written": False,
            "operation_result": {
                "changed_part_count": len(result.changed_parts),
                "preserved_parts": result.preserved_parts,
                "checks": result.checks,
                "repairs": result.repairs,
                "review_required": result.review_required,
            },
            "review_request": {
                "op": "inspect",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
            },
            "binding_policy": "The table workspace keeps its original binding; re-project the new native revision for another synchronized edit.",
        }


def _page(
    record: dict[str, Any], request: NativeDocumentRequest, digest: str
) -> dict[str, Any]:
    data = canonical_table(record)
    text = data.decode("utf-8")
    start = request.text_offset
    if start > len(text):
        raise ValueError("Workspace offset exceeds the representation")
    end = min(start + request.text_limit, len(text))
    result: dict[str, Any] = {
        "success": True,
        "table_id": request.table_id,
        "table_sha256": digest,
        "text_sha256": hashlib.sha256(data).hexdigest(),
        "text_length": len(text),
        "source_written": False,
        "serialization": "canonical-json; UTF-8 SHA-256",
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
