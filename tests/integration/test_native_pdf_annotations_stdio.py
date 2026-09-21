"""SDK2 native annotation CRUD, complete contracts, actual PNGs and historical Wiki."""

import base64
import hashlib
import io
import json
import os
import sys
from functools import partial
from pathlib import Path

import pymupdf
import pytest
from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.integration.test_native_derivation_stdio import ledger_read
from tests.integration.test_native_docx_stdio_e2e import _native
from tests.integration.test_native_pdf_regions_stdio import unwrap
from tests.native_pdf_helpers import build_pdf


async def complete(native, fields, key=None):
    fields = {k: v for k, v in fields.items() if k not in {"text_offset", "text_limit"}}
    chunks, offset, digest = [], 0, None
    while True:
        value = await native(**fields, text_offset=offset, text_limit=3500)
        assert value["success"] and "response_truncated" not in value, value
        page = value[key] if key else value
        current = page.get("text_sha256", page.get("schema_sha256"))
        assert current is not None and (digest is None or digest == current)
        assert page["excerpt_char_range"][0] == offset
        digest = current
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


async def read_annotations(native, asset):
    fields = {"asset_id": asset["asset_id"], "revision": asset["revision"]}
    catalog = await complete(
        native, {"op": "read_pdf_annotations", **fields}, "annotation"
    )
    records = []
    for annotation in catalog["catalog"]["annotations"]:
        record = await complete(
            native,
            {
                "op": "read_pdf_annotation",
                **fields,
                "pdf_annotation_locator": annotation["locator"],
            },
            "annotation",
        )
        assert (await native(op="verify", reference=record["evidence"]))["valid"]
        records.append(record)
    return catalog, records


async def actual_pages(client, native, asset, data):
    listing = await native(
        op="read_pdf", asset_id=asset["asset_id"], revision=asset["revision"]
    )
    assert listing["next_offset"] is None
    records = []
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        for entry in listing["pages"]:
            records.append(
                await complete(
                    native,
                    {
                        "op": "read_pdf_page",
                        "asset_id": asset["asset_id"],
                        "revision": asset["revision"],
                        "pdf_locator": entry["locator"],
                    },
                    "page",
                )
            )
            response = await client.call_tool(
                "document",
                {
                    "op": "native",
                    "native_request": {
                        "op": "render_pdf_page",
                        "asset_id": asset["asset_id"],
                        "revision": asset["revision"],
                        "pdf_locator": entry["locator"],
                        "render_size": 900,
                    },
                },
            )
            result = unwrap(response)
            assert result["success"]
            images = [block for block in response.content if block.type == "image"]
            assert len(images) == 1
            png = base64.b64decode(images[0].data, validate=True)
            assert hashlib.sha256(png).hexdigest() == result["image_sha256"]
            page = pdf[entry["locator"]["page_index"]]
            scale = 900 / max(page.rect.width, page.rect.height)
            expected = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=True
            )
            actual = Image.open(io.BytesIO(png))
            assert actual.size == (expected.width, expected.height)
            assert actual.tobytes() == expected.samples
    return records


