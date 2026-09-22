"""Managed PDF fields with complete, hash-pinned reads and atomic native receipts."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_table_operations import RECEIPT_POLICY
from src.application.native_operation_results import revision_result_dict
from src.domain.native_asset_models import MAX_NATIVE_RESULT_BYTES
from src.domain.native_pdf_fields import FIELD_REVIEW, PdfFieldCreate

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository, NativeDocumentRequest
    from src.domain.native_pdf import NativePdfAdapter, NativePdfReference
    from src.domain.native_pdf_fields import PdfFieldReference


def field_record_text(record: dict[str, Any]) -> str:
    text = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    # Complete native catalog + immutable operation envelope + record metadata.
    if len(text.encode("utf-8")) > 2 * MAX_NATIVE_RESULT_BYTES + 16 * 1024 * 1024:
        raise ValueError("PDF field response exceeds its complete read budget")
    return text


def attach_field_evidence(record: dict[str, Any], asset_id: str, revision: str) -> None:
    record["evidence"] = {
        "schema_version": "native-pdf-field-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": record["locator"],
        "value_sha256": hashlib.sha256(field_record_text(record).encode()).hexdigest(),
        "verification_scope": "immutable_native_representation",
    }


def field_page(
    record: dict[str, Any], request: NativeDocumentRequest
) -> dict[str, Any]:
    text = field_record_text(record)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if request.text_offset and request.pdf_field_text_sha256 is None:
        raise ValueError("PDF field continuation requires pdf_field_text_sha256")
    if (
        request.pdf_field_text_sha256 is not None
        and request.pdf_field_text_sha256 != sha
    ):
        raise ValueError("PDF field response changed; restart the complete read")
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
        "review_required": FIELD_REVIEW,
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
            raise ValueError("PDF field response exceeds the MCP budget")
        end = start + (end - start) // 2


class NativePdfFieldOperations:
    def __init__(self, repository: NativeAssetRepository, pdfs: NativePdfAdapter):
        self.repository, self.pdfs = repository, pdfs

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "pdf":
            raise ValueError("Native PDF field operations require a PDF asset")
        updating = request.op == "update_pdf_fields"
        revision = request.expected_revision if updating else request.revision
        assert revision is not None
        if updating and (asset.archived or asset.revision != revision):
            raise ValueError("Archived or stale native PDF; inspect before editing")
        data = self.repository.read(asset.asset_id, revision)
        if not updating:
            if request.op == "read_pdf_fields":
                history = next(
                    h for h in reversed(asset.history) if h.sha256 == revision
                )
                record = {
                    "schema_version": "native-pdf-fields-read-v1",
                    "catalog": self.pdfs.inspect_fields(data),
                    "operation_result": revision_result_dict(
                        self.repository, asset, history
                    ),
                    "operation_receipt_policy": RECEIPT_POLICY,
                }
            else:
                assert request.pdf_field_locator is not None
                field = self.pdfs.read_field(data, request.pdf_field_locator)
                attach_field_evidence(field, asset.asset_id, revision)
                record = {"schema_version": "native-pdf-field-read-v1", "field": field}
            return field_page(record, request)

        assert request.pdf_fields_update is not None
        for edit in request.pdf_fields_update.edits:
            references: list[NativePdfReference | PdfFieldReference]
            if isinstance(edit, PdfFieldCreate):
                references = [widget.page_reference for widget in edit.field.widgets]
                if edit.parent_reference is not None:
                    references.append(edit.parent_reference)
            else:
                references = [edit.reference]
            if any(
                (ref.asset_id, ref.revision) != (asset.asset_id, revision)
                for ref in references
            ):
                raise ValueError(
                    "PDF field edit references a different asset or revision"
                )
        updated, report = self.pdfs.edit_fields(data, request.pdf_fields_update)
        changed = updated != data
        full_result = report.model_dump(mode="json")
        field_record_text(
            {
                "catalog": self.pdfs.inspect_fields(updated),
                "operation_result": full_result,
            }
        )
        committed = self.repository.commit(asset.asset_id, revision, updated, report)
        result: dict[str, Any] = {
            "success": True,
            "asset": native_asset_summary(committed, pdf_enabled=True),
            "source_written": False,
            "operation_result": {
                "committed": changed,
                "changed_parts": report.changed_parts,
                "checks": report.checks,
                "review_required": report.review_required,
                "full_result_in": "read_pdf_fields.operation_result"
                if changed
                else "operation_result.full_result",
            },
            "review_request": {
                "op": "read_pdf_fields",
                "asset_id": committed.asset_id,
                "revision": committed.revision,
            },
        }
        if not changed:
            result["operation_result"]["full_result"] = full_result
        return result
