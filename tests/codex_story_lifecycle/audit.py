"""Independent package, immutable evidence and actual Agent page-review audit."""

from __future__ import annotations

import argparse
import json
import posixpath
from pathlib import Path

from lxml import etree

from tests.codex_docx_grid.audit import validate_receipt
from tests.codex_docx_stories.audit import package, text_paths, xml
from tests.codex_docx_structure.fonts import environment
from tests.codex_docx_structure.renders import validate_renders
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors
from tests.native_docx_stories_helpers import HEADER_PART
from tests.native_docx_story_lifecycle_helpers import (
    DOC_REL,
    NEW_FOOTER,
    NEW_HEADER,
    OBSOLETE,
    TYPES,
    W,
    assert_native_stages,
    inspect_pages,
    structure_edits,
    text_edit,
)

REQUIRED = {
    "contract",
    "contract_details",
    "register",
    "read_docx_story_structure",
    "read_docx_story",
    "update_docx_story_structure",
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
    "inspect",
    "list",
    "read_docx",
    "read_docx_block",
    "read_docx_stories",
}


def intent_bytes(value):
    """JSON numbers 9 and 9.0 express equal intent; booleans stay distinct."""

    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(value) for key, value in item.items()}
        if isinstance(item, list):
            return [normalize(value) for value in item]
        if type(item) is float and item.is_integer():
            return int(item)
        return item

    return canonical(normalize(value))


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
        "Missing lifecycle workflow",
    )
    return calls


def independent_catalog(data):
    parts = package(data)
    kinds = {}
    for node in etree.fromstring(parts["[Content_Types].xml"]).findall(
        TYPES + "Override"
    ):
        kind = node.get("ContentType", "").split("wordprocessingml.")[-1]
        if kind in {"header+xml", "footer+xml"}:
            kinds[node.get("PartName").lstrip("/")] = kind[:-4]
    expected = (
        {HEADER_PART, "word/header1.xml", "word/footer1.xml", OBSOLETE}
        if OBSOLETE in parts
        else {
            HEADER_PART,
            "word/header1.xml",
            "word/footer1.xml",
            NEW_HEADER,
            NEW_FOOTER,
        }
    )
    require(set(kinds) == expected, "Unexpected native story inventory")
    rels = {
        n.get("Id"): posixpath.normpath("word/" + n.get("Target"))
        for n in etree.fromstring(parts["word/_rels/document.xml.rels"])
        if n.get("TargetMode") != "External"
    }
    main = etree.fromstring(parts["word/document.xml"])
    sections = main.xpath(
        "w:body/w:p/w:pPr/w:sectPr | w:body/w:sectPr", namespaces={"w": W[1:-1]}
    )
    require(len(sections) == 3, "Expected three native sections")
    settings = etree.fromstring(parts["word/settings.xml"])
    even = settings.find(W + "evenAndOddHeaders")
    even = even is not None and even.get(W + "val", "1") not in {"0", "false", "off"}
    inherited = {}
    records = []
    uses = []
    for index, section in enumerate(sections):
        first = section.find(W + "titlePg")
        first = first is not None and first.get(W + "val", "1") not in {
            "0",
            "false",
            "off",
        }
        direct = {
            (kind, n.get(W + "type")): rels[n.get("{" + DOC_REL[:-1] + "}id")]
            for kind in ["header", "footer"]
            for n in section.findall(W + kind + "Reference")
        }
        for key, part in direct.items():
            inherited[key] = part, index
        bindings = []
        for kind in ["header", "footer"]:
            for variant in ["default", "first", "even"]:
                part, origin = inherited.get((kind, variant), (None, None))
                value = {
                    "section_index": index,
                    "story_kind": kind,
                    "variant": variant,
                    "part": part,
                    "declared": (kind, variant) in direct,
                    "inherited_from": origin if origin != index else None,
                    "enabled": first
                    if variant == "first"
                    else even
                    if variant == "even"
                    else True,
                }
                bindings.append(value)
                if part:
                    uses.append(value)
        records.append(
            {
                "section_index": index,
                "different_first_page": first,
                "bindings": bindings,
            }
        )
    return {
        "even_and_odd_headers": even,
        "sections": records,
        "stories": [
            {
                "locator": {"part": part, "story_kind": kind},
                "bindings": [u for u in uses if u["part"] == part],
            }
            for part, kind in sorted(kinds.items())
        ],
    }


def check_catalog(record, data):
    for key, value in independent_catalog(data).items():
        require(
            record[key] == value, "Complete section catalog differs from native XML"
        )


