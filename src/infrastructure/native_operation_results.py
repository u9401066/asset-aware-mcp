"""Immutable, canonical native result blobs separate from the bounded asset index."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from src.domain.native_asset_models import (
    MAX_NATIVE_RESULT_BYTES,
    SHA256_PATTERN,
    NativeAssetRevision,
    NativeEditResult,
    NativeOperationResultReference,
)
from src.domain.native_operation_result import NativeOperationResultBlob, result_binding
from src.infrastructure.native_file_io import _digest, _read_file, _write_atomic

if TYPE_CHECKING:
    from pathlib import Path


def _path(directory: Path, digest: str) -> Path:
    if re.fullmatch(SHA256_PATTERN, digest) is None:
        raise ValueError("Invalid native operation result hash")
    folder = directory / "results"
    if folder.is_symlink() or folder.resolve() != folder:
        raise ValueError("Native operation result directories cannot be symlinks")
    return folder / (digest + ".json")


def _encode(blob: NativeOperationResultBlob) -> bytes:
    data = json.dumps(
        blob.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(data) > MAX_NATIVE_RESULT_BYTES:
        raise ValueError("Native operation result exceeds its complete byte budget")
    return data


def retain_result(
    directory: Path, asset_id: str, index: int, entry: NativeAssetRevision
) -> NativeOperationResultReference:
    if entry.result is None or entry.result_ref is not None:
        raise ValueError("Retaining a native result requires its complete inline value")
    data = _encode(
        NativeOperationResultBlob(
            **result_binding(asset_id, index, entry), result=entry.result
        )
    )
    reference = NativeOperationResultReference(
        sha256=_digest(data), size_bytes=len(data)
    )
    path = _path(directory, reference.sha256)
    path.parent.mkdir(exist_ok=True)
    if not path.exists() and not path.is_symlink():
        _write_atomic(path, data, limit=MAX_NATIVE_RESULT_BYTES)
    actual, _ = _read_file(path, reference.size_bytes)
    if actual != data:
        raise ValueError("Immutable native operation result integrity failure")
    return reference


def read_result(
    directory: Path, asset_id: str, index: int, entry: NativeAssetRevision
) -> NativeEditResult | None:
    reference = entry.result_ref
    if reference is None:
        return entry.result
    try:
        data, _ = _read_file(_path(directory, reference.sha256), reference.size_bytes)
    except FileNotFoundError as exc:
        raise ValueError("Missing immutable native operation result") from exc
    if len(data) != reference.size_bytes or _digest(data) != reference.sha256:
        raise ValueError("Native operation result size/hash verification failed")
    blob = NativeOperationResultBlob.model_validate_json(data)
    if blob.model_dump(exclude={"result", "schema_version"}) != result_binding(
        asset_id, index, entry
    ):
        raise ValueError("Native operation result history/revision binding mismatch")
    if _encode(blob) != data:
        raise ValueError(
            "Native operation result is not its canonical complete representation"
        )
    return blob.result
