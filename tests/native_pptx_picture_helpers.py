"""Asymmetric image assets and real presentation picture requests."""

import hashlib
import io

from PIL import Image

from src.domain.native_file_reference import NativeFileReference
from src.domain.native_pptx_picture import NativePptxPictureCreate
from tests.native_pptx_shape_helpers import addition


def raster(format="PNG", color="red", size=(80, 40)):
    image = Image.new("RGB", size, color)
    image.putpixel((0, 0), (0, 255, 0))
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()


def file_ref(data, letter="a"):
    return NativeFileReference(
        asset_id="file_" + letter * 32, revision=hashlib.sha256(data).hexdigest()
    )


def request(pptx, image, *, fit="contain", region="slide", grouped=False):
    return NativePptxPictureCreate(
        container=addition(pptx, region=region, grouped=grouped).container,
        image=file_ref(image),
        left=914400,
        top=914400,
        width=1828800,
        height=1828800,
        fit=fit,
        name="Evidence picture",
        description="Exact source image µ",
    )


def sources(*images):
    return {
        f"{file_ref(data).asset_id}:{file_ref(data).revision}": data for data in images
    }
