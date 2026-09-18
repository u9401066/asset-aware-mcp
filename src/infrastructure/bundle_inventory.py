"""Bounded validation of bundle ownership, manifest self-hash and complete inventory."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from src.infrastructure.native_file_io import _identity, _read_file

if TYPE_CHECKING:
    from src.domain.bundle_publication import BundlePublicationPolicy

MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_ARTIFACTS = 100_000


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory(payload: dict[str, Any], max_bytes: int) -> dict[str, dict[str, Any]]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) > MAX_ARTIFACTS:
        raise ValueError("Invalid bundle artifact inventory")
    result: dict[str, dict[str, Any]] = {}
    total = 0
    for entry in artifacts:
        if not isinstance(entry, dict) or set(entry) != {
            "path",
            "sha256",
            "size_bytes",
        }:
            raise ValueError("Invalid bundle artifact record")
        path, sha, size = entry["path"], entry["sha256"], entry["size_bytes"]
        if not isinstance(path, str) or not path or len(path) > 4096:
            raise ValueError("Invalid bundle artifact path")
        relative = PurePosixPath(path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in path
            or ":" in path
            or "\x00" in path
            or relative.as_posix() != path
            or path == "manifest.json"
            or path in result
        ):
            raise ValueError("Unsafe or duplicate bundle artifact path")
        if type(size) is not int or size < 0 or not isinstance(sha, str):
            raise ValueError("Invalid bundle artifact size/hash")
        if re.fullmatch(r"[a-f0-9]{64}", sha) is None:
            raise ValueError("Invalid bundle artifact hash")
        total += size
        if total > max_bytes:
            raise ValueError("Existing bundle exceeds output byte limit")
        result[path] = entry
    return result


def _tree_files(target: Path, paths: set[str]) -> dict[str, Path]:
    expected_dirs = {
        parent.as_posix()
        for name in paths
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    }
    found: dict[str, Path] = {}
    pending = [target]
    directories: set[str] = set()
    while pending:
        for entry in pending.pop().iterdir():
            name = entry.relative_to(target).as_posix()
            if entry.is_symlink():
                raise ValueError("Bundle entries cannot be symlinks; files preserved")
            if entry.is_dir():
                if name not in expected_dirs:
                    raise ValueError("Unexpected bundle directory; files preserved")
                directories.add(name)
                pending.append(entry)
            elif name in paths and entry.is_file():
                found[name] = entry
            else:
                raise ValueError("Unexpected bundle entry; files preserved")
    if set(found) != paths or directories != expected_dirs:
        raise ValueError("Bundle files are missing; existing files preserved")
    return found


def inspect_bundle(target: Path, policy: BundlePublicationPolicy) -> str | None:
    if target.is_symlink():
        raise ValueError("Bundle output cannot be a symlink")
    if not target.exists():
        return None
    if not target.is_dir():
        raise ValueError("Bundle output exists and is not a directory")
    before = target.stat()
    try:
        raw, _ = _read_file(
            target / "manifest.json", min(MAX_MANIFEST_BYTES, policy.max_bytes)
        )
        payload = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ValueError(
            "Refusing to replace non-bundle output; files preserved"
        ) from exc
    if not isinstance(payload, dict) or (
        payload.get("doc_id") != policy.doc_id
        or payload.get("bundle_version") != policy.bundle_version
    ):
        raise ValueError("Refusing to replace non-matching bundle")
    checksum = payload.pop("bundle_sha256", None)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if checksum != _hash(canonical.encode("utf-8")):
        raise ValueError("Bundle manifest hash differs; files preserved")
    inventory = _inventory(payload, policy.max_bytes - len(raw))
    files = _tree_files(target, set(inventory) | {"manifest.json"})
    for name, entry in inventory.items():
        data, _ = _read_file(files[name], entry["size_bytes"])
        if len(data) != entry["size_bytes"] or _hash(data) != entry["sha256"]:
            raise ValueError("Bundle was modified; existing notes preserved")
    final, _ = _read_file(target / "manifest.json", len(raw))
    if (
        final != raw
        or target.is_symlink()
        or _identity(target.stat()) != _identity(before)
    ):
        raise ValueError("Bundle changed during verification; files preserved")
    return _hash(raw)
