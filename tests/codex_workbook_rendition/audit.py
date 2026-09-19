"""Independently validate exact workbook/PDF history, trace PNGs and source receipts."""

import argparse
import base64
import io
import json
from pathlib import Path

import openpyxl
import pymupdf

from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import (
    complete_records,
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_table_grid.reads import read_events
from tests.native_workbook_helpers import _parts


def calls_from(events):
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete Codex turn")
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
            "Wrong server/tool",
        )
        if not call_failed(item):
            calls.append(item)
    required = {
        "contract",
        "register",
        "read_workbook",
        "read_cell",
        "update",
        "create_workbook_rendition",
        "read_rendition",
        "read_pdf",
        "read_pdf_page",
        "render_pdf_page",
        "verify",
        "publish",
        "export_wiki",
        "history",
    }
    actual = {c["arguments"]["native_request"]["op"] for c in calls}
    require(
        required <= actual <= required | {"schema", "inspect"},
        "Incomplete/unexpected rendition workflow",
    )
    return calls


def receipts(calls):
    buffers, complete = {}, {}
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] != "read_rendition":
            continue
        result = payload(call)
        key = (args["asset_id"], args["revision"], result["text_sha256"])
        require(result["inspected_revision"] == key[1], "Wrong receipt revision")
        start, end = result["excerpt_char_range"]
        if start == 0:
            buffers[key] = ""
        require(
            start == args.get("text_offset", 0) == len(buffers.get(key, "")),
            "Noncontiguous receipt",
        )
        buffers[key] += result["text_excerpt"]
        require(end == len(buffers[key]), "Receipt offset mismatch")
        if result["next_text_offset"] is None:
            text = buffers.pop(key)
            require(digest(text.encode()) == key[2], "Receipt hash mismatch")
            complete[key[:2]] = json.loads(text)
    require(not buffers, "Unfinished receipt read")
    return complete


