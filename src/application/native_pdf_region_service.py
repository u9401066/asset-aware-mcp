"""Verify source regions and deliver actual previews for Agent interpretation."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.domain.native_pdf import NativePdfReference
from src.domain.native_pdf_region import (
    NativePdfRegionReference,
    NativePdfRegionSelector,
    region_record,
)

if TYPE_CHECKING:
    from src.application.native_evidence_service import NativeEvidenceService
    from src.domain.native_assets import NativeDocumentRequest

REGION_BOUNDARY = "Geometry and source-page integrity only. Agent reviews the actual image, region coverage, transcription and semantic support. Previews may vary with renderer/fonts; old references never migrate."


class NativePdfRegionService:
    def __init__(self, evidence: NativeEvidenceService):
        self.evidence = evidence

    def record(
        self,
        reference: NativePdfReference | NativePdfRegionReference,
        selector: NativePdfRegionSelector | None = None,
    ) -> dict[str, Any]:
        if isinstance(reference, NativePdfRegionReference):
            if selector is not None:
                raise ValueError("Cannot override an existing PDF region selector")
            parent, selector = reference.parent, reference.selector
        else:
            if selector is None:
                raise ValueError(
                    "A PDF page reference requires an explicit pdf_region selector"
                )
            parent = reference
        page = self.evidence.read_parent_record(parent)
        if page.pop("evidence") != parent.model_dump(mode="json"):
            raise ValueError(
                "PDF region parent reference failed integrity verification"
            )
        record = region_record(parent, selector, page)
        if isinstance(reference, NativePdfRegionReference) and record[
            "evidence"
        ] != reference.model_dump(mode="json"):
            raise ValueError("PDF region reference failed integrity verification")
        return record

    def preview(
        self, reference: NativePdfRegionReference, width: int
    ) -> dict[str, Any]:
        return self._preview(self.record(reference), width)

    def _preview(self, record: dict[str, Any], width: int) -> dict[str, Any]:
        reference = NativePdfRegionReference.model_validate(record["evidence"])
        if self.evidence.pdfs is None:
            raise ValueError("Native PDF region renderer is not configured")
        data = self.evidence.repository.read(reference.asset_id, reference.revision)
        result = self.evidence.pdfs.render_region(
            data, reference.parent.locator, reference.selector, width
        )
        return {
            "success": True,
            "asset_id": reference.asset_id,
            "inspected_revision": reference.revision,
            "region": record,
            **result,
            "image_sha256": hashlib.sha256(result["image_png"]).hexdigest(),
            "source_written": False,
            "review_boundary": REGION_BOUNDARY,
        }

    def read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if not isinstance(
            request.reference, NativePdfReference | NativePdfRegionReference
        ):
            raise ValueError(
                "read_pdf_region requires a complete PDF page or region reference"
            )
        record = self.record(request.reference, request.pdf_region)
        return self._preview(record, request.render_size)

    def verify(self, reference: NativePdfRegionReference) -> dict[str, Any]:
        proof = self.evidence.verify(reference.parent)
        valid = False
        if proof["valid"]:
            expected = self.record(reference.parent, reference.selector)
            valid = expected["evidence"] == reference.model_dump(mode="json")
        return {
            **proof,
            "valid": valid,
            "verification_scope": reference.verification_scope,
            "checks": {
                "revision_hash": True,
                "parent_reference": proof["valid"],
                "region_representation_hash": valid,
            },
            "review_boundary": REGION_BOUNDARY,
        }
