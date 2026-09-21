"""Audit complete MCP records/order, actual images and immutable real-PDF artifacts."""

import argparse
import base64
import json
from pathlib import Path

from src.application.native_pdf_annotation_operations import attach_annotation_evidence
from src.domain.native_pdf_annotations import PdfAnnotationLocator
from src.infrastructure.native_pdf import NativePdf
from tests.codex_docx_grid.audit import validate_receipt
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import (
    canonical,
    complete_records,
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pdf_annotations.checks import check_stages
from tests.real_pdf.corpus import check_source

REQUIRED = {
    "contract",
    "contract_details",
    "register",
    "read_pdf",
    "read_pdf_page",
    "render_pdf_page",
    "read_pdf_annotations",
    "read_pdf_annotation",
    "update_pdf_annotations",
    "verify",
    "read_selection",
    "read_derivations",
    "record_derivation",
    "verify_derivation",
    "publish",
    "export_wiki",
    "history",
}


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
            "Unexpected server/tool",
        )
        require(
            item["arguments"]["native_request"]["op"]
            in REQUIRED | {"schema", "inspect", "list"},
            "Unexpected operation",
        )
        if not call_failed(item):
            calls.append(item)
    require(
        {c["arguments"]["native_request"]["op"] for c in calls} >= REQUIRED,
        "Incomplete workflow",
    )
    return calls


def read_page(buffers, args, page):
    sha = page.get(
        "text_sha256", page.get("schema_sha256", page.get("derivations_sha256"))
    )
    require(isinstance(sha, str), "Missing complete representation hash")
    key = (
        args["op"],
        args.get("revision"),
        canonical(args.get("pdf_annotation_locator", args.get("pdf_locator"))),
        sha,
    )
    start, end = page["excerpt_char_range"]
    require(
        start == args.get("text_offset", 0)
        and end - start == len(page["text_excerpt"]),
        "Read range differs",
    )
    if start == 0:
        buffers[key] = ""
    require(
        key in buffers and len(buffers[key]) == start, "Skipped/repeated read chunk"
    )
    buffers[key] += page["text_excerpt"]
    if page["next_text_offset"] is not None:
        require(page["next_text_offset"] == end, "Invalid continuation")
        return None
    require(digest(buffers[key].encode()) == sha, "Complete read hash differs")
    return json.loads(buffers[key])


