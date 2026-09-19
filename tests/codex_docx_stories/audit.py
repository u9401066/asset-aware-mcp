"""Independent audit of native story XML, complete reads and actual Agent review."""

from __future__ import annotations

import argparse
import io
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
from tests.native_docx_stories_helpers import (
    ADDED_TEXT,
    HEADER_CORRECTED,
    HEADER_PART,
    HEADER_TEXT,
    inspect_story_pages,
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PARTS = {HEADER_PART, "word/header1.xml", "word/footer1.xml"}
REQUIRED = {
    "contract",
    "register",
    "read_docx_stories",
    "read_docx_story",
    "update_docx_story",
    "render_docx_page",
    "verify",
    "read_selection",
    "publish",
    "export_wiki",
    "history",
}
OPTIONAL = {
    "schema",
    "contract_details",
    "inspect",
    "list",
    "read_docx",
    "read_docx_block",
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
        "Missing story workflow",
    )
    return calls


def xml(node):
    return etree.tostring(node, method="c14n", exclusive=True)


def package(data):
    with ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def text_paths(root):
    result = []

    def visit(node, path):
        if node.tag == W + "t":
            result.append({"path": path, "text": node.text or ""})
        for index, child in enumerate(node):
            visit(child, [*path, index])

    visit(root, [])
    return result


def check_story(record, data, asset_id, revision):
    part = record["locator"]["part"]
    require(part in PARTS, "Unexpected story part")
    source = package(data)[part]
    root = etree.fromstring(source)
    require(
        xml(etree.fromstring(record["xml"].encode())) == xml(root),
        "Complete native story XML differs",
    )
    require(record["raw_part_sha256"] == digest(source), "Story part hash differs")
    nodes = text_paths(root)
    require(
        record["text_nodes"] == nodes
        and record["text"] == "\n".join(n["text"] for n in nodes),
        "Complete native text paths differ",
    )
    kind = "footer" if part == "word/footer1.xml" else "header"
    variant = "first" if part == "word/header1.xml" else "default"
    expected = [
        {
            "section_index": i,
            "story_kind": kind,
            "variant": variant,
            "part": part,
            "declared": i == 0,
            "inherited_from": None if i == 0 else 0,
            "enabled": i == 0 or variant == "default",
        }
        for i in range(2)
    ]
    require(record["bindings"] == expected, "Shared/inherited section bindings differ")
    excluded = {
        "evidence",
        "operation_result",
        "operation_receipt_policy",
        "note",
        "citation_presentation",
        "source_part_attachment",
    }
    core = {k: v for k, v in record.items() if k not in excluded}
    reference = record["evidence"]
    require(
        reference["asset_id"] == asset_id
        and reference["revision"] == revision
        and reference["locator"] == record["locator"]
        and reference["value_sha256"] == digest(canonical(core)),
        "Story reference identity/hash differs",
    )


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
        "Unexpected managed history",
    )
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    parts = []
    for stage in history:
        data = (root / stage["sha256"]).read_bytes()
        require(digest(data) == stage["sha256"], "History bytes differ")
        parts.append(package(data))
    for before, after, changed in [
        (parts[0], parts[1], HEADER_PART),
        (parts[1], parts[2], "word/footer1.xml"),
    ]:
        require(
            before.keys() == after.keys()
            and all(before[p] == after[p] for p in before if p != changed),
            "Unrelated native part changed",
        )
    before = etree.fromstring(parts[0][HEADER_PART])
    after = etree.fromstring(parts[1][HEADER_PART])
    require(len(before) == len(after) == 3, "Header block inventory differs")
    require(
        after[0].find(".//" + W + "t").text == HEADER_CORRECTED,
        "Long header text differs",
    )
    require(
        "".join(after[2].itertext()) == ADDED_TEXT, "Inserted header paragraph differs"
    )
    restored = deepcopy(after)
    restored[0].find(".//" + W + "t").text = HEADER_TEXT
    restored.remove(restored[2])
    restored.append(deepcopy(before[2]))
    require(xml(restored) == xml(before), "Native header runs/styles/table changed")
    before = etree.fromstring(parts[0]["word/footer1.xml"])
    after = etree.fromstring(parts[2]["word/footer1.xml"])
    require(
        after.find(".//" + W + "t").text == "Verified page ", "Footer prefix differs"
    )
    after.find(".//" + W + "t").text = "Page "
    require(xml(after) == xml(before), "Native footer field/cache/style changed")
    require(
        (workspace / "verified.docx").read_bytes()
        == (root / asset["revision"]).read_bytes(),
        "Published Word differs",
    )
    return root


