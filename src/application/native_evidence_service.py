"""Native evidence integrity against immutable file revisions, independent of display."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeCellReference,
        NativeSpreadsheetAdapter,
    )


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
        self, repository: NativeAssetRepository, spreadsheets: NativeSpreadsheetAdapter
    ):
        self.repository = repository
        self.spreadsheets = spreadsheets

    def verify(self, reference: NativeCellReference) -> dict[str, Any]:
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
