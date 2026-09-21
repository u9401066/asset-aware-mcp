"""Replay the independently checked ODS fixture against an installed package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import src
from src.domain.native_ods import (
    NativeODSCellEdit,
    NativeODSCellLocator,
    NativeODSCreate,
    NativeODSValue,
)
from src.infrastructure.native_ods import NativeODS, create_native_ods


def source_manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.py"))
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    installed = Path(src.__file__).resolve().parent
    assert "site-packages" in str(installed) or "archive-v0" in str(installed), (
        installed
    )
    expected = json.loads(args.source_manifest.read_text())
    assert source_manifest(installed) == expected
    original = (args.proof / "original.ods").read_bytes()
    edits = [
        NativeODSCellEdit(
            locator=NativeODSCellLocator(
                table_index=0, table_name="Sheet1", row=row, column=0
            ),
            value=NativeODSValue(kind=kind, value=value),
            display_policy="replace_paragraphs_preserve_cell_style",
        )
        for row, kind, value in [(0, "string", "NEW TITLE"), (1, "float", "5.75")]
    ]
    changed, receipt = NativeODS(original).edit(edits)
    assert changed == (args.proof / "edited.ods").read_bytes()
    assert receipt.model_dump() == json.loads((args.proof / "receipt.json").read_text())
    created = create_native_ods(NativeODSCreate(tables=["Asset", "中文"]))
    assert NativeODS(created).inspect()["total_physical_records"] == 2
    print(
        json.dumps(
            {
                "installed_source": str(installed),
                "source_files": len(expected),
                "exact_ods_replay": True,
                "complete_receipt_matches": True,
                "native_creation": True,
            }
        )
    )


if __name__ == "__main__":
    main()
