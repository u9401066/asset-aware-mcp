"""Independent OOXML record and Wiki checks for the exact synthetic note fixture."""

import json
from pathlib import Path

from lxml import etree

from tests.codex_docx_stories.audit import text_paths as literal_text_paths
from tests.codex_docx_stories.audit import xml
from tests.codex_native_pdf.artifacts import read_json
from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_pdf.trace import require
from tests.native_docx_notes_helpers import END, FOOT, W, parts


def text_paths(root):
    return [
        {**node, "text_sha256": digest(node["text"].encode())}
        for node in literal_text_paths(root)
    ]


def independent_catalog(data):
    values = parts(data)
    notes, native_parts = [], []
    for part, kind in sorted([(FOOT, "footnote"), (END, "endnote")]):
        native_parts.append(
            {
                "part": part,
                "note_kind": kind,
                "linked_from_main": True,
                "raw_part_sha256": digest(values[part]),
            }
        )
        for index, node in enumerate(etree.fromstring(values[part])):
            notes.append(
                {
                    "locator": {
                        "part": part,
                        "note_kind": kind,
                        "note_id": int(node.get(W + "id")),
                    },
                    "note_type": node.get(W + "type", "normal"),
                    "part_child_index": index,
                    "note_xml_sha256": digest(
                        etree.tostring(node, encoding="unicode").encode()
                    ),
                }
            )
    main = etree.fromstring(values["word/document.xml"])
    references = []

    def visit(node, path):
        for kind, part in [("footnote", FOOT), ("endnote", END)]:
            if node.tag == W + kind + "Reference":
                identity = int(node.get(W + "id"))
                require(
                    any(
                        n["locator"]["part"] == part
                        and n["locator"]["note_id"] == identity
                        and n["note_type"] == "normal"
                        for n in notes
                    ),
                    "Dangling fixture reference",
                )
                references.append(
                    {
                        "part": "word/document.xml",
                        "path": path,
                        "note_kind": kind,
                        "note_id": identity,
                        "target_part": part,
                        "relationship_owner": "word/document.xml",
                        "main_body_reference": True,
                        "resolved_normal_note": True,
                        "xml": etree.tostring(node, encoding="unicode"),
                        "custom_mark_follows": node.get(W + "customMarkFollows"),
                    }
                )
        for i, child in enumerate(node):
            visit(child, [*path, i])

    visit(main, [])
    return {"parts": native_parts, "notes": notes, "references": references}


def check_catalog(record, data):
    for key, value in independent_catalog(data).items():
        require(record[key] == value, "Native note catalog differs: " + key)
    raw = parts(data)["word/document.xml"]
    root = etree.fromstring(raw)
    body = record["body"]
    require(
        body["part"] == "word/document.xml" and body["raw_part_sha256"] == digest(raw),
        "Body identity differs",
    )
    require(
        xml(etree.fromstring(body["xml"].encode())) == xml(root),
        "Full body XML differs",
    )
    require(
        body["text_nodes"] == text_paths(root)
        and body["text"] == "\n".join(n["text"] for n in text_paths(root)),
        "Body text/paths differ",
    )


def check_note(record, data, asset_id, revision):
    values = parts(data)
    listing = independent_catalog(data)
    entry = next(n for n in listing["notes"] if n["locator"] == record["locator"])
    for key, value in entry.items():
        require(record[key] == value, "Note identity/role/hash differs")
    part = entry["locator"]["part"]
    root = etree.fromstring(values[part])[entry["part_child_index"]]
    require(
        xml(etree.fromstring(record["xml"].encode())) == xml(root),
        "Full native note XML differs",
    )
    require(record["raw_part_sha256"] == digest(values[part]), "Note part hash differs")
    nodes = text_paths(root)
    require(
        record["text_nodes"] == nodes
        and record["text"] == "\n".join(n["text"] for n in nodes),
        "Note text/paths differ",
    )
    require(
        record["blocks"] == [{"index": i, "tag": n.tag} for i, n in enumerate(root)],
        "Note blocks differ",
    )
    require(
        record["references"]
        == [
            r
            for r in listing["references"]
            if r["target_part"] == part and r["note_id"] == entry["locator"]["note_id"]
        ],
        "Note reference binding differs",
    )
    require(
        record["relationships_xml"] is None, "Unexpected fixture note relationships"
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
    expected = {
        "schema_version": "native-docx-note-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": entry["locator"],
        "value_sha256": digest(canonical(core)),
        "verification_scope": "immutable_native_representation",
    }
    require(record["evidence"] == expected, "Note evidence differs")


def validate_wikis(workspace, asset, root):
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 2, "Expected both historical note Wikis")
    revisions = set()
    for path in manifests:
        manifest, directory = read_json(path), path.parent
        revision = manifest["revision"]
        revisions.add(revision)
        require(
            manifest["asset_id"] == asset["asset_id"]
            and manifest["projection"] == "docx-notes-v1",
            "Wiki identity differs",
        )
        data = (root / revision).read_bytes()
        values = parts(data)
        require(
            (directory / manifest["source_attachment"]).read_bytes() == data,
            "Wiki source bytes differ",
        )
        require(
            {p.name for p in directory.iterdir() if p.is_file()}
            == set(manifest["files"]) | {"manifest.json"},
            "Wiki inventory differs",
        )
        for name, info in manifest["files"].items():
            require(Path(name).name == name, "Unsafe Wiki filename")
            raw = (directory / name).read_bytes()
            require(
                digest(raw) == info["sha256"] and len(raw) == info["size_bytes"],
                "Wiki hash/size differs",
            )
        require(
            set(values) == set(manifest["part_attachments"]),
            "Wiki part inventory differs",
        )
        for name, info in manifest["part_attachments"].items():
            require(
                (directory / info["attachment"]).read_bytes() == values[name],
                "Native Wiki part bytes differ",
            )
        records = [
            json.loads(line)
            for line in (directory / "notes.jsonl").read_text().splitlines()
        ]
        expected = independent_catalog(data)["notes"]
        require(
            len(records) == len(expected)
            and {canonical(r["locator"]) for r in records}
            == {canonical(r["locator"]) for r in expected},
            "Wiki note coverage differs",
        )
        for record in records:
            check_note(record, data, asset["asset_id"], revision)
            require(
                "[[" in (directory / record["note"]).read_text(), "Missing Wiki link"
            )
        check_catalog(read_json(directory / "note-catalog.json"), data)
    require(
        revisions == {asset["history"][0]["sha256"], asset["revision"]},
        "Wiki historical coverage differs",
    )
