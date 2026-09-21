import hashlib
import io

import pytest
from PIL import Image

from src.domain.native_image import (
    NativeImageCompose,
    NativeImageFrameInput,
    NativeImageRegionSelector,
)
from src.domain.native_image_evidence import image_frame_reference
from src.infrastructure.native_image_document import NativeImage
from tests.native_image_helpers import encoded, grid


def request_for(data, **kwargs):
    native = NativeImage()
    record = native.records(data)[0]
    reference = image_frame_reference(
        record, "file_" + "a" * 32, hashlib.sha256(data).hexdigest()
    )
    request = NativeImageCompose(
        name="ordered.tif",
        frames=[
            NativeImageFrameInput(
                reference=reference, pixel_policy="preserve_decoded", **kwargs
            )
        ],
        metadata_policy="pixels_only",
    )
    return request, {f"{reference.asset_id}:{reference.revision}": data}


def test_tiff_composition_retains_order_duplicates_and_oriented_crop_samples():
    data = encoded("PNG", 6)
    request, sources = request_for(data)
    crop = request.frames[0].model_copy(deep=True)
    crop.region = NativeImageRegionSelector(rect=[0.1, 0.1, 0.6, 0.7])
    request.frames = [crop, request.frames[0], crop.model_copy(deep=True)]
    output, result = NativeImage().compose(request, sources)
    original = grid().transpose(Image.Transpose.ROTATE_270)
    expected = [original.crop((0, 1, 5, 9)), original, original.crop((0, 1, 5, 9))]
    with Image.open(io.BytesIO(output)) as actual:
        assert actual.n_frames == 3
        for index, frame in enumerate(expected):
            actual.seek(index)
            assert actual.size == frame.size
            assert actual.tobytes() == frame.tobytes()
            assert not actual.getexif().get(315)
    assert [c["output_frame"] for c in result.changes] == [0, 1, 2]
    assert all(
        c["source"] == request.frames[0].reference.model_dump(mode="json")
        for c in result.changes
    )
    assert sources[next(iter(sources))] == data


def test_composition_checks_complete_sources_hashes_and_aggregate_bounds(monkeypatch):
    from src.infrastructure import native_image_compose

    data = encoded()
    request, sources = request_for(data)
    with pytest.raises(ValueError, match="exactly"):
        NativeImage().compose(request, {})
    with pytest.raises(ValueError, match="revision"):
        NativeImage().compose(request, {next(iter(sources)): encoded("PNG", 6)})
    monkeypatch.setattr(native_image_compose, "MAX_DOCUMENT_PIXELS", 100)
    request.frames *= 2
    with pytest.raises(ValueError, match="aggregate pixel"):
        NativeImage().compose(request, sources)
    monkeypatch.setattr(native_image_compose, "MAX_NATIVE_BYTES", 1)
    with pytest.raises(ValueError, match="aggregate"):
        NativeImage().compose(request, sources)
