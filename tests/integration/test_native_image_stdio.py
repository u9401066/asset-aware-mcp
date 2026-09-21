"""Actual SDK2 images, frame CRUD, complete receipts and portable raster evidence."""

import base64
import hashlib
import io
import json
import os
import sys
from functools import partial
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.integration.test_native_derivation_stdio import ledger_read
from tests.integration.test_native_docx_stdio_e2e import _native
from tests.integration.test_native_pdf_annotations_stdio import complete
from tests.integration.test_native_pdf_regions_stdio import unwrap
from tests.native_image_helpers import encoded, grid


async def read_all(native, asset):
    common = {"asset_id": asset["asset_id"], "revision": asset["revision"]}
    catalog = await complete(native, {"op": "read_image", **common}, "image")
    frames = []
    for reference in catalog["frame_references"]:
        frame = await complete(
            native,
            {"op": "read_image_frame", **common, "image_locator": reference["locator"]},
            "image",
        )
        assert frame["evidence"] == reference
        assert (await native(op="verify", reference=reference))["valid"]
        frames.append(frame)
    return catalog, frames


async def preview(client, reference, expected, region=None):
    fields = {
        "op": "read_image_region" if region else "render_image_frame",
        "reference": reference,
        "render_size": 64,
    }
    if region:
        fields["image_region"] = region
    response = await client.call_tool(
        "document", {"op": "native", "native_request": fields}
    )
    assert not response.is_error
    metadata = unwrap(response)
    assert metadata["success"] and "response_truncated" not in metadata
    images = [item for item in response.content if item.type == "image"]
    assert len(images) == 1
    png = base64.b64decode(images[0].data, validate=True)
    assert hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
    with Image.open(io.BytesIO(png)) as actual:
        assert (
            actual.size == expected.size
            and actual.tobytes() == expected.convert("RGBA").tobytes()
        )
    return metadata