def audit(output, *, save_images=True):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace, case = output / "workspace", expected["case"]
    original = check_source(workspace / "source.pdf", case)
    require(
        (workspace / "source.pdf").stat().st_mtime_ns == expected["source_mtime_ns"],
        "Source mtime changed",
    )
    require(final["transcription"] == case["rows"][0], "Visual transcription differs")
    asset = load_asset(workspace, final["pdf_asset_id"])
    root = workspace / "data/native-assets" / asset["asset_id"]
    revisions = [s["sha256"] for s in asset["history"]]
    require(
        revisions[0] == expected["source_sha256"], "Original managed revision differs"
    )
    data = [(root / "revisions" / revision).read_bytes() for revision in revisions]
    require(
        data[0] == original and (workspace / "verified.pdf").read_bytes() == data[-1],
        "Source/publication differs",
    )
    check_stages(data, case)
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    calls = calls_from(events)
    pages = complete_records(calls)
    adapter = NativePdf()
    catalogs = {
        rev: adapter.inspect_annotations(raw)
        for rev, raw in zip(revisions, data, strict=True)
    }
    buffers, records, read_catalogs, images, policies, schemas, verified = (
        {},
        {},
        set(),
        set(),
        set(),
        set(),
        set(),
    )
    read_ledgers, exports, pending = set(), [], None
    target_pages = {case["pages"][0]["index"], case["pages"][0]["index"] + 1}
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {
            "contract_details",
            "schema",
            "read_pdf_annotations",
            "read_pdf_annotation",
            "read_pdf_page",
            "read_derivations",
        }:
            key = (
                "annotation"
                if op in {"read_pdf_annotations", "read_pdf_annotation"}
                else "page"
                if op == "read_pdf_page"
                else None
            )
            record = read_page(buffers, args, result[key] if key else result)
            if record is None:
                continue
            revision = args.get("revision")
            if op == "contract_details":
                require(
                    result["text_sha256"] == args["contract_sha256"],
                    "Contract not pinned",
                )
                policies.add(args.get("for_op"))
            elif op == "schema":
                require(
                    result["schema_sha256"] == args["schema_sha256"],
                    "Schema not pinned",
                )
                schemas.add(args.get("for_op"))
            elif op == "read_derivations":
                read_ledgers.add(digest(canonical(record)))
            elif op == "read_pdf_annotations":
                require(record["catalog"] == catalogs[revision], "Catalog differs")
                require(
                    record["catalog_sha256"] == digest(canonical(record["catalog"])),
                    "Catalog hash differs",
                )
                validate_receipt(record, asset, revision)
                read_catalogs.add(revision)
                if pending == revision:
                    pending = None
            elif op == "read_pdf_annotation":
                raw = (root / "revisions" / revision).read_bytes()
                truth = adapter.read_annotation(
                    raw,
                    PdfAnnotationLocator.model_validate(args["pdf_annotation_locator"]),
                )
                attach_annotation_evidence(truth, asset["asset_id"], revision)
                require(
                    {
                        k: v
                        for k, v in record.items()
                        if k not in {"operation_result", "operation_receipt_policy"}
                    }
                    == truth,
                    "Full annotation representation differs",
                )
                validate_receipt(record, asset, revision)
                records[canonical(record["evidence"])] = record
        elif op == "update_pdf_annotations":
            require(pending is None, "Mutation before complete previous receipt")
            revision = args["expected_revision"]
            require(
                revision in read_catalogs
                and "update_pdf_annotations" in policies
                and "update_pdf_annotations" in schemas,
                "Mutation before complete contract/catalog",
            )
            require(
                {(revision, i) for i in target_pages} <= images,
                "Mutation before actual page review",
            )
            expected_locators = {
                canonical(a["locator"]) for a in catalogs[revision]["annotations"]
            }
            observed = {
                canonical(r["locator"])
                for r in records.values()
                if r["evidence"]["revision"] == revision
            }
            require(
                expected_locators <= observed,
                "Mutation before every current annotation read",
            )
            pending = result["asset"]["revision"]
        elif op == "render_pdf_page":
            blocks = [b for b in call["result"]["content"] if b["type"] == "image"]
            require(len(blocks) == 1, "No actual MCP image")
            png = base64.b64decode(blocks[0]["data"], validate=True)
            require(digest(png) == result["image_sha256"], "PNG hash differs")
            validate_image_pixels(workspace, result, args, png)
            key = (result["inspected_revision"], result["locator"]["page_index"])
            images.add(key)
            if save_images:
                (output / f"page-{key[0][:12]}-{key[1]}.png").write_bytes(png)
        elif op == "verify":
            require(result["valid"], "Reference verification failed")
            verified.add(canonical(args["reference"]))
        elif op == "record_derivation":
            require(
                args["expected_derivations_sha256"] in read_ledgers,
                "Append before complete ledger",
            )
        elif op == "export_wiki":
            exports.append(result)
    require(
        pending is None and set(revisions) <= read_catalogs,
        "Missing full receipts/catalogs",
    )
    for revision in revisions:
        require(
            {canonical(a["locator"]) for a in catalogs[revision]["annotations"]}
            <= {
                canonical(r["locator"])
                for r in records.values()
                if r["evidence"]["revision"] == revision
            },
            "Missing complete final annotation record",
        )
    require(
        {(rev, i) for rev in revisions for i in target_pages} <= images,
        "Missing actual stage images",
    )
    created = [
        r
        for r in records.values()
        if r["evidence"]["revision"] == revisions[1]
        and r["subtype"] in {"/Highlight", "/FreeText"}
    ]
    require(
        len(created) == 2
        and all(canonical(r["evidence"]) in verified for r in created),
        "Historical reference not verified",
    )
    require(
        any(
            json.loads(ref).get("schema_version") == "native-selection-ref-v1"
            for ref in verified
        ),
        "Selection not verified",
    )
    ledger = read_json(root / "derivations.json")
    require(
        digest(canonical(ledger)) in read_ledgers and len(ledger["events"]) == 1,
        "Final ledger not completely read",
    )
    claim = ledger["events"][0]["derivation"]
    require(
        claim["target"]["revision"] == revisions[-1]
        and canonical(claim["target"]) in records
        and claim["target"]["schema_version"] == "native-pdf-annotation-ref-v1"
        and len(claim["sources"]) == 1
        and claim["sources"][0]["schema_version"] == "native-pdf-page-ref-v1"
        and claim["sources"][0]["revision"] == revisions[0],
        "Wrong derivation endpoints",
    )
    require(
        canonical(claim["sources"][0]) in pages, "Source page was not completely read"
    )
    require(
        any(
            c["arguments"]["native_request"]["op"] == "verify_derivation"
            and payload(c).get("references_valid")
            and payload(c).get("active")
            for c in calls
        ),
        "Derivation was not verified",
    )
    wiki_revisions = set()
    for export in exports:
        directory = Path(export["output_dir"])
        manifest = read_json(directory / "manifest.json")
        revision = manifest["revision"]
        wiki_revisions.add(revision)
        require(
            (directory / manifest["source_attachment"]).read_bytes()
            == (root / "revisions" / revision).read_bytes(),
            "Wiki PDF differs",
        )
        for name, item in manifest["files"].items():
            require(
                digest((directory / name).read_bytes()) == item["sha256"],
                "Wiki artifact changed",
            )
        if revision == revisions[-1]:
            require(
                manifest["projection"] == "pdf-annotations-v1",
                "Wrong annotation projection",
            )
            require(
                manifest["derivations"]["active_ids_for_revision"]
                == [ledger["events"][0]["derivation_id"]],
                "Wiki derivation missing",
            )
    require(
        {revisions[0], revisions[-1]} <= wiki_revisions, "Missing original/final Wiki"
    )
    review = final["visual_review"]
    require(
        review["scope"] == "static_mupdf_page_preview"
        and review["findings"]
        and final["limitations"],
        "Missing review limits/findings",
    )
    require(
        {(r["revision"], r["page_index"]) for r in review["reviewed_pages"]} == images,
        "Claimed image review differs from actual delivery",
    )
    return {
        "passed": True,
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "case": case["id"],
        "source_pages": case["page_count"],
        "managed_revisions": len(revisions),
        "actual_mcp_images": len(images),
        "complete_annotation_records": len(records),
        "wiki_revisions": sorted(wiki_revisions),
        "limitations": final["limitations"],
    }


def write_audit(output):
    try:
        result = audit(output)
    except Exception as exc:
        result = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
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
