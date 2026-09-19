"""Audit complete MCP-only reads at each transition plus historical source evidence."""

import argparse
import json
from pathlib import Path

from tests.codex_native_pdf.artifacts import load_asset, read_json, validate_source
from tests.codex_native_pdf.trace import complete_records, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pptx_tables.audit import validate_images
from tests.codex_table_create.packages import check_wikis
from tests.codex_table_grid.reads import read_events
from tests.codex_table_totals.packages import check_packages


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
        "register",
        "contract",
        "read_pdf_page",
        "render_pdf_page",
        "create",
        "add_workbook_table",
        "update_workbook_table",
        "read_workbook",
        "read_cell",
        "verify",
        "history",
        "publish",
        "export_wiki",
    }
    actual = {c["arguments"]["native_request"]["op"] for c in calls}
    require(
        required
        <= actual
        <= required | {"schema", "contract_details", "read_pdf", "inspect"},
        "Incomplete/unexpected totals workflow",
    )
    return calls


def check_reads(calls, target):
    edits = [
        (i, c)
        for i, c in enumerate(calls)
        if c["arguments"]["native_request"]["op"]
        in {"add_workbook_table", "update_workbook_table"}
    ]
    require(len(edits) == 4, "Expected four Table mutations")
    reads = list(read_events(calls))
    bounds = [-1, *(i for i, _ in edits), len(calls)]
    for index, entry in enumerate(target["history"]):
        records = [
            r
            for i, a, r, revision in reads
            if bounds[index] < i < bounds[index + 1]
            and a["op"] == "read_workbook"
            and a["asset_id"] == target["asset_id"]
            and a.get("workbook_view") == "references"
            and revision == entry["sha256"]
        ]
        require(bool(records), "Missing complete reference read between mutations")
        require(
            records[-1]["operation_result"] == entry["result"],
            "Read/history receipt mismatch",
        )
        require(
            len(records[-1]["tables"]) == int(index > 0), "Wrong Table read inventory"
        )
        if index:
            _, call = edits[index - 1]
            args, result = call["arguments"]["native_request"], payload(call)
            require(
                args["asset_id"] == target["asset_id"]
                and args["expected_revision"] == target["history"][index - 1]["sha256"]
                and result["asset"]["revision"] == entry["sha256"],
                "Wrong revision transition",
            )
    baseline = target["history"][0]["sha256"]
    evidence, reread, verified = None, False, False
    for index, call in enumerate(calls):
        args, result = call["arguments"]["native_request"], payload(call)
        if (
            args["op"] == "read_cell"
            and args.get("asset_id") == target["asset_id"]
            and args.get("revision") == baseline
            and args.get("cell") == "B2"
        ):
            cell = result["cell"]
            require(
                cell["representation_complete"]
                and cell["next_text_offset"] is None
                and cell["value_excerpt"] == "007",
                "Incomplete/changed scan evidence",
            )
            if index < edits[0][0]:
                evidence = cell["evidence"]
            if index > edits[-1][0]:
                require(
                    evidence is not None and cell["evidence"] == evidence,
                    "Historical cell changed",
                )
                reread = True
        if (
            index > edits[-1][0]
            and args["op"] == "verify"
            and evidence is not None
            and args.get("reference") == evidence
        ):
            require(
                result["valid"] and not result["is_current_managed_revision"],
                "Historical proof failed",
            )
            verified = True
    require(
        evidence is not None and reread and verified,
        "Missing historical reread/verification",
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
    require(bool(complete_records(calls)), "Missing complete source page read")
    check_packages(workspace, target)
    check_reads(calls, target)
    check_wikis(
        workspace, {**target, "history": [target["history"][0], target["history"][-1]]}
    )
    return {
        "passed": True,
        "successful_calls": len(calls),
        "tool_errors": tool_errors(events),
        "images": images,
        "limitations": final.get("limitations", []),
        "scope": "Actual scanned PDF to independent XLSX/Table, totals clear/remove/reuse/keep, five complete revisions, historical cell proof, exact native Wikis. No Excel rendering or recalculation.",
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
