"""Operate on native file assets independently of the PDF ingestion repository."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import (
    native_asset_summary,
    native_document_contract,
)
from src.application.native_docx_operations import NativeDocxOperations
from src.application.native_evidence_service import (
    NativeEvidenceService,
    attach_native_evidence,
)
from src.application.native_pptx_operations import NativePptxOperations
from src.application.native_schema import read_schema
from src.application.native_wiki_service import NativeWikiService

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
        NativeSpreadsheetAdapter,
    )
    from src.domain.native_docx import NativeDocxAdapter
    from src.domain.native_pptx import NativePresentationAdapter
    from src.domain.native_wiki import NativeWikiPublisher


class NativeDocumentService:
    def __init__(
        self,
        repository: NativeAssetRepository,
        spreadsheets: NativeSpreadsheetAdapter,
        wiki_publisher: NativeWikiPublisher | None = None,
        docx: NativeDocxAdapter | None = None,
        presentations: NativePresentationAdapter | None = None,
    ):
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.docx = docx
        self.presentations = presentations
        self.pptx_operations = (
            NativePptxOperations(repository, presentations) if presentations else None
        )
        self.evidence = NativeEvidenceService(
            repository, spreadsheets, docx, presentations
        )
        self.docx_operations = NativeDocxOperations(repository, docx) if docx else None
        self.wiki = (
            NativeWikiService(
                repository, spreadsheets, wiki_publisher, docx, presentations
            )
            if wiki_publisher is not None
            else None
        )

    def _summary(self, asset: NativeFileAsset) -> dict[str, Any]:
        return native_asset_summary(
            asset,
            docx_enabled=self.docx is not None,
            pptx_enabled=self.presentations is not None,
        )

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        handlers = {
            "contract": self._contract,
            "schema": read_schema,
            "list": self._list,
            "register": self._register,
            "create": self._create,
            "history": self._history,
            "read_cell": self._read_cell,
            "create_pptx": self._pptx_operation,
            "read_pptx": self._pptx_operation,
            "read_pptx_shape": self._pptx_operation,
            "update_pptx": self._pptx_operation,
            "add_pptx_shapes": self._pptx_operation,
            "delete_pptx_shapes": self._pptx_operation,
            "read_docx": self._docx_operation,
            "read_docx_block": self._docx_operation,
            "update_docx": self._docx_operation,
            "verify": self._verify,
            "export_wiki": self._export_wiki,
            "inspect": self._inspect,
            "refresh": self._refresh,
            "archive": self._archive,
            "publish": self._publish,
            "writeback": self._writeback,
            "update": self._update,
        }
        return handlers[request.op](request)

    def _export_wiki(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.wiki is None:
            raise ValueError("Native wiki publisher is not configured")
        return self.wiki.export(request)

    def _verify(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.reference is not None
        return self.evidence.verify(request.reference)

    def _contract(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return native_document_contract(
            request,
            docx_enabled=self.docx is not None,
            pptx_enabled=self.presentations is not None,
        )

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
        elif asset.format == "pptx" and self.presentations is not None:
            result["content"] = {
                "representation": "pptx_package",
                "size_bytes": len(data),
                "read_operation": "read_pptx",
            }
        elif asset.format == "docx" and self.docx is not None:
            result["content"] = {
                "representation": "docx_package",
                "size_bytes": len(data),
                "native_editor": "dfm_bridge",
                "read_operation": "read_docx",
            }
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

    def _docx_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.docx_operations is None:
            raise ValueError("The native DOCX bridge is not configured")
        return self.docx_operations.execute(request)

    def _pptx_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.pptx_operations is None:
            raise ValueError("The native PPTX adapter is not configured")
        return self.pptx_operations.execute(request)
