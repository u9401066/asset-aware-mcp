"""Append-only provenance metadata under the native asset's crash-released lock."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.domain.native_asset_models import ASSET_ID_PATTERN
from src.domain.native_derivation import (
    MAX_DERIVATION_BYTES,
    NativeDerivationLedger,
    canonical,
    fingerprint,
)
from src.infrastructure.native_file_io import _read_file, _write_atomic, operation_lock

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.native_assets import NativeAssetRepository
    from src.domain.native_derivation import NativeDerivationEvent


class FileNativeDerivationRepository:
    def __init__(self, root: Path, assets: NativeAssetRepository):
        self.root = root.resolve()
        self.assets = assets

    def _path(self, asset_id: str) -> Path:
        if not re.fullmatch(ASSET_ID_PATTERN, asset_id):
            raise ValueError("Invalid native asset ID")
        directory = self.root / asset_id
        if directory.is_symlink() or directory.resolve() != directory:
            raise ValueError("Derivation directories cannot be symlinks")
        return directory / "derivations.json"

    def load(self, asset_id: str) -> NativeDerivationLedger:
        self.assets.load(asset_id)
        path = self._path(asset_id)
        if path.is_symlink():
            raise ValueError("Derivation ledger cannot be a symlink")
        if not path.exists():
            return NativeDerivationLedger(asset_id=asset_id)
        data, _ = _read_file(path, MAX_DERIVATION_BYTES)
        ledger = NativeDerivationLedger.model_validate_json(data)
        if ledger.asset_id != asset_id:
            raise ValueError("Derivation ledger belongs to a different asset")
        return ledger

    def append(
        self, asset_id: str, expected_sha256: str, event: NativeDerivationEvent
    ) -> NativeDerivationLedger:
        path = self._path(asset_id)
        with operation_lock(path.parent):
            if self.assets.load(asset_id).archived:
                raise ValueError("Archived native asset cannot change derivations")
            current = self.load(asset_id)
            if fingerprint(current) != expected_sha256:
                raise ValueError("Stale derivation ledger; read and reconcile first")
            updated = NativeDerivationLedger.model_validate(
                {
                    "asset_id": asset_id,
                    "events": [*current.events, event],
                }
            )
            _write_atomic(path, canonical(updated), limit=MAX_DERIVATION_BYTES)
            return updated
