"""Real SDK2 restart; optional isolated older Pillow exercises actual version drift."""

import base64
import hashlib
import os
import sys
from functools import partial
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import __version__ as pillow_version

from tests.integration.test_native_docx_stdio_e2e import _native
from tests.integration.test_native_pdf_annotations_stdio import complete
from tests.integration.test_native_pdf_regions_stdio import unwrap
from tests.native_image_helpers import encoded


async def image(client, reference, op="render_image_frame", **fields):
    result = await client.call_tool(
        "document",
        {
            "op": "native",
            "native_request": {
                "op": op,
                "reference": reference,
                "render_size": 768,
                **fields,
            },
        },
    )
    assert not result.is_error
    metadata = unwrap(result)
    assert metadata["success"] and "response_truncated" not in metadata
    images = [item for item in result.content if item.type == "image"]
    assert len(images) == 1
    png = base64.b64decode(images[0].data, validate=True)
    assert hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
    return metadata, png


@pytest.mark.parametrize("surface", ["balanced", "compact"])
@pytest.mark.timeout(180)
async def test_retained_images_across_real_sdk2_process_restart(tmp_path, surface):
    source = tmp_path / "source.png"
    source.write_bytes(encoded("PNG", 6))
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    env = {
        **os.environ,
        "DATA_DIR": str(tmp_path / "data"),
        "ENABLE_LIGHTRAG": "false",
        "ASSET_AWARE_DISABLE_DOTENV": "true",
        "ASSET_AWARE_MCP_TOOL_SURFACE": surface,
    }
    old_env = dict(env)
    old_pillow = os.environ.get("NATIVE_IMAGE_OLD_PILLOW")
    if old_pillow:
        assert (Path(old_pillow) / "PIL" / "__init__.py").is_file()
        old_env["PYTHONPATH"] = os.pathsep.join(
            filter(None, (old_pillow, env.get("PYTHONPATH")))
        )
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "src.server"], env=old_env
    )
    async with Client(stdio_client(params)) as client:
        native = partial(_native, client)
        contract = await native(op="contract", for_op="read_image_frame")
        assert contract["image_evidence_retention_enabled"]
        details = await complete(native, contract["contract_request"])
        assert "current decoder" in details["image_evidence_retention_policy"]
        asset = (await native(op="register", source_path=str(source)))["asset"]
        common = {"asset_id": asset["asset_id"], "revision": asset["revision"]}
        catalog = await complete(native, {"op": "read_image", **common}, "image")
        reference = catalog["frame_references"][0]
        request = {
            "op": "read_image_frame",
            **common,
            "image_locator": reference["locator"],
            "reference": reference,
        }
        frame = await complete(native, request, "image")
        initial_version = frame["decoder"]["version"]
        if old_pillow:
            assert initial_version != pillow_version, (
                "Configured old Pillow did not isolate the subprocess decoder"
            )
        full_preview, full_png = await image(client, reference)
        region_preview, region_png = await image(
            client,
            reference,
            "read_image_region",
            image_region={"rect": [0.1, 0.1, 0.6, 0.7]},
        )
        wiki_request = {
            "op": "export_wiki",
            **common,
            "output_dir": str(tmp_path / "wiki"),
            "image_catalog_sha256": catalog["catalog"]["catalog_sha256"],
        }
        wiki = await native(**wiki_request)
        assert wiki["success"]
        wiki_root = Path(wiki["output_dir"])
        before = {p.name: p.read_bytes() for p in wiki_root.iterdir()}
    # A new server and fresh bounded decoder workers reuse the persisted store.
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "src.server"], env=env
    )
    async with Client(stdio_client(params)) as client:
        native = partial(_native, client)
        assert await complete(native, request, "image") == frame
        assert (
            await complete(
                native,
                {
                    "op": "read_image",
                    **common,
                    "image_catalog_sha256": catalog["catalog"]["catalog_sha256"],
                },
                "image",
            )
            == catalog
        )
        for ref in (reference, region_preview["reference"]):
            proof = await native(op="verify", reference=ref)
            assert (
                proof["valid"]
                and proof["representation_origin"] == "retained_projection"
            )
            assert proof["current_decoder_reproduction"] == "not_checked"
        for op, prior, expected in (
            ("render_image_frame", full_preview, full_png),
            ("read_image_region", region_preview, region_png),
        ):
            metadata, png = await image(client, prior["reference"], op)
            assert png == expected and metadata["rendering"] == prior["rendering"]
            assert metadata["preview_origin"] == "retained_preview"
        again = await native(**wiki_request)
        assert again["success"] and again["output_dir"] == wiki["output_dir"]
        assert before == {p.name: p.read_bytes() for p in wiki_root.iterdir()}
        current = await complete(
            native,
            {key: value for key, value in request.items() if key != "reference"},
            "image",
        )
        assert current["decoder"]["version"] == pillow_version
        if old_pillow:
            assert current["evidence"] != reference
            unavailable = await native(
                op="render_image_frame", reference=reference, render_size=64
            )
            assert (
                not unavailable["success"]
                and "Historical image preview" in unavailable["error"]
            )
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
