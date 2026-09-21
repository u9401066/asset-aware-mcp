"""Revision-bound story discovery, complete evidence pages and shared-content edits."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_table_operations import RECEIPT_POLICY, record_text
from src.application.native_operation_results import revision_result_dict
from src.domain.native_docx_stories import STORY_REVIEW

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeAssetRepository
    from src.domain.native_assets import NativeDocumentRequest
    from src.domain.native_docx_stories import NativeDocxStoryAdapter


def attach_story_evidence(record: dict[str, Any], asset_id: str, revision: str) -> None:
    canonical = record_text(record)
    record["evidence"] = {
        "schema_version": "native-docx-story-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": record["locator"],
        "value_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "verification_scope": "immutable_native_representation",
    }


def page(record: dict[str, Any], offset: int, limit: int) -> dict[str, Any]:
    text = record_text(record)
    start = min(offset, len(text))
    end = min(start + limit, len(text))
    while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
        end = start + (end - start) // 2
    return {
        "text_excerpt": text[start:end],
        "text_length": len(text),
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
    }


class NativeDocxStoryOperations:
    def __init__(
        self, repository: NativeAssetRepository, stories: NativeDocxStoryAdapter
    ):
        self.repository, self.stories = repository, stories

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx":
            raise ValueError("This format has no native Word stories")
        updating = request.op == "update_docx_story"
        revision = request.expected_revision if updating else request.revision
        assert revision is not None
        if updating and (asset.archived or asset.revision != revision):
            raise ValueError("Archived or stale native DOCX; inspect before editing")
        data = self.repository.read(asset.asset_id, revision)
        if request.op == "read_docx_stories":
            record = self.stories.inspect(data)
        elif not updating:
            assert request.docx_story_part is not None
            record = self.stories.read(data, request.docx_story_part)
            attach_story_evidence(record, asset.asset_id, revision)
            latest = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            record["operation_result"] = revision_result_dict(
                self.repository, asset, latest
            )
            record["operation_receipt_policy"] = RECEIPT_POLICY
        else:
            assert (
                request.docx_story_update is not None
                and request.docx_story_reference is not None
            )
            update = request.docx_story_update
            original = self.stories.read(data, update.part)
            attach_story_evidence(original, asset.asset_id, revision)
            if original["evidence"] != request.docx_story_reference.model_dump():
                raise ValueError(
                    "Word story reference differs from the current asset/revision/part"
                )
            updated, checks = self.stories.edit(data, update)
            new_revision = hashlib.sha256(updated).hexdigest()
            final = self.stories.read(updated, update.part)
            attach_story_evidence(final, asset.asset_id, new_revision)
            changed = updated != data
            record_text(
                {
                    **final,
                    "operation_result": checks.model_dump() if changed else None,
                    "operation_receipt_policy": RECEIPT_POLICY,
                }
            )
            committed = self.repository.commit(
                asset.asset_id, revision, updated, checks
            )
            return {
                "success": True,
                "asset": native_asset_summary(committed, docx_enabled=True),
                "source_written": False,
                "operation_result": {
                    "committed": changed,
                    "changed_parts": checks.changed_parts,
                    "checks": checks.checks,
                    "review_required": checks.review_required,
                    "full_result_in": "read_docx_story.operation_result"
                    if changed
                    else None,
                },
                "review_request": {
                    "op": "read_docx_story",
                    "asset_id": asset.asset_id,
                    "revision": committed.revision,
                    "docx_story_part": update.part,
                },
            }
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": revision,
            "story": page(record, request.text_offset, request.text_limit),
            "source_written": False,
            "review_required": STORY_REVIEW,
        }
