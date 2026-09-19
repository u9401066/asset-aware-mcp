"""Validate actual MCP reads, frozen intent and native package outcomes independently."""

import argparse
import json
from pathlib import Path

from tests.codex_native_pdf.artifacts import load_asset, read_json, validate_source
from tests.codex_native_pdf.trace import canonical, complete_records, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pptx_tables.audit import validate_images
from tests.codex_table_expansion.packages import check_packages, check_wikis
from tests.codex_table_grid.audit import _check_snapshot
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
            and item["tool"] in {"document", "table_data", "table_manage"},
            "Unexpected tool/server",
        )
        if item["tool"] == "document":
            require(
                item["arguments"]["op"] == "native", "Non-native document operation"
            )
        if not call_failed(item):
            calls.append(item)
    native = [c for c in calls if c["tool"] == "document"]
    ops = {c["arguments"]["native_request"]["op"] for c in native}
    require(
        {
            "register",
            "contract",
            "read_pdf_page",
            "render_pdf_page",
            "update",
            "project_workbook_table",
            "read_table_workspace",
            "apply_table_workspace",
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
        not {"writeback", "update_worksheet_grid"} & ops,
        "Unexpected direct write/grid replacement",
    )
    return calls, native


def check_reads(calls, workspace, target):
    mutations = [
        (i, c)
        for i, c in enumerate(calls)
        if c["tool"] == "document"
        and c["arguments"]["native_request"]["op"] == "apply_table_workspace"
    ]
    require(len(mutations) == 1, "Expected one structural apply")
    applied_at, call = mutations[0]
    args, result = call["arguments"]["native_request"], payload(call)
    baseline = target["history"][1]["sha256"]
    require(
        args["asset_id"] == target["asset_id"]
        and args["expected_revision"] == baseline
        and result["asset"]["revision"] == target["revision"],
        "Wrong native transition",
    )
    reads = list(read_events(calls))
    a2t = [
        (i, r)
        for i, request, r, _ in reads
        if i < applied_at
        and request["op"] == "read_table_workspace"
        and request["table_id"] == args["table_id"]
    ]
    require(len(a2t) >= 2, "Missing complete pre-edit/pre-apply workspace reads")
    initial, current = a2t[0][1]["table"], a2t[-1][1]["table"]
    require(
        digest(canonical(current)) == args["expected_table_sha256"], "Wrong A2T hash"
    )
    require(
        initial["native_binding"] == current["native_binding"]
        and initial["native_binding"]["source"]["revision"] == baseline,
        "Source binding migrated",
    )
    for key, initial_count in [("row_ids", 3), ("column_ids", 6)]:
        require(
            len(initial[key]) == initial_count
            and len(current[key]) == initial_count + 1
            and current[key][:-1] == initial[key]
            and len(set(current[key])) == len(current[key]),
            "Surviving or new identity differs",
        )
    require(
        current["rows"][-1]["F"] == {"kind": "native_generated", "value": None}
        and current["rows"][0]["Review"] == {"kind": "native_generated", "value": None},
        "Explicit generation intent missing",
    )
    changes = [
        (i, c["arguments"]) for i, c in enumerate(calls) if c["tool"] != "document"
    ]
    require(
        changes
        and all(
            a2t[0][0] < i < a2t[-1][0] and c["table_id"] == args["table_id"]
            for i, c in changes
        ),
        "A2T mutations lack complete surrounding reads",
    )
    grid = args["worksheet_grid"]
    require(
        grid["worksheet"] == initial["native_binding"]["projection"]["worksheet"],
        "Wrong grid worksheet",
    )
    require(len(grid["edits"]) == 2, "Unexpected structural operations")
    for edit, axis, at, ref in zip(
        grid["edits"], ["row", "column"], [4, 7], ["A1:F3", "A1:F4"], strict=True
    ):
        require(
            edit["axis"] == axis
            and edit["operation"] == "insert"
            and edit["at"] == at
            and edit.get("count", 1) == 1
            and edit["expand_tables"]
            == [{"part": "xl/tables/table1.xml", "expected_ref": ref}],
            "Wrong intermediate table expansion",
        )
    check_native_reads(reads, calls, applied_at, target)
    _check_snapshot(calls, reads, applied_at, result, current, workspace)
    live = workspace / "data/tables" / f"{args['table_id']}.json"
    require(live.is_file(), "Live A2T workspace was deleted")
    require(
        read_json(live) == current, "Live A2T differs from the applied frozen intent"
    )


def check_native_reads(reads, calls, applied_at, target):
    baseline = target["history"][1]["sha256"]
    for revision, after in [(baseline, False), (target["revision"], True)]:
        candidates = [
            record
            for i, args, record, rev in reads
            if args["op"] == "read_workbook"
            and args["asset_id"] == target["asset_id"]
            and args.get("workbook_view") == "references"
            and rev == revision
            and (i > applied_at) == after
        ]
        require(
            bool(candidates), "Missing complete native references before/after apply"
        )
        record = candidates[-1]
        require(isinstance(record["references"], list), "Native references missing")
        require(
            record["operation_result"]
            == target["history"][2 if after else 1]["result"],
            "Native receipt mismatch",
        )
        require(
            record["tables"][0]["attributes"]["ref"] == ("A1:G4" if after else "A1:F3"),
            "Table inventory missing or wrong",
        )
    check_historical_cell(calls, applied_at, target)


def check_historical_cell(calls, applied_at, target):
    baseline = target["history"][1]["sha256"]
    evidence = None
    reread = False
    verified = False
    for index, call in enumerate(calls):
        if call["tool"] != "document":
            continue
        args, result = call["arguments"]["native_request"], payload(call)
        if (
            args["op"] == "read_cell"
            and args.get("asset_id") == target["asset_id"]
            and args.get("revision") == baseline
        ):
            cell = result["cell"]
            if cell["cell"] != "B2":
                continue
            require(
                cell["representation_complete"]
                and cell["next_text_offset"] is None
                and cell["excerpt_char_range"] == [0, 3]
                and cell["value_excerpt"] == "007"
                and cell["value_text_sha256"] == digest(b"007"),
                "Historical cell read incomplete or altered",
            )
            if index < applied_at:
                evidence = cell["evidence"]
            else:
                require(
                    evidence is not None and cell["evidence"] == evidence,
                    "Historical reference changed",
                )
                reread = True
        if (
            index > applied_at
            and args["op"] == "verify"
            and evidence is not None
            and args.get("reference") == evidence
        ):
            require(
                result.get("valid")
                and result.get("is_current_managed_revision") is False,
                "Historical cell verification failed",
            )
            verified = True
    require(
        evidence is not None and reread and verified,
        "Historical native cell read/proof missing",
    )


def check_transcription_read(calls, reads, target, expected):
    updates = [
        (i, c)
        for i, c in enumerate(calls)
        if c["tool"] == "document"
        and c["arguments"]["native_request"]["op"] == "update"
    ]
    require(len(updates) == 1, "Expected one native transcription update")
    index, call = updates[0]
    args = call["arguments"]["native_request"]
    require(
        args["asset_id"] == target["asset_id"]
        and args["expected_revision"] == expected["template_sha256"],
        "Wrong transcription source pin",
    )
    require(
        any(
            i < index
            and request["op"] == "read_workbook"
            and request["asset_id"] == target["asset_id"]
            and request.get("workbook_view") == "references"
            and rev == expected["template_sha256"]
            and isinstance(record["references"], list)
            for i, request, record, rev in reads
        ),
        "Missing complete native references before transcription",
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
    calls, native = calls_from(events)
    source = load_asset(workspace, final["source_asset_id"])
    target = load_asset(workspace, final["table_asset_id"])
    validate_source(workspace, expected, source)
    images = validate_images(native, workspace, source)
    require(
        bool(complete_records(native)), "Source page record was not completely read"
    )
    check_packages(workspace, target, expected)
    check_transcription_read(calls, list(read_events(calls)), target, expected)
    check_reads(calls, workspace, target)
    check_wikis(workspace, target)
    return {
        "passed": True,
        "successful_calls": len(calls),
        "tool_errors": tool_errors(events),
        "images": images,
        "limitations": final.get("limitations", []),
        "scope": "Synthetic scan to supplied native Table; A2T row/column expansion and generated header/formula, complete reads, historical evidence and immutable Wiki. No native Excel rendering or recalculation.",
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
