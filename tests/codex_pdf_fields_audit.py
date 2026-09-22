"""Audit actual field MCP calls, native states, complete evidence and page images."""

import argparse
import base64
import json
from pathlib import Path

from src.domain.native_pdf_fields import PdfFieldLocator, PdfFieldsUpdate
from src.infrastructure.native_pdf import NativePdf
from tests.codex_docx_grid.audit import validate_receipt
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import (
    canonical,
    digest,
    payload,
    validate_image_pixels,
)
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pdf_fields import SOURCE_SHA256, VALUE
from tests.codex_pdf_fields_checks import check_states

REQUIRED = {
    "contract",
    "contract_details",
    "schema",
    "register",
    "read_pdf_page",
    "render_pdf_page",
    "read_pdf_fields",
    "read_pdf_field",
    "update_pdf_fields",
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
            "Unexpected server/tool",
        )
        require(
            item["arguments"]["native_request"]["op"]
            in REQUIRED | {"read_pdf", "inspect", "list"},
            "Unexpected operation",
        )
        if not call_failed(item):
            calls.append(item)
    require(
        {c["arguments"]["native_request"]["op"] for c in calls} >= REQUIRED,
        "Missing field workflow operations",
    )
    return calls


def collect_page(buffers, args, page):
    sha = page.get(
        "text_sha256", page.get("schema_sha256", page.get("derivations_sha256"))
    )
    require(isinstance(sha, str), "Missing representation hash")
    start, end = page["excerpt_char_range"]
    require(
        start == args.get("text_offset", 0)
        and end - start == len(page["text_excerpt"]),
        "Read range differs",
    )
    if start and args["op"] in {"read_pdf_fields", "read_pdf_field"}:
        require(
            args.get("pdf_field_text_sha256") == sha,
            "Field continuation hash not pinned",
        )
    key = (
        args["op"],
        args.get("asset_id"),
        args.get("revision"),
        args.get("for_op"),
        canonical(args.get("pdf_field_locator", args.get("pdf_locator"))),
        canonical(args.get("reference")),
        sha,
    )
    if start == 0:
        buffers[key] = ""
    require(
        key in buffers and len(buffers[key]) == start, "Skipped or repeated read chunk"
    )
    buffers[key] += page["text_excerpt"]
    if page["next_text_offset"] is not None:
        require(page["next_text_offset"] == end, "Invalid continuation")
        return None
    text = buffers.pop(key)
    require(
        len(text) == page.get("text_length", len(text)), "Complete text length differs"
    )
    require(digest(text.encode()) == sha, "Complete read hash differs")
    return json.loads(text)


def field_truth(adapter, raw, asset_id, revision, locator):
    record = adapter.read_field(raw, PdfFieldLocator.model_validate(locator))
    record["evidence"] = {
        "schema_version": "native-pdf-field-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": record["locator"],
        "value_sha256": digest(canonical(record)),
        "verification_scope": "immutable_native_representation",
    }
    return record


def require_ready(
    revision, catalogs, read_catalogs, records, images, policies, schemas
):
    require(
        revision in read_catalogs
        and "update_pdf_fields" in policies
        and "update_pdf_fields" in schemas,
        "Mutation before complete contract/catalog",
    )
    require((revision, 0) in images, "Mutation before actual page image")
    expected = {canonical(item["locator"]) for item in catalogs[revision]["fields"]}
    observed = {
        canonical(r["locator"])
        for r in records.values()
        if r["evidence"]["revision"] == revision
    }
    require(expected <= observed, "Mutation before every complete field record")


