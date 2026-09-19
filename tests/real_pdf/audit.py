"""Audit actual model trace, independent real-table truth, bytes and evidence."""

import argparse
import base64
import json
from pathlib import Path

from tests.codex_delimited.audit import check_field, read_chunk
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import (
    canonical,
    complete_records,
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pptx_tables.derivations import complete_page
from tests.real_pdf.checks import differences, expected_revisions, require_coverage
from tests.real_pdf.raster import region_image

ALLOWED = {
    "schema",
    "contract",
    "register",
    "inspect",
    "read_pdf",
    "read_pdf_page",
    "render_pdf_page",
    "read_pdf_region",
    "verify",
    "create_delimited",
    "read_delimited",
    "read_delimited_cell",
    "update_delimited",
    "read_derivations",
    "record_derivation",
    "verify_derivation",
    "export_wiki",
    "publish",
    "history",
}


def trace(output, case):
    events = [
        json.loads(line)
        for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    calls, attempts = [], []
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
        args = item["arguments"]
        require(
            item["server"] == "asset_aware_under_test"
            and item["tool"] == "document"
            and args["op"] == "native",
            "Wrong server/tool",
        )
        request = args["native_request"]
        require(request["op"] in ALLOWED, "Unexpected native operation")
        if request["op"] == "register":
            require(
                Path(request["source_path"]).resolve()
                == output / "workspace" / "source.pdf",
                "Unexpected source/answer access",
            )
        if request["op"] == "create_delimited":
            rows = request["delimited_create"]["rows"]
            attempts.append(
                {
                    "rows": rows,
                    "differences": differences(rows, [case["columns"], *case["rows"]]),
                    "call_failed": call_failed(item),
                }
            )
        if not call_failed(item):
            calls.append(item)
    # Save the first attempt even when the later workflow is incomplete or wrong.
    (output / "transcriptions.json").write_text(
        json.dumps(attempts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete model turn")
    require(
        attempts and len(attempts) == 1 and not attempts[0]["differences"],
        "First transcription differs from independent real-table oracle; see transcriptions.json",
    )
    require(
        {"history", "publish", "export_wiki", "verify_derivation"}
        <= {c["arguments"]["native_request"]["op"] for c in calls},
        "Incomplete workflow",
    )
    return calls, events


def check_wiki(workspace, target, source_sha, fields, ledger):
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 1, "Missing/extra Wiki snapshot")
    path = manifests[0]
    manifest = read_json(path)
    require(
        manifest["revision"] == target["revision"]
        and manifest["representation"] == "delimited_fields",
        "Wrong Wiki revision/representation",
    )
    for name, info in manifest["files"].items():
        data = (path.parent / name).read_bytes()
        require(
            digest(data) == info["sha256"] and len(data) == info["size_bytes"],
            "Wiki artifact mismatch",
        )
    require(
        digest((path.parent / manifest["source_attachment"]).read_bytes())
        == target["revision"],
        "Wiki CSV mismatch",
    )
    records = [
        json.loads(line)
        for line in (path.parent / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    require(
        len(records) == manifest["cell_count"] == len(fields), "Incomplete Wiki fields"
    )
    for record in records:
        require(
            canonical(record["evidence"]) in fields
            and "row " in record["citation_presentation"]["inline"],
            "Wiki field/custom citation mismatch",
        )
    info = manifest["derivations"]
    require(
        set(info["active_ids_for_revision"])
        == {e["derivation_id"] for e in ledger["events"]},
        "Lost assertions",
    )
    require(
        len(info["region_records"]) == len(ledger["events"]), "Missing region records"
    )
    for entry in info["region_records"].values():
        stored = read_json(path.parent / entry["record_file"])
        require(
            digest((path.parent / stored["source_attachment"]).read_bytes())
            == source_sha,
            "Wiki PDF source changed",
        )
        region_image(
            workspace,
            entry["reference"],
            {"image_sha256": entry["preview_sha256"]},
            768,
            (path.parent / entry["preview_attachment"]).read_bytes(),
        )


def audit(output):
    expected = read_json(output / "expected.json")
    case, workspace = expected["case"], output / "workspace"
    calls, events = trace(output, case)
    final = read_json(output / "last-message.txt")
    source, target = (
        load_asset(workspace, final[k]) for k in ("source_asset_id", "table_asset_id")
    )
    original_pdf = workspace / "source.pdf"
    require(
        digest(original_pdf.read_bytes()) == case["sha256"] == source["revision"]
        and original_pdf.stat().st_mtime_ns == expected["source_mtime_ns"],
        "Original PDF changed",
    )
    require(
        len(source["history"]) == 1 and source["source"] is not None,
        "Source lifecycle changed",
    )
    directory = workspace / "data" / "native-assets" / target["asset_id"]
    truth = expected_revisions(case)
    require(
        target["format"] == "csv"
        and target["source"] is None
        and len(target["history"]) == 7,
        "Wrong CSV lifecycle",
    )
    revisions = {}
    for history, wanted in zip(target["history"], truth, strict=True):
        data = (directory / "revisions" / history["sha256"]).read_bytes()
        require(data == wanted, "Intermediate CSV bytes differ")
        revisions[history["sha256"]] = data
    require(
        (workspace / "verified.csv").read_bytes() == truth[0] == truth[-1],
        "Published CSV changed",
    )
    pages = complete_records(calls)
    page_truth = {p["index"]: p for p in case["pages"]}
    require(
        {p["locator"]["page_index"] for p in pages.values()} == set(page_truth),
        "Missing complete source page records",
    )
    require(
        all(
            p["evidence"]["asset_id"] == source["asset_id"]
            and p["evidence"]["revision"] == source["revision"]
            for p in pages.values()
        ),
        "Wrong page identity",
    )
    ledger = read_json(directory / "derivations.json")
    require(len(ledger["events"]) == len(page_truth), "Wrong sampled assertion count")
    by_id = {e["derivation_id"]: e for e in ledger["events"]}
    prefix = {**ledger, "events": []}
    fields, regions, chunks, ledger_chunks = {}, {}, {}, {}
    complete_ledgers, page_images, proven = set(), set(), set()
    available_pages, claimed_pages, final_proven = set(), set(), set()
    field_stages = {0: set(), 6: set()}
    raster_checks = []
    receipts, edits, image_count, historical = [], [], 0, False
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {"read_delimited_cell", "read_delimited"}:
            record = read_chunk(result, args, chunks)
            if record is None:
                continue
            if op == "read_delimited_cell":
                require(
                    record["evidence"]["asset_id"] == target["asset_id"]
                    and record["evidence"]["revision"] == args["revision"],
                    "Wrong field identity",
                )
                check_field(record, revisions[args["revision"]])
                fields[canonical(record["evidence"])] = record
                if (
                    len(edits) in field_stages
                    and args["revision"] == target["revision"]
                ):
                    field_stages[len(edits)].add(
                        (record["locator"]["row"], record["locator"]["column"])
                    )
            else:
                require(record["operation_result"] is not None, "Missing receipt")
                receipts.append(
                    (
                        len(edits),
                        args["revision"],
                        record["operation_result"]["changes"][0]["operation"],
                    )
                )
        elif op == "read_pdf_page" and result["page"]["next_text_offset"] is None:
            available_pages.add(canonical(result["page"]["evidence"]))
        elif op == "update_delimited":
            change = args["delimited_update"]
            if change["operation"] == "set_cells":
                require(
                    all(canonical(e["reference"]) in fields for e in change["cells"]),
                    "Update before full field read",
                )
            edits.append(change["operation"])
        elif op == "render_pdf_page":
            images = [c for c in call["result"]["content"] if c["type"] == "image"]
            require(len(images) == 1, "No actual page image")
            png = base64.b64decode(images[0]["data"], validate=True)
            require(digest(png) == result["image_sha256"], "Page image digest mismatch")
            validate_image_pixels(workspace, result, args, png)
            require(
                result["asset_id"] == source["asset_id"]
                and result["inspected_revision"] == source["revision"],
                "Wrong page image source",
            )
            page_images.add(result["locator"]["page_index"])
        elif op == "read_pdf_region":
            region, reference = result["region"], result["region"]["evidence"]
            require(
                canonical(reference["parent"]) in pages
                and canonical(reference["parent"]) in available_pages
                and reference["parent"] == region["parent"]
                and reference["selector"] == region["selector"],
                "Wrong region parent/selector",
            )
            require(
                digest(canonical({k: v for k, v in region.items() if k != "evidence"}))
                == reference["value_sha256"],
                "Wrong region digest",
            )
            images = [c for c in call["result"]["content"] if c["type"] == "image"]
            require(len(images) == 1, "Missing actual region PNG")
            raster_check = region_image(
                workspace,
                reference,
                result,
                args.get("render_size", 1024),
                base64.b64decode(images[0]["data"], validate=True),
            )
            raster_checks.append(raster_check)
            regions[canonical(reference)] = region
            image_count += 1
        elif op == "read_derivations":
            sha = digest(canonical(prefix))
            require(result["derivations_sha256"] == sha, "Ledger trace mismatch")
            if complete_page(
                result, sha, ledger_chunks, digest_field="derivations_sha256"
            ):
                complete_ledgers.add(sha)
        elif op == "record_derivation":
            sha = digest(canonical(prefix))
            require(
                sha in complete_ledgers and args["expected_derivations_sha256"] == sha,
                "Append before complete ledger",
            )
            event = by_id[result["derivation_id"]]
            claim = event["derivation"]
            require(
                canonical(claim["target"]) in fields
                and len(claim["sources"]) == 1
                and canonical(claim["sources"][0]) in regions,
                "Assertion before full source/field review",
            )
            require(
                claim["target"]["revision"] == digest(truth[0]), "Migrated assertion"
            )
            ref = claim["sources"][0]
            page = page_truth[ref["parent"]["locator"]["page_index"]]
            require(
                page["index"] not in claimed_pages,
                "Repeated page instead of distinct sampled provenance",
            )
            claimed_pages.add(page["index"])
            require(
                claim["target"]["locator"]["row"] == page["first_row"]
                and claim["target"]["locator"]["column"] == 1,
                "Wrong sampled target",
            )
            require_coverage(ref["selector"]["rect"], page["content_bounds"])
            prefix["events"].append(event)
        elif (
            op == "verify_derivation"
            and result["active"]
            and result["references_valid"]
        ):
            proven.add(result["derivation_id"])
            if len(edits) == 6 and result["derivations_sha256"] == digest(
                canonical(ledger)
            ):
                final_proven.add(result["derivation_id"])
        elif (
            op == "verify"
            and result["valid"]
            and not result["is_current_managed_revision"]
        ):
            historical = True
    operations = [
        "set_cells",
        "set_cells",
        "insert_rows",
        "insert_column",
        "delete_rows",
        "delete_columns",
    ]
    require(edits == operations, "Wrong CRUD sequence")
    for i, operation in enumerate(["create_delimited", *operations]):
        require(
            (i, digest(truth[i]), operation) in receipts,
            "Missing full intermediate receipt",
        )
    require(
        not chunks
        and not ledger_chunks
        and prefix == ledger
        and digest(canonical(ledger)) in complete_ledgers,
        "Incomplete final readback",
    )
    require(
        page_images == claimed_pages == set(page_truth)
        and proven == final_proven == set(by_id)
        and historical,
        "Missing image/assertion/historical review",
    )
    final_fields = {
        key: f
        for key, f in fields.items()
        if f["evidence"]["revision"] == target["revision"]
    }
    expected_coordinates = {
        (r, c)
        for r in range(len(case["rows"]) + 1)
        for c in range(len(case["columns"]))
    }
    require(
        field_stages[0] == field_stages[6] == expected_coordinates,
        "Missing initial or post-CRUD complete field review",
    )
    require(
        {(f["locator"]["row"], f["locator"]["column"]) for f in final_fields.values()}
        == {
            (r, c)
            for r in range(len(case["rows"]) + 1)
            for c in range(len(case["columns"]))
        },
        "Missing complete table field readbacks",
    )
    check_wiki(workspace, target, case["sha256"], final_fields, ledger)
    return {
        "passed": True,
        "case": case["id"],
        "successful_native_calls": len(calls),
        "data_rows": len(case["rows"]),
        "data_cells": len(case["rows"]) * len(case["columns"]),
        "actual_page_images": len(page_images),
        "actual_region_images": image_count,
        "csv_history_events": 7,
        "sampled_derivations": len(by_id),
        "first_transcription_exact": True,
        "raster_checks": raster_checks,
        "errors": tool_errors(events),
        "limitations": [
            "Two selected public documents do not establish arbitrary-document fidelity.",
            "Only each page's first-row value has a sampled derivation; remaining fields have no per-field source assertion.",
            "Independent raster checks share the MuPDF renderer; string truth was separately visually reviewed.",
        ],
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    report = write_audit(parser.parse_args().output.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
