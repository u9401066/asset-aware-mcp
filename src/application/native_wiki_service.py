"""Create portable native evidence snapshots without mutating sources or old notes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_delimited_operations import dialect_for
from src.application.native_delimited_wiki import NativeDelimitedWikiContent
from src.application.native_derivation_wiki import add_derivations
from src.application.native_docx_note_operations import attach_note_evidence
from src.application.native_docx_note_wiki import NativeDocxNoteWikiContent
from src.application.native_docx_story_operations import attach_story_evidence
from src.application.native_docx_story_wiki import NativeDocxStoryWikiContent
from src.application.native_docx_wiki import NativeDocxWikiContent
from src.application.native_evidence_service import attach_native_evidence
from src.application.native_image_lineage import add_image_inputs
from src.application.native_image_projection import NativeImageProjection
from src.application.native_image_wiki import NativeImageWikiContent
from src.application.native_ods_wiki import NativeODSWikiContent
from src.application.native_operation_results import revision_result_dict
from src.application.native_pdf_annotation_operations import attach_annotation_evidence
from src.application.native_pdf_annotation_wiki import NativePdfAnnotationWikiContent
from src.application.native_pdf_operations import attach_pdf_evidence
from src.application.native_pdf_wiki import NativePdfWikiContent
from src.application.native_pptx_operations import attach_pptx_evidence
from src.application.native_pptx_wiki import NativePptxWikiContent
from src.application.native_rendition_wiki import add_rendition
from src.application.native_wiki_format import NativeWikiContent
from src.domain.citation_format import CitationMetadata, resolve_citation_format
from src.domain.native_delimited import attach_delimited_evidence
from src.domain.native_derivation import fingerprint
from src.domain.native_image import (
    IMAGE_EXTENSIONS,
    NativeImageFrameReference,
    NativeImageRegionReference,
)
from src.domain.native_ods import attach_ods_evidence
from src.domain.native_selection import NativeSelectionReference
from src.domain.native_wiki import MAX_WIKI_CELLS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.application.native_derivation_service import NativeDerivationService
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
        NativeSpreadsheetAdapter,
    )
    from src.domain.native_delimited import NativeDelimitedAdapter
    from src.domain.native_derivation import NativeDerivationLedger
    from src.domain.native_docx import NativeDocxAdapter
    from src.domain.native_docx_notes import NativeDocxNoteAdapter
    from src.domain.native_docx_stories import NativeDocxStoryAdapter
    from src.domain.native_image import NativeImageAdapter
    from src.domain.native_image_archive import NativeImageArchive
    from src.domain.native_ods import NativeODSAdapter
    from src.domain.native_pdf import NativePdfAdapter
    from src.domain.native_pptx import NativePresentationAdapter
    from src.domain.native_wiki import NativeWikiPublisher


class NativeWikiService:
    def __init__(
        self,
        repository: NativeAssetRepository,
        spreadsheets: NativeSpreadsheetAdapter,
        publisher: NativeWikiPublisher,
        docx: NativeDocxAdapter | None = None,
        presentations: NativePresentationAdapter | None = None,
        pdfs: NativePdfAdapter | None = None,
        derivations: NativeDerivationService | None = None,
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
        self.publisher = publisher
        self.docx = docx
        self.presentations = presentations
        self.pdfs = pdfs
        self.derivations = derivations
        self.delimited = delimited
        self.docx_stories = docx_stories
        self.docx_notes = docx_notes
        self.images = images
        self.image_archive = image_archive

    def export(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.output_dir is not None
        asset = self.repository.load(request.asset_id)
        revision = request.revision or asset.revision
        if request.derivations_sha256 is not None and self.derivations is None:
            raise ValueError("Native derivation repository is not configured")
        ledger = (
            self.derivations.ledger(asset.asset_id, request.derivations_sha256)
            if self.derivations
            else None
        )
        data = self.repository.read(asset.asset_id, revision)
        if request.delimited_dialect is not None and (
            asset.format not in {"csv", "tsv"} or self.delimited is None
        ):
            raise ValueError(
                "Delimited dialect requires a configured CSV/TSV projection"
            )
        structure = (
            self.delimited.inspect(
                data, dialect_for(asset.format, request.delimited_dialect)
            )
            if asset.format in {"csv", "tsv"} and self.delimited
            else None
        )
        catalog = (
            self.docx_stories.inspect(data)
            if asset.format == "docx" and self.docx and self.docx_stories
            else None
        )
        notes = (
            self.docx_notes.inspect(data)
            if asset.format == "docx" and self.docx and self.docx_notes
            else None
        )
        annotations_catalog = (
            self.pdfs.inspect_annotations(data)
            if asset.format == "pdf" and self.pdfs
            else None
        )
        image_catalog, image_records = self._image_records(
            asset, revision, request.image_catalog_sha256
        )
        ods_structure = None
        if asset.format == "ods" and self.ods:
            ods_structure = self.ods.inspect(data, offset=0, limit=1)
            ods_structure.pop("records")
            ods_structure.pop("next_offset")
        content = self._content(
            request,
            asset,
            revision,
            ledger,
            structure,
            catalog,
            notes,
            annotations_catalog,
            image_catalog,
            ods_structure,
        )
        add_rendition(content, asset, self.repository)
        self._populate(content, data, image_records)
        if isinstance(content, NativeImageWikiContent) and self.images:
            add_image_inputs(content, self.repository, self.images, self.image_archive)
        if ledger is not None and self.derivations is not None:
            add_derivations(
                content,
                ledger,
                self.derivations,
                self.repository,
                image_color_policy=request.image_color_policy,
            )
        result = self.publisher.publish(
            request.output_dir,
            content.snapshot_id,
            content.finish(data),
            source_path=asset.source.path if asset.source else None,
        )
        return {
            **result,
            "asset_id": asset.asset_id,
            "revision": revision,
            "index_note": content.index_name,
            **content.record_counts(),
            "review_required": content.review_required(),
        }

    def _content(
        self,
        request: NativeDocumentRequest,
        asset: NativeFileAsset,
        revision: str,
        ledger: NativeDerivationLedger | None,
        delimited_structure: dict[str, Any] | None = None,
        story_catalog: dict[str, Any] | None = None,
        notes_catalog: dict[str, Any] | None = None,
        annotations_catalog: dict[str, Any] | None = None,
        image_catalog: dict[str, Any] | None = None,
        ods_structure: dict[str, Any] | None = None,
    ) -> NativeWikiContent:
        contract = resolve_citation_format(
            request.citation_contract.model_dump(mode="json")
            if request.citation_contract is not None
            else {"preset": "source"}
        )
        builder = (
            NativePdfWikiContent
            if asset.format == "pdf" and self.pdfs
            else NativeDocxWikiContent
            if asset.format == "docx" and self.docx
            else NativePptxWikiContent
            if asset.format == "pptx" and self.presentations
            else NativeWikiContent
        )
        identity = {
            "asset_id": asset.asset_id,
            "revision": revision,
            "name": asset.name,
            "format": asset.format,
            "media_type": asset.media_type,
            **(
                {"derivations_sha256": fingerprint(ledger)}
                if ledger and ledger.events
                else {}
            ),
        }
        metadata = request.citation_metadata or CitationMetadata()
        if ledger is not None and any(
            isinstance(
                ref.parent if isinstance(ref, NativeSelectionReference) else ref,
                NativeImageFrameReference | NativeImageRegionReference,
            )
            for event in ledger.active_records().values()
            if event.derivation.target.revision == revision
            for ref in [event.derivation.target, *event.derivation.sources]
        ):
            identity["image_color_policy"] = request.image_color_policy
        if ods_structure is not None:
            latest = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            return NativeODSWikiContent(
                identity,
                contract,
                metadata,
                ods_structure,
                revision_result_dict(self.repository, asset, latest),
            )
        if image_catalog is not None:
            latest = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            return NativeImageWikiContent(
                identity,
                contract,
                metadata,
                image_catalog,
                revision_result_dict(self.repository, asset, latest),
                request.image_color_policy,
            )
        if annotations_catalog and annotations_catalog["annotations"]:
            return NativePdfAnnotationWikiContent(
                identity, contract, metadata, annotations_catalog
            )
        if delimited_structure is not None:
            return NativeDelimitedWikiContent(
                identity, contract, metadata, delimited_structure
            )
        if notes_catalog and (notes_catalog["notes"] or notes_catalog["references"]):
            return NativeDocxNoteWikiContent(
                identity, contract, metadata, notes_catalog, story_catalog
            )
        if story_catalog and story_catalog["stories"]:
            return NativeDocxStoryWikiContent(
                identity, contract, metadata, story_catalog
            )
        return builder(identity, contract, metadata)

    def _image_records(
        self, asset: NativeFileAsset, revision: str, catalog_sha256: str | None
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        if asset.format in IMAGE_EXTENSIONS and self.images:
            return NativeImageProjection(
                self.repository, self.images, self.image_archive
            ).records(asset.asset_id, revision, catalog_sha256)
        if catalog_sha256 is not None:
            raise ValueError(
                "image_catalog_sha256 requires a configured raster projection"
            )
        return None, []

    def _populate(
        self,
        content: NativeWikiContent,
        data: bytes,
        image_records: list[dict[str, Any]],
    ) -> None:
        identity = content.identity
        if isinstance(content, NativeImageWikiContent) and self.images:
            frames = NativeImageProjection(
                self.repository, self.images, self.image_archive
            ).wiki_frames(
                identity["asset_id"],
                identity["revision"],
                image_records,
                content.color_policy,
            )
            content.add_frames(data, frames)
        elif isinstance(content, NativePdfWikiContent) and self.pdfs:
            for item in self.pdfs.decompose(data):
                attach_pdf_evidence(
                    item["record"], identity["asset_id"], identity["revision"]
                )
                content.add_page(item["record"], item["png"])
            if isinstance(content, NativePdfAnnotationWikiContent):
                annotation_records = self.pdfs.decompose_annotations(data)
                for record in annotation_records:
                    attach_annotation_evidence(
                        record, identity["asset_id"], identity["revision"]
                    )
                content.add_annotations(annotation_records)
        elif isinstance(content, NativeDelimitedWikiContent) and self.delimited:
            for field in self.delimited.decompose(data, content.dialect):
                attach_delimited_evidence(
                    field, identity["asset_id"], identity["revision"]
                )
                content.add_field(field)
        elif isinstance(content, NativeODSWikiContent) and self.ods:
            for count, record in enumerate(self.ods.decompose(data), start=1):
                if count > MAX_WIKI_CELLS:
                    raise ValueError("ODS Wiki exceeds the physical-range limit")
                attach_ods_evidence(record, identity["asset_id"], identity["revision"])
                content.add_range(record)
        elif identity["format"] in {"xlsx", "xlsm"}:
            for count, cell in enumerate(self.spreadsheets.iter_cells(data), start=1):
                if count > MAX_WIKI_CELLS:
                    raise ValueError("Native wiki exceeds the stored-cell limit")
                attach_native_evidence(cell, identity["asset_id"], identity["revision"])
                content.add_cell(cell)
        elif isinstance(content, NativeDocxWikiContent) and self.docx:
            decomposition = self.docx.decompose(
                data, identity["asset_id"], identity["revision"]
            )
            content.add_parts(decomposition.parts)
            for block in decomposition.blocks:
                content.add_block(block)
            if isinstance(content, NativeDocxStoryWikiContent) and self.docx_stories:
                stories = []
                for item in content.catalog["stories"]:
                    record = self.docx_stories.read(data, item["locator"]["part"])
                    attach_story_evidence(
                        record, identity["asset_id"], identity["revision"]
                    )
                    stories.append(record)
                content.add_stories(stories)

            if isinstance(content, NativeDocxNoteWikiContent) and self.docx_notes:
                if self.docx_stories is None:
                    content.add_stories([])

                def records() -> Iterator[dict[str, Any]]:
                    assert self.docx_notes is not None
                    for record in self.docx_notes.decompose(data):
                        attach_note_evidence(
                            record, identity["asset_id"], identity["revision"]
                        )
                        yield record

                content.add_notes(records())

        elif isinstance(content, NativePptxWikiContent) and self.presentations:
            content.add_parts(self.presentations.package_parts(data))
            for shape in self.presentations.iter_shapes(data):
                attach_pptx_evidence(shape, identity["asset_id"], identity["revision"])
                content.add_shape(shape)
