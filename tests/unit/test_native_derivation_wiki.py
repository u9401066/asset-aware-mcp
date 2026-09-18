"""Portable derivation wikis retain sources, historical claims and curated snapshots."""

import hashlib
import json
from pathlib import Path

import pytest

from tests.native_derivation_helpers import pair, record, service_at
from tests.native_workbook_helpers import _call


def export(service, asset, tmp_path, **extra):
    result = _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
        **extra,
    )
    assert result["success"]
    root = Path(result["output_dir"])
    return root, json.loads((root / "manifest.json").read_text())


def test_wiki_retains_exact_sources_and_separate_review_claims(tmp_path):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    old_root, old_manifest = export(service, asset, tmp_path)
    old_bytes = {p.name: p.read_bytes() for p in old_root.iterdir()}
    result = record(service, asset, claim)
    root, manifest = export(
        service, asset, tmp_path, derivations_sha256=result["derivations_sha256"]
    )
    assert root != old_root and "derivations" not in old_manifest
    assert manifest["derivations"]["active_ids_for_revision"] == [
        result["derivation_id"]
    ]
    for attached in manifest["derivations"]["source_attachments"].values():
        data = (root / attached["attachment"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == attached["revision"]
        assert data == b"source content"
    ledger = json.loads((root / "derivations.json").read_text())
    assert ledger["events"][0]["derivation"]["sources"] == claim["sources"]
    note = next(root.glob("*-derivation-*.md")).read_text()
    assert "caller assertions" in note and "not_checked" in note
    assert "[[" in (root / manifest["index_note"]).read_text()
    assert export(service, asset, tmp_path)[0] == root
    assert {p.name: p.read_bytes() for p in old_root.iterdir()} == old_bytes


def test_retraction_and_file_change_make_distinct_snapshots(tmp_path):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    first = record(service, asset, claim)
    old_root, _ = export(service, asset, tmp_path)
    old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
    _call(
        service,
        op="retract_derivation",
        asset_id=asset["asset_id"],
        expected_derivations_sha256=first["derivations_sha256"],
        retraction={
            "derivation_id": first["derivation_id"],
            "agent": "reviewer",
            "reason": "wrong relationship",
        },
    )
    new_root, manifest = export(service, asset, tmp_path)
    assert new_root != old_root
    assert manifest["derivations"]["active_ids_for_revision"] == []
    assert len(json.loads((new_root / "derivations.json").read_text())["events"]) == 2
    assert {p.name: p.read_bytes() for p in old_root.iterdir()} == old_files
    with pytest.raises(ValueError, match="changed"):
        export(service, asset, tmp_path, derivations_sha256=first["derivations_sha256"])


def test_export_rejects_corrupt_source_and_does_not_create_output(tmp_path):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    record(service, asset, claim)
    ref = claim["sources"][0]
    (tmp_path / "store" / ref["asset_id"] / "revisions" / ref["revision"]).write_bytes(
        b"corrupt"
    )
    with pytest.raises(ValueError):
        export(service, asset, tmp_path)
    assert not (tmp_path / "wiki").exists()


def test_active_derivation_is_not_applied_to_another_target_revision(tmp_path):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    record(service, asset, claim)
    _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "Sheet1", "cell": "A1", "value": "008"}],
    )
    _, current = export(service, asset, tmp_path)
    _, historic = export(service, asset, tmp_path, revision=asset["revision"])
    assert current["derivations"]["active_ids_for_revision"] == []
    assert len(historic["derivations"]["active_ids_for_revision"]) == 1
