"""Resolve complete receipts without coupling document workflows to storage layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.native_asset_models import (
        NativeAssetRepository,
        NativeAssetRevision,
        NativeEditResult,
        NativeFileAsset,
    )


def revision_result(
    repository: NativeAssetRepository,
    asset: NativeFileAsset,
    entry: NativeAssetRevision,
) -> NativeEditResult | None:
    if entry.result_ref is None:
        return entry.result
    result = repository.read_result(asset.asset_id, entry)
    if result is None:
        raise ValueError("Referenced native operation result is unavailable")
    return result


def revision_result_dict(
    repository: NativeAssetRepository,
    asset: NativeFileAsset,
    entry: NativeAssetRevision,
) -> dict[str, Any] | None:
    result = revision_result(repository, asset, entry)
    return result.model_dump(mode="json") if result is not None else None
