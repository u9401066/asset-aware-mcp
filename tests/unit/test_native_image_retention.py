"""Decoder drift must preserve historical evidence without weakening edit checks."""

import copy

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_image import NativeImageFrameReference
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_derivation_store import FileNativeDerivationRepository
from src.infrastructure.native_image_archive import FileNativeImageArchive
from src.infrastructure.native_image_document import NativeImage
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_derivation_helpers import pair, record
from tests.native_image_helpers import encoded
from tests.native_image_service_helpers import catalog, complete, frame
from tests.native_workbook_helpers import _call
from tests.unit.test_native_image_wiki import export


def restarted(root):
    repository = FileNativeAssetRepository(root)
    return NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((root,)),
        derivations=FileNativeDerivationRepository(root, repository),
        images=NativeImage(),
        image_archive=FileNativeImageArchive(root),
    )


@pytest.fixture
def managed(tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(encoded("PNG", 6))
    service = restarted(tmp_path / "store")
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def drift(monkeypatch):
    import src.infrastructure.native_image_decode as decoder

    monkeypatch.setattr(decoder, "__version__", "simulated-next-decoder")


def pinned_frame(service, asset, reference):
    return complete(
        service,
        op="read_image_frame",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        image_locator=reference["locator"],
        reference=reference,
    )


def test_restart_and_decoder_drift_preserve_complete_records_regions_selections_and_previews(
    managed, monkeypatch
):
    service, asset, source = managed
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    before = frame(service, asset)
    ref = before["evidence"]
    old_catalog = catalog(service, asset)
    preview = _call(service, op="render_image_frame", reference=ref, render_size=64)
    region = _call(
        service,
        op="read_image_region",
        reference=ref,
        image_region={"rect": [0.1, 0.1, 0.6, 0.7]},
        render_size=64,
    )
    selection = _call(
        service,
        op="read_selection",
        reference=region["reference"],
        selection={"pointer": "/source_pixel_bounds"},
    )["evidence"]
    drift(monkeypatch)
    service = restarted(service.repository.root)
    for reference in (ref, region["reference"], selection):
        assert _call(service, op="verify", reference=reference)["valid"]
    proof = _call(service, op="verify", reference=ref)
    assert proof["representation_origin"] == "retained_projection"
    assert proof["current_decoder_reproduction"] == "not_checked"
    assert pinned_frame(service, asset, ref) == before
    assert (
        complete(
            service,
            op="read_image",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            image_catalog_sha256=old_catalog["catalog"]["catalog_sha256"],
        )
        == old_catalog
    )
    for op, prior in (("render_image_frame", preview), ("read_image_region", region)):
        retained = _call(service, op=op, reference=prior["reference"], render_size=64)
        assert retained["image_png"] == prior["image_png"]
        assert retained["rendering"] == prior["rendering"]
        assert retained["preview_origin"] == "retained_preview"
        assert retained["current_decoder_reproduction"] == "not_checked"
    current = frame(service, asset)
    assert current["evidence"] != ref
    assert current["decoder"]["version"] == "simulated-next-decoder"
    assert catalog(service, asset)["catalog"] != old_catalog["catalog"]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime


@pytest.mark.parametrize("size,policy", [(64, "embedded_to_srgb"), (768, "unmanaged")])
def test_uncaptured_historical_preview_is_not_substituted(
    managed, monkeypatch, size, policy
):
    service, asset, _ = managed
    ref = frame(service, asset)["evidence"]
    _call(service, op="render_image_frame", reference=ref, render_size=768)
    drift(monkeypatch)
    with pytest.raises(ValueError, match="Historical image preview is not retained"):
        _call(
            service,
            op="render_image_frame",
            reference=ref,
            render_size=size,
            image_color_policy=policy,
        )
    assert _call(service, op="verify", reference=ref)["valid"]


def test_old_catalog_and_native_wiki_remain_byte_identical_after_drift(
    managed, tmp_path, monkeypatch
):
    service, asset, _ = managed
    before = catalog(service, asset)
    root, manifest = export(service, asset, tmp_path / "wiki")
    files = {p.name: p.read_bytes() for p in root.iterdir()}
    drift(monkeypatch)
    service = restarted(service.repository.root)
    again, current = export(
        service,
        asset,
        tmp_path / "wiki",
        image_catalog_sha256=before["catalog"]["catalog_sha256"],
    )
    assert again == root and current == manifest
    assert files == {p.name: p.read_bytes() for p in root.iterdir()}
    new_root, _ = export(service, asset, tmp_path / "wiki")
    assert new_root != root
    assert files == {p.name: p.read_bytes() for p in root.iterdir()}


def test_cross_format_derivations_and_direct_operation_inputs_survive_drift(
    managed, tmp_path, monkeypatch
):
    service, asset, _ = managed
    ref = frame(service, asset)["evidence"]
    region = _call(
        service,
        op="read_image_region",
        reference=ref,
        image_region={"rect": [0.1, 0.1, 0.6, 0.7]},
    )["reference"]
    selected = _call(
        service,
        op="read_selection",
        reference=region,
        selection={"pointer": "/source_pixel_bounds"},
    )["evidence"]
    workbook, claim = pair(service)
    claim["sources"] = [ref, region, selected]
    claim["review"] = {
        "notes": "Synthetic decoder-drift test; no semantic review asserted"
    }
    created = record(service, workbook, claim)
    root, manifest = export(service, workbook, tmp_path / "wiki")
    files = {p.name: p.read_bytes() for p in root.iterdir()}
    derivative = _call(
        service,
        op="extract_image",
        image_extract={
            "name": "crop.png",
            "reference": ref,
            "region": {"rect": [0.0, 0.0, 0.5, 0.5]},
            "pixel_policy": "preserve_decoded",
            "metadata_policy": "pixels_only",
        },
    )["asset"]
    old_catalog = catalog(service, derivative)["catalog"]["catalog_sha256"]
    derived_root, derived_manifest = export(service, derivative, tmp_path / "wiki")
    drift(monkeypatch)
    service = restarted(service.repository.root)
    assert _call(
        service,
        op="verify_derivation",
        asset_id=workbook["asset_id"],
        derivation_id=created["derivation_id"],
    )["references_valid"]
    again, current = export(service, workbook, tmp_path / "wiki")
    assert again == root and current == manifest
    assert files == {p.name: p.read_bytes() for p in root.iterdir()}
    again, current = export(
        service, derivative, tmp_path / "wiki", image_catalog_sha256=old_catalog
    )
    assert again == derived_root and current == derived_manifest


def test_legacy_uncaptured_reference_requires_matching_current_decoder(
    managed, monkeypatch
):
    service, asset, _ = managed
    legacy = NativeDocumentService(
        service.repository, SpreadsheetFileAdapter(), images=NativeImage()
    )
    before = frame(legacy, asset)
    ref = before["evidence"]
    archive = service.image_archive
    assert archive.frame(NativeImageFrameReference.model_validate(ref)) is None
    drift(monkeypatch)
    proof = _call(service, op="verify", reference=ref)
    assert not proof["valid"] and proof["current_decoder_reproduction"] == "mismatched"
    with pytest.raises(ValueError, match="not retained"):
        pinned_frame(service, asset, ref)
    assert archive.frame(NativeImageFrameReference.model_validate(ref)) is None
    monkeypatch.undo()
    proof = _call(service, op="verify", reference=ref)
    assert proof["valid"] and proof["current_decoder_reproduction"] == "matched"
    assert archive.frame(NativeImageFrameReference.model_validate(ref)) is not None


def test_mutations_still_require_current_decoder_preconditions(managed, monkeypatch):
    service, asset, _ = managed
    old = catalog(service, asset)
    ref = old["frame_references"][0]
    drift(monkeypatch)
    assert _call(service, op="verify", reference=ref)["valid"]
    with pytest.raises(ValueError):
        _call(
            service,
            op="extract_image",
            image_extract={
                "name": "crop.png",
                "reference": ref,
                "region": {"rect": [0.0, 0.0, 0.5, 0.5]},
                "pixel_policy": "preserve_decoded",
                "metadata_policy": "pixels_only",
            },
        )
    with pytest.raises(ValueError):
        _call(
            service,
            op="update_image",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            image_update={
                "candidate": asset["file_reference"],
                "expected_catalog_sha256": old["catalog"]["catalog_sha256"],
                "frames": [{"op": "map", "before": ref, "after": ref}],
                "container_policy": "accept_exact_candidate_bytes",
            },
        )
    assert service.repository.load(asset["asset_id"]).revision == asset["revision"]


def test_saved_evidence_does_not_bypass_source_integrity_or_full_reference_match(
    managed,
):
    service, asset, _ = managed
    ref = frame(service, asset)["evidence"]
    _call(service, op="render_image_frame", reference=ref)
    wrong = copy.deepcopy(ref)
    wrong["locator"]["frame_index"] = 1
    with pytest.raises(ValueError, match="match asset, revision and locator"):
        complete(
            service,
            op="read_image_frame",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            image_locator={"frame_index": 0},
            reference=wrong,
        )
    blob = service.repository.root / asset["asset_id"] / "revisions" / asset["revision"]
    blob.write_bytes(b"damaged source")
    for op in ("verify", "render_image_frame"):
        with pytest.raises(ValueError):
            _call(service, op=op, reference=ref)


def test_new_decoder_pixels_and_metadata_cannot_impersonate_old_render(
    managed, monkeypatch
):
    service, asset, _ = managed
    old = frame(service, asset)
    ref = old["evidence"]
    import src.infrastructure.native_image_document as module

    original = module._frames

    def changed(data):
        for raw, image in original(data):
            raw["decoded_pixels_sha256"] = "f" * 64
            raw["metadata"]["simulated_decoder_change"] = True
            image.putpixel((0, 0), (1, 2, 3))
            yield raw, image

    monkeypatch.setattr(module, "_frames", changed)
    assert pinned_frame(service, asset, ref) == old
    assert frame(service, asset)["evidence"] != ref
    with pytest.raises(ValueError, match="Historical image preview"):
        _call(service, op="render_image_frame", reference=ref)
