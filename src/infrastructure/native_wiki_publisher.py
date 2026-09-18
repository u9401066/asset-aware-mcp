"""Publish new immutable wiki snapshots with exclusive writes and manifest-last commit."""

from __future__ import annotations

import os
import re
from itertools import islice
from pathlib import Path
from typing import Any

from src.domain.native_wiki import MAX_WIKI_ARTIFACTS, MAX_WIKI_BYTES
from src.infrastructure.native_file_io import _identity, _read_file


class FileNativeWikiPublisher:
    def __init__(self, protected_roots: tuple[Path, ...] = ()):
        self.protected_roots = tuple(path.resolve() for path in protected_roots)

    def publish(
        self,
        output_dir: str,
        snapshot_id: str,
        files: dict[str, bytes],
        *,
        source_path: str | None,
    ) -> dict[str, Any]:
        self._validate_payload(snapshot_id, files)
        target = self._target(output_dir, snapshot_id, source_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.mkdir()
        except FileExistsError:
            self._validate_existing(target, files)
            return {"success": True, "output_dir": str(target), "reused": True}
        identity = target.stat()
        try:
            for name, data in files.items():
                if name != "manifest.json":
                    self._write_new(target / name, data, identity)
            self._validate_existing(
                target,
                {name: data for name, data in files.items() if name != "manifest.json"},
            )
            self._write_new(target / "manifest.json", files["manifest.json"], identity)
            self._validate_existing(target, files)
        except (OSError, ValueError) as exc:
            return {
                "success": False,
                "output_dir": str(target),
                "reconciliation_required": True,
                "error": f"Wiki publication interrupted; files retained: {exc}",
            }
        return {"success": True, "output_dir": str(target), "reused": False}

    def _target(
        self, output_dir: str, snapshot_id: str, source_path: str | None
    ) -> Path:
        root = Path(output_dir).expanduser()
        if root.is_symlink():
            raise ValueError("Wiki output root cannot be a symlink")
        target = root.resolve() / f"native-{snapshot_id}"
        for protected in self.protected_roots:
            if target.is_relative_to(protected) or protected.is_relative_to(target):
                raise ValueError("Wiki output overlaps the native asset store")
        if source_path and Path(source_path).resolve().is_relative_to(target):
            raise ValueError("Wiki output overlaps the human source file")
        return target

    @staticmethod
    def _validate_payload(snapshot_id: str, files: dict[str, bytes]) -> None:
        if re.fullmatch(r"[a-f0-9]{64}", snapshot_id) is None:
            raise ValueError("Invalid native wiki snapshot identity")
        if "manifest.json" not in files or len(files) > MAX_WIKI_ARTIFACTS:
            raise ValueError("Invalid native wiki artifact inventory")
        if sum(len(data) for data in files.values()) > MAX_WIKI_BYTES:
            raise ValueError("Native wiki exceeds the output byte limit")
        if any(
            re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,199}", name) is None for name in files
        ):
            raise ValueError("Unsafe native wiki artifact filename")

    @staticmethod
    def _write_new(path: Path, data: bytes, identity: os.stat_result) -> None:
        current = path.parent.stat()
        if path.parent.is_symlink() or (current.st_dev, current.st_ino) != (
            identity.st_dev,
            identity.st_ino,
        ):
            raise ValueError("Wiki snapshot directory changed during publication")
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _validate_existing(target: Path, files: dict[str, bytes]) -> None:
        if target.is_symlink() or not target.is_dir():
            raise ValueError("Wiki snapshot must be a real directory")
        before = target.stat()
        entries = list(islice(target.iterdir(), len(files) + 1))
        if {entry.name for entry in entries} != set(files):
            raise ValueError(
                "Wiki snapshot inventory differs; existing files preserved"
            )
        for entry in entries:
            data, _ = _read_file(entry, len(files[entry.name]))
            if data != files[entry.name]:
                raise ValueError(
                    "Wiki snapshot was modified or citation display differs; "
                    "existing notes preserved. Use a separate output directory."
                )
        if target.is_symlink() or _identity(target.stat()) != _identity(before):
            raise ValueError("Wiki snapshot changed during verification")
