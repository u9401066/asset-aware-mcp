"""Bounded, immutable frame/catalog/preview storage beside native revisions."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import ASSET_ID_PATTERN, SHA256_PATTERN
from src.domain.native_image import (
    MAX_IMAGE_FRAMES,
    ImageColorPolicy,
    NativeImageFrameLocator,
    NativeImageFrameReference,
    NativeImageRegionReference,
)
from src.domain.native_image_archive import (
    MAX_IMAGE_PREVIEW_BYTES,
    MAX_IMAGE_RECORD_BYTES,
)
from src.domain.native_image_evidence import (
    image_canonical,
    image_catalog_for_revision,
    image_frame_reference,
    image_region_record,
)
from src.infrastructure.native_file_io import _read_file, _write_atomic, operation_lock

if TYPE_CHECKING:
    from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _checked_hash(value: str) -> str:
    if re.fullmatch(SHA256_PATTERN, value) is None:
        raise ValueError("Invalid image archive hash")
    return value


def _read(path: Path, limit: int) -> bytes | None:
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("Image archive paths cannot be symlinks")
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    return _read_file(path, limit)[0]


def _object(path: Path, expected: str) -> dict[str, Any] | None:
    data = _read(path, MAX_IMAGE_RECORD_BYTES)
    if data is None:
        return None
    if _sha(data) != expected:
        raise ValueError("Retained image representation hash mismatch")
    value = json.loads(data)
    if not isinstance(value, dict) or image_canonical(value) != data:
        raise ValueError("Retained image representation is not canonical JSON")
    return value


def _put(path: Path, data: bytes, limit: int) -> None:
    if len(data) > limit:
        raise ValueError("Image archive output exceeds byte limit")
    previous = _read(path, limit)
    if previous is not None:
        if previous != data:
            raise ValueError("Conflicting immutable image archive entry")
    else:
        _write_atomic(path, data, limit=limit)


def _frame_bytes(reference: NativeImageFrameReference, record: dict[str, Any]) -> bytes:
    if (
        record.get("schema_version") != "native-image-frame-v1"
        or image_frame_reference(record, reference.asset_id, reference.revision)
        != reference
    ):
        raise ValueError("Retained image frame does not match its full reference")
    data = image_canonical(record)
    if len(data) > MAX_IMAGE_RECORD_BYTES:
        raise ValueError("Image frame exceeds retained representation budget")
    return data


def _put_frame(directory: Path, key: str, data: bytes) -> None:
    _put(directory / f"frame-{key}.json", data, MAX_IMAGE_RECORD_BYTES)
    _put(directory / f"frame-{key}.index", key.encode("ascii"), 64)


def _recipe(
    reference: NativeImageFrameReference | NativeImageRegionReference,
    size: int,
    color_policy: ImageColorPolicy,
) -> dict[str, Any]:
    if type(size) is not int or not 64 <= size <= 2048:
        raise ValueError("Raster preview size must be 64..2048")
    if color_policy not in {"embedded_to_srgb", "unmanaged"}:
        raise ValueError("Unknown raster preview color policy")
    return {
        "reference": reference.model_dump(mode="json"),
        "render_size": size,
        "color_policy": color_policy,
    }


class FileNativeImageArchive:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _directory(self, asset_id: str, revision: str, *, create: bool = False) -> Path:
        if re.fullmatch(ASSET_ID_PATTERN, asset_id) is None:
            raise ValueError("Invalid image archive asset ID")
        directory = self.root / asset_id / "image-evidence" / _checked_hash(revision)
        if directory.is_symlink() or directory.resolve() != directory:
            raise ValueError("Image archive directories cannot be symlinks")
        if create:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if directory.resolve() != directory:
                raise ValueError("Image archive directory changed during creation")
        return directory

    def retain_frame(
        self, reference: NativeImageFrameReference, record: dict[str, Any]
    ) -> None:
        data = _frame_bytes(reference, record)
        directory = self._directory(reference.asset_id, reference.revision, create=True)
        with operation_lock(directory):
            _put_frame(directory, reference.value_sha256, data)

    def frame(self, reference: NativeImageFrameReference) -> dict[str, Any] | None:
        directory = self._directory(reference.asset_id, reference.revision)
        record = _object(
            directory / f"frame-{reference.value_sha256}.json", reference.value_sha256
        )
        marker = _read(directory / f"frame-{reference.value_sha256}.index", 64)
        if record is None and marker is None:
            return None
        if record is None or marker != reference.value_sha256.encode("ascii"):
            raise ValueError("Retained image frame capture is incomplete or corrupt")
        if record is not None:
            _frame_bytes(reference, record)
        return record

    def retain_catalog(
        self, asset_id: str, revision: str, records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not 1 <= len(records) <= MAX_IMAGE_FRAMES:
            raise ValueError("Invalid retained image frame count")
        entries, total = [], 0
        for index, record in enumerate(records):
            reference = image_frame_reference(record, asset_id, revision)
            if reference.locator.frame_index != index:
                raise ValueError(
                    "Retained catalog requires the complete ordered frame sequence"
                )
            data = _frame_bytes(reference, record)
            total += len(data)
            if total > MAX_IMAGE_RECORD_BYTES:
                raise ValueError("Retained image records exceed aggregate budget")
            entries.append((reference.value_sha256, data))
        catalog = image_catalog_for_revision(revision, records)
        directory = self._directory(asset_id, revision, create=True)
        with operation_lock(directory):
            for key, data in entries:
                _put_frame(directory, key, data)
            # The catalog is the commit marker; incomplete captures cannot resolve it.
            payload = {
                key: value for key, value in catalog.items() if key != "catalog_sha256"
            }
            _put(
                directory / f"catalog-{catalog['catalog_sha256']}.json",
                image_canonical(payload),
                MAX_IMAGE_RECORD_BYTES,
            )
        return catalog

    def catalog(
        self, asset_id: str, revision: str, catalog_sha256: str
    ) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
        directory = self._directory(asset_id, revision)
        catalog = _object(
            directory / f"catalog-{_checked_hash(catalog_sha256)}.json", catalog_sha256
        )
        if catalog is None:
            return None
        if (
            not isinstance(catalog.get("frames"), list)
            or not 1 <= len(catalog["frames"]) <= MAX_IMAGE_FRAMES
        ):
            raise ValueError("Invalid retained image catalog")
        records, total = [], 0
        for index, item in enumerate(catalog["frames"]):
            reference = NativeImageFrameReference(
                asset_id=asset_id,
                revision=revision,
                locator=NativeImageFrameLocator(frame_index=index),
                value_sha256=item["record_sha256"],
            )
            record = self.frame(reference)
            if record is None:
                raise ValueError("Retained image catalog is incomplete")
            total += len(image_canonical(record))
            if total > MAX_IMAGE_RECORD_BYTES:
                raise ValueError("Retained image records exceed aggregate budget")
            records.append(record)
        expected = image_catalog_for_revision(revision, records)
        if {**catalog, "catalog_sha256": catalog_sha256} != expected:
            raise ValueError("Retained image catalog does not match its records/source")
        return expected, records

    def _check_preview(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        size: int,
        preview: dict[str, Any],
    ) -> None:
        parent = (
            reference.parent
            if isinstance(reference, NativeImageRegionReference)
            else reference
        )
        record = preview["record"]
        _frame_bytes(parent, record)
        if isinstance(reference, NativeImageRegionReference):
            region = image_region_record(parent, reference.selector, record)
            if region["evidence"] != reference.model_dump(mode="json"):
                raise ValueError("Retained preview has a different region reference")
            bounds = region["source_pixel_bounds"]
        else:
            bounds = [0, 0, *record["displayed_size_px"]]
        if preview["source_pixel_bounds"] != bounds:
            raise ValueError("Retained preview has different source pixel bounds")
        png = preview["png"]
        if (
            not isinstance(png, bytes)
            or len(png) > MAX_IMAGE_PREVIEW_BYTES
            or _sha(png) != preview["png_sha256"]
        ):
            raise ValueError("Retained image preview hash or byte limit mismatch")
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or png[12:16] != b"IHDR":
            raise ValueError("Retained image preview is not PNG")
        for key, start in (("width_px", 16), ("height_px", 20)):
            if (
                type(preview[key]) is not int
                or not 1 <= preview[key] <= size
                or int.from_bytes(png[start : start + 4], "big") != preview[key]
            ):
                raise ValueError("Retained preview dimensions mismatch")

    def retain_preview(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        size: int,
        color_policy: ImageColorPolicy,
        preview: dict[str, Any],
    ) -> None:
        recipe = _recipe(reference, size, color_policy)
        self._check_preview(reference, size, preview)
        parent = (
            reference.parent
            if isinstance(reference, NativeImageRegionReference)
            else reference
        )
        self.retain_frame(parent, preview["record"])
        descriptor = {
            "schema_version": "retained-image-preview-v1",
            "recipe": recipe,
            "preview": {
                key: value
                for key, value in preview.items()
                if key not in {"png", "record"}
            },
        }
        data = image_canonical(descriptor)
        directory = self._directory(reference.asset_id, reference.revision, create=True)
        index = directory / f"preview-{_sha(image_canonical(recipe))}.index"
        with operation_lock(directory):
            previous = _read(index, 64)
            if previous is not None and previous != _sha(data).encode():
                raise ValueError("Conflicting immutable image preview recipe")
            _put(
                directory / f"png-{preview['png_sha256']}.png",
                preview["png"],
                MAX_IMAGE_PREVIEW_BYTES,
            )
            _put(directory / f"preview-{_sha(data)}.json", data, MAX_IMAGE_RECORD_BYTES)
            _put(index, _sha(data).encode(), 64)

    def preview(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        size: int,
        color_policy: ImageColorPolicy,
    ) -> dict[str, Any] | None:
        recipe = _recipe(reference, size, color_policy)
        directory = self._directory(reference.asset_id, reference.revision)
        index = _read(directory / f"preview-{_sha(image_canonical(recipe))}.index", 64)
        if index is None:
            return None
        key = _checked_hash(index.decode("ascii"))
        descriptor = _object(directory / f"preview-{key}.json", key)
        if (
            descriptor is None
            or descriptor.get("schema_version") != "retained-image-preview-v1"
            or descriptor.get("recipe") != recipe
        ):
            raise ValueError(
                "Retained image preview descriptor is missing or mismatched"
            )
        preview = descriptor["preview"]
        parent = (
            reference.parent
            if isinstance(reference, NativeImageRegionReference)
            else reference
        )
        record = self.frame(parent)
        png = _read(
            directory / f"png-{_checked_hash(preview['png_sha256'])}.png",
            MAX_IMAGE_PREVIEW_BYTES,
        )
        if record is None or png is None:
            raise ValueError("Retained image preview is incomplete")
        result = {**preview, "record": record, "png": png}
        self._check_preview(reference, size, result)
        return result
