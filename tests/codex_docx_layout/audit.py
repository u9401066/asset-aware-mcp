"""Independent audit of actual Agent pagination correction and historical evidence."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from tests.codex_docx_grid.audit import validate_receipt
from tests.codex_docx_structure.fonts import environment
from tests.codex_docx_structure.renders import validate_renders
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.native_docx_layout_helpers import ROWS, inspect_pages

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REQUIRED = {
    "contract",
    "register",
    "read_docx",
    "read_docx_table",
    "render_docx_page",
    "update_docx_table_grid",
    "verify",
    "publish",
    "export_wiki",
    "history",
}
OPTIONAL = {"schema", "contract_details", "inspect", "list", "read_docx_block"}


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
        op = item["arguments"]["native_request"]["op"]
        require(op in REQUIRED | OPTIONAL, "Unexpected native operation")
        if not call_failed(item):
            calls.append(item)
    require(
        {c["arguments"]["native_request"]["op"] for c in calls} >= REQUIRED,
        "Missing correction workflow",
    )
    return calls


def _xml(node):
    return etree.tostring(node, method="c14n", exclusive=True)


def validate_reads(calls, workspace, asset):
    buffers, complete, tables, refs, images, counts = {}, set(), {}, set(), set(), {}
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    verified = False
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op == "read_docx":
            refs.update(canonical(b["evidence"]) for b in result["blocks"])
        if op in {"read_docx", "read_docx_table"}:
            revision = result["inspected_revision"]
            require(
                args["asset_id"] == asset["asset_id"]
                and args.get("revision") == revision,
                "Unpinned/foreign Word read",
            )
            section = result["dfm" if op == "read_docx" else "table"]
            key = (op, revision, section["text_sha256"])
            start, end = section["excerpt_char_range"]
            require(
                start == args.get("text_offset", 0)
                and end - start == len(section["text_excerpt"]),
                "Read range mismatch",
            )
            if start == 0:
                buffers[key] = ""
            require(len(buffers.get(key, "")) == start, "Missing Word chunk")
            buffers[key] += section["text_excerpt"]
            if section["next_text_offset"] is not None:
                require(section["next_text_offset"] == end, "Invalid continuation")
                continue
            text = buffers.pop(key)
            require(
                len(text) == section["text_length"]
                and digest(text.encode()) == key[-1],
                "Incomplete Word hash/length",
            )
            complete.add((op, revision))
            if op == "read_docx_table":
                record = json.loads(text)
                ref = canonical(record["evidence"])
                require(
                    record["evidence"] == args["docx_table_reference"] and ref in refs,
                    "Missing full reference binding",
                )
                validate_receipt(record, asset, revision)
                with ZipFile(root / revision) as archive:
                    table = etree.fromstring(archive.read("word/document.xml")).find(
                        W + "body/" + W + "tbl"
                    )
                require(
                    _xml(table)
                    == _xml(etree.fromstring(record["native_xml"].encode())),
                    "Table XML differs from source",
                )
                require(
                    record["rows"] == ROWS + 2 and record["columns"] == 2,
                    "Unexpected grid dimensions",
                )
                tables[ref] = record
        if op == "render_docx_page":
            revision = args["revision"]
            images.add((revision, args["docx_page_index"]))
            require(
                counts.setdefault(revision, result["page_count"])
                == result["page_count"],
                "Page count drift",
            )
        if op in {"update_docx_table_grid", "publish"}:
            revision = args["expected_revision"]
            require(
                all(
                    (kind, revision) in complete
                    for kind in ["read_docx", "read_docx_table"]
                ),
                "Mutation/publish before full read",
            )
            require(
                revision in counts
                and {(revision, i) for i in range(counts[revision])} <= images,
                "Mutation/publish before complete page review",
            )
            if op == "update_docx_table_grid":
                require(
                    canonical(args["docx_table_grid"]["reference"]) in tables,
                    "Update lacks read table reference",
                )
                refs.add(canonical(result["review_request"]["docx_table_reference"]))
        if (
            op == "verify"
            and args["reference"]["revision"] == asset["history"][0]["sha256"]
        ):
            require(
                canonical(args["reference"]) in tables
                and result["valid"]
                and not result["is_current_managed_revision"],
                "Invalid historical proof",
            )
            verified = True
    require(not buffers and verified, "Incomplete reads/historical proof")
    for stage in asset["history"]:
        require(
            all(
                (kind, stage["sha256"]) in complete
                for kind in ["read_docx", "read_docx_table"]
            ),
            "Missing revision read",
        )
    return len(tables)


def validate_history(workspace, asset, expected):
    source = workspace / "source.docx"
    require(
        digest(source.read_bytes()) == expected["source_sha256"]
        and source.stat().st_mtime_ns == expected["source_mtime_ns"],
        "Human source changed",
    )
    history = asset["history"]
    require(
        len(history) == 2
        and history[0]["sha256"] == expected["source_sha256"]
        and not asset["archived"],
        "Unexpected managed history",
    )
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    parts = []
    for stage in history:
        path = root / stage["sha256"]
        require(digest(path.read_bytes()) == stage["sha256"], "History bytes differ")
        with ZipFile(path) as archive:
            parts.append({name: archive.read(name) for name in archive.namelist()})
    require(
        parts[0].keys() == parts[1].keys()
        and all(
            parts[0][n] == parts[1][n] for n in parts[0] if n != "word/document.xml"
        ),
        "Untouched package part drift",
    )
    before, after = [etree.fromstring(p["word/document.xml"]) for p in parts]
    require(
        [_xml(c) for c in before.iter(W + "tc")]
        == [_xml(c) for c in after.iter(W + "tc")],
        "Native cell content/styles changed",
    )

    def without_layout(node):
        node = deepcopy(node)
        for row in node.find(W + "body/" + W + "tbl").findall(W + "tr"):
            pr = row.find(W + "trPr")
            if pr is None:
                continue
            for child in list(pr):
                if child.tag in {W + "trHeight", W + "cantSplit", W + "tblHeader"}:
                    pr.remove(child)
            if len(pr) == 0 and not pr.attrib and not pr.text:
                row.remove(pr)
        return _xml(node)

    require(without_layout(before) == without_layout(after), "Unrelated XML changed")
    rows = after.find(W + "body/" + W + "tbl").findall(W + "tr")
    require(
        [
            i
            for i, row in enumerate(rows)
            if row.find(W + "trPr/" + W + "tblHeader") is not None
        ]
        == [0, 1],
        "Header prefix incorrect",
    )
    for row in rows[2:]:
        height = row.find(W + "trPr/" + W + "trHeight")
        split = row.find(W + "trPr/" + W + "cantSplit")
        require(
            height is not None
            and height.get(W + "hRule") == "auto"
            and split is not None
            and split.get(W + "val") == "1",
            "Row layout differs",
        )
    changes = history[1]["result"]["changes"]
    require(
        len(changes) == 1
        and [e["op"] for e in changes[0]["edits"]]
        == ["set_header_rows", "set_row_layout"],
        "Wrong layout operations",
    )
    require(
        (workspace / "verified.docx").read_bytes()
        == (root / asset["revision"]).read_bytes(),
        "Published document differs",
    )
    return root


def validate_wikis(workspace, asset, root):
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 2, "Both historical Wiki snapshots required")
    revisions = set()
    for path in manifests:
        manifest = read_json(path)
        directory = path.parent
        require(
            manifest["asset_id"] == asset["asset_id"]
            and manifest["projection"] == "docx-blocks-v1",
            "Wiki identity/projection differs",
        )
        revision = manifest["revision"]
        revisions.add(revision)
        native = (root / revision).read_bytes()
        require(
            (directory / manifest["source_attachment"]).read_bytes() == native,
            "Wiki original attachment differs",
        )
        for name, info in manifest["files"].items():
            require(Path(name).name == name, "Unsafe Wiki attachment")
            raw = (directory / name).read_bytes()
            require(
                digest(raw) == info["sha256"] and len(raw) == info["size_bytes"],
                "Wiki file differs",
            )
        with ZipFile(root / revision) as archive:
            require(
                set(archive.namelist()) == set(manifest["part_attachments"]),
                "Wiki package coverage differs",
            )
            for name, attachment in manifest["part_attachments"].items():
                require(
                    (directory / attachment["attachment"]).read_bytes()
                    == archive.read(name),
                    "Wiki part differs",
                )
        records = [
            json.loads(line)
            for line in (directory / "records.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        require(
            any(record["kind"] == "table" for record in records), "Missing Wiki table"
        )
        for record in records:
            core = {
                k: record[k]
                for k in [
                    "schema_version",
                    "block_id",
                    "kind",
                    "locator",
                    "representation",
                ]
            }
            require(
                digest(canonical(core)) == record["evidence"]["value_sha256"],
                "Wiki evidence hash differs",
            )
            require(
                "[[" in (directory / record["note"]).read_text(encoding="utf-8"),
                "Missing Wiki links",
            )
    require(
        revisions == {h["sha256"] for h in asset["history"]},
        "Historical Wiki revision coverage differs",
    )


def audit(output):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    events = [
        json.loads(line)
        for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    calls = calls_from(events)
    asset = load_asset(workspace, final["docx_asset_id"])
    root = validate_history(workspace, asset, expected)
    count = validate_reads(calls, workspace, asset)
    validate_wikis(workspace, asset, root)
    require(
        isinstance(final.get("limitations"), list) and final["limitations"],
        "Missing limitations",
    )
    with environment(expected["font_environment"]):
        renders = validate_renders(
            workspace, asset, calls, final, {asset["history"][0]["sha256"]}
        )
        pages = []
        for i, stage in enumerate(asset["history"]):
            pdf, texts = inspect_pages(
                (root / stage["sha256"]).read_bytes(), corrected=bool(i)
            )
            (output / f"independent-layout-{i}.pdf").write_bytes(pdf)
            pages.append(len(texts))
    return {
        "passed": True,
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "complete_table_revisions": count,
        "managed_revisions": 2,
        "historical_wikis": 2,
        "before_after_page_counts": pages,
        "renders": renders,
        "limitations": final["limitations"],
    }


def write_audit(output):
    try:
        result = audit(output)
    except Exception as exc:
        result = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    result = write_audit(parser.parse_args().output)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
