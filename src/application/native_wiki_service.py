"""Create portable native evidence snapshots without mutating sources or old notes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_evidence_service import attach_native_evidence
from src.application.native_wiki_format import NativeWikiContent
from src.domain.citation_format import CitationMetadata, resolve_citation_format
from src.domain.native_wiki import MAX_WIKI_CELLS

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeSpreadsheetAdapter,
    )
    from src.domain.native_wiki import NativeWikiPublisher


class NativeWikiService:
    def __init__(
        self,
        repository: NativeAssetRepository,
        spreadsheets: NativeSpreadsheetAdapter,
        publisher: NativeWikiPublisher,
    ):
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.publisher = publisher

    def export(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.output_dir is not None
        asset = self.repository.load(request.asset_id)
        revision = request.revision or asset.revision
        data = self.repository.read(asset.asset_id, revision)
        contract = resolve_citation_format(
            request.citation_contract
            if request.citation_contract is not None
            else {"preset": "source"}
        )
        content = NativeWikiContent(
            {
                "asset_id": asset.asset_id,
                "revision": revision,
                "name": asset.name,
                "format": asset.format,
                "media_type": asset.media_type,
            },
            contract,
            request.citation_metadata or CitationMetadata(),
        )
        if asset.format in {"xlsx", "xlsm"}:
            for count, cell in enumerate(self.spreadsheets.iter_cells(data), start=1):
                if count > MAX_WIKI_CELLS:
                    raise ValueError("Native wiki exceeds the stored-cell limit")
                attach_native_evidence(cell, asset.asset_id, revision)
                content.add_cell(cell)
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
            "cell_count": len(content.records),
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "formula_results",
            ],
        }
