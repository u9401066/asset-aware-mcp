"""Independent actual ETL trace, original pixels, native cells and Wiki audit."""

import argparse
import base64
import io
import json
from pathlib import Path

import pymupdf
from openpyxl import load_workbook
from PIL import Image, ImageChops

from tests.codex_csl.audit import readback
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require, tool_errors


def native_arguments(args):
    request = args["native_request"]
    require(
        request["op"] in {"contract", "schema", "create", "read_cell"},
        "Unexpected native mutation",
    )
    return request


def page_image(item, expected_hash):
    blocks = [b for b in item["result"]["content"] if b["type"] == "image"]
    require(
        len(blocks) == 1 and blocks[0]["mimeType"] == "image/png",
        "No actual PNG response",
    )
    raw = base64.b64decode(blocks[0]["data"], validate=True)
    require(digest(raw) == expected_hash, "Image hash differs")
    return raw


def inventory(root):
    manifest = read_json(root / "manifest.json")
    require(
        {p.name for p in root.iterdir()} == {"manifest.json", *manifest["files"]},
        "Snapshot inventory differs",
    )
    for name, item in manifest["files"].items():
        require(Path(name).name == name, "Nonportable artifact name")
        data = (root / name).read_bytes()
        require(
            digest(data) == item["sha256"] and len(data) == item["size_bytes"],
            "Artifact bytes differ",
        )
    return manifest


def check_citations(result, references, cell, expected):
    doc = result["document"]
    require(
        doc["style"] == "apa" and doc["locale"] == "en-US" and not doc["uncited_ids"],
        "Citation configuration differs",
    )
    require(
        doc["items"]
        == [
            {
                "id": "book",
                "type": "book",
                "title": "Measured Evidence",
                "author": [{"given": "Jane", "family": "Doe"}],
                "issued": {"date-parts": [[2020]]},
                "publisher": "Example Press",
            }
        ],
        "Bibliographic transcription differs",
    )
    require(len(doc["clusters"]) == 1, "Wrong citation cluster count")
    cluster = doc["clusters"][0]
    require(
        cluster["id"] == "c1"
        and cluster["note_index"] == 0
        and len(cluster["cites"]) == 1,
        "Wrong cluster context",
    )
    cite = cluster["cites"][0]
    require(
        cite["id"] == "book"
        and cite["source_keys"] == ["span", "table", "figure", "native"]
        and cite["locator"] is None
        and not cite["prefix"]
        and not cite["suffix"]
        and not cite["suppress_author"],
        "Wrong citation binding",
    )
    require(doc["sources"] == {**references, "native": cell}, "Wrong source references")
    require(
        [c["text"] for c in result["citations"]] == ["(Doe, 2020)"],
        "Wrong inline citation",
    )
    require(
        [b["text"] for b in result["bibliography"]]
        == ["Doe, J. (2020). Measured Evidence. Example Press.\n"],
        "Wrong full bibliography",
    )
    require(
        not result["warnings"] and not result["missing_metadata"],
        "Unexpected metadata warning",
    )
    for key, ref in doc["sources"].items():
        source = result["sources"][key]
        require(
            source["reference"] == ref
            and source["verification"]["valid"]
            and source["semantic_support"] == "not_checked",
            "Verification scope differs",
        )
        if key != "native":
            require(
                source["verification"]["verification_scope"]
                == "immutable_captured_extraction",
                "Wrong ETL scope",
            )
    require(
        result["resources"]["manifest_sha256"] == expected["csl_manifest_sha256"]
        and result["resources"]["worker_sha256"] == expected["csl_worker_sha256"],
        "Wrong CSL resources",
    )


