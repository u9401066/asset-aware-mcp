"""Independent evidence audits reject edited or incomplete portable snapshots."""

import base64
import json

import pytest
from mcp.types import CallToolResult, ImageContent, TextContent

from tests.codex_etl_csl.audit import inventory, native_arguments, page_image
from tests.codex_native_pdf.trace import digest
from tests.integration.test_etl_citations_stdio import preview


@pytest.mark.parametrize("damage", [None, "missing", "extra", "changed", "size"])
def test_etl_audit_checks_exact_inventory_and_bytes(tmp_path, damage):
    original = b"source bytes 007"
    (tmp_path / "original.pdf").write_bytes(original)
    entry = {"sha256": digest(original), "size_bytes": len(original)}
    manifest = {"files": {"original.pdf": entry}}
    if damage == "size":
        entry["size_bytes"] += 1
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if damage == "missing":
        (tmp_path / "original.pdf").unlink()
    elif damage == "extra":
        (tmp_path / "unlisted.pdf").write_bytes(original)
    elif damage == "changed":
        (tmp_path / "original.pdf").write_bytes(b"source bytes 008")
    if damage is None:
        assert inventory(tmp_path) == manifest
    else:
        with pytest.raises(ValueError, match=r"inventory|bytes"):
            inventory(tmp_path)


def test_actual_mcp_image_uses_camelcase_wire_key_and_verifies_hash():
    data = b"MCP image bytes"
    item = {
        "result": {
            "content": [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "data": base64.b64encode(data).decode(),
                }
            ]
        }
    }
    assert page_image(item, digest(data)) == data
    with pytest.raises(ValueError, match="Image hash"):
        page_image(item, "0" * 64)


def test_complete_schema_discovery_is_read_only_but_writeback_is_rejected():
    request = {"op": "schema", "for_op": "create"}
    assert native_arguments({"native_request": request}) == request
    with pytest.raises(ValueError, match="Unexpected native mutation"):
        native_arguments({"native_request": {"op": "writeback"}})


@pytest.mark.parametrize("structured", [None, {"result": [{"type": "text"}]}])
def test_sdk_preview_reads_text_metadata_with_or_without_list_wrapping(structured):
    data = b"independently checked image bytes"
    metadata = {"success": True, "image_sha256": digest(data)}
    response = CallToolResult(
        content=[
            TextContent(type="text", text=json.dumps(metadata)),
            ImageContent(
                type="image",
                data=base64.b64encode(data).decode(),
                mime_type="image/png",
            ),
        ],
        structured_content=structured,
    )
    assert preview(response) == (metadata, data)
    response.content[1].data = base64.b64encode(b"altered image").decode()
    with pytest.raises(AssertionError):
        preview(response)
