"""Complete annotation evidence and receipts over guarded native PDF transactions."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_table_operations import RECEIPT_POLICY
from src.domain.native_pdf_annotations import ANNOTATION_REVIEW, PdfAnnotationCreate

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository, NativeDocumentRequest
    from src.domain.native_pdf import NativePdfAdapter


def annotation_text(record: dict[str, Any]) -> str:
    text = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text.encode()) > 16 * 1024 * 1024:
        raise ValueError("PDF annotation record and operation receipt exceed 16 MiB")
    return text


def attach_annotation_evidence(
    record: dict[str, Any], asset_id: str, revision: str
) -> None:
    digest = hashlib.sha256(annotation_text(record).encode()).hexdigest()
    record["evidence"] = {
        "schema_version": "native-pdf-annotation-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": record["locator"],
        "value_sha256": digest,
        "verification_scope": "immutable_native_representation",
    }


def annotation_catalog(pdfs: NativePdfAdapter, data: bytes) -> dict[str, Any]:
    catalog = pdfs.inspect_annotations(data)
    return {
        "catalog": catalog,
        "catalog_sha256": hashlib.sha256(annotation_text(catalog).encode()).hexdigest(),
    }


def annotation_page(record: dict[str, Any], offset: int, limit: int) -> dict[str, Any]:
    text = annotation_text(record)
    start = min(offset, len(text))
    end = min(start + limit, len(text))
    while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
        end = start + (end - start) // 2
    return {
        "text_excerpt": text[start:end],
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "text_length": len(text),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
    }


class NativePdfAnnotationOperations:
    def __init__(self, repository: NativeAssetRepository, pdfs: NativePdfAdapter):
        self.repository, self.pdfs = repository, pdfs

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "pdf":
            raise ValueError("This format has no native PDF annotations")
        updating = request.op == "update_pdf_annotations"
        revision = request.expected_revision if updating else request.revision
        assert revision is not None
        if updating and (asset.archived or asset.revision != revision):
            raise ValueError("Archived or stale native PDF; inspect before editing")
        data = self.repository.read(asset.asset_id, revision)
        if not updating:
            if request.op == "read_pdf_annotations":
                record = annotation_catalog(self.pdfs, data)
            else:
                assert request.pdf_annotation_locator is not None
                record = self.pdfs.read_annotation(data, request.pdf_annotation_locator)
                attach_annotation_evidence(record, asset.asset_id, revision)
            latest = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            record["operation_result"] = (
                latest.result.model_dump() if latest.result else None
            )
            record["operation_receipt_policy"] = RECEIPT_POLICY
            return {
                "success": True,
                "asset_id": asset.asset_id,
                "inspected_revision": revision,
                "annotation": annotation_page(
                    record, request.text_offset, request.text_limit
                ),
                "source_written": False,
                "review_required": ANNOTATION_REVIEW,
            }
        assert request.pdf_annotations_update is not None
        for edit in request.pdf_annotations_update.edits:
            ref = (
                edit.page_reference
                if isinstance(edit, PdfAnnotationCreate)
                else edit.reference
            )
            if ref.asset_id != asset.asset_id or ref.revision != revision:
                raise ValueError(
                    "PDF annotation edit references a different asset or revision"
                )
        updated, checks = self.pdfs.edit_annotations(
            data, request.pdf_annotations_update
        )
        changed = updated != data
        annotation_text(
            {
                **annotation_catalog(self.pdfs, updated),
                "operation_result": checks.model_dump() if changed else None,
                "operation_receipt_policy": RECEIPT_POLICY,
            }
        )
        committed = self.repository.commit(asset.asset_id, revision, updated, checks)
        return {
            "success": True,
            "asset": native_asset_summary(committed, pdf_enabled=True),
            "source_written": False,
            "operation_result": {
                "committed": changed,
                "changed_parts": checks.changed_parts,
                "checks": checks.checks,
                "review_required": checks.review_required,
                "full_result_in": "read_pdf_annotations.operation_result"
                if changed
                else None,
            },
            "review_request": {
                "op": "read_pdf_annotations",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
            },
        }
