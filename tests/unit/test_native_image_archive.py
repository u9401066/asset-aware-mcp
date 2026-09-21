"""Retained image evidence must detect corruption instead of replacing history."""

import copy
import hashlib
import json

import pytest

from src.domain.native_image import NativeImageFrameLocator, NativeImageRegionSelector
from src.domain.native_image_evidence import image_frame_reference, image_region_record
from src.infrastructure.native_file_io import operation_lock
from src.infrastructure.native_image_archive import FileNativeImageArchive
from src.infrastructure.native_image_document import NativeImage
from tests.native_image_helpers import encoded


@pytest.fixture
def retained(tmp_path):
    data = encoded("PNG", 6)
    revision = hashlib.sha256(data).hexdigest()
    asset_id = "file_" + "a" * 32
    adapter = NativeImage()
    records = adapter.records(data)
    reference = image_frame_reference(records[0], asset_id, revision)
    store = FileNativeImageArchive(tmp_path / "store")
    catalog = store.retain_catalog(asset_id, revision, records)
    preview = adapter.render(data, NativeImageFrameLocator(frame_index=0), 768)
    store.retain_preview(reference, 768, "embedded_to_srgb", preview)
    directory = store.root / asset_id / "image-evidence" / revision
    return store, data, reference, records, catalog, preview, directory


def test_retention_survives_new_repository_and_is_byte_immutable(retained):
    store, _, ref, records, catalog, preview, directory = retained
    files = {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()
    }
    other = FileNativeImageArchive(store.root)
    assert other.frame(ref) == records[0]
    assert other.catalog(ref.asset_id, ref.revision, catalog["catalog_sha256"]) == (
        catalog,
        records,
    )
    assert other.preview(ref, 768, "embedded_to_srgb") == preview
    other.retain_catalog(ref.asset_id, ref.revision, records)
    other.retain_preview(ref, 768, "embedded_to_srgb", preview)
    assert files == {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()
    }
    assert other.preview(ref, 64, "embedded_to_srgb") is None
    assert other.preview(ref, 768, "unmanaged") is None


@pytest.mark.parametrize("kind", ["frame", "catalog", "descriptor", "png", "index"])
@pytest.mark.parametrize("damage", ["replace", "delete", "symlink"])
def test_damaged_archive_never_falls_back_to_fresh_decoding(
    retained, tmp_path, kind, damage
):
    store, _, ref, _, catalog, _, directory = retained
    patterns = {
        "frame": "frame-*.json",
        "catalog": "catalog-*.json",
        "descriptor": "preview-*.json",
        "png": "png-*.png",
        "index": "preview-*.index",
    }
    path = next(directory.glob(patterns[kind]))
    if damage == "replace":
        path.write_bytes(b"corrupt")
    elif damage == "delete":
        path.unlink()
    else:
        target = tmp_path / "external"
        target.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            pytest.skip("Symlink creation requires platform permission")
    # Missing top-level commit markers mean uncaptured; missing referenced files
    # or any corrupt entry are errors, never an apparently valid partial capture.
    read = (
        (lambda: store.catalog(ref.asset_id, ref.revision, catalog["catalog_sha256"]))
        if kind in {"frame", "catalog"}
        else (lambda: store.preview(ref, 768, "embedded_to_srgb"))
    )
    if damage == "delete" and kind in {"catalog", "index"}:
        assert read() is None
    else:
        with pytest.raises(ValueError):
            read()


def test_frame_and_preview_capture_reject_wrong_full_references(retained):
    store, _, ref, records, _, preview, _ = retained
    altered = copy.deepcopy(records[0])
    altered["decoder"]["version"] = "changed"
    with pytest.raises(ValueError, match="full reference"):
        store.retain_frame(ref, altered)
    with pytest.raises(ValueError, match="full reference"):
        store.retain_preview(
            ref, 768, "embedded_to_srgb", {**preview, "record": altered}
        )
    for key, value in (
        ("png", b"bad"),
        ("width_px", 100),
        ("source_pixel_bounds", [0, 0, 1, 1]),
    ):
        with pytest.raises(ValueError):
            store.retain_preview(ref, 768, "embedded_to_srgb", {**preview, key: value})


