"""Audit actual native MCP events, image bytes and complete page readbacks."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re

import pymupdf
from PIL import Image

from tests.codex_pdf.trace import call_failed, require, result_text


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def payload(call):
    value = json.loads(result_text(call))
    if set(value) == {"result"}:
        value = value["result"]
    require(isinstance(value, dict), "MCP result is not an object")
    return value


def completed_calls(events):
    require(
        any(e["type"] == "turn.completed" for e in events), "Codex did not complete"
    )
    calls = []
    for event in events:
        if event["type"] != "item.completed":
            continue
        item = event.get("item", {})
        kind = item.get("type")
        require(
            kind in {"agent_message", "reasoning", "plan", "mcp_tool_call"},
            "Non-MCP action",
        )
        if kind != "mcp_tool_call":
            continue
        require(item.get("server") == "asset_aware_under_test", "Wrong MCP server")
        args = item["arguments"]
        require(
            item.get("tool") == "document" and args.get("op") == "native",
            "Non-native call",
        )
        if not call_failed(item):
            calls.append(item)
    required = {
        "contract",
        "register",
        "read_pdf",
        "read_pdf_page",
        "render_pdf_page",
        "create_pdf",
        "add_pdf_pages",
        "update_pdf",
        "delete_pdf_pages",
        "reorder_pdf_pages",
        "verify",
        "publish",
        "export_wiki",
        "history",
    }
    observed = {c["arguments"]["native_request"]["op"] for c in calls}
    require(required <= observed, f"Missing native operations: {required - observed}")
    require("writeback" not in observed, "Unexpected source writeback")
    return calls


def validate_images(calls, source, target, workspace=None):
    viewed = set()
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != "render_pdf_page":
            continue
        result = payload(call)
        images = [b for b in call["result"]["content"] if b["type"] == "image"]
        require(len(images) == 1, "Render did not deliver one actual image")
        raw = base64.b64decode(images[0]["data"], validate=True)
        require(digest(raw) == result["image_sha256"], "MCP image hash mismatch")
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        if workspace is not None:
            validate_image_pixels(workspace, result, args, raw)
        viewed.add(
            (
                result["asset_id"],
                result["inspected_revision"],
                result["locator"]["page_index"],
            )
        )
    expected = {
        (a["asset_id"], a["revision"], i) for a in (source, target) for i in range(3)
    }
    require(expected <= viewed, "Missing original or final page image delivery")
    return len(viewed)


def validate_image_pixels(workspace, result, args, raw):
    asset_id, revision = result["asset_id"], result["inspected_revision"]
    require(re.fullmatch(r"file_[0-9a-f]{32}", asset_id), "Invalid image asset ID")
    require(re.fullmatch(r"[0-9a-f]{64}", revision), "Invalid image revision")
    path = workspace / "data" / "native-assets" / asset_id / "revisions" / revision
    require(digest(path.read_bytes()) == revision, "Image revision hash mismatch")
    with pymupdf.open(path) as pdf, Image.open(io.BytesIO(raw)) as image:
        page = pdf[result["locator"]["page_index"]]
        scale = args.get("render_size", 1024) / max(page.rect.width, page.rect.height)
        expected = page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=True
        )
        require(
            image.size == (expected.width, expected.height),
            "Delivered image dimensions mismatch",
        )
        require(
            image.convert("RGB").tobytes() == expected.samples,
            "Delivered image pixels differ from source revision",
        )


def validate_record(record):
    evidence = record["evidence"]
    require(record["locator"] == evidence["locator"], "Page evidence locator mismatch")
    value = {k: v for k, v in record.items() if k != "evidence"}
    require(
        digest(canonical(value)) == evidence["value_sha256"],
        "Page representation hash mismatch",
    )


def complete_records(calls, *, operation="read_pdf_page", record_key="page"):
    buffers, records = {}, {}
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != operation:
            continue
        result = payload(call)
        page = result[record_key]
        key = (result["asset_id"], result["inspected_revision"], page["text_sha256"])
        start, end = page["excerpt_char_range"]
        require(start == args.get("text_offset", 0), "Readback offset mismatch")
        require(end - start == len(page["text_excerpt"]), "Readback range mismatch")
        if start == 0:
            buffers[key] = ""
        require(
            key in buffers and len(buffers[key]) == start,
            "Missing/noncontiguous page chunks",
        )
        buffers[key] += page["text_excerpt"]
        if page["next_text_offset"] is not None:
            require(page["next_text_offset"] == end, "Bad page continuation")
            continue
        text = buffers.pop(key)
        require(
            len(text) == page["text_length"] and digest(text.encode()) == key[2],
            "Incomplete/corrupt page JSON",
        )
        record = json.loads(text)
        validate_record(record)
        evidence = record["evidence"]
        require(
            (evidence["asset_id"], evidence["revision"]) == key[:2],
            "Readback identity mismatch",
        )
        records[canonical(evidence)] = record
    require(not buffers, "Unfinished page readback")
    return records


def validate_reference_use(calls, records, source, target):
    available = set()
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] == "read_pdf_page":
            page = payload(call)["page"]
            key = canonical(page["evidence"])
            if page["next_text_offset"] is None and key in records:
                available.add(key)
        refs = args.get("pdf_page_refs", []) + args.get("pdf_order", [])
        refs += [e["reference"] for e in args.get("pdf_edits", [])]
        for name in ("pdf_create", "pdf_insert"):
            refs += [
                p["reference"]
                for p in args.get(name, {}).get("pages", [])
                if "reference" in p
            ]
        require(
            all(canonical(ref) in available for ref in refs),
            "Mutation used a reference without complete page readback",
        )
    original_pages = {
        r["locator"]["page_index"]
        for r in records.values()
        if r["evidence"]["asset_id"] == source["asset_id"]
        and r["evidence"]["revision"] == source["revision"]
    }
    require(original_pages == {0, 1, 2}, "Original page representations missing")
    historical = [
        payload(c)
        for c in calls
        if c["arguments"]["native_request"]["op"] == "verify"
        and c["arguments"]["native_request"]["reference"]["asset_id"]
        == target["asset_id"]
    ]
    require(
        any(
            p.get("valid") and p.get("is_current_managed_revision") is False
            for p in historical
        ),
        "No valid historical target reference",
    )
