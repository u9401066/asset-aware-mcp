"""Independently check actual MCP-only execution, complete reads and native outputs."""

import argparse
import json
from pathlib import Path

from tests.codex_native_pdf.artifacts import load_asset, read_json, validate_source
from tests.codex_native_pdf.trace import complete_records, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pptx_tables.audit import validate_images
from tests.codex_table_edit.packages import check_packages
from tests.codex_table_expansion.audit import (
    check_historical_cell,
    check_transcription_read,
)
from tests.codex_table_expansion.packages import check_wikis
from tests.codex_table_grid.reads import read_events


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
            "Unexpected tool/server",
        )
        if not call_failed(item):
            calls.append(item)
    ops = {c["arguments"]["native_request"]["op"] for c in calls}
    require(
        {
            "register",
            "contract",
            "read_pdf_page",
            "render_pdf_page",
            "update",
            "update_workbook_table",
            "read_workbook",
            "read_cell",
            "verify",
            "history",
            "publish",
            "export_wiki",
        }
        <= ops,
        "Incomplete native workflow",
    )
    require(
        ops
        <= {
            "register",
            "contract",
            "schema",
            "read_pdf",
            "read_pdf_page",
            "render_pdf_page",
            "update",
            "update_workbook_table",
            "read_workbook",
            "read_cell",
            "verify",
            "history",
            "publish",
            "export_wiki",
            "inspect",
        },
        "Unexpected native operation",
    )
    return calls


def check_reads(calls, target, expected):
    edits = [
        (i, c)
        for i, c in enumerate(calls)
        if c["arguments"]["native_request"]["op"] == "update_workbook_table"
    ]
    require(len(edits) == 1, "Expected one specialized Table edit")
    at, call = edits[0]
    args, result = call["arguments"]["native_request"], payload(call)
    baseline = target["history"][1]["sha256"]
    require(
        args["expected_revision"] == baseline
        and args["asset_id"] == target["asset_id"]
        and result["asset"]["revision"] == target["revision"],
        "Wrong Table revision transition",
    )
    columns = {c["column_id"]: c for c in args["table_update"]["columns"]}
    require(set(columns) == {1, 2, 6}, "Wrong Table column edits")
    require(
        columns[2]["name"] == "Quantity"
        and columns[2]["expected_name"] == "Count"
        and columns[2]["header_runs"] == ["Quan", "tity"],
        "Wrong rich header intent",
    )
    require(
        columns[6]["calculated"]
        == {"formula": "=LEN([@Quantity])+1", "policy": "require_matching"}
        and columns[6]["totals"] == {"kind": "function", "value": "sum"},
        "Wrong calculated/totals intent",
    )
    reads = list(read_events(calls))
    check_transcription_read(calls, reads, target, expected)
    for revision, after in [(baseline, False), (target["revision"], True)]:
        records = [
            r
            for i, a, r, rev in reads
            if a["op"] == "read_workbook"
            and a["asset_id"] == target["asset_id"]
            and a.get("workbook_view") == "references"
            and rev == revision
            and (i > at) == after
        ]
        require(
            bool(records), "Missing complete pinned Table references before/after edit"
        )
        record = records[-1]
        require(
            record["operation_result"]
            == target["history"][2 if after else 1]["result"],
            "Operation receipt differs",
        )
        if after:
            check_original_receipt(record["operation_result"]["changes"][0]["cells"])
        require(
            record["tables"][0]["header_cells"][1]["value"]["value"]
            == ("Quantity" if after else "Count"),
            "Header inspection missing",
        )
    check_historical_cell(calls, at, target)
    check_header_evidence(calls, at, target, baseline)


def check_original_receipt(cells):
    for location in ("F2", "F3"):
        require(
            cells[location]["before"]["value"] == "=LEN([[#This Row],Count])"
            and cells[location]["after"]["value"] == "=LEN([@Quantity])+1",
            "Receipt before formula is not the original revision",
        )


def check_header_evidence(calls, at, target, baseline):
    evidence, reread, verified = None, False, False
    for index, call in enumerate(calls):
        args, result = call["arguments"]["native_request"], payload(call)
        if (
            args["op"] == "read_cell"
            and args.get("asset_id") == target["asset_id"]
            and args.get("revision") == baseline
            and args.get("cell") == "B1"
        ):
            cell = result["cell"]
            require(
                cell["representation_complete"]
                and cell["next_text_offset"] is None
                and cell["excerpt_char_range"] == [0, 5]
                and cell["value_excerpt"] == "Count"
                and cell["value_text_sha256"] == digest(b"Count"),
                "Historical header text changed or incomplete",
            )
            if index < at:
                evidence = cell["evidence"]
            else:
                require(
                    evidence is not None and cell["evidence"] == evidence,
                    "Historical header reference changed",
                )
                reread = True
        if (
            index > at
            and args["op"] == "verify"
            and evidence is not None
            and args.get("reference") == evidence
        ):
            require(
                result["valid"] and result["is_current_managed_revision"] is False,
                "Historical header proof failed",
            )
            verified = True
    require(
        evidence is not None and reread and verified,
        "Missing historical header read/proof",
    )


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
    source, target = (
        load_asset(workspace, final["source_asset_id"]),
        load_asset(workspace, final["table_asset_id"]),
    )
    validate_source(workspace, expected, source)
    images = validate_images(calls, workspace, source)
    require(bool(complete_records(calls)), "Source page record was not completely read")
    check_packages(workspace, target, expected)
    check_reads(calls, target, expected)
    check_wikis(workspace, target)
    return {
        "passed": True,
        "successful_calls": len(calls),
        "tool_errors": tool_errors(events),
        "images": images,
        "limitations": final.get("limitations", []),
        "scope": "Actual scan to supplied native Table; rich header/calculated/totals edit, complete reads, historical evidence and two Wikis. No native Excel rendering or recalculation.",
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
