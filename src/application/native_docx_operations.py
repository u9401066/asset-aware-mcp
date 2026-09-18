"""Managed native DOCX reads/edits, preserving immutable source identity."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_records import docx_block_excerpt

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository, NativeDocumentRequest
    from src.domain.native_docx import NativeDocxAdapter


class NativeDocxOperations:
    def __init__(self, repository: NativeAssetRepository, docx: NativeDocxAdapter):
        self.repository = repository
        self.docx = docx

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "read_docx": self._read,
            "update_docx": self._update,
            "read_docx_block": self._read_block,
        }[request.op](request)

    def _read_block(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.block_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx":
            raise ValueError("This format has no native DOCX block reader")
        revision = request.revision or asset.revision
        record = self.docx.read_block(
            self.repository.read(asset.asset_id, revision),
            asset.asset_id,
            revision,
            request.block_id,
        )
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": revision,
            "block": docx_block_excerpt(
                record, request.text_offset, request.text_limit
            ),
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "fields_and_revisions",
            ],
        }

    def _read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx" or self.docx is None:
            raise ValueError("This format has no configured native DOCX bridge")
        revision = request.revision or asset.revision
        document = self.docx.read(
            self.repository.read(asset.asset_id, revision), asset.asset_id, revision
        )
        text = document.dfm_text
        start = min(request.text_offset, len(text))
        end = min(start + request.text_limit, len(text))
        return {
            "success": True,
            "asset": native_asset_summary(asset, docx_enabled=True),
            "inspected_revision": revision,
            "dfm": {
                "text_excerpt": text[start:end],
                "text_length": len(text),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "excerpt_char_range": [start, end],
                "next_text_offset": end if end < len(text) else None,
                "representation_complete": start == 0 and end == len(text),
            },
            "blocks": document.blocks[request.offset : request.offset + request.limit],
            "block_count": len(document.blocks),
            "next_offset": request.offset + request.limit
            if request.offset + request.limit < len(document.blocks)
            else None,
            "locator_scope": "immutable_revision; block IDs may change in later revisions",
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "fields_and_revisions",
            ],
        }

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.expected_revision is not None
        assert request.docx_edit is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx" or self.docx is None:
            raise ValueError("This format has no configured native DOCX bridge")
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        data = self.repository.read(asset.asset_id, request.expected_revision)
        updated, checks, warnings = self.docx.edit(
            data, asset.asset_id, request.expected_revision, request.docx_edit
        )
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": native_asset_summary(committed, docx_enabled=True),
            "operation_result": checks.model_dump(),
            "warnings": warnings,
            "source_written": False,
        }