def validate_reads(calls, workspace, asset):
    buffers, complete, refs, counts, images = {}, {}, set(), {}, set()
    catalogs, verified = set(), set()
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    initial, current = asset["history"][0]["sha256"], asset["revision"]
    pending = None
    writes = 0
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {"read_docx_stories", "read_docx_story"}:
            revision = result["inspected_revision"]
            require(
                args["asset_id"] == asset["asset_id"]
                and args.get("revision") == revision,
                "Unpinned or foreign story read",
            )
            part = args.get("docx_story_part")
            page = result["story"]
            key = (op, revision, part, page["text_sha256"])
            start, end = page["excerpt_char_range"]
            require(
                start == args.get("text_offset", 0)
                and end - start == len(page["text_excerpt"]),
                "Read range differs",
            )
            if start == 0:
                buffers[key] = ""
            require(len(buffers.get(key, "")) == start, "Missing story chunk")
            buffers[key] += page["text_excerpt"]
            if page["next_text_offset"] is not None:
                require(page["next_text_offset"] == end, "Bad continuation")
                continue
            text = buffers.pop(key)
            require(
                len(text) == page["text_length"] and digest(text.encode()) == key[-1],
                "Incomplete story hash/length",
            )
            record = json.loads(text)
            if part is None:
                require(
                    {s["locator"]["part"] for s in record["stories"]} == PARTS
                    and len(record["sections"]) == 2,
                    "Incomplete story catalog",
                )
                catalogs.add(revision)
            else:
                require(record["locator"]["part"] == part, "Story locator differs")
                check_story(
                    record, (root / revision).read_bytes(), asset["asset_id"], revision
                )
                validate_receipt(record, asset, revision)
                complete[revision, part] = record
                refs.add(canonical(record["evidence"]))
                if pending == (revision, part):
                    pending = None
        elif op == "render_docx_page":
            revision, index = args["revision"], args["docx_page_index"]
            require(
                args["asset_id"] == asset["asset_id"]
                and result["inspected_revision"] == revision,
                "Foreign rendered story",
            )
            require(
                any(c["type"] == "image" for c in call["result"]["content"]),
                "Missing actual image",
            )
            require(
                counts.setdefault(revision, result["page_count"])
                == result["page_count"]
                == 3,
                "Page count differs",
            )
            images.add((revision, index))
        elif op == "update_docx_story":
            require(pending is None, "Previous story receipt not read")
            part = args["docx_story_update"]["part"]
            revision = args["expected_revision"]
            require(
                (revision, part) in complete
                and canonical(args["docx_story_reference"]) in refs,
                "Missing complete current story reference",
            )
            require(
                args["docx_story_reference"] == complete[revision, part]["evidence"],
                "Edit reference differs",
            )
            require(
                args["docx_story_update"]["shared_scope"] == "all_sections_using_part",
                "Implicit shared edit",
            )
            if writes == 0:
                require(
                    initial in catalogs
                    and all((initial, p) in complete for p in PARTS),
                    "Initial full stories missing",
                )
                require(
                    {(initial, i) for i in range(3)} <= images,
                    "Initial pages not reviewed",
                )
            writes += 1
            pending = result["asset"]["revision"], part
        elif op == "verify":
            require(result["valid"], "Historical reference verification failed")
            verified.add(args["reference"]["schema_version"])
        elif op == "publish":
            require(
                pending is None
                and current in catalogs
                and all((current, p) in complete for p in PARTS),
                "Published without complete final stories",
            )
            require(
                {(current, i) for i in range(3)} <= images,
                "Final pages not reviewed before publication",
            )
            require(
                {"native-docx-story-ref-v1", "native-selection-ref-v1"} <= verified,
                "Historical story/selection not verified",
            )
    require(writes == 2 and pending is None, "Unexpected or unreviewed story edits")
    return len(complete)


def validate_wikis(workspace, asset, root):
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 2, "Both historical Wikis required")
    revisions = set()
    for path in manifests:
        manifest, directory = read_json(path), path.parent
        revision = manifest["revision"]
        revisions.add(revision)
        require(
            manifest["asset_id"] == asset["asset_id"]
            and manifest["projection"] == "docx-stories-v1",
            "Wiki identity/projection differs",
        )
        data = (root / revision).read_bytes()
        require(
            (directory / manifest["source_attachment"]).read_bytes() == data,
            "Wiki original differs",
        )
        require(
            {p.name for p in directory.iterdir() if p.is_file()}
            == set(manifest["files"]) | {"manifest.json"},
            "Wiki file inventory differs",
        )
        for name, info in manifest["files"].items():
            require(Path(name).name == name, "Unsafe Wiki file")
            raw = (directory / name).read_bytes()
            require(
                digest(raw) == info["sha256"] and len(raw) == info["size_bytes"],
                "Wiki file hash differs",
            )
        parts = package(data)
        require(
            set(parts) == set(manifest["part_attachments"]),
            "Wiki native part inventory differs",
        )
        for name, info in manifest["part_attachments"].items():
            require(
                (directory / info["attachment"]).read_bytes() == parts[name],
                "Wiki part bytes differ",
            )
        records = [
            json.loads(line)
            for line in (directory / "stories.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        require(
            len(records) == 3 and {r["locator"]["part"] for r in records} == PARTS,
            "Wiki story coverage differs",
        )
        for record in records:
            check_story(record, data, asset["asset_id"], revision)
            require(
                "[[" in (directory / record["note"]).read_text(encoding="utf-8"),
                "Wiki link missing",
            )
        catalog = read_json(directory / "story-catalog.json")
        require(
            {s["locator"]["part"] for s in catalog["stories"]} == PARTS,
            "Wiki story catalog differs",
        )
    require(
        revisions == {asset["history"][0]["sha256"], asset["revision"]},
        "Wiki historical revision coverage differs",
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
    complete = validate_reads(calls, workspace, asset)
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
            pdf, texts = inspect_story_pages((root / stage["sha256"]).read_bytes(), i)
            (output / f"independent-story-{i}.pdf").write_bytes(pdf)
            pages.append(len(texts))
    return {
        "passed": True,
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "complete_story_records": complete,
        "managed_revisions": 3,
        "historical_wikis": 2,
        "page_counts": pages,
        "renders": renders,
        "limitations": final["limitations"],
    }


def write_audit(output):
    result = audit(output)
    (output / "audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(
        json.dumps(
            write_audit(parser.parse_args().output), ensure_ascii=False, indent=2
        )
    )


if __name__ == "__main__":
    main()
