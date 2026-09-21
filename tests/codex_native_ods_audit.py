"""Independent ODS XML/ZIP, canonical reference, readback and snapshot audit."""

import io
import json
import zipfile
from pathlib import Path

from lxml import etree as ET

from tests.codex_delimited.audit import read_chunk
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


def attr(prefix, name):
    return "{" + NS[prefix] + "}" + name


def parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def xml_cells(data):
    root = ET.fromstring(
        parts(data)["content.xml"],
        parser=ET.XMLParser(resolve_entities=False, no_network=True),
    )
    result = {}
    for index, table in enumerate(
        root.findall("office:body/office:spreadsheet/table:table", NS)
    ):
        row_index = 0
        for row in table.findall("table:table-row", NS):
            repeat_rows = int(row.get(attr("table", "number-rows-repeated"), "1"))
            require(repeat_rows <= 10, "Unexpected fixture row expansion")
            column_index = 0
            for cell in row.findall("table:table-cell", NS):
                repeat_columns = int(
                    cell.get(attr("table", "number-columns-repeated"), "1")
                )
                require(repeat_columns <= 10, "Unexpected fixture column expansion")
                for r in range(row_index, row_index + repeat_rows):
                    for c in range(column_index, column_index + repeat_columns):
                        result[index, table.get(attr("table", "name")), r, c] = dict(
                            cell.attrib
                        )
                column_index += repeat_columns
            row_index += repeat_rows
    return result


