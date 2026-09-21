import hashlib
import io
import struct
import zlib

import pytest
from PIL import Image, ImageCms

from src.domain.native_image import NativeImageExtract, NativeImageFrameMap
from src.domain.native_image_evidence import image_frame_reference
from src.infrastructure.native_image_document import NativeImage
from tests.unit.test_native_image_revision import (
    CANDIDATE_ID,
    SOURCE_ID,
    plan_for,
    references,
)


def palette_png(color, transparency=None):
    image = Image.new("P", (3, 2))
    image.putdata([0, 1, 0, 1, 1, 0])
    image.putpalette([*color, 0, 255, 0] + [0] * 762)
    stream = io.BytesIO()
    kwargs = {} if transparency is None else {"transparency": transparency}
    image.save(stream, format="PNG", **kwargs)
    return stream.getvalue()


@pytest.mark.parametrize("change", ["palette", "transparency"])
def test_palette_and_transparency_are_pixels_not_ignorable_metadata(change):
    before = palette_png((255, 0, 0))
    after = (
        palette_png((0, 0, 255)) if change == "palette" else palette_png((255, 0, 0), 0)
    )
    old_records, old = references(before, SOURCE_ID)
    new_records, new = references(after, CANDIDATE_ID)
    assert (
        old_records[0]["decoded_pixels_sha256"]
        == new_records[0]["decoded_pixels_sha256"]
    )
    assert (
        old_records[0]["decoded_rgba8_sha256"] != new_records[0]["decoded_rgba8_sha256"]
    )
    request = plan_for(
        before,
        after,
        [NativeImageFrameMap(before=old[0], after=new[0], metadata="replace")],
    )
    with pytest.raises(ValueError, match="changed pixels"):
        NativeImage().accept_candidate(before, after, request, SOURCE_ID)


def rgb16_png(low_byte=52):
    def chunk(kind, body):
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", zlib.crc32(kind + body))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 16, 2, 0, 0, 0))
        + chunk(
            b"IDAT",
            zlib.compress(
                bytes([0, 18, low_byte, 86, 120, 154, 188, 1, 2, 3, 4, 5, 6])
            ),
        )
        + chunk(b"IEND", b"")
    )


def test_equal_rgb8_decoding_cannot_prove_high_precision_sample_preservation():
    before, after = rgb16_png(), rgb16_png(53)
    old_records, old = references(before, SOURCE_ID)
    new_records, new = references(after, CANDIDATE_ID)
    assert old_records[0]["source_bits_per_sample"] == [16]
    assert old_records[0]["decoded_bits_per_sample"] == 8
    assert (
        old_records[0]["decoded_pixels_sha256"]
        == new_records[0]["decoded_pixels_sha256"]
    )
    request = plan_for(
        before, after, [NativeImageFrameMap(before=old[0], after=new[0])]
    )
    with pytest.raises(ValueError, match="precision"):
        NativeImage().accept_candidate(before, after, request, SOURCE_ID)
    extraction = NativeImageExtract(
        name="projection.png",
        reference=old[0],
        pixel_policy="preserve_decoded",
        metadata_policy="pixels_only",
    )
    with pytest.raises(ValueError, match="precision"):
        NativeImage().extract(before, extraction)
    extraction.pixel_policy = "srgb_rgba8"
    output, _ = NativeImage().extract(before, extraction)
    assert NativeImage().records(output)[0]["source_bits_per_sample"] == [8]


def test_monochrome_bmp_reports_one_bit_and_preserves_native_samples():
    image = Image.new("1", (9, 3))
    image.putdata([index % 3 == 0 for index in range(27)])
    stream = io.BytesIO()
    image.save(stream, format="BMP")
    data = stream.getvalue()
    native = NativeImage()
    record = native.records(data)[0]
    assert record["source_bits_per_sample"] == [1]
    reference = image_frame_reference(
        record, SOURCE_ID, hashlib.sha256(data).hexdigest()
    )
    output, _ = native.extract(
        data,
        NativeImageExtract(
            name="mono.png",
            reference=reference,
            pixel_policy="preserve_decoded",
            metadata_policy="pixels_only",
        ),
    )
    with Image.open(io.BytesIO(output)) as actual:
        assert actual.mode == "1" and actual.tobytes() == image.tobytes()


def test_transparent_palette_extraction_retains_alpha_in_both_pixel_policies():
    data = palette_png((255, 0, 0), 0)
    _, refs = references(data, SOURCE_ID)
    request = NativeImageExtract(
        name="alpha.png",
        reference=refs[0],
        pixel_policy="preserve_decoded",
        metadata_policy="pixels_only",
    )
    output, _ = NativeImage().extract(data, request)
    with Image.open(io.BytesIO(output)) as actual:
        assert actual.mode == "P"
        assert actual.convert("RGBA").getpixel((0, 0)) == (255, 0, 0, 0)
        assert actual.convert("RGBA").getpixel((1, 0)) == (0, 255, 0, 255)
    request.pixel_policy = "srgb_rgba8"
    output, _ = NativeImage().extract(data, request)
    with Image.open(io.BytesIO(output)) as actual:
        assert actual.mode == "RGBA"
        assert actual.getpixel((0, 0)) == (255, 0, 0, 0)
        assert actual.getpixel((1, 0)) == (0, 255, 0, 255)


def test_lab_tiff_native_samples_and_explicit_icc_projection():
    native = NativeImage()
    image = Image.new("LAB", (4, 3), (180, 130, 140))
    stream = io.BytesIO()
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()
    image.save(stream, format="TIFF", icc_profile=profile)
    data = stream.getvalue()
    record = native.records(data)[0]
    assert record["decoded_mode"] == "LAB"
    assert record["decoded_rgba8_sha256"] is None
    reference = image_frame_reference(
        record, SOURCE_ID, hashlib.sha256(data).hexdigest()
    )
    request = NativeImageExtract(
        name="lab.tif",
        reference=reference,
        pixel_policy="preserve_decoded",
        metadata_policy="pixels_only",
    )
    output, _ = native.extract(data, request)
    with Image.open(io.BytesIO(output)) as result:
        assert result.mode == "LAB" and result.tobytes() == image.tobytes()
    request.pixel_policy = "srgb_rgba8"
    output, report = native.extract(data, request)
    assert native.records(output)[0]["decoded_mode"] == "RGBA"
    assert report.changes[0]["color_transform"] == "embedded_icc_to_srgb"