def test_same_recipe_cannot_be_overwritten_even_when_new_output_is_valid(retained):
    store, _, ref, _, _, preview, _ = retained
    changed = {**preview, "rendering": {**preview["rendering"], "version": "new"}}
    with pytest.raises(ValueError, match="immutable image preview recipe"):
        store.retain_preview(ref, 768, "embedded_to_srgb", changed)
    assert store.preview(ref, 768, "embedded_to_srgb") == preview


def test_region_preview_binds_geometry_size_and_color_recipe(retained):
    store, data, ref, records, _, _, _ = retained
    selector = NativeImageRegionSelector(rect=[0.1, 0.1, 0.6, 0.7])
    from src.domain.native_image import NativeImageRegionReference

    region = NativeImageRegionReference.model_validate(
        image_region_record(ref, selector, records[0])["evidence"]
    )
    preview = NativeImage().render_region(data, ref.locator, selector, 64, "unmanaged")
    store.retain_preview(region, 64, "unmanaged", preview)
    assert store.preview(region, 64, "unmanaged") == preview
    assert store.preview(region, 64, "embedded_to_srgb") is None
    assert store.preview(ref, 64, "unmanaged") is None


def test_catalog_complete_order_budget_and_lock_guards(retained, monkeypatch):
    store, _, ref, records, _, _, directory = retained
    with pytest.raises(ValueError, match="complete ordered"):
        store.retain_catalog(ref.asset_id, ref.revision, records * 2)
    with pytest.raises(ValueError, match="frame count"):
        store.retain_catalog(ref.asset_id, ref.revision, [])
    with operation_lock(directory), pytest.raises(ValueError, match="busy"):
        store.retain_frame(ref, records[0])
    import src.infrastructure.native_image_archive as module

    monkeypatch.setattr(module, "MAX_IMAGE_RECORD_BYTES", 10)
    with pytest.raises(ValueError, match="budget"):
        store.retain_catalog(ref.asset_id, ref.revision, records)


def test_paths_and_ancestor_symlinks_cannot_escape_archive(retained, tmp_path):
    store, _, ref, _, _, _, directory = retained
    with pytest.raises(ValueError, match="asset ID"):
        store.catalog("../outside", ref.revision, "a" * 64)
    with pytest.raises(ValueError, match="hash"):
        store.catalog(ref.asset_id, ref.revision, "../outside")
    original = directory.parent
    moved = tmp_path / "moved"
    original.rename(moved)
    try:
        original.symlink_to(moved, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation requires platform permission")
    with pytest.raises(ValueError, match="symlink"):
        store.frame(ref)


def test_catalog_hash_cannot_bind_different_source_revision(retained):
    store, _, ref, _, catalog, _, directory = retained
    other = store.root / ref.asset_id / "image-evidence" / ("b" * 64)
    other.mkdir()
    for path in directory.iterdir():
        if path.name == ".operation.lock":
            continue
        (other / path.name).write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="records/source"):
        store.catalog(ref.asset_id, "b" * 64, catalog["catalog_sha256"])


def test_preview_index_and_descriptor_cannot_rebind_recipe(retained):
    store, _, ref, _, _, _, directory = retained
    path = next(directory.glob("preview-*.json"))
    descriptor = json.loads(path.read_bytes())
    descriptor["recipe"]["render_size"] = 64
    from src.domain.native_image_evidence import image_canonical

    data = image_canonical(descriptor)
    key = hashlib.sha256(data).hexdigest()
    (directory / f"preview-{key}.json").write_bytes(data)
    next(directory.glob("preview-*.index")).write_text(key)
    with pytest.raises(ValueError, match="descriptor"):
        store.preview(ref, 768, "embedded_to_srgb")