def audit(output):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    calls = calls_from(events)
    source = load_asset(workspace, final["source_asset_id"])
    original = (workspace / "source.xlsx").read_bytes()
    require(
        digest(original) == expected["source_sha256"]
        and (workspace / "source.xlsx").stat().st_mtime_ns
        == expected["source_mtime_ns"],
        "Human source changed",
    )
    require(
        len(source["history"]) == 2
        and source["history"][0]["sha256"] == digest(original),
        "Wrong workbook history",
    )
    updated = (workspace / "verified.xlsx").read_bytes()
    require(digest(updated) == source["revision"], "Wrong published workbook")
    old_parts, new_parts = _parts(original), _parts(updated)
    require(set(old_parts) == set(new_parts), "Workbook part inventory changed")
    require(
        {name for name in old_parts if old_parts[name] != new_parts[name]}
        <= {"xl/worksheets/sheet1.xml", "xl/workbook.xml"},
        "Unrelated workbook parts changed",
    )
    require(
        old_parts["xl/styles.xml"] == new_parts["xl/styles.xml"],
        "Source styles changed",
    )
    for data, formula in ((original, "=1+2"), (updated, "=2+3")):
        book = openpyxl.load_workbook(io.BytesIO(data))
        try:
            require(book["First"]["B2"].value == formula, "Wrong formula history")
            require(book["Hidden"].sheet_state == "hidden", "Hidden state changed")
        finally:
            book.close()
    references = [
        r for r in read_events(calls) if r[1].get("workbook_view") == "references"
    ]
    require(
        {r[3] for r in references} >= {digest(original), source["revision"]},
        "Incomplete workbook reference reads",
    )
    reports = receipts(calls)
    records = complete_records(calls)
    assets = [
        load_asset(workspace, identity) for identity in final["rendition_asset_ids"]
    ]
    require(
        len(assets) == 3 and len({a["asset_id"] for a in assets}) == 3,
        "Expected three independent PDF assets",
    )
    expected_pages = set()
    for index, (asset, name, mode, calculation, result) in enumerate(
        zip(
            assets,
            ("cached.pdf", "recalculated.pdf", "updated.pdf"),
            ("print", "whole_sheet", "whole_sheet"),
            ("prefer_cache", "recalculate", "recalculate"),
            ("999", "3", "5"),
            strict=True,
        )
    ):
        require(
            len(asset["history"]) == 1 and asset["source"] is None,
            "Rendition was mutated or source-bound",
        )
        receipt = reports[(asset["asset_id"], asset["revision"])]
        require(
            receipt == asset["history"][0]["result"], "Stored/read receipt mismatch"
        )
        record = receipt["changes"][0]
        require(
            record["requested"]["mode"] == mode
            and record["requested"]["calculation"] == calculation,
            "Wrong render policies",
        )
        ref = record["source_reference"]
        require(
            ref["asset_id"] == source["asset_id"]
            and ref["revision"]
            == (digest(original) if index < 2 else source["revision"]),
            "Rendition source revision mismatch",
        )
        data = (workspace / name).read_bytes()
        require(digest(data) == asset["revision"], "Published PDF differs")
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            count = 2 if index == 0 else 4
            require(len(pdf) == count, "Wrong PDF page count")
            require(
                result in pdf[0].get_text().splitlines(),
                "Wrong rendered formula result",
            )
            require(
                ("OUTSIDE PRINT RANGE" in pdf[0].get_text()) == (index != 0),
                "Print scope mismatch",
            )
            if index:
                require(
                    not pdf[1].get_text() and "HIDDEN" in pdf[2].get_text(),
                    "Missing blank/hidden worksheet output",
                )
            expected_pages.update(
                (asset["asset_id"], asset["revision"], n) for n in range(count)
            )
    require(
        expected_pages
        <= {
            (
                r["evidence"]["asset_id"],
                r["evidence"]["revision"],
                r["locator"]["page_index"],
            )
            for r in records.values()
        },
        "Incomplete PDF page readback",
    )
    seen, image_count, historical = set(), 0, False
    verified_files = set()
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] == "verify":
            if (
                args["reference"]["schema_version"] == "native-file-ref-v1"
                and result.get("valid") is True
            ):
                verified_files.add(
                    (args["reference"]["asset_id"], args["reference"]["revision"])
                )
            historical |= (
                args["reference"]["asset_id"] == source["asset_id"]
                and args["reference"]["revision"] == digest(original)
                and result.get("valid") is True
                and result.get("is_current_managed_revision") is False
            )
        if args["op"] == "render_pdf_page":
            images = [b for b in call["result"]["content"] if b["type"] == "image"]
            require(len(images) == 1, "Missing actual MCP image")
            raw = base64.b64decode(images[0]["data"], validate=True)
            require(digest(raw) == result["image_sha256"], "PNG identity mismatch")
            validate_image_pixels(workspace, result, args, raw)
            seen.add(
                (args["asset_id"], args["revision"], args["pdf_locator"]["page_index"])
            )
            image_count += 1
    require(
        expected_pages <= seen and image_count >= 11, "Incomplete frozen image review"
    )
    require(historical, "Original cell was not verified after update")
    require(
        {(a["asset_id"], a["revision"]) for a in assets} <= verified_files,
        "PDF file verification missing",
    )
    manifests = list((workspace / "wiki").glob("native-*/manifest.json"))
    require(len(manifests) == 1, "Wrong Wiki inventory")
    manifest = read_json(manifests[0])
    folder = manifests[0].parent
    require(manifest["revision"] == assets[-1]["revision"], "Wrong Wiki PDF revision")
    require(
        (folder / manifest["rendition"]["source_attachment"]).read_bytes() == updated,
        "Wiki lost exact conversion source",
    )
    require(
        read_json(folder / "rendition.json") == assets[-1]["history"][0]["result"],
        "Wiki receipt mismatch",
    )
    for name, entry in manifest["files"].items():
        data = (folder / name).read_bytes()
        require(
            digest(data) == entry["sha256"] and len(data) == entry["size_bytes"],
            "Wiki artifact mismatch",
        )
    return {
        "passed": True,
        "successful_calls": len(calls),
        "tool_errors": tool_errors(events),
        "images": image_count,
        "observations": final.get("observations"),
        "limitations": final.get("limitations"),
        "scope": "Exact XLSX revisions, explicit Calc policies, frozen PDF pages/actual pixels, formula999/3/5, hidden/blank/print scopes and portable conversion provenance; not Excel fidelity certification.",
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    report = write_audit(parser.parse_args().output.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
