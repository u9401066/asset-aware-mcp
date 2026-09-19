"""Create portable native evidence snapshots without mutating sources or old notes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_derivation_wiki import add_derivations
from src.application.native_docx_wiki import NativeDocxWikiContent
from src.application.native_evidence_service import attach_native_evidence
from src.application.native_pdf_operations import attach_pdf_evidence
from src.application.native_pdf_wiki import NativePdfWikiContent
from src.application.native_pptx_operations import attach_pptx_evidence
from src.application.native_pptx_wiki import NativePptxWikiContent
from src.application.native_rendition_wiki import add_rendition
from src.application.native_wiki_format import NativeWikiContent
from src.domain.citation_format import CitationMetadata, resolve_citation_format
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
    from src.domain.native_derivation import NativeDerivationLedger
    from src.domain.native_docx import NativeDocxAdapter
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
    ):
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.publisher = publisher
        self.docx = docx
        self.presentations = presentations
        self.pdfs = pdfs
        self.derivations = derivations

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
        content = self._content(request, asset, revision, ledger)
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
        return builder(
            {
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
            },
            contract,
            request.citation_metadata or CitationMetadata(),
        )

    def _populate(self, content: NativeWikiContent, data: bytes) -> None:
        identity = content.identity
        if isinstance(content, NativePdfWikiContent) and self.pdfs:
            for item in self.pdfs.decompose(data):
                attach_pdf_evidence(
                    item["record"], identity["asset_id"], identity["revision"]
                )
                content.add_page(item["record"], item["png"])
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

        elif isinstance(content, NativePptxWikiContent) and self.presentations:
            content.add_parts(self.presentations.package_parts(data))
            for shape in self.presentations.iter_shapes(data):
                attach_pptx_evidence(shape, identity["asset_id"], identity["revision"])
                content.add_shape(shape)
