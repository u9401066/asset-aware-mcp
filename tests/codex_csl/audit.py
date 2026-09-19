"""Independent actual-call, citation, page-pixel and portable source audit."""

import argparse
import base64
import json
from pathlib import Path

import pymupdf

from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import (
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.native_pdf_helpers import page_reference


def check_result(result, original, asset_id):
    doc = result["document"]
    expected_items = [
        {
            "id": item_id,
            "type": "book",
            "title": title,
            "author": [{"family": "Doe", "given": "Jane"}],
            "issued": {"date-parts": [[2020]]},
            "publisher": "Example Press",
        }
        for item_id, title in (("a", "Alpha"), ("b", "Beta"))
    ]
    require(
        sorted(doc["items"], key=lambda x: x["id"]) == expected_items,
        "Bibliographic transcription differs",
    )
    require(
        doc["locale"] == "en-US" and not doc["uncited_ids"],
        "Unexpected citation configuration",
    )
    require(
        [c["id"] for c in doc["clusters"]] == ["c1", "c2", "c3"],
        "Cluster IDs/order differ",
    )
    for cluster, item_id in zip(doc["clusters"], ("b", "a", "b"), strict=True):
        require(
            cluster["note_index"] == 0 and len(cluster["cites"]) == 1,
            "Invalid cluster context",
        )
        cite = cluster["cites"][0]
        require(
            cite["id"] == item_id
            and cite["source_keys"] == [item_id + "_source"]
            and cite["locator"] is None
            and not cite["prefix"]
            and not cite["suffix"]
            and not cite["suppress_author"],
            "Changed citation identity/locator",
        )
    for index, key in enumerate(("a_source", "b_source")):
        reference = page_reference(original, index, asset_id).model_dump(mode="json")
        require(
            doc["sources"][key] == reference == result["sources"][key]["reference"],
            "Citation source differs from exact original page",
        )
        require(
            result["sources"][key]["verification"]["valid"]
            and result["sources"][key]["semantic_support"] == "not_checked",
            "Invalid verification scope",
        )
    require(
        not result["missing_metadata"] and not result["warnings"],
        "Citation metadata/engine warnings",
    )
    if doc["style"] == "apa":
        require(
            [c["text"] for c in result["citations"]]
            == ["(Doe, 2020b)", "(Doe, 2020a)", "(Doe, 2020b)"],
            "APA disambiguation failed",
        )
        require(
            [b["text"] for b in result["bibliography"]]
            == [
                "Doe, J. (2020a). Alpha. Example Press.\n",
                "Doe, J. (2020b). Beta. Example Press.\n",
            ],
            "APA bibliography differs",
        )
    else:
        require(
            doc["style"] == "vancouver"
            and [c["text"] for c in result["citations"]] == ["(1)", "(2)", "(1)"],
            "Vancouver sequence differs",
        )
        require(
            [b["item_ids"] for b in result["bibliography"]] == [["b"], ["a"]],
            "Vancouver bibliography order differs",
        )


def readback(result, op, tool, args, buffers):
    if op == "read_pdf_page":
        result = result["page"]
    if "text_excerpt" in result:
        sha = result.get("text_sha256", result.get("schema_sha256"))
        key = (tool, op, sha)
        start, end = result["excerpt_char_range"]
        require(start == args.get("text_offset", 0), "Wrong requested offset")
        if start == 0:
            buffers[key] = ""
        require(key in buffers and len(buffers[key]) == start, "Noncontiguous readback")
        buffers[key] += result["text_excerpt"]
        require(len(buffers[key]) == end, "Excerpt length differs")
        if result["next_text_offset"] is None:
            text = buffers.pop(key)
            require(
                len(text) == result["text_length"] and digest(text.encode()) == sha,
                "Incomplete or changed result hash",
            )
            record = json.loads(text)
            return op, sha, record
    return None


def audit(output):
    expected = read_json(output / "expected.json")
    final = read_json(output / "last-message.txt")
    workspace = output / "workspace"
    original = (workspace / "source.pdf").read_bytes()
    require(
        digest(original) == expected["source_sha256"]
        and (workspace / "source.pdf").stat().st_mtime_ns
        == expected["source_mtime_ns"],
        "Human source changed",
    )
    asset = load_asset(workspace, final["source_asset_id"])
    require(
        len(asset["history"]) == 2
        and asset["history"][0]["sha256"] == expected["source_sha256"],
        "Unexpected PDF mutation history",
    )
    current = (
        workspace
        / "data/native-assets"
        / asset["asset_id"]
        / "revisions"
        / asset["revision"]
    )
    with pymupdf.open(current) as pdf:
        require(
            len(pdf) == 2 and [p.rotation for p in pdf] == [90, 0],
            "Managed PDF rotations differ",
        )
    events = [
        json.loads(line)
        for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete Codex turn")
    calls, images, buffers, completed = [], set(), {}, []
    old_verified, ops = set(), set()
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
            and item["tool"] in {"document", "evidence"},
            "Wrong tool/server",
        )
        if call_failed(item):
            continue
        calls.append(item)
        args = item["arguments"]
        if item["tool"] == "document":
            require(args["op"] == "native", "Non-native document action")
            args = args["native_request"]
            require(
                args["op"] not in {"writeback", "publish"}, "Human source publication"
            )
        op = args["op"]
        ops.add(op)
        result = payload(item)
        if op == "render_pdf_page":
            blocks = [b for b in item["result"]["content"] if b["type"] == "image"]
            require(len(blocks) == 1, "No actual PDF image")
            raw = base64.b64decode(blocks[0]["data"], validate=True)
            require(digest(raw) == result["image_sha256"], "Image hash differs")
            validate_image_pixels(workspace, result, args, raw)
            images.add((result["inspected_revision"], result["locator"]["page_index"]))
        if (
            op == "verify"
            and result.get("valid")
            and not result.get("is_current_managed_revision", True)
        ):
            old_verified.add(args["reference"]["locator"]["page_index"])
        complete = readback(result, op, item["tool"], args, buffers)
        if complete is not None:
            completed.append(complete)
            if op == "render_citations":
                check_result(complete[2], original, asset["asset_id"])
    require(
        {
            "csl_contract",
            "read_pdf",
            "read_pdf_page",
            "render_pdf_page",
            "render_citations",
            "update_pdf",
            "verify",
            "history",
        }
        <= ops,
        "Missing workflow operation",
    )
    require(
        {
            (revision, page)
            for revision in (expected["source_sha256"], asset["revision"])
            for page in range(2)
        }
        <= images
        and old_verified == {0, 1},
        "Missing original/current review or historical verification",
    )
    require(
        any(op == "csl_contract" for op, _, _ in completed), "Incomplete CSL contract"
    )
    read_pages = {
        (record["evidence"]["revision"], record["evidence"]["locator"]["page_index"])
        for op, _, record in completed
        if op == "read_pdf_page"
    }
    require(
        {
            (revision, page)
            for revision in (expected["source_sha256"], asset["revision"])
            for page in range(2)
        }
        <= read_pages,
        "Missing complete original/current page records",
    )
    snapshots = list((workspace / "citation-wiki").glob("*/manifest.json"))
    require(len(snapshots) == 2, "Missing or extra citation snapshot")
    for path in snapshots:
        root = path.parent
        manifest = read_json(path)
        require(
            {p.name for p in root.iterdir()} == {"manifest.json", *manifest["files"]},
            "Wiki inventory mismatch",
        )
        for name, entry in manifest["files"].items():
            data = (root / name).read_bytes()
            require(
                digest(data) == entry["sha256"] and len(data) == entry["size_bytes"],
                "Wiki file differs",
            )
        result = read_json(root / "citations.json")
        check_result(result, original, asset["asset_id"])
        for source in result["sources"].values():
            require(
                (root / source["attachment"]["name"]).read_bytes() == original,
                "Portable source bytes differ",
            )
        sha = digest((root / "citations.json").read_bytes())
        required_reads = 3 if result["document"]["style"] == "apa" else 2
        require(
            sum(op == "render_citations" and value == sha for op, value, _ in completed)
            >= required_reads,
            "Missing complete preview/export/historical readbacks",
        )
        require(
            result["resources"]["manifest_sha256"] == expected["csl_manifest_sha256"]
            and result["resources"]["worker_sha256"] == expected["csl_worker_sha256"],
            "Wrong rendered resources",
        )
    return {
        "passed": True,
        "successful_mcp_calls": len(calls),
        "actual_pdf_images": len(images),
        "citation_snapshots": len(snapshots),
        "tool_errors": tool_errors(events),
        "limitations": [
            "Fictional bibliographic fixture, not a real scholarly publication.",
            "Native source integrity does not verify bibliographic truth or semantic support.",
        ],
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(write_audit(args.output), ensure_ascii=False))