def validate_selection(args, result, record, records):
    reference = args["reference"]
    existing = reference["schema_version"] == "native-selection-ref-v1"
    parent = reference["parent"] if existing else reference
    require(canonical(parent) in records, "Selection parent was not completely read")
    require(
        not existing or args.get("selection") is None,
        "Existing selector was overridden",
    )
    selector = (
        reference["selector"]
        if existing
        else {"char_range": None, **args.get("selection", {})}
    )
    require(
        selector == {"pointer": "/inherited_entries/~1V/text", "char_range": None},
        "Unexpected selected field value",
    )
    value = records[canonical(parent)]["inherited_entries"]["/V"]["text"]
    require(value == VALUE, "Selected parent value differs")
    context = {
        "char_range": [0, len(value)],
        "utf8_byte_range": [0, len(value.encode())],
        "source_text_length": len(value),
        "source_text_sha256": digest(value.encode()),
        "prefix": "",
        "suffix": "",
        "coordinate_scope": "Unicode codepoints and UTF-8 bytes of the selected parsed string; not source-file offsets",
    }
    expected = {
        "schema_version": "native-selection-v1",
        "parent": parent,
        "selector": selector,
        "value": value,
        "text_context": context,
    }
    evidence = {
        "schema_version": "native-selection-ref-v1",
        "asset_id": parent["asset_id"],
        "revision": parent["revision"],
        "parent": parent,
        "selector": selector,
        "value_sha256": digest(canonical(expected)),
        "verification_scope": "immutable_representation_selection",
    }
    require(
        record == {**expected, "evidence": evidence},
        "Complete selected value/context differs",
    )
    require(
        result["evidence"] == evidence
        and result["asset_id"] == parent["asset_id"]
        and result["inspected_revision"] == parent["revision"],
        "Selection envelope identity differs",
    )
    require(
        not existing or reference == evidence, "Historical selection reference differs"
    )
    return evidence


