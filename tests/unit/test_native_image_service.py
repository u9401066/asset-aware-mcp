import io

import pytest
from PIL import Image

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_derivation_store import FileNativeDerivationRepository
from src.infrastructure.native_image_document import NativeImage
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_image_helpers import encoded, grid
from tests.native_image_service_helpers import catalog, complete, frame, update
from tests.native_workbook_helpers import _call


@pytest.fixture
def managed_image(tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(encoded("PNG", 6))
    repository = FileNativeAssetRepository(tmp_path / "store")
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((tmp_path / "store",)),
        derivations=FileNativeDerivationRepository(tmp_path / "store", repository),
        images=NativeImage(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def test_native_image_crud_references_pixels_receipts_and_historical_sources(
    managed_image,
):
    service, asset, source = managed_image
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    initial = catalog(service, asset)
    before = frame(service, asset)
    reference = before["evidence"]
    assert initial["frame_references"] == [reference]
    assert asset["capabilities"]["read_image"] and asset["capabilities"]["edit_image"]
    assert (
        _call(service, op="inspect", asset_id=asset["asset_id"])["content"][
            "read_operation"
        ]
        == "read_image"
    )
    region = {"rect": [0.1, 0.1, 0.6, 0.7]}
    preview = _call(
        service,
        op="read_image_region",
        reference=reference,
        image_region=region,
        render_size=64,
    )
    expected = (
        grid().transpose(Image.Transpose.ROTATE_270).convert("RGBA").crop((0, 1, 5, 9))
    )
    with Image.open(io.BytesIO(preview["image_png"])) as actual:
        assert actual.tobytes() == expected.tobytes()
    assert _call(service, op="verify", reference=preview["reference"])["valid"]
    selected = _call(
        service,
        op="read_selection",
        reference=reference,
        selection={"pointer": "/stored_size_px"},
    )["evidence"]
    candidate = _call(
        service,
        op="extract_image",
        image_extract={
            "name": "crop.png",
            "reference": reference,
            "region": region,
            "pixel_policy": "preserve_decoded",
            "metadata_policy": "pixels_only",
        },
    )["asset"]
    after = frame(service, candidate)["evidence"]
    changed = update(
        service,
        asset,
        candidate,
        [
            {
                "op": "map",
                "before": reference,
                "after": after,
                "pixels": "replace",
                "metadata": "replace",
            }
        ],
    )
    receipt = complete(service, **changed["review_request"])
    assert (
        receipt["operation_result"]["changes"][0]["candidate"]
        == candidate["file_reference"]
    )
    assert service.repository.read(asset["asset_id"]) == service.repository.read(
        candidate["asset_id"]
    )
    for old in (reference, preview["reference"], selected):
        proof = _call(service, op="verify", reference=old)
        assert proof["valid"] and not proof["is_current_managed_revision"]
    current = changed["asset"]
    current_ref = frame(service, current)["evidence"]
    noop = update(
        service,
        current,
        candidate,
        [{"op": "map", "before": current_ref, "after": after}],
    )
    assert not noop["operation_result"]["committed"]
    assert complete(service, **noop["review_request"]) == receipt
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    restored = update(
        service,
        current,
        asset,
        [
            {
                "op": "map",
                "before": current_ref,
                "after": reference,
                "pixels": "replace",
                "metadata": "replace",
            }
        ],
    )
    assert restored["asset"]["revision"] == asset["revision"]
    latest = complete(service, **restored["review_request"])
    assert (
        latest["operation_result"]["changes"][0]["source_revision"]
        == current["revision"]
    )
    assert frame(service, asset)["evidence"] == reference
    assert len(service.repository.load(asset["asset_id"]).history) == 3
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime


def test_blank_and_multiframe_composition_have_complete_creation_receipts(
    managed_image,
):
    service, asset, source = managed_image
    original = source.read_bytes()
    canvas = _call(
        service,
        op="create_image",
        image_create={
            "name": "canvas.png",
            "width": 5,
            "height": 3,
            "rgba": [7, 9, 11, 128],
        },
    )
    canvas_ref = frame(service, canvas["asset"])["evidence"]
    source_ref = frame(service, asset)["evidence"]
    composed = _call(
        service,
        op="compose_images",
        image_compose={
            "name": "pages.tif",
            "metadata_policy": "pixels_only",
            "frames": [
                {"reference": ref, "pixel_policy": "preserve_decoded"}
                for ref in [canvas_ref, source_ref, canvas_ref]
            ],
        },
    )
    receipt = complete(service, **composed["review_request"])
    assert receipt["catalog"]["frame_count"] == 3
    assert [part["source"] for part in receipt["operation_result"]["changes"]] == [
        canvas_ref,
        source_ref,
        canvas_ref,
    ]
    with Image.open(
        io.BytesIO(service.repository.read(composed["asset"]["asset_id"]))
    ) as image:
        assert image.n_frames == 3
        assert image.getpixel((0, 0)) == (7, 9, 11, 128)
        image.seek(1)
        assert image.tobytes() == grid().transpose(Image.Transpose.ROTATE_270).tobytes()
    assert source.read_bytes() == original


@pytest.mark.parametrize("fault", ["stale", "archived", "reference", "receipt"])
def test_rejected_image_updates_leave_source_and_history_intact(
    managed_image, monkeypatch, fault
):
    from src.application import native_image_operations

    service, asset, source = managed_image
    original = source.read_bytes()
    before = frame(service, asset)["evidence"]
    if fault == "archived":
        _call(
            service,
            op="archive",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
        )
    if fault == "reference":
        before["value_sha256"] = "0" * 64
    request = {
        "op": "update_image",
        "asset_id": asset["asset_id"],
        "expected_revision": "0" * 64 if fault == "stale" else asset["revision"],
        "image_update": {
            "candidate": asset["file_reference"],
            "expected_catalog_sha256": catalog(service, asset)["catalog"][
                "catalog_sha256"
            ],
            "frames": [{"op": "map", "before": before, "after": before}],
            "container_policy": "accept_exact_candidate_bytes",
        },
    }
    if fault == "receipt":
        monkeypatch.setattr(native_image_operations, "MAX_IMAGE_READ_BYTES", 100)
    with pytest.raises(ValueError):
        _call(service, **request)
    assert len(service.repository.load(asset["asset_id"]).history) == 1
    assert source.read_bytes() == original


def test_forged_regions_and_frame_references_cannot_render_as_verified(managed_image):
    service, asset, _ = managed_image
    reference = frame(service, asset)["evidence"]
    reference["value_sha256"] = "0" * 64
    assert not _call(service, op="verify", reference=reference)["valid"]
    with pytest.raises(ValueError, match="verification"):
        _call(service, op="render_image_frame", reference=reference)
