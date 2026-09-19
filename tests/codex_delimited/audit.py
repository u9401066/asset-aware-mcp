"""Independent CSV bytes, scan pixels, complete readbacks and derivation history."""

import argparse
import base64
import csv
import io
import json
from pathlib import Path

from tests.codex_native_pdf.artifacts import load_asset, read_json, validate_source
from tests.codex_native_pdf.trace import canonical, complete_records, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.codex_pdf_regions.audit import region_image
from tests.codex_pptx_tables.derivations import complete_page


def expected_revisions():
    prefix = b"\xef\xbb\xbf"
    original = prefix + b"Count,Reading,Unit\r\n007,-0.50,mg/L\r\n"
    corrected = original.replace(b"007", b"008")
    inserted = corrected + "012,1.25,µg/L\n".encode()
    column = (
        prefix
        + "Count,Reading,Unit,Review\r\n008,-0.50,mg/L,checked\r\n012,1.25,µg/L,temporary\n".encode()
    )
    removed_row = column[: column.index(b"012")]
    return [original, corrected, inserted, column, removed_row, corrected]


def check_field(record, data):
    reference, locator = record["evidence"], record["locator"]
    require(reference["locator"] == locator, "Field/reference locator mismatch")
    require(
        digest(canonical({k: v for k, v in record.items() if k != "evidence"}))
        == reference["value_sha256"],
        "Field record digest mismatch",
    )
    text = data.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    value = rows[locator["row"]][locator["column"]]
    require(
        record["kind"] == "string" and record["value"] == value,
        "Field transcription/type mismatch",
    )
    raw = data[locator["byte_start"] : locator["byte_end"]]
    require(
        raw.decode()
        == record["raw"]
        == text[locator["char_start"] : locator["char_end"]],
        "Wrong byte/character field span",
    )
    require(digest(raw) == record["raw_sha256"], "Wrong raw spelling digest")


def read_chunk(result, args, buffers):
    key = (
        args["op"],
        result["asset_id"],
        result["inspected_revision"],
        result["text_sha256"],
    )
    start, end = result["excerpt_char_range"]
    require(start == args.get("text_offset", 0), "Wrong requested read offset")
    if start == 0:
        buffers[key] = ""
    require(
        key in buffers
        and len(buffers[key]) == start
        and end - start == len(result["text_excerpt"]),
        "Noncontiguous field/receipt readback",
    )
    buffers[key] += result["text_excerpt"]
    if result["next_text_offset"] is not None:
        require(result["next_text_offset"] == end, "Wrong continuation")
        return None
    text = buffers.pop(key)
    require(
        len(text) == result["text_length"] and digest(text.encode()) == key[-1],
        "Incomplete field/receipt JSON",
    )
    return json.loads(text)


