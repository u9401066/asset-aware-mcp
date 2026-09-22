"""Independent native history, complete reads, delivered pixels and Wiki audit."""

import base64
import json
from pathlib import Path

import pymupdf

from tests.codex_delimited.audit import read_chunk
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import (
    canonical,
    complete_records,
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_workbook_rendition.audit import receipts
from tests.integration.test_native_ods_rename_calc import compare_reimport, oracle


def check_observer_values(page, *, broken):
    # This generated fixture places its four cells above the chart. PDF extraction
    # can put the page footer before body text, so textual position is not a cell
    # locator. Exclude the chart axis's unrelated '1' by explicit page geometry.
    values = [
        word[4] for word in page.get_text("words") if word[1] > 70 and word[3] < 140
    ]
    require(
        values == ["6", "6", "A", "#REF!" if broken else "1"],
        "Wrong rendered Observer cell values",
    )


def audit(output):
    workspace = output / "workspace"
    expected = read_json(output / "expected.json")
    final = read_json(output / "last-message.txt")
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete Agent turn")
    calls = []
    for event in events:
        if event["type"] != "item.completed":
            continue
        item = event["item"]
        require(
            item["type"] in {"reasoning", "agent_message", "plan", "mcp_tool_call"},
            "Non-MCP action",
        )
        if item["type"] != "mcp_tool_call":
            continue
        require(
            item["server"] == "asset_aware_under_test"
            and item["tool"] == "document"
            and item["arguments"]["op"] == "native",
            "Wrong tool/server",
        )
        if not call_failed(item):
            calls.append(item)
    operations = [c["arguments"]["native_request"]["op"] for c in calls]
    required = {
        "contract",
        "register",
        "inspect",
        "read_ods",
        "read_ods_cell",
        "read_ods_dependencies",
        "rename_ods_table",
        "update_ods",
        "create_workbook_rendition",
        "read_rendition",
        "read_pdf",
        "read_pdf_page",
        "render_pdf_page",
        "verify",
        "export_wiki",
        "publish",
        "history",
    }
    require(
        required <= set(operations) <= required | {"schema", "contract_details"},
        "Missing/unexpected operations",
    )
    require(
        operations.count("rename_ods_table") == operations.count("update_ods") == 1,
        "Unexpected native edits",
    )
    path = workspace / "source.ods"
    require(
        digest(path.read_bytes()) == expected["source_sha256"]
        and path.stat().st_mtime_ns == expected["source_mtime_ns"],
        "Human source changed",
    )
    source = load_asset(workspace, final["source_asset_id"])
    revisions = [h["sha256"] for h in source["history"]]
    require(
        len(revisions) == 3 and revisions[0] == expected["source_sha256"],
        "Wrong native history",
    )
    require(
        digest((workspace / "verified.ods").read_bytes()) == revisions[-1],
        "Wrong publication",
    )
    buffers, inventories, read_receipts, cells = {}, {}, {}, []
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] not in {"read_ods", "read_ods_cell", "read_ods_dependencies"}:
            continue
        require(args["asset_id"] == source["asset_id"], "Wrong read asset")
        if args.get("text_offset", 0):
            require(
                args.get("ods_text_sha256") == result["text_sha256"],
                "Unpinned continuation",
            )
        record = read_chunk(result, args, buffers)
        if record is None:
            continue
        revision = args["revision"]
        if args["op"] == "read_ods_dependencies":
            require(
                record["inventory_sha256"]
                == digest(
                    canonical(
                        {k: v for k, v in record.items() if k != "inventory_sha256"}
                    )
                ),
                "Wrong inventory digest",
            )
            inventories[revision] = record
        elif args["op"] == "read_ods":
            history = next(h for h in source["history"] if h["sha256"] == revision)
            require(
                record["operation_result"] == history.get("result"),
                "Incomplete receipt",
            )
            read_receipts[revision] = record["operation_result"]
        else:
            cell = record["cell"]
            require(
                cell["evidence"]["value_sha256"]
                == digest(
                    canonical({k: v for k, v in cell.items() if k != "evidence"})
                ),
                "Wrong complete cell reference",
            )
            require(cell["evidence"]["revision"] == revision, "Wrong cell revision")
            cells.append(cell)
    require(
        not buffers and set(revisions) <= set(read_receipts), "Unfinished receipt reads"
    )
    require(set(revisions[:2]) <= set(inventories), "Missing complete inventories")
    rename = next(
        c["arguments"]["native_request"]
        for c in calls
        if c["arguments"]["native_request"]["op"] == "rename_ods_table"
    )
    require(
        rename["expected_revision"] == revisions[0]
        and rename["ods_table_rename"]
        == {
            "table_index": 0,
            "table_name": "Source",
            "new_name": "New 中文 O'Brien",
            "dependencies_sha256": inventories[revisions[0]]["inventory_sha256"],
        },
        "Wrong original rename identity",
    )
    correction = next(
        c["arguments"]["native_request"]
        for c in calls
        if c["arguments"]["native_request"]["op"] == "update_ods"
    )
    require(
        correction["expected_revision"] == revisions[1]
        and len(correction["ods_update"]["cells"]) == 1,
        "Wrong correction revision/scope",
    )
    edit = correction["ods_update"]["cells"][0]
    require(
        edit["reference"] in [c["evidence"] for c in cells]
        and edit["reference"]["locator"]
        == {
            "part": "content.xml",
            "table_index": 1,
            "table_name": "Observer",
            "row": 3,
            "column": 0,
        },
        "Correction lost current full evidence",
    )
    require(
        any(
            c["arguments"]["native_request"].get("reference", {}).get("revision")
            == revisions[0]
            and payload(c).get("valid")
            and payload(c).get("is_current_managed_revision") is False
            for c in calls
            if c["arguments"]["native_request"]["op"] == "verify"
        ),
        "No historical verification",
    )
    pdfs = [
        load_asset(workspace, identity) for identity in final["rendition_asset_ids"]
    ]
    require(
        len(pdfs) == len({p["asset_id"] for p in pdfs}) == 3, "Need three frozen PDFs"
    )
    reports, expected_pages = receipts(calls), set()
    for index, pdf in enumerate(pdfs):
        require(len(pdf["history"]) == 1, "Frozen PDF was modified")
        receipt = reports[(pdf["asset_id"], pdf["revision"])]
        require(receipt == pdf["history"][0]["result"], "Incomplete rendition receipt")
        change = receipt["changes"][0]
        require(
            change["requested"]["mode"] == "print"
            and change["requested"]["calculation"] == "recalculate",
            "Wrong Calc policy",
        )
        require(
            change["source_reference"]["asset_id"] == source["asset_id"]
            and change["source_reference"]["revision"] == revisions[index],
            "Wrong rendition source",
        )
        path = (
            workspace
            / "data"
            / "native-assets"
            / pdf["asset_id"]
            / "revisions"
            / pdf["revision"]
        )
        with pymupdf.open(path) as document:
            require(len(document) == 2, "Wrong printed coverage")
            lines = document[1].get_text().splitlines()
            require(
                ("#REF!" in lines) == (index == 1), "Dynamic formula correction failed"
            )
            check_observer_values(document[1], broken=index == 1)
            expected_pages.update(
                (pdf["asset_id"], pdf["revision"], i) for i in range(2)
            )
    records = complete_records(calls)
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
        "Incomplete page reads",
    )
    viewed = set()
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] != "render_pdf_page":
            continue
        images = [b for b in call["result"]["content"] if b["type"] == "image"]
        require(len(images) == 1, "Missing actual image")
        raw = base64.b64decode(images[0]["data"], validate=True)
        require(digest(raw) == result["image_sha256"], "Image hash mismatch")
        validate_image_pixels(workspace, result, args, raw)
        viewed.add(
            (
                result["asset_id"],
                result["inspected_revision"],
                result["locator"]["page_index"],
            )
        )
    require(expected_pages <= viewed, "Missing original/renamed/corrected actual PNGs")
    wiki_revisions = set()
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] != "export_wiki":
            continue
        folder = Path(result["output_dir"])
        require(folder.is_relative_to(workspace / "wiki"), "Unexpected Wiki output")
        manifest = read_json(folder / "manifest.json")
        require(
            manifest["revision"] == args["revision"]
            and digest((folder / manifest["source_attachment"]).read_bytes())
            == args["revision"],
            "Wiki source identity mismatch",
        )
        for name, item in manifest["files"].items():
            raw = (folder / name).read_bytes()
            require(
                digest(raw) == item["sha256"] and len(raw) == item["size_bytes"],
                "Wiki integrity mismatch",
            )
        wiki_revisions.add(args["revision"])
    require(
        {revisions[0], revisions[-1]} <= wiki_revisions, "Missing historical/final Wiki"
    )
    comparisons = []
    for index, control in ((1, "control.ods"), (2, "corrected-control.ods")):
        target = output / f"independent-review-{index}"
        candidate = (
            workspace
            / "data"
            / "native-assets"
            / source["asset_id"]
            / "revisions"
            / revisions[index]
        )
        if not target.exists():
            oracle(
                target,
                "--candidate",
                candidate,
                "--control",
                output / "independent" / control,
            )
        proof = read_json(target / "oracle.json")
        require(
            proof["inputs"]["candidate"]["sha256"] == revisions[index],
            "Wrong retained oracle input",
        )
        comparisons.append(compare_reimport(target))
    return {
        "passed": True,
        "successful_calls": len(calls),
        "tool_errors": tool_errors(events),
        "actual_pages_delivered": len(viewed),
        "native_revisions": revisions,
        "independent_comparisons": comparisons,
        "observations": final.get("observations"),
        "limitations": final.get("limitations"),
        "scope": "Generated ODS rename and Agent formula correction; native history, Wiki and actual Calc pages. Not universal semantic/visual certification.",
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
