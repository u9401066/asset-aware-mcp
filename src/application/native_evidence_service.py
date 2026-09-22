"""Native evidence integrity against immutable file revisions, independent of display."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_docx_note_operations import attach_note_evidence
from src.application.native_docx_story_operations import attach_story_evidence
from src.application.native_image_evidence import NativeImageEvidence
from src.application.native_pdf_annotation_operations import attach_annotation_evidence
from src.application.native_pdf_field_operations import attach_field_evidence
from src.application.native_pdf_operations import PDF_REVIEW, attach_pdf_evidence
from src.application.native_pdf_region_service import NativePdfRegionService
from src.application.native_pptx_operations import attach_pptx_evidence
from src.application.native_selection_service import NativeSelectionService
from src.domain.native_assets import NativeCellReference, NativeDocxBlockReference
from src.domain.native_delimited import (
    DELIMITED_REVIEW,
    NativeDelimitedReference,
    attach_delimited_evidence,
)
from src.domain.native_docx_notes import NOTE_REVIEW, DocxNoteReference
from src.domain.native_docx_stories import STORY_REVIEW, DocxStoryReference
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_image import (
    NativeImageFrameReference,
    NativeImageRegionReference,
)
from src.domain.native_ods import (
    ODS_REVIEW,
    NativeODSCellReference,
    attach_ods_evidence,
)
from src.domain.native_pdf import NativePdfReference
from src.domain.native_pdf_annotations import ANNOTATION_REVIEW, PdfAnnotationReference
from src.domain.native_pdf_fields import FIELD_REVIEW, PdfFieldReference
from src.domain.native_pdf_region import NativePdfRegionReference
from src.domain.native_pptx import NativePptxReference
from src.domain.native_selection import NativeSelectionReference

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeSpreadsheetAdapter,
    )
    from src.domain.native_delimited import NativeDelimitedAdapter
    from src.domain.native_docx import NativeDocxAdapter
    from src.domain.native_docx_notes import NativeDocxNoteAdapter
    from src.domain.native_docx_stories import NativeDocxStoryAdapter
    from src.domain.native_image import NativeImageAdapter
    from src.domain.native_image_archive import NativeImageArchive
    from src.domain.native_ods import NativeODSAdapter
    from src.domain.native_pdf import NativePdfAdapter
    from src.domain.native_pptx import NativePresentationAdapter
    from src.domain.native_selection import NativeSelectionParent


def attach_native_evidence(cell: dict[str, Any], asset_id: str, revision: str) -> None:
    canonical = json.dumps(
        cell, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    cell["evidence"] = {
        "schema_version": "native-cell-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": dict(cell["locator"]),
        "value_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "verification_scope": "immutable_native_representation",
    }


class NativeEvidenceService:
    def __init__(
        self,
        repository: NativeAssetRepository,
        spreadsheets: NativeSpreadsheetAdapter,
        docx: NativeDocxAdapter | None = None,
        presentations: NativePresentationAdapter | None = None,
        pdfs: NativePdfAdapter | None = None,
        delimited: NativeDelimitedAdapter | None = None,
        docx_stories: NativeDocxStoryAdapter | None = None,
        docx_notes: NativeDocxNoteAdapter | None = None,
        images: NativeImageAdapter | None = None,
        image_archive: NativeImageArchive | None = None,
        ods: NativeODSAdapter | None = None,
    ):
        self.ods = ods
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.docx = docx
        self.presentations = presentations
        self.pdfs = pdfs
        self.delimited = delimited
        self.docx_stories = docx_stories
        self.docx_notes = docx_notes
        self.images = images
        self.image_archive = image_archive

    def _image_evidence(self) -> NativeImageEvidence:
        if self.images is None:
            raise ValueError("Native image adapter is not configured")
        return NativeImageEvidence(self.repository, self.images, self.image_archive)

    def read_parent_record(self, reference: NativeSelectionParent) -> dict[str, Any]:
        if isinstance(reference, NativeImageRegionReference):
            return self._image_evidence().region(reference)
        if isinstance(reference, NativeImageFrameReference):
            return self._image_evidence().frame(reference)
        if isinstance(reference, NativePdfRegionReference):
            return NativePdfRegionService(self).record(reference)
        asset = self.repository.load(reference.asset_id)
        data = self.repository.read(reference.asset_id, reference.revision)
        if (
            isinstance(reference, NativeODSCellReference)
            and asset.format == "ods"
            and self.ods
        ):
            record = self.ods.read_cell(data, reference.locator)
            attach_ods_evidence(record, asset.asset_id, reference.revision)
        elif isinstance(reference, NativeCellReference) and asset.format in {
            "xlsx",
            "xlsm",
        }:
            record = self.spreadsheets.read_cell_by_locator(data, reference.locator)
            attach_native_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, NativeDocxBlockReference)
            and asset.format == "docx"
            and self.docx
        ):
            record = self.docx.read_block(
                data,
                asset.asset_id,
                reference.revision,
                reference.locator.block_id,
                reference.locator,
            )
        elif (
            isinstance(reference, DocxNoteReference)
            and asset.format == "docx"
            and self.docx_notes
        ):
            record = self.docx_notes.read(data, reference.locator)
            attach_note_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, DocxStoryReference)
            and asset.format == "docx"
            and self.docx_stories
        ):
            record = self.docx_stories.read(data, reference.locator.part)
            attach_story_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, NativePptxReference)
            and asset.format == "pptx"
            and self.presentations
        ):
            record = self.presentations.read_shape(data, reference.locator)
            attach_pptx_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, PdfFieldReference)
            and asset.format == "pdf"
            and self.pdfs
        ):
            record = self.pdfs.read_field(data, reference.locator)
            attach_field_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, PdfAnnotationReference)
            and asset.format == "pdf"
            and self.pdfs
        ):
            record = self.pdfs.read_annotation(data, reference.locator)
            attach_annotation_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, NativePdfReference)
            and asset.format == "pdf"
            and self.pdfs
        ):
            record = self.pdfs.read_page(data, reference.locator)
            attach_pdf_evidence(record, asset.asset_id, reference.revision)
        elif (
            isinstance(reference, NativeDelimitedReference)
            and asset.format in {"csv", "tsv"}
            and self.delimited
        ):
            record = self.delimited.read_cell(
                data, reference.dialect, reference.locator.row, reference.locator.column
            )
            attach_delimited_evidence(record, asset.asset_id, reference.revision)
        else:
            raise ValueError("This format has no configured native selection reader")
        return record

    def verify(
        self,
        reference: NativeCellReference
        | NativeDocxBlockReference
        | DocxStoryReference
        | DocxNoteReference
        | NativePptxReference
        | NativePdfReference
        | PdfAnnotationReference
        | PdfFieldReference
        | NativePdfRegionReference
        | NativeDelimitedReference
        | NativeODSCellReference
        | NativeImageFrameReference
        | NativeImageRegionReference
        | NativeFileReference
        | NativeSelectionReference,
    ) -> dict[str, Any]:
        if isinstance(
            reference, NativeImageFrameReference | NativeImageRegionReference
        ):
            return self._image_evidence().verify(reference)
        if isinstance(reference, (PdfAnnotationReference, PdfFieldReference)):
            asset = self.repository.load(reference.asset_id)
            record = self.read_parent_record(reference)
            valid = record["evidence"] == reference.model_dump()
            return {
                "success": True,
                "valid": valid,
                "asset_id": asset.asset_id,
                "revision": reference.revision,
                "is_current_managed_revision": asset.revision == reference.revision,
                "archived": asset.archived,
                "verification_scope": "immutable_native_representation",
                "checks": {
                    "revision_hash": True,
                    "field_representation_hash"
                    if isinstance(reference, PdfFieldReference)
                    else "annotation_representation_hash": valid,
                },
                "source_freshness": "not_checked; refresh tracks external human edits",
                "review_required": FIELD_REVIEW
                if isinstance(reference, PdfFieldReference)
                else ANNOTATION_REVIEW,
            }
        if isinstance(reference, (DocxStoryReference, DocxNoteReference)):
            asset = self.repository.load(reference.asset_id)
            record = self.read_parent_record(reference)
            valid = record["evidence"] == reference.model_dump()
            return {
                "success": True,
                "valid": valid,
                "asset_id": asset.asset_id,
                "revision": reference.revision,
                "is_current_managed_revision": asset.revision == reference.revision,
                "archived": asset.archived,
                "verification_scope": "immutable_native_representation",
                "checks": {
                    "revision_hash": True,
                    "note_representation_hash"
                    if isinstance(reference, DocxNoteReference)
                    else "story_representation_hash": valid,
                },
                "source_freshness": "not_checked; refresh tracks external human edits",
                "review_required": NOTE_REVIEW
                if isinstance(reference, DocxNoteReference)
                else STORY_REVIEW,
            }
        if isinstance(reference, NativeSelectionReference):
            return NativeSelectionService(self).verify(reference)
        if isinstance(reference, NativePdfRegionReference):
            return NativePdfRegionService(self).verify(reference)
        if isinstance(reference, NativeODSCellReference):
            asset = self.repository.load(reference.asset_id)
            record = self.read_parent_record(reference)
            valid = record["evidence"] == reference.model_dump(mode="json")
            return {
                "success": True,
                "valid": valid,
                "asset_id": asset.asset_id,
                "revision": reference.revision,
                "is_current_managed_revision": asset.revision == reference.revision,
                "archived": asset.archived,
                "verification_scope": reference.verification_scope,
                "checks": {
                    "revision_hash": True,
                    "native_locator": True,
                    "cell_representation_hash": valid,
                },
                "source_freshness": "not_checked; refresh tracks external human edits",
                "reference_scope": "one_logical_coordinate; repetition metadata is not coverage verification",
                "review_required": list(ODS_REVIEW),
            }
        if isinstance(reference, NativeDelimitedReference):
            return self._verify_delimited(reference)
        if isinstance(reference, NativeFileReference):
            return self._verify_file(reference)
        if isinstance(reference, NativePdfReference):
            return self._verify_pdf(reference)
        if isinstance(reference, NativePptxReference):
            return self._verify_pptx(reference)
        if isinstance(reference, NativeDocxBlockReference):
            return self._verify_docx(reference)
        asset = self.repository.load(reference.asset_id)
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native cell verifier")
        data = self.repository.read(reference.asset_id, reference.revision)
        cell = self.spreadsheets.read_cell_by_locator(data, reference.locator)
        attach_native_evidence(cell, reference.asset_id, reference.revision)
        valid = cell["evidence"] == reference.model_dump()
        return {
            "success": True,
            "valid": valid,
            "asset_id": reference.asset_id,
            "revision": reference.revision,
            "is_current_managed_revision": asset.revision == reference.revision,
            "archived": asset.archived,
            "verification_scope": "immutable_native_representation",
            "checks": {
                "revision_hash": True,
                "native_locator": True,
                "cell_representation_hash": valid,
            },
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "formula_results",
            ],
        }

    def _verify_delimited(self, reference: NativeDelimitedReference) -> dict[str, Any]:
        asset = self.repository.load(reference.asset_id)
        record = self.read_parent_record(reference)
        valid = record["evidence"] == reference.model_dump(mode="json")
        return {
            "success": True,
            "valid": valid,
            "asset_id": asset.asset_id,
            "revision": reference.revision,
            "is_current_managed_revision": asset.revision == reference.revision,
            "archived": asset.archived,
            "verification_scope": "immutable_delimited_field",
            "checks": {
                "revision_hash": True,
                "dialect_and_locator": record["locator"]
                == reference.locator.model_dump()
                and record["dialect"] == reference.dialect.model_dump(),
                "field_representation_hash": valid,
            },
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": DELIMITED_REVIEW,
        }

    def _verify_docx(self, reference: NativeDocxBlockReference) -> dict[str, Any]:
        asset = self.repository.load(reference.asset_id)
        if asset.format != "docx" or self.docx is None:
            raise ValueError("This format has no native DOCX verifier")
        data = self.repository.read(reference.asset_id, reference.revision)
        record = self.docx.read_block(
            data,
            reference.asset_id,
            reference.revision,
            reference.locator.block_id,
            reference.locator,
        )
        valid = record["evidence"] == reference.model_dump()
        return {
            "success": True,
            "valid": valid,
            "asset_id": reference.asset_id,
            "revision": reference.revision,
            "is_current_managed_revision": asset.revision == reference.revision,
            "archived": asset.archived,
            "verification_scope": "immutable_native_representation",
            "checks": {
                "revision_hash": True,
                "native_locator": True,
                "block_representation_hash": valid,
            },
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "fields_and_revisions",
            ],
        }

    def _verify_file(self, reference: NativeFileReference) -> dict[str, Any]:
        asset = self.repository.load(reference.asset_id)
        data = self.repository.read(asset.asset_id, reference.revision)
        valid = hashlib.sha256(data).hexdigest() == reference.revision
        return {
            "success": True,
            "valid": valid,
            "asset_id": asset.asset_id,
            "revision": reference.revision,
            "archived": asset.archived,
            "is_current_managed_revision": asset.revision == reference.revision,
            "verification_scope": "immutable_file_bytes",
            "checks": {"revision_hash": valid},
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "content_interpretation",
            ],
        }

    def _verify_pdf(self, reference: NativePdfReference) -> dict[str, Any]:
        asset = self.repository.load(reference.asset_id)
        if asset.format != "pdf" or self.pdfs is None:
            raise ValueError("This format has no native PDF verifier")
        record = self.pdfs.read_page(
            self.repository.read(asset.asset_id, reference.revision), reference.locator
        )
        attach_pdf_evidence(record, asset.asset_id, reference.revision)
        valid = record["evidence"] == reference.model_dump()
        return {
            "success": True,
            "valid": valid,
            "asset_id": asset.asset_id,
            "revision": reference.revision,
            "is_current_managed_revision": asset.revision == reference.revision,
            "archived": asset.archived,
            "verification_scope": "immutable_native_representation",
            "checks": {
                "revision_hash": True,
                "native_locator": True,
                "page_representation_hash": valid,
            },
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": PDF_REVIEW,
        }

    def _verify_pptx(self, reference: NativePptxReference) -> dict[str, Any]:
        asset = self.repository.load(reference.asset_id)
        if asset.format != "pptx" or self.presentations is None:
            raise ValueError("This format has no native PPTX verifier")
        record = self.presentations.read_shape(
            self.repository.read(reference.asset_id, reference.revision),
            reference.locator,
        )
        attach_pptx_evidence(record, reference.asset_id, reference.revision)
        valid = record["evidence"] == reference.model_dump()
        return {
            "success": True,
            "valid": valid,
            "asset_id": reference.asset_id,
            "revision": reference.revision,
            "is_current_managed_revision": asset.revision == reference.revision,
            "archived": asset.archived,
            "verification_scope": "immutable_native_representation",
            "checks": {
                "revision_hash": True,
                "native_locator": True,
                "shape_representation_hash": valid,
            },
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "text_overflow",
                "inherited_formatting",
            ],
        }
