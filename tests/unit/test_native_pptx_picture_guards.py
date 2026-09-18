"""Reject picture corruption, unintended mappings and unsupported image sources."""

from __future__ import annotations

import io

import pytest
from lxml import etree
from PIL import Image

from src.domain.native_pptx import NativePptxShapeLocator
from src.domain.native_pptx_picture import NativePptxPictureReplace
from src.infrastructure import native_pptx_picture_parts, native_raster_image
from src.infrastructure.native_ooxml import DOC_REL_NS, xml_bytes
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_pptx_package import A_NS, NS, NativePptxPackage
from src.infrastructure.native_pptx_pictures import (
    add_pictures,
    read_picture,
    replace_pictures,
)
from src.infrastructure.native_raster_image import inspect_image
from tests.native_pptx_helpers import build_presentation
from tests.native_pptx_picture_helpers import file_ref, raster, request, sources
from tests.native_pptx_shape_helpers import reference
from tests.native_workbook_helpers import _replace


@pytest.fixture
def picture():
    data, image = build_presentation(), raster()
    updated, result = add_pictures(data, [request(data, image)], sources(image))
    return updated, NativePptxShapeLocator(**result.changes[0]["locator"]), image


@pytest.mark.parametrize(
    "corruption", ["unrelated", "media", "relationship", "inventory"]
)
def test_writer_corruption_is_rejected(corruption, monkeypatch):
    original = native_pptx_picture_parts.extend_package

    def corrupt(package, replacements, additions):
        data = original(package, replacements, additions)
        if corruption == "unrelated":
            return _replace(data, {"customXml/preserve.xml": b"<tampered/>"})
        if corruption == "media":
            part = next(p for p in additions if p.endswith(".png"))
            return _replace(data, {part: raster(color="blue")})
        if corruption == "relationship":
            part = next(p for p in replacements if p.endswith(".rels"))
            root = NativePptxPackage(data).xml(part)
            root[-1].set("Target", "missing.png")
            return _replace(data, {part: xml_bytes(root)})
        return _replace(data, {"unexpected.bin": b"extra"})

    monkeypatch.setattr(native_pptx_picture_parts, "extend_package", corrupt)
    data, image = build_presentation(), raster()
    with pytest.raises(ValueError, match=r"package|addition|readback"):
        add_pictures(data, [request(data, image)], sources(image))


def test_replacement_cannot_change_target_geometry(picture, monkeypatch):
    data, locator, image = picture
    original = native_pptx_picture_parts.PictureParts.embed

    def change_geometry(self, *args):
        result = original(self, *args)
        self.package.locate(locator).find("p:spPr/a:xfrm", NS).set("rot", "600000")
        return result

    monkeypatch.setattr(
        native_pptx_picture_parts.PictureParts, "embed", change_geometry
    )
    ref = reference(data, NativePresentation().read_shape(data, locator))
    edit = NativePptxPictureReplace(reference=ref, image=file_ref(image))
    with pytest.raises(ValueError, match="outside the requested"):
        replace_pictures(data, [edit], sources(image))


@pytest.mark.parametrize("kind", ["external", "alternate", "wrong_type", "missing"])
def test_picture_relationship_guards(picture, kind):
    data, locator, _ = picture
    package = NativePptxPackage(data)
    node = package.locate(locator)
    blip = node.find("p:blipFill/a:blip", NS)
    if kind == "external":
        blip.set(f"{{{DOC_REL_NS}}}link", "externalRel")
    elif kind == "alternate":
        etree.SubElement(blip, f"{{{A_NS}}}extLst")
    elif kind == "missing":
        blip.set(f"{{{DOC_REL_NS}}}embed", "missing")
    else:
        blip.set(f"{{{DOC_REL_NS}}}embed", "rId1")  # Slide layout is not an image.
    bad = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    with pytest.raises(ValueError):
        read_picture(bad, locator)


@pytest.mark.parametrize(
    "failure",
    ["format", "orientation", "animated", "truncated", "crc", "pixels", "bytes"],
)
def test_raster_source_guards(failure, monkeypatch):
    raw = raster()
    if failure == "format":
        raw = raster("GIF")
    elif failure == "orientation":
        output = io.BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (20, 40)).save(output, format="JPEG", exif=exif)
        raw = output.getvalue()
    elif failure == "animated":
        output = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(
            output,
            format="PNG",
            save_all=True,
            append_images=[Image.new("RGB", (20, 20), "blue")],
        )
        raw = output.getvalue()
    elif failure == "truncated":
        raw = raster("JPEG")[:-30]
    elif failure == "crc":
        raw = raw[:-5] + bytes([raw[-5] ^ 1]) + raw[-4:]
    else:
        monkeypatch.setattr(
            native_raster_image,
            "MAX_IMAGE_PIXELS" if failure == "pixels" else "MAX_IMAGE_BYTES",
            1,
        )
    with pytest.raises(ValueError):
        inspect_image(raw)


def test_source_hash_is_not_trusted_from_input():
    data, image = build_presentation(), raster()
    item = request(data, image)
    with pytest.raises(ValueError, match="Stale image"):
        add_pictures(
            data,
            [item],
            {f"{item.image.asset_id}:{item.image.revision}": raster(color="blue")},
        )


def test_repeated_source_counts_toward_batch_pixel_budget():
    output = io.BytesIO()
    Image.new("RGB", (3000, 3000), "red").save(output, "PNG")
    data, image = build_presentation(), output.getvalue()
    item = request(data, image)
    with pytest.raises(ValueError, match="Picture batch"):
        add_pictures(data, [item] * 8, sources(image))


def test_repeated_embedding_does_not_overwrite_existing_media(picture):
    data, locator, image = picture
    before = NativePptxPackage(data)
    old_media = read_picture(data, locator)["media_part"]
    updated, result = add_pictures(data, [request(data, image)], sources(image))
    assert result.changes[0]["media_part"] != old_media
    after = NativePptxPackage(updated)
    assert after.parts[old_media] == before.parts[old_media] == image
    assert after.parts[result.changes[0]["media_part"]] == image