def audit(output, *, save_images=True):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    source = workspace / "source.pdf"
    original = source.read_bytes()
    require(
        digest(original) == expected["source_sha256"] == SOURCE_SHA256,
        "Pinned original source differs",
    )
    require(
        source.stat().st_mtime_ns == expected["source_mtime_ns"], "Source mtime changed"
    )
    require(
        expected["model_selection"] == "Codex default; no model override",
        "Model override",
    )
    command = read_json(output / "command.json")
    require(
        "--model" not in command
        and "-m" not in command
        and not any(arg.startswith("model=") for arg in command),
        "Model override in command",
    )
    asset = load_asset(workspace, final["pdf_asset_id"])
    root = workspace / "data/native-assets" / asset["asset_id"]
    revisions = [h["sha256"] for h in asset["history"]]
    data = {rev: (root / "revisions" / rev).read_bytes() for rev in revisions}
    require(
        data[revisions[0]] == original
        and (workspace / "verified.pdf").read_bytes() == data[revisions[-1]],
        "Source/publication differs",
    )
    check_states([data[rev] for rev in revisions])
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    calls = calls_from(events)
    adapter = NativePdf()
    catalogs = {rev: adapter.inspect_fields(raw) for rev, raw in data.items()}
    buffers, records, page_refs = {}, {}, set()
    images, policies, schemas, read_catalogs, verified, read_ledgers = (
        set(),
        set(),
        set(),
        set(),
        set(),
        set(),
    )
    selections, exports, pending, read_after_deletion = {}, [], None, set()
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {
            "contract_details",
            "schema",
            "read_pdf_fields",
            "read_pdf_field",
            "read_pdf_page",
            "read_derivations",
            "read_selection",
        }:
            page = result["page"] if op == "read_pdf_page" else result
            record = collect_page(buffers, args, page)
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
            elif op == "read_selection":
                evidence = validate_selection(args, result, record, records)
                selections[canonical(evidence)] = evidence
            elif op == "read_pdf_page":
                require(
                    record["evidence"]["revision"] == revision
                    and record["evidence"]["asset_id"] == asset["asset_id"],
                    "Page identity differs",
                )
                require(
                    digest(
                        canonical({k: v for k, v in record.items() if k != "evidence"})
                    )
                    == record["evidence"]["value_sha256"],
                    "Page record hash differs",
                )
                page_refs.add(canonical(record["evidence"]))
            else:
                require(
                    args["asset_id"] == asset["asset_id"] == result["asset_id"]
                    and result["inspected_revision"] == revision,
                    "Field read identity differs",
                )
                if op == "read_pdf_fields":
                    require(
                        record["catalog"] == catalogs[revision],
                        "Complete field catalog differs",
                    )
                    validate_receipt(record, asset, revision)
                    read_catalogs.add(revision)
                    if pending == revision:
                        pending = None
                else:
                    truth = field_truth(
                        adapter,
                        data[revision],
                        asset["asset_id"],
                        revision,
                        args["pdf_field_locator"],
                    )
                    require(
                        record
                        == {
                            "schema_version": "native-pdf-field-read-v1",
                            "field": truth,
                        },
                        "Complete field representation differs",
                    )
                    records[canonical(truth["evidence"])] = truth
                    if revisions[-1] in read_catalogs and revision != revisions[-1]:
                        read_after_deletion.add(canonical(truth["evidence"]))
        elif op == "update_pdf_fields":
            require(pending is None, "Mutation before complete previous receipt")
            revision = args["expected_revision"]
            require_ready(
                revision, catalogs, read_catalogs, records, images, policies, schemas
            )
            for edit in args["pdf_fields_update"]["edits"]:
                for member in ("reference", "parent_reference"):
                    if edit.get(member) is not None:
                        require(
                            canonical(edit[member]) in records,
                            "Mutation field reference was not read",
                        )
                for widget in edit.get("field", {}).get("widgets", []):
                    require(
                        canonical(widget["page_reference"]) in page_refs,
                        "Create page reference was not read",
                    )
            candidate, report = adapter.edit_fields(
                data[revision],
                PdfFieldsUpdate.model_validate(args["pdf_fields_update"]),
            )
            after = result["asset"]["revision"]
            require(candidate == data[after], "Replayed mutation bytes differ")
            if after != revision:
                receipt = next(
                    h["result"]
                    for h in reversed(asset["history"])
                    if h["sha256"] == after
                )
                require(
                    report.model_dump(mode="json") == receipt,
                    "Replayed complete receipt differs",
                )
                pending = after
            else:
                require(
                    result["operation_result"]["full_result"]
                    == report.model_dump(mode="json"),
                    "No-op receipt differs",
                )
        elif op == "render_pdf_page":
            blocks = [b for b in call["result"]["content"] if b["type"] == "image"]
            require(len(blocks) == 1, "Missing actual MCP image")
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
        "Missing complete receipts/catalogs",
    )
    for revision in revisions:
        require_ready(
            revision, catalogs, read_catalogs, records, images, policies, schemas
        )
    require({(rev, 0) for rev in revisions} <= images, "Missing actual revision image")
    deleted = [
        r
        for r in records.values()
        if r["qualified_name"] == "Text1"
        and r["inherited_entries"].get("/V", {}).get("text") == VALUE
    ]
    created = [
        r
        for r in records.values()
        if r["qualified_name"] == "ReviewCopy"
        and r["evidence"]["revision"] != revisions[-1]
    ]
    require(deleted and created, "Missing updated/deleted historical field records")
    for candidates in (deleted, created):
        require(
            any(
                canonical(r["evidence"]) in verified & read_after_deletion
                for r in candidates
            ),
            "Historical field not verified and reread after deletion",
        )
    ledger = read_json(root / "derivations.json")
    require(
        digest(canonical(ledger)) in read_ledgers and len(ledger["events"]) == 1,
        "Final ledger not completely read",
    )
    claim = ledger["events"][0]["derivation"]
    require(
        canonical(claim["target"]) in records
        and claim["target"]["revision"] == revisions[-1]
        and records[canonical(claim["target"])]["qualified_name"] == "ReviewCopy",
        "Wrong derivation target",
    )
    require(len(claim["sources"]) == 1, "Wrong derivation source count")
    selected = claim["sources"][0]
    require(
        canonical(selected) in selections and canonical(selected) in verified,
        "Historical selection not read/verified",
    )
    require(
        canonical(selected["parent"]) in {canonical(r["evidence"]) for r in deleted}
        and selected["selector"]
        == {"pointer": "/inherited_entries/~1V/text", "char_range": None},
        "Wrong historical selection",
    )
    require(
        any(
            c["arguments"]["native_request"]["op"] == "verify_derivation"
            and payload(c).get("references_valid")
            and payload(c).get("active")
            for c in calls
        ),
        "Derivation not verified",
    )
    wiki_revisions = check_wikis(exports, root, asset, catalogs, adapter, ledger)
    require(
        {revisions[0], revisions[-1]} <= wiki_revisions, "Missing original/final Wiki"
    )
    review = final["visual_review"]
    require(
        review["scope"] == "static_mupdf_page_preview"
        and review["findings"]
        and final["limitations"],
        "Missing review findings/limits",
    )
    require(
        {(r["revision"], r["page_index"]) for r in review["reviewed_pages"]} == images,
        "Claimed visual review differs from actual image delivery",
    )
    return {
        "passed": True,
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "managed_revisions": len(revisions),
        "actual_mcp_images": len(images),
        "complete_field_records": len(records),
        "wiki_revisions": sorted(wiki_revisions),
        "limitations": final["limitations"],
    }


