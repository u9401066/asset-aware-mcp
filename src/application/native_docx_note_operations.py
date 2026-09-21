"""Complete note delivery and atomic revision-bound content/definition operations."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_story_operations import page
from src.application.native_docx_table_operations import RECEIPT_POLICY, record_text
from src.application.native_operation_results import revision_result_dict
from src.domain.native_docx_notes import NOTE_REVIEW

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeAssetRepository
    from src.domain.native_assets import NativeDocumentRequest
    from src.domain.native_docx_notes import NativeDocxNoteAdapter


def attach_note_evidence(record: dict[str, Any], asset_id: str, revision: str) -> None:
    canonical = record_text(record)
    record["evidence"] = {
        "schema_version": "native-docx-note-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": record["locator"],
        "value_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "verification_scope": "immutable_native_representation",
    }


def catalog_record(notes: NativeDocxNoteAdapter, data: bytes) -> dict[str, Any]:
    listing = notes.inspect(data)
    return {
        "catalog": listing,
        "catalog_sha256": hashlib.sha256(record_text(listing).encode()).hexdigest(),
    }


class NativeDocxNoteOperations:
    def __init__(self, repository: NativeAssetRepository, notes: NativeDocxNoteAdapter):
        self.repository, self.notes = repository, notes

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx":
            raise ValueError("This format has no native Word notes")
        updating = request.op.startswith("update_")
        structure = request.op in {"read_docx_notes", "update_docx_notes"}
        revision = request.expected_revision if updating else request.revision
        assert revision is not None
        if updating and (asset.archived or asset.revision != revision):
            raise ValueError("Archived or stale native DOCX; inspect before editing")
        data = self.repository.read(asset.asset_id, revision)
        if not updating:
            if structure:
                record = catalog_record(self.notes, data)
            else:
                assert request.docx_note_locator is not None
                record = self.notes.read(data, request.docx_note_locator)
                attach_note_evidence(record, asset.asset_id, revision)
            latest = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            record["operation_result"] = revision_result_dict(
                self.repository, asset, latest
            )
            record["operation_receipt_policy"] = RECEIPT_POLICY
            return {
                "success": True,
                "asset_id": asset.asset_id,
                "inspected_revision": revision,
                "note": page(record, request.text_offset, request.text_limit),
                "source_written": False,
                "review_required": NOTE_REVIEW,
            }
        if structure:
            assert request.docx_notes_update is not None
            updated, checks = self.notes.change_structure(
                data, request.docx_notes_update
            )
            final = catalog_record(self.notes, updated)
        else:
            assert (
                request.docx_note_update is not None
                and request.docx_note_reference is not None
            )
            update = request.docx_note_update
            original = self.notes.read(data, update.locator)
            attach_note_evidence(original, asset.asset_id, revision)
            if original["evidence"] != request.docx_note_reference.model_dump():
                raise ValueError(
                    "Word note reference differs from the current asset/revision/locator"
                )
            updated, checks = self.notes.edit(data, update)
            final = self.notes.read(updated, update.locator)
            attach_note_evidence(
                final, asset.asset_id, hashlib.sha256(updated).hexdigest()
            )
        changed = updated != data
        record_text(
            {
                **final,
                "operation_result": checks.model_dump() if changed else None,
                "operation_receipt_policy": RECEIPT_POLICY,
            }
        )
        committed = self.repository.commit(asset.asset_id, revision, updated, checks)
        read_op = "read_docx_notes" if structure else "read_docx_note"
        review: dict[str, Any] = {
            "op": read_op,
            "asset_id": asset.asset_id,
            "revision": committed.revision,
        }
        if not structure:
            assert request.docx_note_update is not None
            review["docx_note_locator"] = request.docx_note_update.locator.model_dump()
        return {
            "success": True,
            "asset": native_asset_summary(committed, docx_enabled=True),
            "source_written": False,
            "operation_result": {
                "committed": changed,
                "changed_parts": checks.changed_parts,
                "checks": checks.checks,
                "review_required": checks.review_required,
                "full_result_in": read_op + ".operation_result" if changed else None,
            },
            "review_request": review,
        }