@pytest.mark.parametrize("surface", ["balanced", "compact"])
# Complete paged records across four revisions make hundreds of isolated-worker
# calls. Both Python 3.10 CI cases exceeded 180s; retain every integrity assertion.
@pytest.mark.timeout(300)
async def test_annotations_over_sdk2_preserve_native_source_and_evidence(
    tmp_path, surface
):
    source = tmp_path / "批註.pdf"
    original = build_pdf(links=True, forms=True, labels=True)
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
        contract = await native(op="contract", for_op="update_pdf_annotations")
        assert contract["pdf_annotations_enabled"]
        details = await complete(native, contract["contract_request"])
        assert "replace_appearance" in details["pdf_annotations_policy"]
        schema = await complete(native, contract["schema_request"])
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        asset = (await native(op="register", source_path=str(source)))["asset"]
        initial = asset.copy()
        before, records = await read_annotations(native, asset)
        assert before["catalog"]["annotation_count"] == 8
        pages = await actual_pages(client, native, asset, original)
        old_ref = next(r["evidence"] for r in records if r["subtype"] == "/Text")
        selected = await native(
            op="read_selection", reference=old_ref, selection={"pointer": "/contents"}
        )
        selection = selected["evidence"]
        first = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        old_root = Path(first["output_dir"])
        old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}

        async def change(edits):
            nonlocal asset
            fields = {
                "op": "update_pdf_annotations",
                "asset_id": asset["asset_id"],
                "expected_revision": asset["revision"],
                "pdf_annotations_update": {"edits": edits},
            }
            validator.validate(fields)
            response = await native(**fields)
            assert response["success"], response
            asset = response["asset"]
            receipt = await complete(native, response["review_request"], "annotation")
            assert len(receipt["operation_result"]["changes"]) == len(edits)
            return fields, receipt

        stale_fields, receipt = await change(
            [
                {
                    "op": "update",
                    "reference": old_ref,
                    "metadata": {"contents": "核對 007 µg", "author": "SDK2"},
                },
                {
                    "op": "create",
                    "page_reference": pages[1]["evidence"],
                    "appearance": {
                        "kind": "FreeText",
                        "rect": [0.1, 0.5, 0.8, 0.8],
                        "text": "Added 007 µg",
                        "fill_color": [1, 1, 0],
                    },
                },
            ]
        )
        assert (
            receipt["operation_result"]["changes"][0]["after"]["contents"]
            == "核對 007 µg"
        )
        assert not (await native(**stale_fields))["success"]
        middle, updated_records = await read_annotations(native, asset)
        assert middle["catalog"]["annotation_count"] == 9
        created = next(r for r in updated_records if r["contents"] == "Added 007 µg")
        created_ref = created["evidence"]
        revisions = tmp_path / "data/native-assets" / asset["asset_id"] / "revisions"
        await actual_pages(
            client, native, asset, (revisions / asset["revision"]).read_bytes()
        )
        _, ledger_sha = await ledger_read(client, asset["asset_id"])
        derived = await native(
            op="record_derivation",
            asset_id=asset["asset_id"],
            expected_derivations_sha256=ledger_sha,
            derivation={
                "target": created_ref,
                "sources": [selection],
                "agent": "SDK2 fixture",
                "activity": "Copy authored annotation into a visible FreeText comment",
                "review": {"notes": "Transport fixture; semantic support not assessed"},
            },
        )
        assert derived["success"]
        ledger, _ = await ledger_read(client, asset["asset_id"])
        assert ledger["events"][0]["derivation"]["target"] == created_ref
        middle_wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        middle_root = Path(middle_wiki["output_dir"])
        manifest = json.loads((middle_root / "manifest.json").read_text())
        assert manifest["derivations"]["active_ids_for_revision"] == [
            derived["derivation_id"]
        ]
        middle_files = {p.name: p.read_bytes() for p in middle_root.iterdir()}
        await change(
            [
                {
                    "op": "update",
                    "reference": created_ref,
                    "replace_appearance": {
                        "kind": "FreeText",
                        "rect": [0.2, 0.5, 0.9, 0.75],
                        "text": "Revised -0.50 mg/L",
                        "fill_color": [0, 1, 1],
                    },
                }
            ]
        )
        _, revised_records = await read_annotations(native, asset)
        changed = next(
            r for r in revised_records if r["contents"] == "Revised -0.50 mg/L"
        )
        await actual_pages(
            client, native, asset, (revisions / asset["revision"]).read_bytes()
        )
        await change(
            [
                {
                    "op": "delete",
                    "reference": changed["evidence"],
                    "scope": "annotation_and_owned_popup",
                }
            ]
        )
        final, _ = await read_annotations(native, asset)
        assert final["catalog"]["annotation_count"] == 8
        await actual_pages(
            client, native, asset, (revisions / asset["revision"]).read_bytes()
        )
        for reference in [old_ref, selection, created_ref, changed["evidence"]]:
            proof = await native(op="verify", reference=reference)
            assert proof["valid"] and not proof["is_current_managed_revision"]
        historical, historical_records = await read_annotations(native, initial)
        assert historical == before and historical_records == records
        proof = await native(
            op="verify_derivation",
            asset_id=asset["asset_id"],
            derivation_id=derived["derivation_id"],
        )
        assert proof["active"] and proof["references_valid"]
        final_wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        final_manifest = json.loads(
            (Path(final_wiki["output_dir"]) / "manifest.json").read_text()
        )
        assert final_manifest["derivations"]["active_ids_for_revision"] == []
        assert old_files == {p.name: p.read_bytes() for p in old_root.iterdir()}
        assert middle_files == {p.name: p.read_bytes() for p in middle_root.iterdir()}
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