def check_wikis(exports, root, asset, catalogs, adapter, ledger):
    revisions = set()
    for export in exports:
        directory = Path(export["output_dir"])
        manifest = read_json(directory / "manifest.json")
        rev = manifest["revision"]
        revisions.add(rev)
        raw = (root / "revisions" / rev).read_bytes()
        require(
            (directory / manifest["source_attachment"]).read_bytes() == raw,
            "Wiki PDF differs",
        )
        for name, metadata in manifest["files"].items():
            require(
                digest((directory / name).read_bytes()) == metadata["sha256"],
                "Wiki artifact changed",
            )
        receipt = next(
            h.get("result") for h in reversed(asset["history"]) if h["sha256"] == rev
        )
        require(
            manifest["projection"] == "pdf-fields-v1:" + digest(canonical(receipt)),
            "Wrong Wiki receipt projection",
        )
        require(
            read_json(directory / "operation-result.json") == receipt,
            "Wiki receipt differs",
        )
        require(
            read_json(directory / "field-catalog.json") == catalogs[rev],
            "Wiki catalog differs",
        )
        records = [
            json.loads(line)
            for line in (directory / "fields.jsonl").read_text().splitlines()
        ]
        require(
            len(records) == catalogs[rev]["field_count"] == manifest["field_count"],
            "Wiki field count differs",
        )
        require(
            {canonical(r["locator"]) for r in records}
            == {canonical(r["locator"]) for r in catalogs[rev]["fields"]},
            "Wiki field identities differ",
        )
        for record in records:
            truth = field_truth(adapter, raw, asset["asset_id"], rev, record["locator"])
            require(
                {k: record[k] for k in truth} == truth, "Wiki complete field differs"
            )
            expected_pages = sorted(
                {
                    item["locator"]["page"]["page_index"]
                    for widget in truth["widgets"]
                    for item in widget["page_occurrences"]
                }
            )
            require(
                [link["page_index"] for link in record["page_links"]] == expected_pages,
                "Wiki widget pages differ",
            )
            for link in record["page_links"]:
                require(
                    (directory / link["note"]).is_file()
                    and (directory / link["preview_attachment"]).is_file(),
                    "Missing widget page note/PNG",
                )
            if rev == asset["revision"]:
                require(
                    record["citation_presentation"]["inline"].startswith(
                        "Field [PDF field path"
                    ),
                    "Missing custom physical field citation",
                )
        if rev == asset["revision"]:
            require(
                manifest["derivations"]["active_ids_for_revision"]
                == [ledger["events"][0]["derivation_id"]],
                "Wiki derivation missing",
            )
    return revisions


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    repo = Path(__file__).resolve().parents[1]
    report["audit_sources"] = {
        name: digest((repo / name).read_bytes())
        for name in (
            "tests/codex_pdf_fields.py",
            "tests/codex_pdf_fields_audit.py",
            "tests/codex_pdf_fields_checks.py",
            "tests/unit/test_codex_pdf_fields_audit.py",
        )
    }
    (output / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    report = write_audit(parser.parse_args().output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