def audit(output):
    expected, final = (
        read_json(output / "expected.json"),
        read_json(output / "last-message.txt"),
    )
    workspace = output / "workspace"
    source = workspace / "source.pdf"
    original = source.read_bytes()
    require(
        digest(original) == expected["source_sha256"]
        and source.stat().st_mtime_ns == expected["source_mtime_ns"],
        "Human PDF changed",
    )
    asset = load_asset(workspace, final["workbook_asset_id"])
    require(
        asset["format"] == "xlsx" and len(asset["history"]) == 1,
        "Unexpected workbook mutation",
    )
    workbook_bytes = (
        workspace
        / "data/native-assets"
        / asset["asset_id"]
        / "revisions"
        / asset["revision"]
    ).read_bytes()
    workbook = load_workbook(io.BytesIO(workbook_bytes))
    require(
        workbook["Sheet1"]["A1"].value == "007"
        and workbook["Sheet1"]["A1"].data_type == "s",
        "Lost leading-zero string",
    )
    workbook.close()
    events = [
        json.loads(line)
        for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete Codex turn")
    calls, completed, buffers, images, references = [], [], {}, [], {}
    deleted, cell, reused = False, None, False
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
            and item["tool"] in {"document", "evidence", "get_job_status"},
            "Unexpected tool/server",
        )
        if call_failed(item):
            continue
        calls.append(item)
        args = item["arguments"]
        op = args.get("op", "get_job_status")
        if item["tool"] == "document":
            if op == "delete":
                require(args["doc_id"] == final["doc_id"], "Wrong deleted document")
                deleted = True
                continue
            if op != "native":
                require(
                    op in {"preflight", "ingest", "inspect"},
                    "Unexpected document action",
                )
                continue
            args = native_arguments(args)
            op = args["op"]
        if item["tool"] == "get_job_status" or op == "find":
            continue
        result = payload(item)
        if op == "read_cell":
            record = result["cell"]
            require(
                record["value_excerpt"] == "007"
                and record["representation_complete"]
                and record["next_text_offset"] is None
                and record["value_text_sha256"] == digest(b"007"),
                "Incomplete cell readback",
            )
            cell = record["evidence"]
            require(
                cell["asset_id"] == asset["asset_id"]
                and cell["revision"] == asset["revision"],
                "Wrong native cell binding",
            )
        if op == "view_etl_source":
            ref = args["ref"]
            require(
                result["reference"] == ref and result["source_page"] == 1,
                "Wrong captured page",
            )
            raw = page_image(item, result["image_sha256"])
            with pymupdf.open(stream=original, filetype="pdf") as pdf:
                page = pdf[0]
                scale = args.get("render_size", 1024) / max(
                    page.rect.width, page.rect.height
                )
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=True
                )
            actual = Image.open(io.BytesIO(raw)).convert("RGB")
            truth = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            require(
                actual.size == truth.size
                and ImageChops.difference(actual, truth).getbbox() is None,
                "Original-page pixels differ",
            )
            images.append((ref["source_type"], deleted))
        complete = readback(result, op, item["tool"], args, buffers)
        if complete is not None:
            completed.append((*complete, deleted))
            if op == "capture_etl_source":
                reference = complete[2]["reference"]
                references[reference["source_type"]] = reference
        if op == "render_citations" and deleted:
            require(
                args.get("expected_text_sha256") == result["text_sha256"],
                "Unpinned historical publication",
            )
            reused |= result.get("publication", {}).get("reused", False)
    require(not buffers, "Unfinished paged read")
    require(
        deleted and not (workspace / "data" / final["doc_id"]).exists(),
        "ETL data was not deleted",
    )
    require(
        cell is not None and set(references) == {"span", "table", "figure"},
        "Missing full references",
    )
    require(
        {(kind, old) for kind in references for old in (False, True)} <= set(images),
        "Missing initial/historical actual PNGs",
    )
    require(
        any(op == "csl_contract" for op, _, _, _ in completed),
        "Incomplete CSL contract",
    )
    for kind, reference in references.items():
        root = (
            workspace / "data/citation-sources" / ("native-" + reference["snapshot_id"])
        )
        manifest = inventory(root)
        require(
            digest((root / "manifest.json").read_bytes()) == reference["snapshot_id"],
            "Snapshot identity differs",
        )
        record = read_json(root / "evidence.json")
        require(
            digest((root / "evidence.json").read_bytes())
            == reference["record_sha256"]
            == manifest["record_sha256"],
            "Record hash differs",
        )
        require(
            (root / "original.pdf").read_bytes() == original
            and record["source_identity"]["source_sha256"] == expected["source_sha256"],
            "Captured source differs",
        )
        require(
            record["source_reference"]["source_type"] == kind
            and record["source_reference"]["doc_id"] == final["doc_id"]
            and record["verification"]["valid"],
            "Captured evidence identity differs",
        )
        if kind == "span":
            require(
                "Observed count" in record["source_reference"]["quote"],
                "Wrong captured text span",
            )
        if kind == "table":
            require("007" in record["evidence"]["markdown"], "Wrong captured table")
        if kind == "figure":
            require(
                any(p.name.startswith("figure.") for p in root.iterdir()),
                "Missing captured figure",
            )
        require(
            any(
                op == "inspect_etl_source"
                and value["asset_ref"] == record["source_reference"]
                and value["record"] == record
                for op, _, value, _ in completed
            ),
            "Incomplete source inspection",
        )
        for old in (False, True):
            require(
                any(
                    op == "read_etl_source"
                    and historical == old
                    and value == {"reference": reference, "record": record}
                    for op, _, value, historical in completed
                ),
                "Missing exact full initial/historical evidence read",
            )
    wikis = list((workspace / "citation-wiki").glob("*/manifest.json"))
    require(len(wikis) == 1 and reused, "Wiki was not reused unchanged")
    root = wikis[0].parent
    require(root == Path(final["wiki_dir"]), "Reported Wiki differs")
    inventory(root)
    result = read_json(root / "citations.json")
    check_citations(result, references, cell, expected)
    sha = digest((root / "citations.json").read_bytes())
    renders = [
        (value, old)
        for op, value_sha, value, old in completed
        if op == "render_citations" and value_sha == sha
    ]
    require(
        sum(not old for _, old in renders) >= 2 and any(old for _, old in renders),
        "Missing complete preview/export/historical rendering",
    )
    require(
        all(canonical(value) == canonical(result) for value, _ in renders),
        "Rendering changed",
    )
    for kind, reference in references.items():
        snapshot = (
            workspace / "data/citation-sources" / ("native-" + reference["snapshot_id"])
        )
        attachments = result["sources"][kind]["snapshot_artifacts"]
        require(
            set(attachments) == {p.name for p in snapshot.iterdir()},
            "Incomplete portable snapshot",
        )
        for name, attachment in attachments.items():
            require(
                (root / attachment["name"]).read_bytes()
                == (snapshot / name).read_bytes(),
                "Portable evidence differs",
            )
    require(
        (root / result["sources"]["native"]["attachment"]["name"]).read_bytes()
        == workbook_bytes,
        "Portable native source differs",
    )
    return {
        "passed": True,
        "successful_mcp_calls": len(calls),
        "actual_pdf_images": len(images),
        "etl_snapshots": len(references),
        "citation_snapshots": len(wikis),
        "tool_errors": tool_errors(events),
        "limitations": [
            "Synthetic one-page fixture, not arbitrary extraction fidelity.",
            "Hashes verify captured artifacts; semantic and bibliographic review belongs to the Agent.",
        ],
    }


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(write_audit(args.output), ensure_ascii=False))
