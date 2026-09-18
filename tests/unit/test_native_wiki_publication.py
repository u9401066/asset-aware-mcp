"""Interrupted or conflicting wiki publication never replaces existing user files."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher


def _publish(root: Path, publisher: FileNativeWikiPublisher | None = None) -> dict:
    return (publisher or FileNativeWikiPublisher()).publish(
        str(root),
        "a" * 64,
        {"note.md": b"# Note\n", "manifest.json": b'{"complete":true}\n'},
        source_path=None,
    )


def _symlink(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError:
        if os.name == "nt":
            pytest.skip("Windows runner does not grant symlink privileges")
        raise


def test_symlink_note_and_snapshot_are_not_followed(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    result = _publish(wiki)
    root = Path(result["output_dir"])
    note = root / "note.md"
    external = tmp_path / "human.md"
    external.write_bytes(note.read_bytes())
    note.unlink()
    _symlink(note, external)
    with pytest.raises((OSError, ValueError)):
        _publish(wiki)
    assert external.read_bytes() == b"# Note\n"
    moved = tmp_path / "moved"
    root.rename(moved)
    _symlink(root, moved, directory=True)
    with pytest.raises(ValueError, match="real directory"):
        _publish(wiki)
    assert (moved / "manifest.json").exists()


def test_output_root_symlink_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    root = tmp_path / "wiki"
    _symlink(root, real, directory=True)
    with pytest.raises(ValueError, match="symlink"):
        _publish(root)
    assert list(real.iterdir()) == []


def test_failure_retains_partial_output_without_claiming_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publisher = FileNativeWikiPublisher()
    original = publisher._write_new

    def fail_manifest(path: Path, data: bytes, identity: os.stat_result) -> None:
        if path.name == "manifest.json":
            raise OSError("simulated full disk")
        original(path, data, identity)

    monkeypatch.setattr(publisher, "_write_new", fail_manifest)
    result = _publish(tmp_path / "wiki", publisher)
    assert result["success"] is False
    assert result["reconciliation_required"] is True
    root = Path(result["output_dir"])
    assert (root / "note.md").read_bytes() == b"# Note\n"
    assert not (root / "manifest.json").exists()
    with pytest.raises(ValueError, match="inventory"):
        _publish(tmp_path / "wiki")


def test_file_created_during_publication_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publisher = FileNativeWikiPublisher()
    original = publisher._write_new

    def race(path: Path, data: bytes, identity: os.stat_result) -> None:
        if path.name == "note.md":
            path.write_bytes(b"human race")
        original(path, data, identity)

    monkeypatch.setattr(publisher, "_write_new", race)
    result = _publish(tmp_path / "wiki", publisher)
    assert result["success"] is False
    root = Path(result["output_dir"])
    assert (root / "note.md").read_bytes() == b"human race"
    assert not (root / "manifest.json").exists()


def test_source_inside_snapshot_is_protected(tmp_path: Path) -> None:
    root = tmp_path / "wiki"
    source = root / ("native-" + "a" * 64) / "source.xlsx"
    with pytest.raises(ValueError, match="human source"):
        FileNativeWikiPublisher().publish(
            str(root), "a" * 64, {"manifest.json": b"{}"}, source_path=str(source)
        )
    assert not root.exists()


@pytest.mark.parametrize("name", ["../escape", "/escape", "a/b", "a\\b", "CON:"])
def test_unsafe_artifact_names_rejected_before_writing(
    tmp_path: Path, name: str
) -> None:
    with pytest.raises(ValueError, match="filename"):
        FileNativeWikiPublisher().publish(
            str(tmp_path / "wiki"),
            "a" * 64,
            {"manifest.json": b"{}", name: b"data"},
            source_path=None,
        )
    assert not (tmp_path / "wiki").exists()
