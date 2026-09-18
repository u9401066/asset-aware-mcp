"""Inspect actual image bytes, native history and independent python-pptx readback."""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path

from PIL import Image

from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import complete_records, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pptx_pictures.history import validate_history, validate_references


def calls_from(events):
    require(any(e["type"] == "turn.completed" for e in events), "Codex turn incomplete")
    calls = []
    for event in events:
        if event["type"] != "item.completed":
            continue
        item = event["item"]
        require(
            item["type"] in {"agent_message", "reasoning", "plan", "mcp_tool_call"},
            "Non-MCP action",
        )
        if item["type"] != "mcp_tool_call":
            continue
        require(
            item["server"] == "asset_aware_under_test"
            and item["tool"] == "document"
            and item["arguments"]["op"] == "native",
            "Unexpected tool/server",
        )
        if not call_failed(item):
            calls.append(item)
    operations = {c["arguments"]["native_request"]["op"] for c in calls}
    require(
        {
            "contract",
            "register",
            "add_pptx_pictures",
            "read_pptx_picture",
            "read_pptx_shape",
            "extract_pptx_picture",
            "replace_pptx_pictures",
            "delete_pptx_shapes",
            "verify",
            "publish",
            "export_wiki",
            "history",
        }
        <= operations,
        "Incomplete picture workflow",
    )
    require("writeback" not in operations, "Unexpected source writeback")
    return calls


def validate_images(calls, workspace):
    observed = []
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != "read_pptx_picture":
            continue
        result = payload(call)
        images = [b for b in call["result"]["content"] if b["type"] == "image"]
        require(len(images) == 1, "Actual picture image missing")
        png = base64.b64decode(images[0]["data"], validate=True)
        require(digest(png) == result["image_sha256"], "Preview hash mismatch")
        source = next(
            (
                workspace / name
                for name in ("original.png", "replacement.png")
                if digest((workspace / name).read_bytes()) == result["image"]["sha256"]
            ),
            None,
        )
        require(source is not None, "Preview is not a fixture image")
        with Image.open(source) as expected, Image.open(io.BytesIO(png)) as actual:
            expected.thumbnail((args.get("render_size", 1024),) * 2)
            require(
                actual.size == expected.size
                and actual.convert("RGBA").tobytes()
                == expected.convert("RGBA").tobytes(),
                "Delivered image pixels mismatch",
            )
        observed.append(source.name)
    require(
        observed.count("original.png") >= 2 and "replacement.png" in observed,
        "Original/shared/replaced previews missing",
    )
    return observed


def validate_wiki(workspace, deck):
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 1, "Expected one picture evidence wiki")
    manifest = read_json(manifests[0])
    require(
        manifest["revision"] == deck["revision"]
        and manifest["projection"] == "pptx-shapes-v1",
        "Wiki projection/revision mismatch",
    )
    directory = manifests[0].parent
    for name, info in manifest["files"].items():
        require(Path(name).name == name, "Unsafe wiki path")
        data = (directory / name).read_bytes()
        require(
            digest(data) == info["sha256"] and len(data) == info["size_bytes"],
            "Wiki file mismatch",
        )
    require(
        (directory / manifest["source_attachment"]).read_bytes()
        == (workspace / "verified.pptx").read_bytes(),
        "Wiki source differs",
    )


def audit(output):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    for name, info in expected["sources"].items():
        path = workspace / name
        require(
            digest(path.read_bytes()) == info["sha256"]
            and path.stat().st_mtime_ns == info["mtime_ns"],
            "Original source changed",
        )
    for key in ("seen_original", "seen_replacement"):
        require(
            final[key] == expected[key],
            "Visual interpretation differs from exact fixture truth",
        )
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    calls = calls_from(events)
    records = complete_records(calls, operation="read_pptx_shape", record_key="shape")
    deck = load_asset(workspace, final["deck_asset_id"])
    child = load_asset(workspace, final["extracted_asset_id"])
    image_assets = []
    for key, name in [
        ("original_image_asset_id", "original.png"),
        ("replacement_image_asset_id", "replacement.png"),
    ]:
        asset = load_asset(workspace, final[key])
        image_assets.append(asset)
        require(
            asset["revision"] == expected["sources"][name]["sha256"],
            "Image source asset mismatch",
        )
    images = validate_images(calls, workspace)
    validate_history(workspace, deck, child, image_assets, records)
    validate_wiki(workspace, deck)
    validate_references(calls, records, deck)
    return {
        "passed": True,
        "mcp_calls": len(calls),
        "full_shape_records": len(records),
        "images": images,
        "tool_errors": tool_errors(events),
        "scope": "Synthetic raster assets and native XML/package checks; slide rendering and general OCR accuracy are not established",
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    report = write_audit(parser.parse_args().output.resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)