@pytest.mark.parametrize("surface", ["balanced", "compact"])
@pytest.mark.timeout(180)
async def test_native_image_crud_and_provenance_over_sdk2(tmp_path, surface):
    source = tmp_path / "來源.png"
    original = encoded("PNG", 6)
    source.write_bytes(original)
    mtime = source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "ASSET_AWARE_MCP_TOOL_SURFACE": surface,
        },
    )
    async with Client(stdio_client(params)) as client:
        native = partial(_native, client)
        contract = await native(op="contract", for_op="update_image")
        assert contract["images_enabled"] and "response_truncated" not in contract
        details = await complete(native, contract["contract_request"])
        assert "candidate" in details["image_policy"]
        schema = await complete(native, contract["schema_request"])
        Draft202012Validator.check_schema(schema)
        asset = (await native(op="register", source_path=str(source)))["asset"]
        _, source_frames = await read_all(native, asset)
        reference = source_frames[0]["evidence"]
        oriented = grid().transpose(Image.Transpose.ROTATE_270)
        await preview(client, reference, oriented)
        rect = {"rect": [0.1, 0.1, 0.6, 0.7]}
        region = await preview(client, reference, oriented.crop((0, 1, 5, 9)), rect)
        crop = (
            await native(
                op="extract_image",
                image_extract={
                    "name": "crop.png",
                    "reference": reference,
                    "region": rect,
                    "pixel_policy": "preserve_decoded",
                    "metadata_policy": "pixels_only",
                },
            )
        )["asset"]
        _, crop_frames = await read_all(native, crop)
        blank = (
            await native(
                op="create_image",
                image_create={
                    "name": "canvas.png",
                    "width": 4,
                    "height": 3,
                    "rgba": [7, 9, 11, 128],
                },
            )
        )["asset"]
        _, blank_frames = await read_all(native, blank)

        async def compose(name, refs):
            result = await native(
                op="compose_images",
                image_compose={
                    "name": name,
                    "metadata_policy": "pixels_only",
                    "frames": [
                        {"reference": ref, "pixel_policy": "preserve_decoded"}
                        for ref in refs
                    ],
                },
            )
            assert result["success"]
            return result["asset"]

        target = await compose("pages.tif", [reference, crop_frames[0]["evidence"]])
        candidate = await compose(
            "candidate.tif", [blank_frames[0]["evidence"], reference]
        )
        old_catalog, old = await read_all(native, target)
        _, new = await read_all(native, candidate)
        wiki_before = await native(
            op="export_wiki",
            asset_id=target["asset_id"],
            revision=target["revision"],
            output_dir=str(tmp_path / "wiki"),
        )
        old_root = Path(wiki_before["output_dir"])
        old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
        fields = {
            "op": "update_image",
            "asset_id": target["asset_id"],
            "expected_revision": target["revision"],
            "image_update": {
                "candidate": candidate["file_reference"],
                "expected_catalog_sha256": old_catalog["catalog"]["catalog_sha256"],
                "container_policy": "accept_exact_candidate_bytes",
                "frames": [
                    {"op": "delete", "before": old[1]["evidence"]},
                    {"op": "insert", "after": new[0]["evidence"]},
                    {
                        "op": "map",
                        "before": old[0]["evidence"],
                        "after": new[1]["evidence"],
                        "metadata": "replace",
                    },
                ],
            },
        }
        Draft202012Validator(schema).validate(fields)
        changed = await native(**fields)
        assert changed["success"] and changed["operation_result"]["committed"]
        current = changed["asset"]
        receipt, current_frames = await read_all(native, current)
        assert (
            receipt["operation_result"]["changes"][0]["candidate"]
            == candidate["file_reference"]
        )
        await preview(
            client,
            current_frames[0]["evidence"],
            Image.new("RGBA", (4, 3), (7, 9, 11, 128)),
        )
        await preview(client, current_frames[1]["evidence"], oriented)
        for before in old:
            proof = await native(op="verify", reference=before["evidence"])
            assert proof["valid"] and not proof["is_current_managed_revision"]
        stale = await native(**fields)
        assert not stale["success"] and "stale" in stale["error"]
        history = await native(op="history", asset_id=current["asset_id"])
        assert len(history["history"]) == 2
        ledger, ledger_sha = await ledger_read(client, current["asset_id"])
        assert ledger["events"] == []
        assertion = await native(
            op="record_derivation",
            asset_id=current["asset_id"],
            expected_derivations_sha256=ledger_sha,
            derivation={
                "target": current_frames[1]["evidence"],
                "sources": [region["reference"]],
                "agent": "SDK regression",
                "activity": "Synthetic region correspondence; no transcription assertion",
                "review": {"notes": "Semantic support not reviewed"},
            },
        )
        assert assertion["success"]
        output = await native(
            op="export_wiki",
            asset_id=current["asset_id"],
            revision=current["revision"],
            output_dir=str(tmp_path / "wiki"),
            citation_contract={
                "name": "image-location",
                "inline_template": "{source_id}|{locator}",
                "reference_template": "{title}|{locator}",
            },
        )
        root = Path(output["output_dir"])
        manifest = json.loads((root / "manifest.json").read_text())
        assert root != old_root and manifest["frame_count"] == 2
        for name, meta in manifest["files"].items():
            data = (root / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == meta["sha256"]
        assert len(manifest["derivations"]["image_records"]) == 2
        published = tmp_path / "reviewed.tif"
        assert (
            await native(
                op="publish",
                asset_id=current["asset_id"],
                expected_revision=current["revision"],
                output_path=str(published),
            )
        )["success"]
        assert (
            hashlib.sha256(published.read_bytes()).hexdigest() == candidate["revision"]
        )
        with Image.open(published) as image:
            assert image.n_frames == 2 and image.getpixel((0, 0)) == (7, 9, 11, 128)
            image.seek(1)
            assert image.tobytes() == oriented.tobytes()
        assert old_files == {p.name: p.read_bytes() for p in old_root.iterdir()}
        assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
