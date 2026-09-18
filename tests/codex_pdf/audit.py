"""Independent artifact/event checks for an opted-in Codex PDF run."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pymupdf as fitz
from openpyxl import load_workbook
from PIL import Image

from tests.codex_pdf.citation_readback import validate_citation_readbacks
from tests.codex_pdf.fixtures import COLUMNS, sha256
from tests.codex_pdf.trace import completed_calls, require, result_text, tool_errors


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_rows(actual: list[dict[str, Any]], expected: list[dict[str, Any]]) -> None:
    def normalize(rows):
        return sorted(
            json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows
        )

    require(
        normalize(actual) == normalize(expected),
        "Transcription differs from independent source truth",
    )


def validate_images(
    calls: list[dict[str, Any]], manifest: dict[str, Any], mode: str
) -> None:
    figures = {figure["id"]: figure for figure in manifest["assets"]["figures"]}
    viewed_pages = set()
    for call in calls:
        args = call["arguments"]
        if call["tool"] != "document_asset" or args.get("asset_type") != "figure":
            continue
        blocks = (call.get("result") or {}).get("content", [])
        images = [block for block in blocks if block["type"] == "image"]
        if not images:
            continue  # A retry may legitimately use a smaller max_size.
        require(
            args["doc_id"] == manifest["doc_id"], "Viewed image from wrong document"
        )
        require(args["asset_id"] in figures, "Viewed an unknown figure")
        for block in images:
            payload = base64.b64decode(block["data"], validate=True)
            with Image.open(io.BytesIO(payload)) as image:
                image.verify()
        viewed_pages.add(figures[args["asset_id"]]["page"])
    required_pages = (
        {1, 2, 3} if mode == "scanned" else {2, 3} if mode == "mixed" else set()
    )
    require(
        required_pages <= viewed_pages,
        f"Missing actual image responses for pages {required_pages - viewed_pages}",
    )


def validate_citations(table: dict[str, Any], manifest: dict[str, Any]) -> None:
    assets = {
        (kind[:-1], item["id"]): item
        for kind in ("figures", "tables")
        for item in manifest["assets"][kind]
    }
    for row, row_id in zip(table["rows"], table["row_ids"], strict=True):
        cite = table.get("citations", {}).get(f"rid:{row_id}:Reading", {})
        require(cite.get("refs"), f"Missing citation for {row['Sample']}")
        expected_page = {"A": 1, "B": 2, "C": 3}[row["Sample"][0]]
        for ref in cite["refs"]:
            asset = assets.get((ref["source_type"], ref.get("asset_id")))
            require(asset is not None, "Citation points to unknown source asset")
            require(
                ref.get("doc_id") == manifest["doc_id"], "Citation document mismatch"
            )
            require(
                ref.get("page") == asset["page"] == expected_page,
                "Citation page mismatch",
            )
            if ref["source_type"] == "figure":
                require(
                    not any(
                        ref.get(key)
                        for key in (
                            "span_id",
                            "quote",
                            "line_range",
                            "char_range",
                            "byte_range",
                        )
                    ),
                    "Visual transcription invents text-span evidence",
                )


def validate_history(table: dict[str, Any], calls: list[dict[str, Any]]) -> None:
    entries = table.get("change_log", {}).get("entries", [])
    target = next(
        row_id
        for row, row_id in zip(table["rows"], table["row_ids"], strict=True)
        if row["Sample"] == "B202"
    )
    edits = [
        entry
        for entry in entries
        if entry["operation"] == "update_cell"
        and entry["target"] == f"rid:{target}/col:Reading"
    ]
    require(
        [(e.get("old_value"), e.get("new_value")) for e in edits]
        == [("12.5%", "13.0%"), ("13.0%", "12.5%")],
        "Missing checked update/restoration history for B202 Reading",
    )
    removed = [entry for entry in entries if entry["operation"] == "delete_row"]
    require(
        len(removed) == 1 and removed[0]["old_value"]["Sample"] == "A101",
        "Missing A101 deletion history",
    )
    reads = [
        result_text(c)
        for c in calls
        if c["tool"] == "table_data"
        and c["arguments"].get("operation") in {"get_cell", "get_row", "query_rows"}
    ]
    require(any("13.0%" in text for text in reads), "Changed value was not read back")
    require(
        any("**Rows:** 6" in text and "A101" not in text for text in reads),
        "Deleted row was not checked before restoration",
    )


def validate_bundle(bundle: Path, source_hash: str) -> None:
    manifest = read_json(bundle / "manifest.json")
    require(
        manifest["source_identity"]["source_sha256"] == source_hash,
        "Bundle source hash mismatch",
    )
    for artifact in manifest["artifacts"]:
        path = (bundle / artifact["path"]).resolve()
        require(path.is_relative_to(bundle.resolve()), "Bundle path escapes root")
        require(
            path.stat().st_size == artifact["size_bytes"],
            "Bundle artifact size mismatch",
        )
        require(sha256(path) == artifact["sha256"], "Bundle artifact hash mismatch")
    records = [
        json.loads(line)
        for line in (bundle / "assets.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for record in records:
        digest = record.pop("record_sha256")
        encoded = json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        require(
            hashlib.sha256(encoded.encode()).hexdigest() == digest,
            "Bundle record hash mismatch",
        )
    require((bundle / "index.md").is_file(), "Missing Foam index")


def validate_scan_pixels(source: Path, manifest: dict[str, Any], mode: str) -> None:
    pages = {1, 2, 3} if mode == "scanned" else {2, 3} if mode == "mixed" else set()
    with fitz.open(source) as document:
        for number in pages:
            require(
                not document[number - 1].get_text().strip(),
                "Scan fixture has a hidden text layer",
            )
            figure = next(
                f
                for f in manifest["assets"]["figures"]
                if f["page"] == number
                and f["extraction_strategy"] == "xobject_page_crop"
            )
            expected = document[number - 1].get_pixmap(
                matrix=fitz.Matrix(2, 2), alpha=False
            )
            with Image.open(figure["path"]) as actual:
                require(
                    actual.size == (expected.width, expected.height),
                    "Full-page scan crop lost visible area",
                )
                require(
                    actual.convert("RGB").tobytes() == expected.samples,
                    "Scan crop pixels differ from source render",
                )


def validate_excel(directory: Path, expected: list[dict[str, Any]]) -> None:
    files = list(directory.glob("*.xlsx"))
    require(len(files) == 1, "Expected one rendered workbook")
    workbook = load_workbook(files[0], data_only=False)
    try:
        rows = list(workbook.active.values)
        start = next(i for i, row in enumerate(rows) if tuple(row[:5]) == COLUMNS)
        values = [
            dict(zip(COLUMNS, row[:5], strict=True))
            for row in rows[start + 1 : start + 1 + len(expected)]
        ]
        validate_rows(values, expected)
    finally:
        workbook.close()


def retained_table(data: Path) -> dict[str, Any]:
    tables = [
        read_json(path)
        for path in (data / "tables").glob("tbl_*.json")
        if not path.name.endswith(".manifest.json")
    ]
    require(
        len(tables) == 1, "Disposable table survived or transcription table missing"
    )
    return tables[0]


def audit(output: Path) -> dict[str, Any]:
    run = read_json(output / "run.json")
    require(
        run["returncode"] == 0 and not run["timed_out"],
        "Codex process failed or timed out",
    )
    expected = read_json(output / "expected.json")
    source = output / "workspace/source.pdf"
    data = output / "workspace/data"
    events = [
        json.loads(line)
        for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    calls = completed_calls(events)
    manifests = list(data.glob("doc_*/*_manifest.json"))
    require(len(manifests) == 1, "Expected one ingested document")
    manifest = read_json(manifests[0])
    table = retained_table(data)
    checks = evaluate_artifacts(
        expected,
        source,
        data,
        calls,
        manifest,
        table,
        manifests[0].parent / "agent-assets",
    )
    errors = tool_errors(events)
    passed = all(c["passed"] for c in checks)
    return {
        "schema": "codex-pdf-eval-v1",
        "passed": passed,
        "status": "failed"
        if not passed
        else "passed_with_recoveries"
        if errors
        else "passed",
        "mode": expected["mode"],
        "mcp_calls": len(calls),
        "first_transcription_exact": first_transcription_exact(
            calls, table["id"], expected["expected_rows"]
        ),
        "recovered_tool_errors": errors,
        "doc_id": manifest["doc_id"],
        "table_id": table["id"],
        "checks": checks,
    }


def first_transcription_exact(
    calls: list[dict], table_id: str, expected: list[dict]
) -> bool:
    initial = []
    for call in calls:
        args = call["arguments"]
        if call["tool"] != "table_data" or args.get("table_id") != table_id:
            continue
        if args.get("operation") in {
            "update_cell",
            "update_row",
            "clear_cell",
            "delete_row",
        }:
            break
        if args.get("operation") == "add_rows":
            initial.extend(args.get("rows", []))
    try:
        validate_rows(initial, expected)
    except ValueError:
        return False
    return True


def evaluate_artifacts(
    expected: dict,
    source: Path,
    data: Path,
    calls: list[dict],
    manifest: dict,
    table: dict,
    bundle: Path,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    steps = {
        "source_unchanged": lambda: require(
            sha256(source) == expected["source_sha256"]
            and source.stat().st_mtime_ns == expected["source_mtime_ns"],
            "Original source changed",
        ),
        "transcription": lambda: validate_rows(
            table["rows"], expected["expected_rows"]
        ),
        "mcp_image_delivery": lambda: validate_images(
            calls, manifest, expected["mode"]
        ),
        "scan_pixel_integrity": lambda: validate_scan_pixels(
            source, manifest, expected["mode"]
        ),
        "citations": lambda: validate_citations(table, manifest),
        "crud_history_and_readbacks": lambda: validate_history(table, calls),
        "excel_readback": lambda: validate_excel(
            data / "tables", expected["expected_rows"]
        ),
        "asset_bundle_integrity": lambda: validate_bundle(
            bundle, expected["source_sha256"]
        ),
    }
    if expected.get("citation_readback_required"):
        steps["canonical_citation_readbacks"] = lambda: validate_citation_readbacks(
            table, calls, require_paging=expected.get("citation_paging_required", False)
        )
    for name, step in steps.items():
        try:
            step()
            checks.append({"check": name, "passed": True})
        except (ValueError, KeyError, OSError, StopIteration, TypeError) as exc:
            checks.append({"check": name, "passed": False, "error": str(exc)})
    return checks


def write_audit(output: Path) -> dict[str, Any]:
    try:
        report = audit(output)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        report = {"schema": "codex-pdf-eval-v1", "passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    report = write_audit(parser.parse_args().output.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
