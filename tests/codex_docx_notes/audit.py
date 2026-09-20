"""Actual trace order, native note identity, historical evidence and page audit."""

import argparse
import json
from pathlib import Path

from tests.codex_docx_grid.audit import validate_receipt
from tests.codex_docx_notes.records import (
    check_catalog,
    check_note,
    independent_catalog,
    validate_wikis,
)
from tests.codex_docx_structure.fonts import environment
from tests.codex_docx_structure.renders import validate_renders
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_story_lifecycle.audit import intent_bytes
from tests.native_docx_note_lifecycle_helpers import (
    assert_native_stages,
    edits,
    inspect_pages,
    text_edit,
)
from tests.native_docx_notes_helpers import locator

REQUIRED = {
    "contract",
    "contract_details",
    "register",
    "read_docx_notes",
    "read_docx_note",
    "update_docx_notes",
    "update_docx_note",
    "render_docx_page",
    "verify",
    "read_selection",
    "publish",
    "export_wiki",
    "history",
}
OPTIONAL = {"schema", "inspect", "list", "read_docx", "read_docx_block"}


def calls_from(events):
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete model turn")
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
        require(
            item["arguments"]["native_request"]["op"] in REQUIRED | OPTIONAL,
            "Unexpected native operation",
        )
        if not call_failed(item):
            calls.append(item)
    require(
        {c["arguments"]["native_request"]["op"] for c in calls} >= REQUIRED,
        "Missing note workflow",
    )
    return calls


def validate_history(workspace, asset, expected):
    source = workspace / "source.docx"
    require(
        digest(source.read_bytes()) == expected["source_sha256"]
        and source.stat().st_mtime_ns == expected["source_mtime_ns"],
        "Human source changed",
    )
    history = asset["history"]
    require(
        len(history) == 3
        and history[0]["sha256"] == expected["source_sha256"]
        and not asset["archived"],
        "Managed history differs",
    )
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    data = []
    for stage in history:
        raw = (root / stage["sha256"]).read_bytes()
        require(digest(raw) == stage["sha256"], "Managed bytes differ")
        data.append(raw)
    assert_native_stages(*data)
    require(
        (workspace / "verified.docx").read_bytes() == data[-1], "Published bytes differ"
    )
    return root


