"""Immutable native file revisions with locked, optimistic metadata publication."""

from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.native_assets import (
    ASSET_ID_PATTERN,
    MAX_NATIVE_BYTES,
    SHA256_PATTERN,
    NativeAssetRevision,
    NativeEditResult,
    NativeFileAsset,
    NativeSource,
)
from src.infrastructure.native_file_io import (
    NativeSourcePublication,
    _digest,
    _read_file,
    _source,
    _write_atomic,
    operation_lock,
    publish_new_file,
)
from src.infrastructure.native_spreadsheet import NativeSpreadsheet

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

MAX_METADATA_BYTES = 16 * 1024 * 1024


class FileNativeAssetRepository:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _directory(self, asset_id: str) -> Path:
        if re.fullmatch(ASSET_ID_PATTERN, asset_id) is None:
            raise ValueError("Invalid native asset ID")
        path = self.root / asset_id
        if path.is_symlink() or path.resolve() != path:
            raise ValueError("Native asset directories cannot be symlinks")
        return path

    def _lock(self, asset_id: str) -> AbstractContextManager[Path]:
        return operation_lock(self._directory(asset_id))

    def _save(self, asset: NativeFileAsset) -> None:
        data = asset.model_dump_json(indent=2).encode("utf-8")
        _write_atomic(
            self._directory(asset.asset_id) / "asset.json",
            data,
            limit=MAX_METADATA_BYTES,
        )

    def _blob(self, asset_id: str, revision: str) -> Path:
        if re.fullmatch(SHA256_PATTERN, revision) is None:
            raise ValueError("Invalid native revision")
        directory = self._directory(asset_id) / "revisions"
        if directory.is_symlink():
            raise ValueError("Native revisions directory cannot be a symlink")
        return directory / revision

    def _store_blob(self, asset_id: str, data: bytes) -> str:
        revision = _digest(data)
        path = self._blob(asset_id, revision)
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            actual, _ = _read_file(path, MAX_NATIVE_BYTES)
            if actual != data:
                raise ValueError("Immutable native revision integrity failure")
        else:
            _write_atomic(path, data, limit=MAX_NATIVE_BYTES)
        return revision

    def register(self, source_path: str) -> NativeFileAsset:
        path = Path(source_path).expanduser()
        if path.is_symlink():
            raise ValueError("Register the real source file, not a symlink")
        path = path.resolve(strict=True)
        data, info = _read_file(path, MAX_NATIVE_BYTES)
        kind = path.suffix.lower().lstrip(".") or "opaque"
        if kind in {"xlsx", "xlsm"}:
            NativeSpreadsheet(data).inspect(limit=1)
        asset = self._create(
            path.name,
            data,
            kind,
            mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            source=_source(path, data, info),
        )
        return asset

    def create(
        self,
        name: str,
        data: bytes,
        format_name: str,
        media_type: str,
        *,
        result: NativeEditResult | None = None,
    ) -> NativeFileAsset:
        return self._create(name, data, format_name, media_type, result=result)

    def _create(
        self,
        name: str,
        data: bytes,
        format_name: str,
        media_type: str,
        *,
        source: NativeSource | None = None,
        result: NativeEditResult | None = None,
    ) -> NativeFileAsset:
        if not name or "/" in name or "\\" in name or "\x00" in name:
            raise ValueError("Native asset names must be filenames")
        if len(data) > MAX_NATIVE_BYTES:
            raise ValueError("Native document exceeds byte limit")
        asset_id = "file_" + uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        directory = self._directory(asset_id)
        directory.mkdir(mode=0o700)
        revision = self._store_blob(asset_id, data)
        asset = NativeFileAsset(
            asset_id=asset_id,
            name=name,
            format=format_name,
            media_type=media_type,
            revision=revision,
            source=source,
            history=[
                NativeAssetRevision(
                    sha256=revision,
                    size_bytes=len(data),
                    operation="register" if source else "create",
                    result=result,
                )
            ],
        )
        self._save(asset)
        return asset

    def load(self, asset_id: str) -> NativeFileAsset:
        data, _ = _read_file(
            self._directory(asset_id) / "asset.json", MAX_METADATA_BYTES
        )
        asset = NativeFileAsset.model_validate_json(data)
        if asset.asset_id != asset_id or asset.history[-1].sha256 != asset.revision:
            raise ValueError("Native asset metadata identity/revision mismatch")
        return asset

    def list_assets(self, offset: int, limit: int) -> list[NativeFileAsset]:
        if offset < 0 or not 1 <= limit <= 1000:
            raise ValueError("Invalid native asset pagination")
        if not self.root.exists():
            return []
        identities = sorted(
            path.name
            for path in self.root.iterdir()
            if re.fullmatch(ASSET_ID_PATTERN, path.name)
            and (path / "asset.json").exists()
        )
        return [self.load(identity) for identity in identities[offset : offset + limit]]

    def read(self, asset_id: str, revision: str | None = None) -> bytes:
        asset = self.load(asset_id)
        revision = revision or asset.revision
        if not any(item.sha256 == revision for item in asset.history):
            raise ValueError("Revision does not belong to this native asset")
        data, _ = _read_file(self._blob(asset_id, revision), MAX_NATIVE_BYTES)
        if _digest(data) != revision:
            raise ValueError("Native revision hash verification failed")
        return data

    @staticmethod
    def _check(asset: NativeFileAsset, expected_revision: str) -> None:
        if asset.archived:
            raise ValueError("Native asset is archived")
        if asset.revision != expected_revision:
            raise ValueError(
                "Stale native revision; inspect the current asset before editing"
            )

    def commit(
        self,
        asset_id: str,
        expected_revision: str,
        data: bytes,
        result: NativeEditResult,
    ) -> NativeFileAsset:
        with self._lock(asset_id):
            asset = self.load(asset_id)
            self._check(asset, expected_revision)
            self.read(asset_id, expected_revision)
            revision = self._store_blob(asset_id, data)
            if revision == expected_revision:
                return asset
            if len(asset.history) >= 10000:
                raise ValueError("Native revision history limit reached")
            asset.history.append(
                NativeAssetRevision(
                    sha256=revision,
                    size_bytes=len(data),
                    operation="update",
                    parent_sha256=expected_revision,
                    result=result,
                )
            )
            asset.revision = revision
            self._save(asset)
            return asset

    def archive(self, asset_id: str, expected_revision: str) -> NativeFileAsset:
        with self._lock(asset_id):
            asset = self.load(asset_id)
            self._check(asset, expected_revision)
            asset.archived = True
            self._save(asset)
            return asset

    def refresh(
        self, asset_id: str, expected_revision: str, expected_source_sha256: str
    ) -> NativeFileAsset:
        """Adopt external edits only when they cannot discard an unpublished edit."""
        with self._lock(asset_id):
            asset = self.load(asset_id)
            self._check(asset, expected_revision)
            source = asset.source
            if source is None:
                raise ValueError("This asset has no registered source to refresh")
            if source.sha256 != expected_source_sha256:
                raise ValueError("Stale source metadata; inspect before refreshing")
            self.read(asset_id, expected_revision)
            path = Path(source.path)
            data, info = _read_file(path, MAX_NATIVE_BYTES)
            current = _source(path, data, info)
            if current == source:
                return asset
            if current.sha256 == source.sha256:
                # File replacement/touch with identical bytes is safe even if
                # a managed edit is waiting for writeback.
                asset.source = current
                self._save(asset)
                return asset
            if asset.revision not in {source.sha256, current.sha256}:
                raise ValueError(
                    "Source and managed revision diverged; compare both versions "
                    "and reconcile before refresh (no revision was discarded)"
                )
            if asset.format in {"xlsx", "xlsm"}:
                NativeSpreadsheet(data).inspect(limit=1)
            if current.sha256 != asset.revision:
                if len(asset.history) >= 10000:
                    raise ValueError("Native revision history limit reached")
                revision = self._store_blob(asset_id, data)
                asset.history.append(
                    NativeAssetRevision(
                        sha256=revision,
                        size_bytes=len(data),
                        operation="refresh",
                        parent_sha256=asset.revision,
                    )
                )
                asset.revision = revision
            # Also reconciles a writeback whose bytes succeeded but metadata
            # publication failed, without inventing another content revision.
            asset.source = current
            self._save(asset)
            return asset

    def publish(
        self, asset_id: str, expected_revision: str, output_path: str
    ) -> dict[str, Any]:
        """Create a new external file. Existing paths are never overwritten."""
        with self._lock(asset_id):
            asset = self.load(asset_id)
            self._check(asset, expected_revision)
            target = Path(output_path).expanduser().absolute()
            if target.suffix.lower() != Path(asset.name).suffix.lower():
                raise ValueError("Output must retain the native file extension")
            if target.exists() or target.is_symlink():
                raise ValueError("Publish requires a new output file")
            parent = target.parent.resolve(strict=True)
            target = parent / target.name
            data = self.read(asset_id, expected_revision)
            return publish_new_file(target, data, expected_revision)

    def writeback(
        self, asset_id: str, expected_revision: str, expected_source_sha256: str
    ) -> dict[str, Any]:
        with self._lock(asset_id):
            asset = self.load(asset_id)
            self._check(asset, expected_revision)
            source = asset.source
            if source is None:
                raise ValueError(
                    "This asset has no original source; use publish to create a file"
                )
            if source.sha256 != expected_source_sha256:
                raise ValueError(
                    "Expected source revision does not match registered source state"
                )
            data = self.read(asset_id, expected_revision)

            def save_source(updated_source: NativeSource) -> None:
                asset.source = updated_source
                self._save(asset)

            return NativeSourcePublication(source, data).execute(save_source)
