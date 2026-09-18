"""Independent PDF pixels, native history, exact source and wiki artifact checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

from tests.codex_native_pdf.trace import canonical, digest, validate_record
from tests.codex_pdf.trace import require


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_transcription(actual, expected):
    require(
        actual == expected,
        "Transcription differs from exact source truth (Unicode is not normalized)",
    )


def load_asset(workspace, asset_id):
    require(re.fullmatch(r"file_[0-9a-f]{32}", asset_id), "Invalid asset ID")
    directory = workspace / "data" / "native-assets" / asset_id
    asset = read_json(directory / "asset.json")
    require(asset["asset_id"] == asset_id, "Asset identity mismatch")
    for item in asset["history"]:
        revision = item["sha256"]
        require(re.fullmatch(r"[0-9a-f]{64}", revision), "Invalid revision")
        require(
            digest((directory / "revisions" / revision).read_bytes()) == revision,
            "Stored revision hash mismatch",
        )
    require(
        asset["history"][-1]["sha256"] == asset["revision"], "Current history mismatch"
    )
    return asset


def validate_source(workspace, expected, source):
    path = workspace / "source.pdf"
    require(
        digest(path.read_bytes()) == expected["source_sha256"], "Source bytes changed"
    )
    require(
        path.stat().st_mtime_ns == expected["source_mtime_ns"], "Source mtime changed"
    )
    require(
        source["revision"] == expected["source_sha256"], "Registered source mismatch"
    )
    require(len(source["history"]) == 1, "Original managed source was mutated")
    with pymupdf.open(path) as pdf:
        require(
            len(pdf) == 3 and all(not p.get_text().strip() for p in pdf),
            "Fixture is not image-only",
        )


def validate_pdf(workspace, target, final):
    published = workspace / "verified.pdf"
    require(
        Path(final["exported_pdf"]).resolve() == published, "Unexpected published path"
    )
    data = published.read_bytes()
    require(
        digest(data) == target["revision"],
        "Published PDF differs from managed revision",
    )
    with (
        pymupdf.open(workspace / "source.pdf") as source,
        pymupdf.open(published) as output,
    ):
        require(len(source) == len(output) == 3, "Final page count is wrong")
        source[2].set_rotation(180)
        for expected, actual in zip(source, output, strict=True):
            require(
                expected.rotation == actual.rotation, "Final page rotation mismatch"
            )
            require(
                expected.mediabox == actual.mediabox
                and expected.cropbox == actual.cropbox,
                "Page geometry changed",
            )
            require(expected.get_text() == actual.get_text(), "Native text changed")
            a, b = expected.get_pixmap(), actual.get_pixmap()
            require(
                (a.width, a.height, a.samples) == (b.width, b.height, b.samples),
                "Independent final pixels mismatch",
            )


def validate_history(source, target, records):
    history = target["history"]
    require(
        target["source"] is None and not target["archived"],
        "Result is not a new retained asset",
    )
    require(len(history) >= 5, "Required managed revisions missing")
    initial = history[0]["result"]["changes"]
    copied = sorted(
        (c for c in initial if c["operation"] == "copy_page"),
        key=lambda c: c["position"],
    )
    require(
        [c["source_reference"]["locator"]["page_index"] for c in copied] == [2, 0, 1],
        "Initial composition order mismatch",
    )
    for change in copied:
        ref = change["source_reference"]
        require(
            (ref["asset_id"], ref["revision"])
            == (source["asset_id"], source["revision"]),
            "Copy lineage mismatch",
        )
        require(canonical(ref) in records, "Copy lineage lacks readback evidence")
    changes = [c for h in history for c in (h.get("result") or {}).get("changes", [])]
    require(
        sum(c["operation"] == "insert_blank_page" for c in changes) == 2,
        "Expected two blank insertions",
    )
    require(
        sum(c["operation"] == "delete_page" for c in changes) == 2,
        "Expected two blank deletions",
    )
    require(
        any(
            c["operation"] == "update_page_geometry" and c.get("rotation") == 180
            for c in changes
        ),
        "Rotation history missing",
    )
    require(
        sum(c["operation"] == "reorder_page" for c in changes) >= 3,
        "Reorder history missing",
    )


def validate_wiki(workspace, target, final):
    root = workspace / "native-wiki"
    require(
        Path(final["wiki_dir"]).resolve().is_relative_to(root), "Unexpected wiki path"
    )
    manifests = list(root.rglob("manifest.json"))
    require(len(manifests) == 1, "Expected one wiki snapshot")
    path = manifests[0].parent
    manifest = read_json(manifests[0])
    require(
        manifest["projection"] == "pdf-pages-v1" and manifest["page_count"] == 3,
        "Wrong wiki projection",
    )
    require(
        (manifest["asset_id"], manifest["revision"])
        == (target["asset_id"], target["revision"]),
        "Wiki revision mismatch",
    )
    for name, info in manifest["files"].items():
        require(Path(name).name == name, "Unsafe wiki filename")
        raw = (path / name).read_bytes()
        require(
            digest(raw) == info["sha256"] and len(raw) == info["size_bytes"],
            "Wiki artifact hash mismatch",
        )
    require(
        (path / manifest["source_attachment"]).read_bytes()
        == (workspace / "verified.pdf").read_bytes(),
        "Wiki source differs",
    )
    records = [
        json.loads(line) for line in (path / "records.jsonl").read_text().splitlines()
    ]
    require(
        [r["locator"]["page_index"] for r in records] == [0, 1, 2],
        "Wiki page coverage mismatch",
    )
    extra = {"note", "preview_attachment", "preview_sha256", "citation_presentation"}
    for record in records:
        validate_record({k: v for k, v in record.items() if k not in extra})
        require(
            digest((path / record["preview_attachment"]).read_bytes())
            == record["preview_sha256"],
            "Wiki preview mismatch",
        )
        require("[[" in (path / record["note"]).read_text(), "Wiki link missing")
