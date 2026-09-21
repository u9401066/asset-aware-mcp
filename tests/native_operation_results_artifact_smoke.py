"""Replay a real 5,000-formula capacity failure against checkout/wheel/container."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

from lxml import etree

import src
from src.domain.native_ods import NativeODSCellEdit, NativeODSCreate
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_odf_package import NS, NativeODFPackage, q, xml_bytes
from src.infrastructure.native_ods import NativeODS, create_native_ods


def formula_source(count):
    package = NativeODFPackage(create_native_ods(NativeODSCreate()))
    root = package.xml("content.xml")
    table = root.find("office:body/office:spreadsheet/table:table", NS)
    assert table is not None
    for child in list(table):
        table.remove(child)
    for index in range(count + 1):
        row = etree.SubElement(table, q("table", "table-row"))
        cell = etree.SubElement(row, q("table", "table-cell"))
        cell.set(q("office", "value-type"), "float")
        cell.set(q("office", "value"), "2" if index else "1")
        if index:
            cell.set(q("table", "formula"), "of:=[.A1]*2")
        etree.SubElement(cell, q("text", "p")).text = "2" if index else "1"
    # Keep the exact historical 5093031 input for its captured output/receipt
    # goldens. That fixture declared an unused legacy drawing namespace; new
    # native documents now declare the correct ODF drawing namespace.
    package.parts["content.xml"] = xml_bytes(root).replace(
        b'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"',
        b'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:draw:1.0"',
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, value in package.parts.items():
            info = zipfile.ZipInfo(name, (2001, 2, 3, 4, 5, 6))
            info.compress_type = (
                zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            )
            archive.writestr(info, value)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-installed", action="store_true")
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    source = Path(src.__file__).resolve().parent
    if args.require_installed:
        assert "site-packages" in str(source) or "archive-v0" in str(source), source
    actual = {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(source.rglob("*.py"))
    }
    assert actual == json.loads(args.source_manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    original = formula_source(5000)
    path = args.output / "source.ods"
    path.write_bytes(original)
    mtime = path.stat().st_mtime_ns
    repository = FileNativeAssetRepository(args.output / "assets")
    initial = repository.register(str(path))
    edit = NativeODSCellEdit.model_validate(
        {
            "locator": {
                "table_index": 0,
                "table_name": "Sheet1",
                "row": 0,
                "column": 0,
            },
            "value": {"kind": "float", "value": "3"},
            "display_policy": "replace_paragraphs_preserve_cell_style",
        }
    )
    start = time.monotonic()
    changed, result = NativeODS(original).edit([edit])
    edit_seconds = time.monotonic() - start
    canonical = json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    result_sha = hashlib.sha256(canonical).hexdigest()
    output_sha = hashlib.sha256(changed).hexdigest()
    if args.baseline is not None:
        baseline = json.loads(args.baseline.read_text())
        assert initial.revision == baseline["source_sha256"]
        assert output_sha == baseline["output_sha256"]
        assert result_sha == baseline["full_receipt_sha256"]
    caches = [
        c for c in result.changes if c["operation"] == "invalidate_typed_formula_cache"
    ]
    assert len(caches) == 5000
    for index, change in enumerate(caches, 1):
        assert change["locator"]["row"] == index
        assert change["before"]["value_attributes"]["value"] == "2"
        assert change["after"]["value_attributes"] == {}
        assert change["before"]["formula"] == change["after"]["formula"]
    committed = repository.commit(initial.asset_id, initial.revision, changed, result)
    metadata = args.output / "assets" / initial.asset_id / "asset.json"
    restarted = FileNativeAssetRepository(args.output / "assets")
    loaded = restarted.load(initial.asset_id)
    assert loaded == committed
    assert restarted.read_result(initial.asset_id, loaded.history[-1]) == result
    assert restarted.read(initial.asset_id, initial.revision) == original
    assert restarted.read(initial.asset_id) == changed
    assert path.read_bytes() == original and path.stat().st_mtime_ns == mtime
    legacy = loaded.model_dump(mode="json")
    legacy["schema_version"] = "native-file-asset-v1"
    for entry in legacy["history"]:
        entry.pop("result_ref")
    legacy["history"][-1]["result"] = result.model_dump(mode="json")
    legacy_bytes = len(json.dumps(legacy, ensure_ascii=False, indent=2).encode())
    assert legacy_bytes > 16 * 1024 * 1024
    assert metadata.stat().st_size < 64 * 1024
    proof = {
        "source_files": len(actual),
        "source_path": str(source),
        "formula_cells": len(caches),
        "native_seconds": edit_seconds,
        "source_bytes": len(original),
        "source_sha256": initial.revision,
        "output_sha256": output_sha,
        "full_receipt_sha256": result_sha,
        "legacy_metadata_bytes": legacy_bytes,
        "metadata_bytes": metadata.stat().st_size,
        "complete_result_bytes": loaded.history[-1].result_ref.size_bytes,
        "complete_result_after_restart": True,
        "all_before_after_caches_retained": True,
        "source_bytes_and_mtime_unchanged": True,
    }
    (args.output / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
