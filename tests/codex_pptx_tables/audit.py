"""Independently audit real scanned-page pixels and editable table package output."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from tests.codex_native_pdf.artifacts import load_asset, read_json, validate_source
from tests.codex_native_pdf.trace import (
    canonical,
    complete_records,
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pptx_pictures.audit import validate_wiki
from tests.codex_pptx_tables.tables import validate_revisions, validate_table


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
            "read_pdf_page",
            "render_pdf_page",
            "create_pptx",
            "add_pptx_tables",
            "read_pptx_shape",
            "update_pptx",
            "delete_pptx_shapes",
            "verify",
            "publish",
            "export_wiki",
            "history",
        }
        <= operations,
        "Incomplete native table workflow",
    )
    require("writeback" not in operations, "Unexpected source writeback")
    return calls


def validate_refs(calls, records, source_id, deck_id):
    available = set()
    historical = False
    source_proof = False
    for call in calls:
        args = call["arguments"]["native_request"]
        result = payload(call)
        if args["op"] in {"read_pptx_shape", "read_pdf_page"}:
            part = result["shape" if args["op"] == "read_pptx_shape" else "page"]
            key = canonical(part["evidence"])
            if part["next_text_offset"] is None and key in records:
                available.add(key)
        for ref in args.get("pptx_shape_refs", []):
            require(
                canonical(ref) in available, "Deletion lacks prior complete readback"
            )
        for edit in args.get("pptx_edits", []):
            candidates = [
                records[key]
                for key in available
                if records[key]["evidence"]["asset_id"] == args["asset_id"]
                and records[key]["evidence"]["revision"] == args["expected_revision"]
                and all(
                    records[key]["locator"].get(k) == v
                    for k, v in edit["locator"].items()
                    if k in records[key]["locator"]
                )
            ]
            require(
                len(candidates) == 1, "Cell edit lacks prior complete shape readback"
            )
            validate_edit_run(candidates[0], edit)
        if args["op"] == "verify":
            ref = args["reference"]
            require(canonical(ref) in available, "Proof lacks full readback")
            historical |= (
                ref["asset_id"] == deck_id
                and result.get("valid") is True
                and result.get("is_current_managed_revision") is False
            )
            source_proof |= ref["asset_id"] == source_id and result.get("valid") is True
    require(
        historical and source_proof, "Historical table or source page proof missing"
    )


def validate_edit_run(record, edit):
    loc = edit["locator"]
    run = record["table"]["rows"][loc["row"]]["cells"][loc["column"]]["paragraphs"][
        loc["paragraph"]
    ]["items"][loc["run"]]
    require(
        run["text_sha256"] == edit["expected_text_sha256"],
        "Edit run hash differs from readback",
    )


def validate_images(calls, workspace, source):
    count = 0
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != "render_pdf_page":
            continue
        result = payload(call)
        require(
            (
                result["asset_id"],
                result["inspected_revision"],
                result["locator"]["page_index"],
            )
            == (source["asset_id"], source["revision"], 0),
            "Wrong scanned preview",
        )
        images = [b for b in call["result"]["content"] if b["type"] == "image"]
        require(len(images) == 1, "Actual PNG missing")
        png = base64.b64decode(images[0]["data"], validate=True)
        require(digest(png) == result["image_sha256"], "PNG hash mismatch")
        validate_image_pixels(workspace, result, args, png)
        count += 1
    require(count > 0, "Scanned image never delivered")
    return count


def audit(output):
    expected = read_json(output / "expected.json")
    final = read_json(output / "last-message.txt")
    workspace = output / "workspace"
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    calls = calls_from(events)
    source = load_asset(workspace, final["source_asset_id"])
    deck = load_asset(workspace, final["table_asset_id"])
    validate_source(workspace, expected, source)
    records = complete_records(calls)
    records.update(
        complete_records(calls, operation="read_pptx_shape", record_key="shape")
    )
    validate_refs(calls, records, source["asset_id"], deck["asset_id"])
    images = validate_images(calls, workspace, source)
    root = workspace / "data" / "native-assets" / deck["asset_id"] / "revisions"
    first_exact = validate_revisions(
        root,
        deck,
        grid=expected.get("grid", False) or expected.get("merges", False),
        slides=expected.get("slides", False),
    )
    validate_table(workspace / "verified.pptx")
    require(
        digest((workspace / "verified.pptx").read_bytes()) == deck["revision"],
        "Published revision differs",
    )
    validate_wiki(workspace, deck)
    grids = None
    if expected.get("grid"):
        from tests.codex_pptx_tables.grids import validate_grids

        grids = validate_grids(
            workspace, deck, calls, following_merges=expected.get("merges", False)
        )
    merges = None
    if expected.get("merges"):
        from tests.codex_pptx_tables.merges import validate_merges

        merges = validate_merges(
            workspace, deck, calls, preceding_grid=expected.get("grid", False)
        )
    slides = None
    if expected.get("slides"):
        from tests.codex_pptx_tables.slides import validate_slides

        slides = validate_slides(workspace, deck, calls)
    derivations = None
    renders = None
    if expected.get("render"):
        from tests.codex_pptx_tables.renders import validate_renders

        renders = validate_renders(workspace, deck, calls, final)
    if expected.get("derivations"):
        from tests.codex_pptx_tables.derivations import validate_derivations

        derivations = validate_derivations(
            workspace,
            source,
            deck,
            calls,
            records,
            expected.get("source_attachment_suffix"),
        )
    return {
        "passed": True,
        "first_transcription_exact": first_exact,
        "passed_with_recoveries": not first_exact or bool(tool_errors(events)),
        "recovery_scope": "Observed MCP tool errors and corrected transcription only; agent-reported limitations are retained separately.",
        "agent_reported_limitations": final.get("limitations", []),
        "mcp_calls": len(calls),
        "tool_call_attempts": len(calls) + len(tool_errors(events)),
        "complete_records": len(records),
        "images": images,
        "tool_errors": tool_errors(events),
        "derivations": derivations,
        "grids": grids,
        "merges": merges,
        "slides": slides,
        "renders": renders,
        "scope": "Synthetic scanned first page, editable table strings/grid/merge and native package evidence; optional static LibreOffice previews are reported separately. No general OCR or PowerPoint fidelity claim.",
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