def check_story(record, data, asset_id, revision):
    part = record["locator"]["part"]
    sources = package(data)
    expected = next(
        e for e in independent_catalog(data)["stories"] if e["locator"]["part"] == part
    )
    require(
        record["locator"] == expected["locator"]
        and record["bindings"] == expected["bindings"],
        "Story bindings differ",
    )
    root = etree.fromstring(sources[part])
    require(
        xml(etree.fromstring(record["xml"].encode())) == xml(root),
        "Complete native story XML differs",
    )
    require(
        record["raw_part_sha256"] == digest(sources[part]), "Story part hash differs"
    )
    nodes = text_paths(root)
    require(
        record["text_nodes"] == nodes
        and record["text"] == "\n".join(n["text"] for n in nodes),
        "Complete native text paths differ",
    )
    require(
        record["blocks"] == [{"index": i, "tag": n.tag} for i, n in enumerate(root)],
        "Story block inventory differs",
    )
    require(
        record["relationships_xml"] is None, "Unexpected story relationships in fixture"
    )
    excluded = {
        "evidence",
        "operation_result",
        "operation_receipt_policy",
        "note",
        "citation_presentation",
        "source_part_attachment",
    }
    core = {k: v for k, v in record.items() if k not in excluded}
    ref = record["evidence"]
    require(
        ref["asset_id"] == asset_id
        and ref["revision"] == revision
        and ref["locator"] == record["locator"]
        and ref["value_sha256"] == digest(canonical(core)),
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
    data = []
    for stage in history:
        raw = (root / stage["sha256"]).read_bytes()
        require(digest(raw) == stage["sha256"], "History bytes differ")
        data.append(raw)
    assert_native_stages(*data)
    require(
        (workspace / "verified.docx").read_bytes() == data[-1], "Published Word differs"
    )
    return root


def validate_reads(calls, workspace, asset):
    buffers, complete, structures, images, verified = {}, {}, {}, set(), set()
    initial, current = asset["history"][0]["sha256"], asset["revision"]
    root = workspace / "data/native-assets" / asset["asset_id"] / "revisions"
    metadata = set()
    pending = None
    writes = 0
    historical_selection = False
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {
            "read_docx_story_structure",
            "read_docx_story",
            "read_docx_stories",
            "contract_details",
        }:
            contract = op == "contract_details"
            revision = "contract" if contract else result["inspected_revision"]
            part = args.get("docx_story_part")
            if not contract:
                require(
                    args["asset_id"] == asset["asset_id"]
                    and args["revision"] == revision,
                    "Unpinned or foreign story read",
                )
            page = (
                result
                if contract
                else result["story_structure"]
                if op == "read_docx_story_structure"
                else result["story"]
            )
            key = op, revision, part, page["text_sha256"]
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
                require(page["next_text_offset"] == end, "Bad continuation")
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
                    and record["docx_story_structure_enabled"]
                    and record["docx_story_structure_policy"],
                    "Incomplete contract metadata",
                )
                metadata.add(key[-1])
                continue
            data = (root / revision).read_bytes()
            if part is not None:
                require(record["locator"]["part"] == part, "Story locator differs")
                check_story(record, data, asset["asset_id"], revision)
                validate_receipt(record, asset, revision)
                complete[revision, part] = record
                if pending == (revision, part):
                    pending = None
            elif op == "read_docx_story_structure":
                check_catalog(record["catalog"], data)
                require(
                    record["catalog_sha256"] == digest(canonical(record["catalog"])),
                    "Catalog hash differs",
                )
                validate_receipt(record, asset, revision)
                structures[revision] = record
                if pending == (revision, None):
                    pending = None
            else:
                check_catalog(record, data)
        elif op == "render_docx_page":
            revision, index = args["revision"], args["docx_page_index"]
            require(
                args["asset_id"] == asset["asset_id"]
                and result["inspected_revision"] == revision,
                "Foreign rendered story",
            )
            require(
                any(b["type"] == "image" for b in call["result"]["content"]),
                "Missing actual image",
            )
            require(result["page_count"] == 4, "Page count differs")
            images.add((revision, index))
        elif op in {"update_docx_story_structure", "update_docx_story"}:
            require(pending is None, "Previous complete receipt not read")
            revision = args["expected_revision"]
            if writes == 0:
                require(
                    metadata and initial in structures,
                    "Initial complete contract/structure missing",
                )
                parts = {
                    e["locator"]["part"]
                    for e in independent_catalog((root / initial).read_bytes())[
                        "stories"
                    ]
                }
                require(
                    all((initial, p) in complete for p in parts),
                    "Initial full stories missing",
                )
                require(
                    {(initial, i) for i in range(4)} <= images,
                    "Initial pages not reviewed",
                )
            if op == "update_docx_story_structure":
                require(
                    writes == 0 and revision == initial,
                    "Unexpected structure mutation order",
                )
                edit = args["docx_story_structure"]
                require(
                    edit["expected_catalog_sha256"]
                    == structures[revision]["catalog_sha256"]
                    and edit["scope"] == "sections_and_following_inheritors",
                    "Wrong structure precondition/scope",
                )
                require(
                    sorted(intent_bytes(e) for e in edit["edits"])
                    == sorted(
                        intent_bytes(e)
                        for e in structure_edits(
                            complete[initial, HEADER_PART],
                            complete[initial, OBSOLETE],
                            "word/footer1.xml",
                        )
                    ),
                    "Lifecycle request differs from independent intent",
                )
                pending = result["asset"]["revision"], None
            else:
                require(
                    writes == 1 and (revision, NEW_HEADER) in complete,
                    "Missing current cloned story",
                )
                require(
                    args["docx_story_reference"]
                    == complete[revision, NEW_HEADER]["evidence"]
                    and args["docx_story_update"]
                    == text_edit(complete[revision, NEW_HEADER]),
                    "Content edit differs from full current reference/intent",
                )
                pending = result["asset"]["revision"], NEW_HEADER
            writes += 1
        elif op == "read_selection":
            require(
                args["reference"] == complete[initial, OBSOLETE]["evidence"]
                and args["selection"] == {"pointer": "/text"},
                "Wrong historical deleted-story selection",
            )
            historical_selection = True
        elif op == "verify":
            require(result["valid"], "Historical verification failed")
            ref = args["reference"]
            if ref["schema_version"] == "native-docx-story-ref-v1":
                require(
                    ref == complete[initial, OBSOLETE]["evidence"],
                    "Wrong historical deleted-story reference",
                )
            verified.add(ref["schema_version"])
        elif op == "publish":
            parts = {
                e["locator"]["part"]
                for e in independent_catalog((root / current).read_bytes())["stories"]
            }
            require(
                pending is None
                and current in structures
                and all((current, p) in complete for p in parts),
                "Published without full final stories/structure",
            )
            require(
                {(current, i) for i in range(4)} <= images,
                "Final pages not reviewed before publication",
            )
            require(
                historical_selection
                and {"native-docx-story-ref-v1", "native-selection-ref-v1"} <= verified,
                "Historical deleted story/selection not verified",
            )
    require(writes == 2 and pending is None, "Unexpected or unreviewed mutations")
    return {
        "story_records": len(complete),
        "structure_records": len(structures),
        "contract_records": len(metadata),
    }


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
        parts = package(data)
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
        require(
            set(parts) == set(manifest["part_attachments"]),
            "Wiki part inventory differs",
        )
        for name, info in manifest["part_attachments"].items():
            require(
                (directory / info["attachment"]).read_bytes() == parts[name],
                "Wiki native bytes differ",
            )
        records = [
            json.loads(line)
            for line in (directory / "stories.jsonl").read_text().splitlines()
        ]
        expected = {e["locator"]["part"] for e in independent_catalog(data)["stories"]}
        require(
            len(records) == len(expected)
            and {r["locator"]["part"] for r in records} == expected,
            "Wiki story coverage differs",
        )
        for record in records:
            check_story(record, data, asset["asset_id"], revision)
            require(
                "[[" in (directory / record["note"]).read_text(), "Wiki link missing"
            )
        check_catalog(read_json(directory / "story-catalog.json"), data)
    require(
        revisions == {asset["history"][0]["sha256"], asset["revision"]},
        "Wiki historical coverage differs",
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
        pages = []
        for i, stage in enumerate(asset["history"]):
            pdf, texts = inspect_pages((root / stage["sha256"]).read_bytes(), i)
            (output / f"independent-lifecycle-{i}.pdf").write_bytes(pdf)
            pages.append(len(texts))
    # Tool images have independently replayed pixels; unchanged pages must match.
    import base64

    images = {}
    for call in calls:
        args = call["arguments"]["native_request"]
        if args["op"] == "render_docx_page":
            blob = next(
                b["data"] for b in call["result"]["content"] if b["type"] == "image"
            )
            images[args["revision"], args["docx_page_index"]] = base64.b64decode(blob)
    first = asset["history"][0]["sha256"]
    require(
        all(images[first, i] == images[asset["revision"], i] for i in [0, 1, 3]),
        "Unrelated actual pages changed",
    )
    return {
        "passed": True,
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "complete_reads": reads,
        "managed_revisions": 3,
        "historical_wikis": 2,
        "page_counts": pages,
        "renders": renders,
        "limitations": final["limitations"],
    }


def write_audit(output):
    result = audit(output)
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
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
