import hashlib
import io

import pytest
from PIL import Image

from src.domain.native_image import (
    NativeImageBlank,
    NativeImageExtract,
    NativeImageRegionSelector,
)
from src.domain.native_image_evidence import image_frame_reference, image_region_record
from src.infrastructure.native_image_document import NativeImage
from tests.native_image_helpers import encoded, grid


def test_blank_image_creation_and_exact_readback():
    request = NativeImageBlank(
        name="canvas.png", width=9, height=7, rgba=[7, 50, 200, 128]
    )
    data, receipt = NativeImage().create(request)
    with Image.open(io.BytesIO(data)) as image:
        assert image.mode == "RGBA" and image.size == (9, 7)
        assert image.tobytes() == bytes(request.rgba) * 63
    assert "decoded_sample_exact_readback" in receipt.checks


@pytest.mark.parametrize("format_name", ["PNG", "TIFF"])
def test_extracted_region_retains_samples_and_explicitly_omits_metadata(format_name):
    data = encoded("PNG", 6)
    native = NativeImage()
    record = native.records(data)[0]
    reference = image_frame_reference(
        record, "file_" + "a" * 32, hashlib.sha256(data).hexdigest()
    )
    region = NativeImageRegionSelector(rect=[0.1, 0.1, 0.6, 0.7])
    request = NativeImageExtract(
        name="crop." + ("png" if format_name == "PNG" else "tif"),
        reference=reference,
        region=region,
        pixel_policy="preserve_decoded",
        metadata_policy="pixels_only",
    )
    output, receipt = native.extract(data, request)
    expected = grid().transpose(Image.Transpose.ROTATE_270).crop((0, 1, 5, 9))
    with Image.open(io.BytesIO(output)) as actual:
        assert actual.tobytes() == expected.tobytes()
        assert actual.mode == expected.mode
        assert not actual.getexif().get(315) and "comment" not in actual.info
    assert receipt.changes[0]["source"] == reference.model_dump(mode="json")
    assert receipt.changes[0]["source_pixel_bounds"] == [0, 1, 5, 9]
    region_record = image_region_record(reference, region, record)
    assert region_record["source_pixel_bounds"] == [0, 1, 5, 9]
    assert data == encoded("PNG", 6)


def test_extraction_rejects_wrong_source_or_full_representation():
    data = encoded()
    record = NativeImage().records(data)[0]
    reference = image_frame_reference(
        record, "file_" + "a" * 32, hashlib.sha256(data).hexdigest()
    )
    request = NativeImageExtract(
        name="crop.png",
        reference=reference,
        pixel_policy="srgb_rgba8",
        metadata_policy="pixels_only",
    )
    with pytest.raises(ValueError, match="revision"):
        NativeImage().extract(encoded("PNG", 6), request)
    reference.value_sha256 = "0" * 64
    with pytest.raises(ValueError, match="complete"):
        NativeImage().extract(data, request)


def test_sixteen_bit_tiff_derivative_preserves_samples():
    image = Image.new("I;16", (3, 2))
    image.putdata([0, 255, 256, 1024, 32768, 65535])
    buffer = io.BytesIO()
    image.save(buffer, format="TIFF")
    data = buffer.getvalue()
    native = NativeImage()
    record = native.records(data)[0]
    reference = image_frame_reference(
        record, "file_" + "a" * 32, hashlib.sha256(data).hexdigest()
    )
    output, _ = native.extract(
        data,
        NativeImageExtract(
            name="pixels.tif",
            reference=reference,
            pixel_policy="preserve_decoded",
            metadata_policy="pixels_only",
        ),
    )
    with Image.open(io.BytesIO(output)) as result:
        assert list(result.get_flattened_data()) == [0, 255, 256, 1024, 32768, 65535]
