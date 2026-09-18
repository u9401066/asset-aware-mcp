"""Portable native wiki snapshots retain exact evidence and immutable note targets."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_spreadsheet import (
    NativeSpreadsheet,
    SpreadsheetFileAdapter,
)
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_workbook_helpers import _call


@pytest.fixture
def service(tmp_path: Path) -> NativeDocumentService:
    store = tmp_path / "store"
    return NativeDocumentService(
        FileNativeAssetRepository(store),
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((store,)),
    )


def _create(service: NativeDocumentService) -> dict:
    return _call(
        service,
        op="create",
        workbook={
            "name": "evidence.xlsx",
            "sheets": ["O'Brien 成本", "Notes"],
            "edits": [
                {
                    "sheet": "O'Brien 成本",
                    "cell": "A1",
                    "value": "中文\n[[bad]] <script>x</script>",
                },
                {"sheet": "O'Brien 成本", "cell": "B2", "kind": "number", "value": 42},
                {"sheet": "Notes", "cell": "A1", "kind": "formula", "value": "=1+2"},
                {"sheet": "Notes", "cell": "C9", "value": "長" * 10000},
            ],
        },
    )["asset"]


def _export(
    service: NativeDocumentService, asset: dict, root: Path, **kwargs: object
) -> dict:
    return _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(root),
        **kwargs,
    )


def _records(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in (path / "records.jsonl").read_text().splitlines()
    ]


def test_portable_snapshot_has_exact_source_resolvable_links_and_full_references(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    asset = _create(service)
    result = _export(service, asset, tmp_path / "wiki")
    assert result["success"] and result["cell_count"] == 4
    assert result["reused"] is False
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    source = (root / manifest["source_attachment"]).read_bytes()
    assert hashlib.sha256(source).hexdigest() == asset["revision"]
    assert NativeSpreadsheet(source).read_cell("O'Brien 成本", "B2")["value"] == 42
    assert set(manifest["files"]) | {"manifest.json"} == {
        p.name for p in root.iterdir()
    }
    for name, info in manifest["files"].items():
        data = (root / name).read_bytes()
        assert info == {
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }
    for record in _records(root):
        assert _call(service, op="verify", reference=record["evidence"])["valid"]
        note = (root / record["note"]).read_text()
        assert record["evidence"]["value_sha256"] in note
        assert len(re.findall(r"^# ", note, flags=re.MULTILINE)) == 1
        assert "<script>" not in note
        for target in re.findall(r"(?<!\\)\[\[([^]|]+)", note):
            assert (root / (target + ".md")).exists()
        for target in re.findall(r"(?<!\\)\]\(([^)]+)\)", note):
            assert (root / target).exists()
    assert next(r for r in _records(root) if r["cell"] == "C9")["value"] == "長" * 10000
    formula = next(r for r in _records(root) if r["kind"] == "formula")
    assert formula["cached_value_verified"] is False
    assert "formula_results" in result["review_required"]


def test_reexport_is_idempotent_and_does_not_touch_adjacent_curated_notes(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    root = tmp_path / "wiki"
    root.mkdir()
    curated = root / "my-analysis.md"
    curated.write_text("Human synthesis", encoding="utf-8")
    asset = _create(service)
    first = _export(service, asset, root)
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in Path(first["output_dir"]).iterdir()
    }
    second = _export(service, asset, root)
    assert second["reused"] is True
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}
    assert curated.read_text() == "Human synthesis"


def test_new_revision_preserves_old_links_even_after_archival(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    asset = _create(service)
    first = _export(service, asset, tmp_path / "wiki")
    old_root = Path(first["output_dir"])
    old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
    changed = _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "O'Brien 成本", "cell": "B2", "kind": "number", "value": 43}],
    )["asset"]
    new = _export(service, changed, tmp_path / "wiki")
    assert first["output_dir"] != new["output_dir"]
    assert old_files == {p.name: p.read_bytes() for p in old_root.iterdir()}
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=changed["revision"],
    )
    old = _export(service, asset, tmp_path / "wiki", revision=asset["revision"])
    assert old["reused"] is True
    for record in _records(old_root):
        assert _call(service, op="verify", reference=record["evidence"])["valid"]


def test_custom_citation_changes_display_without_changing_reference_or_note_identity(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    asset = _create(service)
    first = _export(service, asset, tmp_path / "wiki")
    custom = {
        "inline_template": "{authors} / {year} / {locator}",
        "reference_template": "{title}",
    }
    kwargs = {
        "citation_contract": custom,
        "citation_metadata": {"authors": "Lin", "year": "2026"},
    }
    second = _export(service, asset, tmp_path / "styled", **kwargs)
    old, new = _records(Path(first["output_dir"])), _records(Path(second["output_dir"]))
    assert [(r["note"], r["evidence"]) for r in old] == [
        (r["note"], r["evidence"]) for r in new
    ]
    assert (
        new[0]["citation_presentation"]["inline"] == "Lin / 2026 / 'O''Brien 成本'!A1"
    )
    with pytest.raises(ValueError):
        _export(service, asset, tmp_path / "wiki", **kwargs)
    assert _records(Path(first["output_dir"])) == old


@pytest.mark.parametrize("mutation", ["changed", "added", "deleted", "directory"])
def test_modified_or_unexpected_snapshot_entries_are_preserved(
    service: NativeDocumentService, tmp_path: Path, mutation: str
) -> None:
    asset = _create(service)
    result = _export(service, asset, tmp_path / "wiki")
    root = Path(result["output_dir"])
    note = root / result["index_note"]
    if mutation == "changed":
        note.write_text("Human edit", encoding="utf-8")
    elif mutation == "added":
        (root / "extra.md").write_text("Human note", encoding="utf-8")
    elif mutation == "deleted":
        note.unlink()
    else:
        (root / "human-notes").mkdir()
    before = {p.name: p.read_bytes() if p.is_file() else None for p in root.iterdir()}
    with pytest.raises(ValueError):
        _export(service, asset, tmp_path / "wiki")
    assert before == {
        p.name: p.read_bytes() if p.is_file() else None for p in root.iterdir()
    }


def test_missing_citation_metadata_and_output_limits_leave_no_snapshot(
    service: NativeDocumentService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset = _create(service)
    with pytest.raises(ValueError, match="Missing citation metadata"):
        _export(
            service,
            asset,
            tmp_path / "wiki",
            citation_contract={"preset": "author-year"},
        )
    assert not (tmp_path / "wiki").exists()
    monkeypatch.setattr("src.application.native_wiki_service.MAX_WIKI_CELLS", 1)
    with pytest.raises(ValueError, match="stored-cell limit"):
        _export(service, asset, tmp_path / "wiki")
    assert not (tmp_path / "wiki").exists()
    monkeypatch.setattr("src.application.native_wiki_service.MAX_WIKI_CELLS", 20000)
    monkeypatch.setattr("src.application.native_wiki_format.MAX_WIKI_BYTES", 20)
    with pytest.raises(ValueError, match="byte limit"):
        _export(service, asset, tmp_path / "wiki")
    assert not (tmp_path / "wiki").exists()


def test_opaque_source_has_no_invented_native_interpretation(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    source = tmp_path / "未知.custom"
    source.write_bytes(b"opaque bytes")
    before = source.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(source))["asset"]
    result = _export(service, asset, tmp_path / "wiki")
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["representation"] == "opaque_binary"
    assert result["cell_count"] == 0
    assert (root / manifest["source_attachment"]).read_bytes() == b"opaque bytes"
    assert _records(root) == []
    assert source.stat().st_mtime_ns == before


def test_output_inside_store_is_rejected(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="overlaps"):
        _export(service, _create(service), tmp_path / "store" / "wiki")
