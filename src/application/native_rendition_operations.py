"""Persist converter output and its exact source receipt as a new native asset."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_operation_results import revision_result
from src.domain.native_asset_models import MAX_NATIVE_BYTES, NativeEditResult
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_pdf import PDF_MEDIA_TYPE

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
    )
    from src.domain.native_rendition import NativeWorkbookRenderer

MAX_RENDITION_RECEIPT_BYTES = 1024 * 1024


def rendition_receipt(
    asset: NativeFileAsset, revision: str, repository: NativeAssetRepository
) -> NativeEditResult | None:
    initial = asset.history[0]
    if asset.format != "pdf" or initial.sha256 != revision:
        return None
    report = revision_result(repository, asset, initial)
    if (
        report is not None
        and len(report.changes) == 1
        and report.changes[0].get("schema_version") == "native-rendition-v1"
    ):
        return report
    return None


def receipt_text(record: dict[str, Any]) -> str:
    text = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(text.encode("utf-8")) > MAX_RENDITION_RECEIPT_BYTES:
        raise ValueError("Rendition receipt exceeds the complete read-back budget")
    return text


class NativeRenditionOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        renderer: NativeWorkbookRenderer | None = None,
        ods_renderer: NativeWorkbookRenderer | None = None,
    ):
        self.repository = repository
        self.renderer = renderer
        self.ods_renderer = ods_renderer

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if request.op == "read_rendition":
            return self.read(request)
        assert request.asset_id is not None and request.revision is not None
        assert request.workbook_rendition is not None
        source = self.repository.load(request.asset_id)
        if source.format not in {"xlsx", "ods"}:
            raise ValueError("Workbook renditions require native XLSX or ODS assets")
        renderer = self.ods_renderer if source.format == "ods" else self.renderer
        if renderer is None:
            raise ValueError(
                "Workbook rendition renderer is not configured for this format"
            )
        data = self.repository.read(source.asset_id, request.revision)
        pdf, rendering = renderer.convert(data, request.workbook_rendition)
        revision = hashlib.sha256(pdf).hexdigest()
        if (
            not 0 < len(pdf) <= MAX_NATIVE_BYTES
            or rendering.get("rendered_pdf_sha256") != revision
        ):
            raise ValueError(
                "Rendered PDF byte count or identity does not match receipt"
            )
        source_ref = NativeFileReference(
            asset_id=source.asset_id, revision=request.revision
        )
        record = {
            "schema_version": "native-rendition-v1",
            "source_reference": source_ref.model_dump(),
            "requested": request.workbook_rendition.model_dump(),
            "rendering": rendering,
        }
        report = NativeEditResult(
            changed_parts=[],
            preserved_parts=0,
            changes=[record],
            checks=[
                "source_revision_pinned",
                "private_source_copy_unchanged",
                "rendered_pdf_parsed",
                "rendered_pdf_sha256",
                "complete_receipt_bounded",
            ],
        )
        receipt_text(
            report.model_dump()
        )  # Reject before creating an unreviewable asset.
        asset = self.repository.create(
            request.workbook_rendition.name, pdf, "pdf", PDF_MEDIA_TYPE, result=report
        )
        return {
            "success": True,
            "asset": native_asset_summary(asset, pdf_enabled=True),
            "source_reference": source_ref.model_dump(),
            "source_written": False,
            "page_count": rendering["page_count"],
            "review_required": report.review_required,
            "review_request": {
                "op": "read_rendition",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
            },
            "pages_request": {
                "op": "read_pdf",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
            },
        }

    def read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.revision is not None
        asset = self.repository.load(request.asset_id)
        report = rendition_receipt(asset, request.revision, self.repository)
        if report is None:
            raise ValueError(
                "No rendition receipt for this exact PDF creation revision"
            )
        self.repository.read(asset.asset_id, request.revision)
        text = receipt_text(report.model_dump())
        start = min(request.text_offset, len(text))
        end = min(start + request.text_limit, len(text))
        while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
            end = start + (end - start) // 2
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": request.revision,
            "source_written": False,
            "text_excerpt": text[start:end],
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "excerpt_char_range": [start, end],
            "next_text_offset": end if end < len(text) else None,
            "representation_complete": start == 0 and end == len(text),
            "serialization": "canonical-json; UTF-8 SHA-256",
            "review_boundary": "Exact conversion provenance; no semantic, visual or formula-result verdict. Page mappings apply only to this PDF revision.",
        }
