"""Exercise installed ODS application wiring with an independently rendered fixture."""

import argparse
import hashlib
import json
from pathlib import Path

import src
from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_ods import NativeODSFileAdapter
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher


def service_at(root):
    return NativeDocumentService(
        FileNativeAssetRepository(root),
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((root,)),
        ods=NativeODSFileAdapter(),
    )


def call(service, **fields):
    return service.execute(NativeDocumentRequest.model_validate(fields))


def complete(service, **fields):
    text, sha, offset = "", None, 0
    while True:
        page = call(
            service,
            **fields,
            text_offset=offset,
            **({"ods_text_sha256": sha} if sha else {}),
        )
        sha = sha or page["text_sha256"]
        assert page["text_sha256"] == sha and page["excerpt_char_range"][0] == offset
        text += page["text_excerpt"]
        if page["next_text_offset"] is None:
            break
        offset = page["next_text_offset"]
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-installed", action="store_true")
    args = parser.parse_args()
    installed = Path(src.__file__).resolve().parent
    if args.require_installed:
        assert "site-packages" in str(installed) or "archive-v0" in str(installed), (
            installed
        )
    manifest = {
        str(p.relative_to(installed)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(installed.rglob("*.py"))
    }
    assert manifest == json.loads(args.source_manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / "source.ods"
    source.write_bytes((args.proof / "original.ods").read_bytes())
    before, mtime = source.read_bytes(), source.stat().st_mtime_ns
    root = args.output / "assets"
    service = service_at(root)
    asset = call(service, op="register", source_path=str(source))["asset"]
    refs = []
    for row in [0, 1]:
        record = complete(
            service,
            op="read_ods_cell",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            ods_locator={
                "table_index": 0,
                "table_name": "Sheet1",
                "row": row,
                "column": 0,
            },
        )["cell"]
        assert call(service, op="verify", reference=record["evidence"])["valid"]
        refs.append(record["evidence"])
    updated = call(
        service,
        op="update_ods",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        ods_update={
            "cells": [
                {
                    "reference": ref,
                    "value": {"kind": kind, "value": value},
                    "display_policy": "replace_paragraphs_preserve_cell_style",
                }
                for ref, kind, value in zip(
                    refs, ["string", "float"], ["NEW TITLE", "5.75"], strict=True
                )
            ]
        },
    )
    current = updated["asset"]
    actual = service.repository.read(asset["asset_id"], current["revision"])
    assert actual == (args.proof / "edited.ods").read_bytes()
    full = complete(service, **updated["review_request"])
    expected = json.loads((args.proof / "receipt.json").read_text())
    expected["checks"].append("all_original_logical_cell_references_verified")
    assert full["operation_result"] == expected
    request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "revision": current["revision"],
        "output_dir": str(args.output / "wiki"),
    }
    wiki = call(service, **request)
    directory = Path(wiki["output_dir"])
    files = {p.name: p.read_bytes() for p in directory.iterdir()}
    assert json.loads(files["operation-result.json"]) == expected
    reopened = service_at(root)
    assert complete(reopened, **updated["review_request"]) == full
    assert all(call(reopened, op="verify", reference=ref)["valid"] for ref in refs)
    assert call(reopened, **request)["reused"]
    assert files == {p.name: p.read_bytes() for p in directory.iterdir()}
    created = call(
        reopened, op="create_ods", ods_create={"name": "獨立.ods", "tables": ["證據"]}
    )
    assert (
        complete(reopened, **created["review_request"])["tables"][0]["table_name"]
        == "證據"
    )
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (before, mtime)
    result = {
        "source_files": len(manifest),
        "installed_source": str(installed),
        "ods_exact_calc_fixture_output": True,
        "complete_receipt_matches": True,
        "restart_and_wiki_bytes_identical": True,
        "old_references_valid": True,
        "independent_create": True,
        "source_bytes_and_mtime_unchanged": True,
    }
    (args.output / "proof.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