def validate_reads(calls, workspace, asset):
    buffers, records, catalogs = {}, {}, {}
    images, verified, metadata = set(), set(), set()
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    initial, current = asset["history"][0]["sha256"], asset["revision"]
    pending, writes, selected = None, 0, False
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {"read_docx_notes", "read_docx_note", "contract_details"}:
            contract = op == "contract_details"
            revision = "contract" if contract else result["inspected_revision"]
            location = args.get("docx_note_locator")
            key_loc = canonical(location) if location else None
            if not contract:
                require(
                    args["asset_id"] == asset["asset_id"]
                    and args["revision"] == revision,
                    "Unpinned note read",
                )
            page = result if contract else result["note"]
            key = op, revision, key_loc, page["text_sha256"]
            start, end = page["excerpt_char_range"]
            require(
                start == args.get("text_offset", 0)
                and end - start == len(page["text_excerpt"]),
                "Read range differs",
            )
            if start == 0:
                buffers[key] = ""
            require(len(buffers.get(key, "")) == start, "Missing complete read chunk")
            buffers[key] += page["text_excerpt"]
            if page["next_text_offset"] is not None:
                require(page["next_text_offset"] == end, "Bad read continuation")
                continue
            text = buffers.pop(key)
            require(
                len(text) == page["text_length"] and digest(text.encode()) == key[-1],
                "Incomplete hash/length",
            )
            record = json.loads(text)
            if contract:
                require(
                    args["contract_sha256"] == key[-1]
                    and record["docx_notes_enabled"]
                    and record["docx_notes_policy"],
                    "Incomplete contract",
                )
                metadata.add(key[-1])
                continue
            data = (root / revision).read_bytes()
            validate_receipt(record, asset, revision)
            if location:
                require(record["locator"] == location, "Read locator differs")
                check_note(record, data, asset["asset_id"], revision)
                records[revision, key_loc] = record
            else:
                check_catalog(record["catalog"], data)
                require(
                    record["catalog_sha256"] == digest(canonical(record["catalog"])),
                    "Catalog hash differs",
                )
                catalogs[revision] = record
            if pending == (revision, key_loc):
                pending = None
        elif op == "render_docx_page":
            require(
                args["asset_id"] == asset["asset_id"]
                and args["revision"] == result["inspected_revision"]
                and result["page_count"] == 3,
                "Wrong rendered note source",
            )
            require(
                any(b["type"] == "image" for b in call["result"]["content"]),
                "Missing actual image",
            )
            images.add((args["revision"], args["docx_page_index"]))
        elif op in {"update_docx_notes", "update_docx_note"}:
            require(pending is None, "Previous complete receipt missing")
            revision = args["expected_revision"]
            if writes == 0:
                require(
                    metadata and initial in catalogs, "Initial contract/catalog missing"
                )
                locations = [
                    canonical(n["locator"])
                    for n in independent_catalog((root / initial).read_bytes())["notes"]
                ]
                require(
                    all((initial, loc) in records for loc in locations),
                    "Initial full note records missing",
                )
                require(
                    {(initial, i) for i in range(3)} <= images, "Initial pages missing"
                )
            if op == "update_docx_notes":
                require(writes == 0 and revision == initial, "Wrong structure order")
                request = args["docx_notes_update"]
                require(
                    request["scope"] == "definitions_and_native_body_references"
                    and request["expected_catalog_sha256"]
                    == catalogs[initial]["catalog_sha256"],
                    "Wrong catalog precondition",
                )
                expected = edits(
                    catalogs[initial]["catalog"],
                    records[initial, canonical(locator(identity=8))],
                )
                require(
                    intent_bytes(request["edits"]) == intent_bytes(expected),
                    "Wrong definition edit intent",
                )
                pending = result["asset"]["revision"], None
            else:
                require(
                    writes == 1 and (revision, canonical(locator())) in records,
                    "Missing current note read",
                )
                note = records[revision, canonical(locator())]
                require(
                    args["docx_note_reference"] == note["evidence"]
                    and args["docx_note_update"] == text_edit(note),
                    "Wrong content reference/intent",
                )
                pending = result["asset"]["revision"], canonical(locator())
            writes += 1
        elif op == "read_selection":
            require(
                args["reference"]
                == records[initial, canonical(locator(identity=8))]["evidence"]
                and args["selection"] == {"pointer": "/text"},
                "Wrong deleted-note selection",
            )
            selected = True
        elif op == "verify":
            require(result["valid"], "Invalid historical evidence")
            ref = args["reference"]
            if ref["schema_version"] == "native-docx-note-ref-v1":
                require(
                    ref == records[initial, canonical(locator(identity=8))]["evidence"],
                    "Wrong deleted-note reference",
                )
            verified.add(ref["schema_version"])
        elif op == "publish":
            locations = [
                canonical(n["locator"])
                for n in independent_catalog((root / current).read_bytes())["notes"]
            ]
            require(
                pending is None
                and current in catalogs
                and all((current, loc) in records for loc in locations),
                "Final full note records missing",
            )
            require({(current, i) for i in range(3)} <= images, "Final pages missing")
            require(
                selected
                and {"native-docx-note-ref-v1", "native-selection-ref-v1"} <= verified,
                "Historical evidence not verified",
            )
    require(writes == 2 and pending is None, "Unexpected or unreviewed mutations")
    return {
        "note_records": len(records),
        "catalog_records": len(catalogs),
        "contract_records": len(metadata),
    }


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
    asset = load_asset(workspace, final["docx_asset_id"])
    root = validate_history(workspace, asset, expected)
    reads = validate_reads(calls, workspace, asset)
    validate_wikis(workspace, asset, root)
    require(
        isinstance(final.get("limitations"), list) and final["limitations"],
        "Missing limitations",
    )
    with environment(expected["font_environment"]):
        renders = validate_renders(
            workspace, asset, calls, final, {asset["history"][0]["sha256"]}
        )
        for index in [0, 2]:
            pdf, _ = inspect_pages(
                (root / asset["history"][index]["sha256"]).read_bytes(),
                final=index == 2,
            )
            (output / f"independent-notes-{index}.pdf").write_bytes(pdf)
    return {
        "passed": True,
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "complete_reads": reads,
        "managed_revisions": 3,
        "historical_wikis": 2,
        "renders": renders,
        "limitations": final["limitations"],
    }


def write_audit(output):
    result = audit(output)
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(
        json.dumps(
            write_audit(parser.parse_args().output), ensure_ascii=False, indent=2
        )
    )
