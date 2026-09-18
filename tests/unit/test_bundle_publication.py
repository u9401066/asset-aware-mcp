"""Human edits, racing writers and failed publication retain recoverable evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from src.application.agent_asset_bundle_format import canonical_json, sha256_text
from src.application.agent_asset_record_builder import AgentAssetRecordBuilder
from src.domain.bundle_publication import BundlePublicationPolicy
from src.infrastructure.bundle_inventory import inspect_bundle
from src.infrastructure.bundle_publisher import FileBundlePublisher
from src.infrastructure.native_file_io import operation_lock
from src.presentation.tools.citation_support import asset_ref_from_span
from src.presentation.tools.document_evidence_support import (
    _asset_ref_from_manifest_asset,
)
from tests.unit.test_agent_asset_bundle_service import _export, _fixture, _snapshot


async def _styled(service: Any, doc_id: str) -> dict:
    return await service.export(
        doc_id,
        output_dir="bundle",
        span_ref_factory=asset_ref_from_span,
        asset_ref_factory=_asset_ref_from_manifest_asset,
        citation_contract={
            "inline_template": "Source {source_id}",
            "reference_template": "{title}",
        },
    )


@pytest.mark.parametrize(
    "change", ["same_size", "longer", "missing", "extra", "directory", "manifest"]
)
async def test_manual_changes_block_reexport_without_altering_them(
    tmp_path: Path, change: str
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    result = await _export(service, doc_id, "bundle")
    root = Path(result["output_dir"])
    note = next((root / "notes").iterdir())
    if change == "same_size":
        data = note.read_bytes()
        note.write_bytes(b"X" + data[1:])
    elif change == "longer":
        note.write_bytes(note.read_bytes() + b"\nHuman analysis\n")
    elif change == "missing":
        note.unlink()
    elif change == "extra":
        (root / "curated.md").write_bytes(b"Human analysis")
    elif change == "directory":
        (root / "human-notes").mkdir()
    else:
        manifest = root / "manifest.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["bundle_sha256"] = "f" * 64
        manifest.write_text(json.dumps(payload), encoding="utf-8")
    before = _snapshot(root)
    with pytest.raises(ValueError):
        await _export(service, doc_id, "bundle")
    assert _snapshot(root) == before
    assert not list(root.parent.glob(".bundle.backup-*"))
    if change == "directory":
        assert (root / "human-notes").is_dir()


async def test_identical_export_preserves_mtime_without_creating_backups(
    tmp_path: Path,
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    result = await _export(service, doc_id, "bundle")
    root = Path(result["output_dir"])
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    second = await _export(service, doc_id, "bundle")
    assert second["reused"] is True and second["backup_path"] is None
    assert {p: p.stat().st_mtime_ns for p in before} == before


async def test_changed_citation_export_retains_original_tree_and_old_links(
    tmp_path: Path,
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    original = _snapshot(root)
    updated = await _styled(service, doc_id)
    backup = Path(updated["backup_path"])
    assert updated["reused"] is False
    assert _snapshot(backup) == original
    assert set(_snapshot(root)) == set(original)
    assert _snapshot(root) != original


@pytest.mark.skipif(os.name == "nt", reason="POSIX open inode rename semantics")
async def test_late_write_through_open_editor_handle_survives_in_backup(
    tmp_path: Path,
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    note = next((root / "notes").iterdir())
    with note.open("ab") as editor:
        updated = await _styled(service, doc_id)
        editor.write(b"\nLate human edit\n")
        editor.flush()
    backup_note = Path(updated["backup_path"]) / note.relative_to(root)
    assert backup_note.read_bytes().endswith(b"Late human edit\n")
    assert b"Late human edit" not in note.read_bytes()


async def test_edit_during_generation_is_detected_before_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    build = AgentAssetRecordBuilder.build

    def race(*args: Any, **kwargs: Any) -> Any:
        records = build(*args, **kwargs)
        (root / "index.md").write_bytes(b"Concurrent human note")
        return records

    monkeypatch.setattr(AgentAssetRecordBuilder, "build", race)
    with pytest.raises(ValueError):
        await _styled(service, doc_id)
    assert (root / "index.md").read_bytes() == b"Concurrent human note"
    assert not list(root.parent.glob(".bundle.backup-*"))
    assert not list(root.parent.glob(".bundle.staging-*"))


async def test_failed_rename_restores_original_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    before = _snapshot(root)
    rename = Path.rename

    def fail_stage(path: Path, target: Path) -> Path:
        if path.name.startswith(".bundle.staging-"):
            raise OSError("simulated rename failure")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_stage)
    with pytest.raises(OSError, match="simulated"):
        await _styled(service, doc_id)
    assert _snapshot(root) == before
    assert not list(root.parent.glob(".bundle.staging-*"))


async def test_competing_output_preserves_both_new_human_files_and_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    before = _snapshot(root)
    rename = Path.rename

    def race(path: Path, target: Path) -> Path:
        if path.name.startswith(".bundle.staging-"):
            target.mkdir()
            (target / "human.md").write_bytes(b"Racing writer")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", race)
    with pytest.raises(ValueError, match="previous files retained"):
        await _styled(service, doc_id)
    assert (root / "human.md").read_bytes() == b"Racing writer"
    backup = next(root.parent.glob(".bundle.backup-*"))
    assert _snapshot(backup) == before


async def test_bundle_symlink_is_rejected_without_following(tmp_path: Path) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    note = root / "index.md"
    external = tmp_path / "human.md"
    external.write_bytes(note.read_bytes())
    note.unlink()
    try:
        note.symlink_to(external)
    except OSError:
        if os.name == "nt":
            pytest.skip("Symlink privilege unavailable")
        raise
    before = external.read_bytes()
    with pytest.raises(ValueError, match="symlink"):
        await _export(service, doc_id, "bundle")
    assert external.read_bytes() == before


@pytest.mark.parametrize(
    "path", ["../human.md", "/human.md", "notes\\human.md", "notes/../index.md"]
)
async def test_forged_inventory_paths_are_rejected(tmp_path: Path, path: str) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    marker = root / "manifest.json"
    payload = json.loads(marker.read_text(encoding="utf-8"))
    payload["artifacts"][0]["path"] = path
    del payload["bundle_sha256"]
    payload["bundle_sha256"] = sha256_text(canonical_json(payload))
    marker.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact path"):
        await _export(service, doc_id, "bundle")


async def test_stale_manifest_token_and_busy_lock_reject_publication(
    tmp_path: Path,
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])
    policy = BundlePublicationPolicy(doc_id, "agent-asset-bundle-v1", 256 * 1024 * 1024)
    token = inspect_bundle(root, policy)
    publisher = FileBundlePublisher()
    with pytest.raises(ValueError, match="changed since export"):
        publisher.publish(tmp_path / "unused-stage", root, policy, "f" * 64)
    with operation_lock(root.parent), pytest.raises(ValueError, match="busy"):
        publisher.publish(tmp_path / "unused-stage", root, policy, token)


async def test_identical_export_rechecks_target_after_staging_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _, doc_id = _fixture(tmp_path)
    initial = await _export(service, doc_id, "bundle")
    root = Path(initial["output_dir"])

    def race(target: Path, policy: BundlePublicationPolicy) -> str | None:
        token = inspect_bundle(target, policy)
        if target.name.startswith(".bundle.staging-"):
            (root / "index.md").write_bytes(b"Human edit during stage verification")
        return token

    monkeypatch.setattr("src.infrastructure.bundle_publisher.inspect_bundle", race)
    with pytest.raises(ValueError):
        await _export(service, doc_id, "bundle")
    assert (root / "index.md").read_bytes() == b"Human edit during stage verification"
