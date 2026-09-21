import base64
import hashlib
import io
import json

import pytest
from PIL import Image, TiffImagePlugin, features
from PIL.PngImagePlugin import iTXt

from src.domain.native_image import NativeImageFrameLocator, NativeImageRegionSelector
from src.infrastructure.native_image_document import NativeImage
from src.infrastructure.native_image_metadata import MetadataEncoder, canonical
from src.infrastructure.native_image_structure import tiff_frame_count
from tests.native_image_helpers import encoded, grid, srgb_profile


@pytest.mark.parametrize("format_name", ["PNG", "JPEG", "TIFF"])
@pytest.mark.parametrize("orientation", list(range(1, 9)))
def test_oriented_frame_pixels_metadata_and_source(format_name, orientation):
    data = encoded(format_name, orientation)
    before = hashlib.sha256(data).hexdigest()
    native = NativeImage()
    record = native.read_frame(data, NativeImageFrameLocator(frame_index=0))
    assert record["source_orientation"] == orientation
    assert record["stored_size_px"] == [12, 8]
    assert record["displayed_size_px"] == ([8, 12] if orientation >= 5 else [12, 8])
    assert "Agent fixture" in json.dumps(record)
    if format_name == "PNG":
        assert "研究 007 µg" in json.dumps(record, ensure_ascii=False)
    # The lossless fixture's raw pixels are known before encoding; do not reuse
    # ImageOps or TIFF's automatic orientation as the expected-value oracle.
    expected = grid()
    if format_name == "JPEG":
        with Image.open(io.BytesIO(data)) as jpeg:
            expected = jpeg.copy()  # JPEG decoding does not apply EXIF orientation.
    methods = {
        2: Image.Transpose.FLIP_LEFT_RIGHT,
        3: Image.Transpose.ROTATE_180,
        4: Image.Transpose.FLIP_TOP_BOTTOM,
        5: Image.Transpose.TRANSPOSE,
        6: Image.Transpose.ROTATE_270,
        7: Image.Transpose.TRANSVERSE,
        8: Image.Transpose.ROTATE_90,
    }
    if orientation in methods:
        expected = expected.transpose(methods[orientation])
    expected = expected.convert("RGBA")
    actual = native.render(data, NativeImageFrameLocator(frame_index=0), 64)
    with Image.open(io.BytesIO(actual["png"])) as preview:
        assert preview.size == expected.size
        assert preview.tobytes() == expected.tobytes()
    assert hashlib.sha256(data).hexdigest() == before
    assert native.inspect(data)["frame_count"] == 1
    assert canonical(record) == canonical(
        native.read_frame(data, NativeImageFrameLocator(frame_index=0))
    )


def test_fraction_region_uses_oriented_geometry_and_explicit_pixel_rounding():
    data = encoded("PNG", 6)
    native = NativeImage()
    selector = NativeImageRegionSelector(rect=[0.1, 0.1, 0.6, 0.7])
    result = native.render_region(
        data, NativeImageFrameLocator(frame_index=0), selector, 64
    )
    assert result["source_pixel_bounds"] == [0, 1, 5, 9]
    expected = (
        grid().transpose(Image.Transpose.ROTATE_270).convert("RGBA").crop((0, 1, 5, 9))
    )
    with Image.open(io.BytesIO(result["png"])) as preview:
        assert preview.tobytes() == expected.tobytes()


def test_multipage_tiff_reads_every_frame_and_keeps_typed_metadata():
    first, second = grid(), Image.new("I;16", (5, 3))
    second.putdata([256 + n for n in range(15)])
    output = io.BytesIO()
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[65000] = b"private\x00bytes"
    first.save(
        output, format="TIFF", save_all=True, append_images=[second], tiffinfo=tags
    )
    data = output.getvalue()
    assert tiff_frame_count(data) == 2
    native = NativeImage()
    assert native.inspect(data)["frame_count"] == 2
    record = native.read_frame(data, NativeImageFrameLocator(frame_index=1))
    assert record["decoded_mode"].startswith("I;16")
    assert record["source_bits_per_sample"] == [16]
    assert record["decoded_bits_per_sample"] == 16
    assert "65000" in json.dumps(record)
    assert len(native.decompose(data)) == 2


def test_apng_default_frame_and_animation_timing_are_not_flattened():
    poster, first, second = [
        Image.new("RGBA", (10, 7), color) for color in ["red", "green", "blue"]
    ]
    output = io.BytesIO()
    poster.save(
        output,
        format="PNG",
        save_all=True,
        append_images=[first, second],
        default_image=True,
        duration=[50, 125],
        loop=2,
    )
    native = NativeImage()
    records = [entry["record"] for entry in native.decompose(output.getvalue())]
    assert len(records) == 3
    assert [r["frame_role"] for r in records] == ["default_image", "frame", "frame"]
    assert [r["duration_ms"] for r in records] == [None, 50.0, 125.0]
    assert len({r["decoded_pixels_sha256"] for r in records}) == 3


