"""Native PDF use cases: immutable evidence, composition and guarded revisions."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_pptx_operations import shape_excerpt as component_excerpt
from src.domain.native_pdf import PDF_MEDIA_TYPE

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeEditResult,
        NativeFileAsset,
    )
    from src.domain.native_pdf import NativePdfAdapter, NativePdfPageInput

PDF_REVIEW = [
    "semantic_accuracy",
    "full_resolution_rendering",
    "forms_and_viewer_behavior",
    "accessibility",
    "logical_reading_order",
]


def attach_pdf_evidence(record: dict[str, Any], asset_id: str, revision: str) -> None:
    canonical = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    record["evidence"] = {
        "schema_version": "native-pdf-page-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": record["locator"],
        "value_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "verification_scope": "immutable_native_representation",
    }


class NativePdfOperations:
    def __init__(self, repository: NativeAssetRepository, pdfs: NativePdfAdapter):
        self.repository = repository
        self.pdfs = pdfs

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "create_pdf": self._create,
            "read_pdf": self._read,
            "read_pdf_page": self._read_page,
            "render_pdf_page": self._render,
            "add_pdf_pages": self._update,
            "update_pdf": self._update,
            "delete_pdf_pages": self._update,
            "reorder_pdf_pages": self._update,
        }[request.op](request)

    def _source(
        self, request: NativeDocumentRequest
    ) -> tuple[bytes, NativeFileAsset, str]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "pdf":
            raise ValueError("This format has no native PDF adapter")
        revision = request.revision or asset.revision
        return self.repository.read(asset.asset_id, revision), asset, revision

    def _sources(self, inputs: list[NativePdfPageInput]) -> dict[str, bytes]:
        sources: dict[str, bytes] = {}
        size = 0
        for item in inputs:
            if item.reference is None:
                continue
            ref = item.reference
            key = f"{ref.asset_id}:{ref.revision}"
            if key in sources:
                continue
            if self.repository.load(ref.asset_id).format != "pdf":
                raise ValueError("PDF composition source must be a native PDF asset")
            sources[key] = self.repository.read(ref.asset_id, ref.revision)
            size += len(sources[key])
            if size > 64 * 1024 * 1024:
                raise ValueError("PDF composition sources exceed 64 MiB in aggregate")
        return sources

    def _create(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.pdf_create is not None
        data, report = self.pdfs.create(
            request.pdf_create, self._sources(request.pdf_create.pages)
        )
        asset = self.repository.create(
            request.pdf_create.name, data, "pdf", PDF_MEDIA_TYPE, result=report
        )
        return {
            "success": True,
            "asset": native_asset_summary(asset, pdf_enabled=True),
            "operation_result": report.model_dump(),
            "source_written": False,
            "review_required": PDF_REVIEW,
        }

    def _read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        data, asset, revision = self._source(request)
        metadata = self.pdfs.inspect(data)
        pages = metadata.pop("pages")
        end = request.offset + request.limit
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": revision,
            "metadata": metadata,
            "pages": pages[request.offset : end],
            "next_offset": end if end < len(pages) else None,
            "review_required": PDF_REVIEW,
        }

    def _read_page(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.pdf_locator is not None
        data, asset, revision = self._source(request)
        record = self.pdfs.read_page(data, request.pdf_locator)
        attach_pdf_evidence(record, asset.asset_id, revision)
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": revision,
            "page": component_excerpt(record, request.text_offset, request.text_limit),
            "review_required": PDF_REVIEW,
        }

    def _render(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.pdf_locator is not None
        data, asset, revision = self._source(request)
        png = self.pdfs.render(data, request.pdf_locator, request.render_size)
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": revision,
            "locator": request.pdf_locator.model_dump(),
            "image_png": png,
            "image_sha256": hashlib.sha256(png).hexdigest(),
            "review_required": PDF_REVIEW,
        }

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.expected_revision is not None
        data, asset, revision = self._source(request)
        if asset.archived or revision != request.expected_revision:
            raise ValueError("Archived or stale native PDF asset")
        references = (
            request.pdf_page_refs
            + request.pdf_order
            + [edit.reference for edit in request.pdf_edits]
        )
        if any(
            ref.asset_id != asset.asset_id or ref.revision != revision
            for ref in references
        ):
            raise ValueError("PDF mutation reference has a different asset or revision")
        updated, report = self._mutate(data, request)
        committed = self.repository.commit(asset.asset_id, revision, updated, report)
        return {
            "success": True,
            "asset": native_asset_summary(committed, pdf_enabled=True),
            "operation_result": report.model_dump(),
            "source_written": False,
            "review_request": {
                "op": "read_pdf",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
            },
        }

    def _mutate(
        self, data: bytes, request: NativeDocumentRequest
    ) -> tuple[bytes, NativeEditResult]:
        if request.op == "add_pdf_pages":
            assert request.pdf_insert is not None
            return self.pdfs.insert(
                data, request.pdf_insert, self._sources(request.pdf_insert.pages)
            )
        if request.op == "update_pdf":
            return self.pdfs.edit(data, request.pdf_edits)
        if request.op == "delete_pdf_pages":
            return self.pdfs.delete(data, request.pdf_page_refs)
        return self.pdfs.reorder(data, request.pdf_order)
