"""Create portable native evidence snapshots without mutating sources or old notes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_delimited_operations import dialect_for
from src.application.native_delimited_wiki import NativeDelimitedWikiContent
from src.application.native_derivation_wiki import add_derivations
from src.application.native_docx_story_operations import attach_story_evidence
from src.application.native_docx_story_wiki import NativeDocxStoryWikiContent
from src.application.native_docx_wiki import NativeDocxWikiContent
from src.application.native_evidence_service import attach_native_evidence
from src.application.native_pdf_operations import attach_pdf_evidence
from src.application.native_pdf_wiki import NativePdfWikiContent
from src.application.native_pptx_operations import attach_pptx_evidence
from src.application.native_pptx_wiki import NativePptxWikiContent
from src.application.native_rendition_wiki import add_rendition
from src.application.native_wiki_format import NativeWikiContent
from src.domain.citation_format import CitationMetadata, resolve_citation_format
from src.domain.native_delimited import attach_delimited_evidence
from src.domain.native_derivation import fingerprint
from src.domain.native_wiki import MAX_WIKI_CELLS

if TYPE_CHECKING:
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
    from src.domain.native_docx_stories import NativeDocxStoryAdapter
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
    ):
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.publisher = publisher
        self.docx = docx
        self.presentations = presentations
        self.pdfs = pdfs
        self.derivations = derivations
        self.delimited = delimited
        self.docx_stories = docx_stories

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
        content = self._content(request, asset, revision, ledger, structure, catalog)
        add_rendition(content, asset, self.repository)
        self._populate(content, data)
        if ledger is not None and self.derivations is not None:
            add_derivations(content, ledger, self.derivations, self.repository)
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
        if delimited_structure is not None:
            return NativeDelimitedWikiContent(
                identity, contract, metadata, delimited_structure
            )
        if story_catalog and story_catalog["stories"]:
            return NativeDocxStoryWikiContent(
                identity, contract, metadata, story_catalog
            )
        return builder(identity, contract, metadata)

    def _populate(self, content: NativeWikiContent, data: bytes) -> None:
        identity = content.identity
        if isinstance(content, NativePdfWikiContent) and self.pdfs:
            for item in self.pdfs.decompose(data):
                attach_pdf_evidence(
                    item["record"], identity["asset_id"], identity["revision"]
                )
                content.add_page(item["record"], item["png"])
        elif isinstance(content, NativeDelimitedWikiContent) and self.delimited:
            for field in self.delimited.decompose(data, content.dialect):
                attach_delimited_evidence(
                    field, identity["asset_id"], identity["revision"]
                )
                content.add_field(field)
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

        elif isinstance(content, NativePptxWikiContent) and self.presentations:
            content.add_parts(self.presentations.package_parts(data))
            for shape in self.presentations.iter_shapes(data):
                attach_pptx_evidence(shape, identity["asset_id"], identity["revision"])
                content.add_shape(shape)