@pytest.mark.parametrize("format_name", ["GIF", "WEBP", "BMP", "AVIF"])
def test_other_raster_decoders(format_name):
    if format_name in {"WEBP", "AVIF"} and not features.check(format_name.lower()):
        pytest.skip(f"Pillow {format_name} decoder is unavailable")
    output = io.BytesIO()
    image = grid()
    image.save(output, format=format_name)
    native = NativeImage()
    assert native.inspect(output.getvalue())["format"] == format_name
    assert native.render(output.getvalue(), NativeImageFrameLocator(frame_index=0), 64)[
        "png"
    ].startswith(b"\x89PNG")


def test_tiff_truncated_or_cyclic_main_chain_is_rejected_before_decoding():
    data = bytearray(encoded("TIFF"))
    order = "little" if data[:2] == b"II" else "big"
    offset = int.from_bytes(data[4:8], order)
    count = int.from_bytes(data[offset : offset + 2], order)
    next_at = offset + 2 + count * 12
    data[next_at : next_at + 4] = offset.to_bytes(4, order)
    with pytest.raises(ValueError, match="cycle"):
        NativeImage().inspect(bytes(data))
    data[next_at : next_at + 4] = (len(data) + 10).to_bytes(4, order)
    with pytest.raises(ValueError, match="truncated"):
        NativeImage().inspect(bytes(data))


def test_metadata_encoder_retains_rational_binary_large_integer_and_surrogates():
    source = {
        1: TiffImagePlugin.IFDRational(1, 3),
        2: b"\x00\xff",
        3: 2**100,
        4: "bad\ud800text",
        5: float("inf"),
    }
    value = MetadataEncoder().encode(source)
    entries = {entry["key"]["decimal"]: entry["value"] for entry in value["entries"]}
    assert entries["1"] == {"type": "rational", "numerator": "1", "denominator": "3"}
    assert base64.b64decode(entries["2"]["base64"]) == b"\x00\xff"
    assert entries["3"]["decimal"] == str(2**100)
    assert (
        base64.b64decode(entries["4"]["base64"]).decode("utf-8", "surrogatepass")
        == source[4]
    )
    assert entries["5"]["finite"] is False
    canonical(value)


def test_international_png_metadata_retains_language_and_plain_transport_types():
    record = MetadataEncoder().encode(iTXt("研究", "zh-TW", "說明"))
    assert record["text"] == {"type": "text", "value": "研究"}
    assert record["language"]["value"] == "zh-TW"
    assert record["translated_keyword"]["value"] == "說明"
    assert type(record["text"]["value"]) is str


def test_truncated_gif_cannot_masquerade_as_a_shorter_valid_sequence():
    first, second = [Image.new("RGB", (5, 4), color) for color in ["red", "blue"]]
    output = io.BytesIO()
    first.save(
        output,
        format="GIF",
        save_all=True,
        append_images=[second],
        duration=[40, 90],
        loop=2,
    )
    data = output.getvalue()
    records = NativeImage().records(data)
    assert len(records) == 2
    assert [r["duration_ms"] for r in records] == [40, 90]
    assert data[-1:] == b";"
    for truncated in (data[:-1], data[:-10]):
        with pytest.raises(ValueError, match="truncated"):
            NativeImage().read_frame(truncated, NativeImageFrameLocator(frame_index=0))


def test_color_managed_preview_has_explicit_policy_and_no_stale_source_profile():
    native = NativeImage()
    data = encoded(icc_profile=srgb_profile())
    preview = native.render(data, NativeImageFrameLocator(frame_index=0), 64)
    assert preview["rendering"]["color_transform"] == "embedded_icc_to_srgb"
    with Image.open(io.BytesIO(preview["png"])) as image:
        assert "icc_profile" not in image.info
    invalid = encoded(icc_profile=b"invalid profile")
    assert native.inspect(invalid)["frame_count"] == 1
    with pytest.raises(ValueError, match="ICC"):
        native.render(invalid, NativeImageFrameLocator(frame_index=0), 64)
    assert (
        native.render(invalid, NativeImageFrameLocator(frame_index=0), 64, "unmanaged")[
            "rendering"
        ]["color_transform"]
        == "unmanaged_rgba8"
    )


def test_invalid_frame_geometry_and_metadata_limits(monkeypatch):
    from src.infrastructure import native_image_decode, native_image_metadata

    data = encoded()
    with pytest.raises(ValueError, match="outside"):
        NativeImage().read_frame(data, NativeImageFrameLocator(frame_index=1))
    with pytest.raises(ValueError, match="nonempty"):
        NativeImageRegionSelector(rect=[0.5, 0.1, 0.4, 0.9])
    monkeypatch.setattr(native_image_decode, "MAX_FRAME_PIXELS", 20)
    with pytest.raises(ValueError, match="pixel limit"):
        NativeImage().inspect(data)
    monkeypatch.setattr(native_image_metadata, "MAX_IMAGE_METADATA_BYTES", 20)
    with pytest.raises(ValueError, match="byte limit"):
        MetadataEncoder().encode(b"x" * 100)