def audit(output):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    source_path = workspace / "source.ods"
    source_bytes = source_path.read_bytes()
    require(
        digest(source_bytes) == expected["source_sha256"]
        and source_path.stat().st_mtime_ns == expected["source_mtime_ns"],
        "Source changed",
    )
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
            item["type"] in {"reasoning", "agent_message", "plan", "mcp_tool_call"},
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
            "register",
            "create_ods",
            "read_ods",
            "read_ods_cell",
            "update_ods",
            "read_selection",
            "verify",
            "record_derivation",
            "verify_derivation",
            "export_wiki",
            "publish",
            "history",
        }
        <= ops,
        "Incomplete ODS workflow",
    )
    require(not ({"writeback", "archive"} & ops), "Unexpected source mutation")
    if expected.get("inspection_required"):
        require("inspect" in ops, "ODS inspection not exercised")
    assets = {
        key: load_asset(workspace, final[key])
        for key in ("source_asset_id", "table_asset_id")
    }
    source, target = assets.values()
    require(
        source["format"] == target["format"] == "ods" and target["source"] is None,
        "Wrong source identity",
    )
    require(
        len(source["history"]) == 3 and len(target["history"]) == 2,
        "Wrong revision counts",
    )
    revisions = {}
    for asset in assets.values():
        for entry in asset["history"]:
            data = (
                workspace
                / "data"
                / "native-assets"
                / asset["asset_id"]
                / "revisions"
                / entry["sha256"]
            ).read_bytes()
            revisions[asset["asset_id"], entry["sha256"]] = data
    for index, entry in enumerate(source["history"]):
        data = revisions[source["asset_id"], entry["sha256"]]
        for name, original in parts(source_bytes).items():
            if name != "content.xml":
                require(parts(data)[name] == original, "Untouched member changed")
        cells = xml_cells(data)
        require(len(cells) == 11, "Changed logical coverage")
        for row in range(4):
            for col in range(2):
                attributes = cells[0, "Sheet1", row, col]
                value = (
                    None
                    if index == 2 and (row, col) == (0, 0)
                    else "008"
                    if index and (row, col) == (3, 1)
                    else "007"
                )
                require(
                    attributes.get(attr("office", "string-value")) == value,
                    "Wrong exact string",
                )
                require(attributes[attr("table", "style-name")] == "kept", "Lost style")
        formula = cells[0, "Sheet1", 4, 2]
        require(formula[attr("table", "formula")] == "of:=[.A1]*2", "Formula altered")
        require(
            formula.get(attr("office", "value")) == ("14" if index == 0 else None),
            "Wrong cache invalidation",
        )
    require(
        xml_cells(revisions[target["asset_id"], target["revision"]])[
            0, "Evidence", 0, 0
        ][attr("office", "string-value")]
        == "007",
        "Lost leading zeros",
    )
    buffers, complete_reads, read_receipts, wiki_count, ref_count = {}, [], set(), 0, 0
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] == "inspect":
            require(
                result["content"]["read_operation"] == "read_ods"
                and result["asset"]["capabilities"]["edit_constraints"],
                "ODS discovery inconsistent",
            )
        if args["op"] in {"read_ods", "read_ods_cell"}:
            if args.get("text_offset", 0):
                require(
                    args.get("ods_text_sha256") == result["text_sha256"],
                    "Unpinned continuation",
                )
            record = read_chunk(result, args, buffers)
            if record is None:
                continue
            complete_reads.append(record)
            if args["op"] == "read_ods":
                asset = next(
                    a for a in assets.values() if a["asset_id"] == args["asset_id"]
                )
                history = next(
                    h
                    for h in reversed(asset["history"])
                    if h["sha256"] == args["revision"]
                )
                require(
                    record["operation_result"] == history.get("result"),
                    "Incomplete or wrong operation receipt",
                )
                read_receipts.add((asset["asset_id"], history["sha256"]))
            else:
                cell = record["cell"]
                ref = cell["evidence"]
                require(
                    (ref["asset_id"], ref["revision"], ref["locator"])
                    == (args["asset_id"], args["revision"], args["ods_locator"]),
                    "Read reference was rebound",
                )
                require(
                    cell["cached_value_verified"] is False,
                    "Formula result falsely verified",
                )
                require(
                    digest(
                        canonical({k: v for k, v in cell.items() if k != "evidence"})
                    )
                    == ref["value_sha256"],
                    "Wrong cell hash",
                )
                loc = ref["locator"]
                actual = xml_cells(revisions[ref["asset_id"], ref["revision"]]).get(
                    (loc["table_index"], loc["table_name"], loc["row"], loc["column"])
                )
                require(
                    cell["attributes"] == (actual or {})
                    and cell["present"] == (actual is not None),
                    "Cell differs from independent XML",
                )
                ref_count += 1
        if args["op"] == "export_wiki":
            root = Path(result["output_dir"])
            manifest = read_json(root / "manifest.json")
            for name, info in manifest["files"].items():
                data = (root / name).read_bytes()
                require(
                    digest(data) == info["sha256"] and len(data) == info["size_bytes"],
                    "Wiki artifact mismatch",
                )
            require(
                (root / manifest["source_attachment"]).read_bytes()
                == revisions[args["asset_id"], args["revision"]],
                "Wrong Wiki source",
            )
            require(
                manifest["representation"] == "ods_physical_ranges",
                "Wrong Wiki projection",
            )
            if args["asset_id"] == target["asset_id"]:
                require(
                    len(manifest["derivations"]["ods_cell_records"]) == 2,
                    "Missing exact derivation endpoints",
                )
                ledger = read_json(root / "derivations.json")
                require(len(ledger["events"]) == 1, "Wrong derivation ledger")
                claim = ledger["events"][0]["derivation"]
                require(len(claim["sources"]) == 1, "Wrong source count")
                for ref, asset, revision, table, row, col in [
                    (claim["target"], target, target["revision"], "Evidence", 0, 0),
                    (
                        claim["sources"][0],
                        source,
                        source["history"][0]["sha256"],
                        "Sheet1",
                        3,
                        1,
                    ),
                ]:
                    require(
                        ref["asset_id"] == asset["asset_id"]
                        and ref["revision"] == revision
                        and ref["locator"]
                        == {
                            "part": "content.xml",
                            "table_index": 0,
                            "table_name": table,
                            "row": row,
                            "column": col,
                        },
                        "Wrong exact derivation endpoint",
                    )
                require(
                    claim["review"]["rendered_layout"]
                    == claim["review"]["formula_results"]
                    == "not_checked",
                    "Fabricated visual or calculation review",
                )
            wiki_count += 1
    require(
        not buffers and ref_count >= 8 and wiki_count == 3,
        "Incomplete reads or snapshots",
    )
    require(
        set(revisions) <= read_receipts,
        "A revision's receipt was never read completely",
    )
    require(
        (workspace / "verified.ods").read_bytes()
        == revisions[source["asset_id"], source["revision"]],
        "Wrong published bytes",
    )
    require(final["limitations"], "Missing review boundary")
    return {
        "passed": True,
        "successful_calls": len(calls),
        "errors": tool_errors(events),
        "complete_ods_reads": len(complete_reads),
        "complete_cell_records": ref_count,
        "source_revisions": 3,
        "independent_revisions": 2,
        "wiki_snapshots": wiki_count,
        "visual_review": "not_checked",
        "formula_recalculation": "not_checked",
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    (output / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report
