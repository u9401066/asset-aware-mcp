"""Hash-paged lifecycle receipts and atomic revision-bound Word structure edits."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_story_operations import page
from src.application.native_docx_table_operations import RECEIPT_POLICY, record_text
from src.application.native_operation_results import revision_result_dict
from src.domain.native_docx_stories import STORY_REVIEW

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeAssetRepository
    from src.domain.native_assets import NativeDocumentRequest
    from src.domain.native_docx_stories import NativeDocxStoryAdapter


class NativeDocxStoryStructureOperations:
    def __init__(
        self, repository: NativeAssetRepository, stories: NativeDocxStoryAdapter
    ):
        self.repository, self.stories = repository, stories

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        updating = request.op == "update_docx_story_structure"
        revision = request.expected_revision if updating else request.revision
        assert revision is not None
        if asset.format != "docx":
            raise ValueError("This format has no Word story structure")
        if updating and (asset.archived or asset.revision != revision):
            raise ValueError("Archived or stale Word structure; inspect before editing")
        data = self.repository.read(asset.asset_id, revision)
        catalog = self.stories.inspect(data)
        digest = hashlib.sha256(record_text(catalog).encode()).hexdigest()
        latest = next(
            item for item in reversed(asset.history) if item.sha256 == revision
        )
        if not updating:
            record = {
                "catalog": catalog,
                "catalog_sha256": digest,
                "operation_result": revision_result_dict(
                    self.repository, asset, latest
                ),
                "operation_receipt_policy": RECEIPT_POLICY,
            }
            return {
                "success": True,
                "asset_id": asset.asset_id,
                "inspected_revision": revision,
                "story_structure": page(
                    record, request.text_offset, request.text_limit
                ),
                "source_written": False,
                "review_required": STORY_REVIEW,
            }
        edit = request.docx_story_structure
        assert edit is not None
        if edit.expected_catalog_sha256 != digest:
            raise ValueError(
                "Word story catalog hash changed; read complete structure first"
            )
        updated, result = self.stories.change_structure(data, edit)
        changed = updated != data
        current_catalog = self.stories.inspect(updated)
        # Ensure the complete review is deliverable before committing any revision.
        record_text(
            {
                "catalog": current_catalog,
                "catalog_sha256": hashlib.sha256(
                    record_text(current_catalog).encode()
                ).hexdigest(),
                "operation_result": result.model_dump()
                if changed
                else revision_result_dict(self.repository, asset, latest),
                "operation_receipt_policy": RECEIPT_POLICY,
            }
        )
        committed = self.repository.commit(asset.asset_id, revision, updated, result)
        return {
            "success": True,
            "asset": native_asset_summary(committed, docx_enabled=True),
            "source_written": False,
            "operation_result": {
                "committed": changed,
                "changed_parts": result.changed_parts,
                "checks": result.checks,
                "review_required": result.review_required,
                "full_result_in": "read_docx_story_structure.operation_result"
                if changed
                else None,
            },
            "review_request": {
                "op": "read_docx_story_structure",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
            },
        }