def audit(output):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
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
        if item["type"] == "mcp_tool_call":
            require(
                item["server"] == "asset_aware_under_test"
                and item["tool"] == "document"
                and item["arguments"]["op"] == "native",
                "Wrong tool/server",
            )
            if not call_failed(item):
                calls.append(item)
    ops = {c["arguments"]["native_request"]["op"] for c in calls}
    require(
        {
            "contract",
            "read_pdf_region",
            "create_delimited",
            "read_delimited",
            "read_delimited_cell",
            "update_delimited",
            "record_derivation",
            "verify_derivation",
            "verify",
            "publish",
            "export_wiki",
            "history",
        }
        <= ops
        and "writeback" not in ops,
        "Incomplete workflow",
    )
    source, target = (
        load_asset(workspace, final[k]) for k in ("source_asset_id", "table_asset_id")
    )
    validate_source(workspace, expected, source)
    directory = workspace / "data" / "native-assets" / target["asset_id"]
    truth = expected_revisions()
    require(
        target["format"] == "csv"
        and target["source"] is None
        and len(target["history"]) == len(truth),
        "Wrong CSV lifecycle",
    )
    revisions = {}
    for history, wanted in zip(target["history"], truth, strict=True):
        data = (directory / "revisions" / history["sha256"]).read_bytes()
        require(data == wanted, "Intermediate CSV bytes/encoding/format differ")
        revisions[history["sha256"]] = data
    require(
        (workspace / "verified.csv").read_bytes() == truth[-1], "Published CSV changed"
    )
    original = target["history"][0]["sha256"]
    pages = complete_records(calls)
    ledger = read_json(directory / "derivations.json")
    by_id = {e["derivation_id"]: e for e in ledger["events"]}
    require(len(by_id) == 3, "Missing per-field assertions")
    prefix = {**ledger, "events": []}
    fields, regions, sizes, chunks, ledger_chunks, complete_ledgers = (
        {},
        {},
        {},
        {},
        {},
        set(),
    )
    receipts, edits, image_count = set(), [], 0
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
                    "Field identity mismatch",
                )
                check_field(record, revisions[args["revision"]])
                fields[canonical(record["evidence"])] = record
            else:
                receipt = record["operation_result"]
                require(receipt is not None, "Missing complete operation result")
                receipts.add(receipt["changes"][0]["operation"])
        elif op == "update_delimited":
            change = args["delimited_update"]
            edits.append(change["operation"])
            if change["operation"] == "set_cells":
                require(
                    all(canonical(e["reference"]) in fields for e in change["cells"]),
                    "Edit before full field read",
                )
        elif op == "read_pdf_region":
            region = result["region"]
            reference = region["evidence"]
            require(
                canonical(reference["parent"]) in pages
                and reference["parent"] == region["parent"]
                and reference["selector"] == region["selector"],
                "Missing/inconsistent full parent",
            )
            require(
                digest(canonical({k: v for k, v in region.items() if k != "evidence"}))
                == reference["value_sha256"],
                "Region digest mismatch",
            )
            images = [c for c in call["result"]["content"] if c["type"] == "image"]
            require(len(images) == 1, "Missing actual PNG")
            region_image(
                workspace,
                reference,
                result,
                args.get("render_size", 1024),
                base64.b64decode(images[0]["data"], validate=True),
            )
            regions[canonical(reference)] = region
            sizes.setdefault(canonical(reference), set()).add(
                args.get("render_size", 1024)
            )
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
                "Append before full ledger read",
            )
            event = by_id[result["derivation_id"]]
            require(
                canonical(event["derivation"]["target"]) in fields
                and all(
                    canonical(ref) in regions for ref in event["derivation"]["sources"]
                ),
                "Assertion before field/image review",
            )
            prefix["events"].append(event)
    operations = [
        "set_cells",
        "insert_rows",
        "insert_column",
        "delete_rows",
        "delete_columns",
    ]
    require(
        edits == operations and set(operations) | {"create_delimited"} <= receipts,
        "Missing ordered CRUD/complete receipts",
    )
    require(
        not chunks
        and not ledger_chunks
        and prefix == ledger
        and digest(canonical(ledger)) in complete_ledgers,
        "Incomplete readbacks",
    )
    require(
        len(regions) == 3 and any({256, 384} <= s for s in sizes.values()),
        "Missing region/detail review",
    )
    for revision in (original, target["revision"]):
        read = {
            (f["locator"]["row"], f["locator"]["column"])
            for f in fields.values()
            if f["evidence"]["revision"] == revision
        }
        require(
            {(r, c) for r in range(2) for c in range(3)} <= read,
            "Missing six complete original/final fields",
        )
    columns = set()
    glyphs = [(153, 202, 181, 216), (233, 202, 266, 216), (363, 202, 393, 216)]
    for event in ledger["events"]:
        claim = event["derivation"]
        require(
            len(claim["sources"]) == 1
            and claim["target"]["revision"] == original
            and claim["target"]["locator"]["row"] == 1,
            "Migrated/ambiguous assertion",
        )
        column = claim["target"]["locator"]["column"]
        require(column in range(3), "Wrong data field")
        columns.add(column)
        ref = claim["sources"][0]
        require(ref["revision"] == expected["source_sha256"], "Wrong source revision")
        x0, y0, x1, y1 = ref["selector"]["rect"]
        gx0, gy0, gx1, gy1 = glyphs[column]
        require(
            x0 * 612 <= gx0
            and y0 * 792 <= gy0
            and x1 * 612 >= gx1
            and y1 * 792 >= gy1
            and (x1 - x0) * 612 < 145
            and (y1 - y0) * 792 < 70,
            "Wrong/clipped glyph region",
        )
    require(columns == {0, 1, 2}, "Missing distinct per-field evidence")
    proofs = [
        payload(c)
        for c in calls
        if c["arguments"]["native_request"]["op"] == "verify_derivation"
    ]
    require(
        {p["derivation_id"] for p in proofs if p["active"] and p["references_valid"]}
        == set(by_id),
        "Missing derivation proofs",
    )
    require(
        any(
            c["arguments"]["native_request"]["op"] == "verify"
            and payload(c)["valid"]
            and not payload(c)["is_current_managed_revision"]
            for c in calls
        ),
        "Missing historical proof",
    )
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 2, "Missing Wiki snapshots")
    for path in manifests:
        manifest = read_json(path)
        current = manifest["revision"] == target["revision"]
        require(
            manifest["representation"] == "delimited_fields"
            and manifest["cell_count"] == 6,
            "Wrong field Wiki",
        )
        require(
            (path.parent / manifest["source_attachment"]).read_bytes()
            == revisions[manifest["revision"]],
            "Wiki CSV bytes changed",
        )
        for name, info in manifest["files"].items():
            data = (path.parent / name).read_bytes()
            require(
                digest(data) == info["sha256"] and len(data) == info["size_bytes"],
                "Wiki artifact digest mismatch",
            )
        info = manifest["derivations"]
        require(
            len(info["active_ids_for_revision"]) == (0 if current else 3),
            "Inherited/lost assertions",
        )
        for line in (path.parent / "records.jsonl").read_text().splitlines():
            record = json.loads(line)
            require(
                canonical(record["evidence"]) in fields
                and "row " in record["citation_presentation"]["inline"],
                "Wiki field/citation mismatch",
            )
        if not current:
            require(
                len(info["region_records"]) == 3, "Missing portable region evidence"
            )
            for entry in info["region_records"].values():
                stored = read_json(path.parent / entry["record_file"])
                require(
                    digest((path.parent / stored["source_attachment"]).read_bytes())
                    == expected["source_sha256"],
                    "Wiki PDF bytes changed",
                )
                region_image(
                    workspace,
                    entry["reference"],
                    {"image_sha256": entry["preview_sha256"]},
                    768,
                    (path.parent / entry["preview_attachment"]).read_bytes(),
                )
        else:
            require("region_records" not in info, "Inherited region records")
    return {
        "passed": True,
        "successful_native_calls": len(calls),
        "actual_region_images": image_count,
        "intermediate_csv_revisions": len(truth),
        "distinct_regions": 3,
        "derivations": 3,
        "errors": tool_errors(events),
        "limitations": [
            "Synthetic scan and CSV fixture; no arbitrary-document fidelity claim.",
            "Semantic review is caller supplied; this auditor checks known values, glyph coverage and native bytes.",
        ],
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    result = write_audit(parser.parse_args().output.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
