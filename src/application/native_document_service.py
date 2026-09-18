"""Operate on native file assets independently of the PDF ingestion repository."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_evidence_service import (
    NativeEvidenceService,
    attach_native_evidence,
)
from src.domain.native_assets import NativeDocumentRequest

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeFileAsset,
        NativeSpreadsheetAdapter,
    )


class NativeDocumentService:
    def __init__(
        self, repository: NativeAssetRepository, spreadsheets: NativeSpreadsheetAdapter
    ):
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.evidence = NativeEvidenceService(repository, spreadsheets)

    @staticmethod
    def _summary(asset: NativeFileAsset) -> dict[str, Any]:
        return {
            "asset_id": asset.asset_id,
            "name": asset.name,
            "format": asset.format,
            "media_type": asset.media_type,
            "revision": asset.revision,
            "archived": asset.archived,
            "source": asset.source.model_dump() if asset.source else None,
            "revision_count": len(asset.history),
            "capabilities": {
                "inspect_metadata": True,
                "immutable_history": True,
                "refresh_source": asset.source is not None and not asset.archived,
                "inspect_cells": asset.format in {"xlsx", "xlsm"},
                "verify_cells": asset.format in {"xlsx", "xlsm"},
                "edit_cells": asset.format in {"xlsx", "xlsm"} and not asset.archived,
                "writeback": asset.source is not None and not asset.archived,
                "rendered_verification": False,
                "formula_evaluation": False,
                "edit_constraints": [
                    "protected_sheets",
                    "shared_array_formulas",
                    "rich_text_runs",
                    "table_headers_totals_calculated_columns",
                    "digital_signatures",
                ],
            },
        }

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        handlers = {
            "contract": self._contract,
            "list": self._list,
            "register": self._register,
            "create": self._create,
            "history": self._history,
            "read_cell": self._read_cell,
            "verify": self._verify,
            "inspect": self._inspect,
            "refresh": self._refresh,
            "archive": self._archive,
            "publish": self._publish,
            "writeback": self._writeback,
            "update": self._update,
        }
        return handlers[request.op](request)

    def _verify(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.reference is not None
        return self.evidence.verify(request.reference)

    def _contract(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "success": True,
            "schema": NativeDocumentRequest.model_json_schema(),
            "identity": "Stable asset ID; immutable SHA-256 revisions; native sheet/cell locators",
            "formats": {
                "xlsx": ["create", "inspect_cells", "edit_cells"],
                "xlsm": ["inspect_cells", "edit_cells"],
                "other": [
                    "register",
                    "inspect_metadata",
                    "history",
                    "publish",
                    "archive",
                ],
            },
            "verification": "Package/locator/source checks are mechanical; agents verify semantics and rendered layout.",
            "archive_policy": "Archive preserves revisions and never deletes the human source file.",
        }

    def _list(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "success": True,
            "assets": [
                self._summary(asset)
                for asset in self.repository.list_assets(request.offset, request.limit)
            ],
        }

    def _register(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.source_path is not None
        asset = self.repository.register(request.source_path)
        return {"success": True, "asset": self._summary(asset)}

    def _create(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.workbook is not None
        data = self.spreadsheets.create(request.workbook)
        asset = self.repository.create(
            request.workbook.name,
            data,
            "xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return {"success": True, "asset": self._summary(asset)}

    def _history(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        return {
            "success": True,
            "asset": self._summary(asset),
            "history": [
                revision.model_dump(exclude={"result"})
                for revision in asset.history[
                    request.offset : request.offset + request.limit
                ]
            ],
            "next_offset": request.offset + request.limit
            if request.offset + request.limit < len(asset.history)
            else None,
        }

    def _read_cell(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        asset = self.repository.load(asset_id)
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native cell reader")
        assert request.sheet is not None and request.cell is not None
        revision = request.revision or asset.revision
        cell = self.spreadsheets.read_cell(
            self.repository.read(asset_id, revision), request.sheet, request.cell
        )
        attach_native_evidence(cell, asset_id, revision)
        if isinstance(cell.get("value"), str):
            value = cell.pop("value")
            start = min(request.text_offset, len(value))
            end = min(start + request.text_limit, len(value))
            cell.update(
                value_excerpt=value[start:end],
                value_length=len(value),
                value_text_sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
                excerpt_char_range=[start, end],
                next_text_offset=end if end < len(value) else None,
                representation_complete=start == 0 and end == len(value),
            )
        return {
            "success": True,
            "asset_id": asset_id,
            "inspected_revision": revision,
            "cell": cell,
        }

    def _inspect(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        asset = self.repository.load(asset_id)
        revision = request.revision or asset.revision
        data = self.repository.read(asset_id, revision)
        result: dict[str, Any] = {
            "success": True,
            "asset": self._summary(asset),
            "inspected_revision": revision,
        }
        if asset.format in {"xlsx", "xlsm"}:
            result["content"] = self.spreadsheets.inspect(
                data,
                sheet=request.sheet,
                offset=request.offset,
                limit=request.limit,
            )
            for cell in result["content"]["cells"]:
                attach_native_evidence(cell, asset_id, revision)
        else:
            result["content"] = {
                "representation": "opaque_binary",
                "size_bytes": len(data),
                "native_editor": "unavailable",
            }
        return result

    def _refresh(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        assert request.expected_source_sha256 is not None
        return {
            "success": True,
            "asset": self._summary(
                self.repository.refresh(
                    asset_id,
                    request.expected_revision,
                    request.expected_source_sha256,
                )
            ),
            "source_written": False,
        }

    def _archive(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        return {
            "success": True,
            "asset": self._summary(
                self.repository.archive(asset_id, request.expected_revision)
            ),
            "source_deleted": False,
        }

    def _publish(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        assert request.output_path is not None
        return self.repository.publish(
            asset_id, request.expected_revision, request.output_path
        )

    def _writeback(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        assert request.expected_source_sha256 is not None
        return self.repository.writeback(
            asset_id, request.expected_revision, request.expected_source_sha256
        )

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        asset = self.repository.load(asset_id)
        assert request.expected_revision is not None
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native editing adapter yet")
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        data = self.repository.read(asset_id, request.expected_revision)
        updated, checks = self.spreadsheets.edit(data, request.edits)
        committed = self.repository.commit(
            asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": self._summary(committed),
            "operation_result": checks.model_dump(),
            "source_written": False,
        }
