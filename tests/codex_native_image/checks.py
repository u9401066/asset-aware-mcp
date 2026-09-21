"""Pixel and artifact checks independent of the native raster operation code."""

import base64
import io
import math

from PIL import Image, ImageOps

from tests.codex_native_pdf.trace import digest, payload
from tests.codex_pdf.trace import require


def source_bytes(workspace, asset_id, revision):
    from tests.codex_native_pdf.artifacts import load_asset

    asset = load_asset(workspace, asset_id)
    require(revision in {s["sha256"] for s in asset["history"]}, "Unknown revision")
    return (
        workspace / "data/native-assets" / asset_id / "revisions" / revision
    ).read_bytes()


def validate_workbook_read(args, record, data):
    from src.infrastructure.native_workbook_structure import NativeWorkbookStructure

    require(
        record.get("asset_id") == args["asset_id"]
        and record.get("revision") == args["revision"]
        and digest(data) == args["revision"],
        "Workbook read is not bound to its requested source revision",
    )
    expected = NativeWorkbookStructure().read(
        data, references=args.get("workbook_view", "structure") == "references"
    )
    actual = {
        key: value
        for key, value in record.items()
        if key not in {"asset_id", "revision", "operation_result"}
    }
    require(actual == expected, "Complete workbook read differs from native source")


def frames(data):
    result = []
    with Image.open(io.BytesIO(data)) as image:
        for index in range(image.n_frames):
            image.seek(index)
            result.append(ImageOps.exif_transpose(image).copy())
    return result


def same_pixels(actual, expected):
    require(
        (actual.mode, actual.size, actual.tobytes())
        == (expected.mode, expected.size, expected.tobytes()),
        "Native frame pixels/mode/geometry differ",
    )


def crop_bounds(rect, size):
    x0, y0, x1, y1 = rect
    width, height = size
    require(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, "Invalid crop geometry")
    return [
        math.floor(x0 * width),
        math.floor(y0 * height),
        math.ceil(x1 * width),
        math.ceil(y1 * height),
    ]


def covers_row(rect, expected):
    x0, y0, x1, y1 = rect
    a, b, c, d = expected["derivation"]["first_row_text_bounds"]
    # Font boxes include whitespace. Permit one raster pixel at their outer edge,
    # but never a crop omitting a glyph column or a different row.
    width, height = expected["derivation"]["size_px"]
    require(
        x0 <= a + 1 / width
        and y0 <= b + 1 / height
        and x1 >= c - 1 / width
        and y1 >= d - 1 / height,
        "Crop omits first-row text geometry",
    )
    require(y0 >= b - 0.02 and y1 <= d + 0.009, "Crop includes unrelated rows")


def validate_png(data, png, frame_index, size, rect=None):
    decoded = frames(data)[frame_index].convert("RGBA")
    bounds = crop_bounds(rect, decoded.size) if rect else [0, 0, *decoded.size]
    expected = decoded.crop(bounds)
    expected.thumbnail((size, size), Image.Resampling.LANCZOS)
    with Image.open(io.BytesIO(png)) as actual:
        require(actual.format == "PNG", "Preview is not PNG")
        same_pixels(actual, expected)
    return bounds


def validate_preview(call, workspace):
    args, result = call["arguments"]["native_request"], payload(call)
    ref = result["reference"]
    is_region = ref["schema_version"] == "native-image-region-ref-v1"
    parent = ref["parent"] if is_region else ref
    requested = args["reference"]
    require(
        requested == (parent if is_region and "image_region" in args else ref),
        "Preview reference differs from request",
    )
    if is_region:
        from tests.codex_native_pdf.trace import canonical

        record = result["region"]
        require(
            record["evidence"] == ref and record["parent"] == parent,
            "Region identity differs",
        )
        require(
            digest(canonical({k: v for k, v in record.items() if k != "evidence"}))
            == ref["value_sha256"],
            "Region representation hash differs",
        )
        if "image_region" in args:
            require(
                args["image_region"]["rect"] == ref["selector"]["rect"],
                "Region selector differs",
            )
    blocks = [b for b in call["result"]["content"] if b["type"] == "image"]
    require(len(blocks) == 1, "Missing actual MCP image delivery")
    png = base64.b64decode(blocks[0]["data"], validate=True)
    require(digest(png) == result["image_sha256"], "MCP PNG hash differs")
    require(
        (result["asset_id"], result["inspected_revision"])
        == (ref["asset_id"], ref["revision"]),
        "MCP preview identity differs",
    )
    raw = source_bytes(workspace, ref["asset_id"], ref["revision"])
    bounds = validate_png(
        raw,
        png,
        parent["locator"]["frame_index"],
        args.get("render_size", 1024),
        ref["selector"]["rect"] if is_region else None,
    )
    require(bounds == result["source_pixel_bounds"], "Preview crop bounds differ")
    if is_region:
        require(
            bounds == result["region"]["source_pixel_bounds"],
            "Region record bounds differ",
        )
    return ref, png


def validate_stages(data, upright, crop):
    require(len(data) == 3, "Expected original, insertion and deletion revisions")
    canvas = Image.new("RGBA", (4, 3), (7, 9, 11, 128))
    expected = [[upright, crop], [crop, upright, canvas], [crop, upright]]
    for raw, truth in zip(data, expected, strict=True):
        actual = frames(raw)
        require(len(actual) == len(truth), "Frame lifecycle count differs")
        for a, b in zip(actual, truth, strict=True):
            same_pixels(a, b)
