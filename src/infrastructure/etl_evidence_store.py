"""Bounded extraction capture and immutable, hash-verified evidence storage."""

from __future__ import annotations

import hashlib
import json
import re
from itertools import islice
from pathlib import Path

from src.domain.entities import DocumentManifest
from src.domain.etl_evidence import MAX_ETL_METADATA_BYTES, MAX_ETL_SNAPSHOT_BYTES
from src.infrastructure.encoding_guard import normalize_text_input, safe_decode
from src.infrastructure.native_file_io import _identity, _read_file
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("ETL evidence directory must be a real directory")


class FileEtlSourceReader:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @staticmethod
    def decode_text(data: bytes) -> str:
        return normalize_text_input(safe_decode(data, hint="captured ETL text"))

    def capture(self, doc_id: str, figure_id: str | None) -> dict[str, bytes]:
        if re.fullmatch(r"doc_[a-z0-9_]{1,252}", doc_id) is None:
            raise ValueError("Invalid ETL document ID")
        directory = self.root / doc_id
        _directory(directory)
        directory_identity = _identity(directory.stat())
        files: dict[str, bytes] = {}
        observed: dict[Path, tuple[bytes, tuple[int, int, int, int]]] = {}

        def read(name: str, path: Path, limit: int) -> bytes:
            if ".." in path.parts or not path.is_relative_to(directory):
                raise ValueError("ETL attachment path escapes its document directory")
            for parent in (path, *path.parents):
                if parent == directory:
                    break
                if parent.is_symlink():
                    raise ValueError("ETL attachments cannot use symlinks")
            remaining = MAX_ETL_SNAPSHOT_BYTES - sum(map(len, files.values()))
            data, stat = _read_file(path, min(limit, remaining))
            observed[path] = (data, _identity(stat))
            files[name] = data
            return data

        manifest_data = read(
            "source-manifest.json",
            directory / f"{doc_id}_manifest.json",
            MAX_ETL_METADATA_BYTES,
        )
        manifest = DocumentManifest.model_validate_json(self.decode_text(manifest_data))
        if manifest.doc_id != doc_id:
            raise ValueError("ETL manifest document identity mismatch")
        read("canonical.md", directory / f"{doc_id}_full.md", MAX_ETL_METADATA_BYTES)
        read("blocks.json", directory / "blocks.json", MAX_ETL_METADATA_BYTES)
        suffix = Path(manifest.filename).suffix.lower()
        if re.fullmatch(r"\.[a-z0-9]{1,12}", suffix) is None:
            raise ValueError("ETL source filename has no safe format suffix")
        name = "original" + suffix
        read(name, directory / name, MAX_ETL_SNAPSHOT_BYTES)
        if figure_id is not None:
            figure = manifest.assets.find_figure(figure_id)
            if figure is None:
                raise ValueError("ETL figure not found")
            for role, raw in (("figure", figure.path), ("raw-figure", figure.raw_path)):
                if not raw:
                    if role == "figure":
                        raise ValueError("ETL figure has no image attachment")
                    continue
                path = Path(raw)
                if not path.is_absolute():
                    path = directory / path
                extension = path.suffix.lower()
                if extension not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                    raise ValueError("Unsupported ETL image attachment format")
                read(role + extension, path, MAX_ETL_METADATA_BYTES)
        # Compare every captured artifact again. Neither stale manifest metadata nor
        # a file changed midway through a multi-file read can certify one snapshot.
        for path, (expected, identity) in observed.items():
            current, stat = _read_file(path, len(expected))
            if current != expected or _identity(stat) != identity:
                raise ValueError("ETL source artifacts changed during capture")
        _directory(directory)
        if _identity(directory.stat()) != directory_identity:
            raise ValueError("ETL source directory changed during capture")
        return files


class FileEtlSnapshotRepository:
    def __init__(self, root: Path):
        if root.is_symlink():
            raise ValueError("ETL snapshot root cannot be a symlink")
        self.root = root.resolve()
        self.publisher = FileNativeWikiPublisher()

    def save(self, snapshot_id: str, files: dict[str, bytes]) -> None:
        if _sha(files["manifest.json"]) != snapshot_id:
            raise ValueError("ETL snapshot manifest hash mismatch")
        result = self.publisher.publish(
            str(self.root), snapshot_id, files, source_path=None
        )
        if not result["success"]:
            raise ValueError(result["error"])

    def read(self, snapshot_id: str) -> dict[str, bytes]:
        if re.fullmatch(r"[a-f0-9]{64}", snapshot_id) is None:
            raise ValueError("Invalid ETL snapshot ID")
        _directory(self.root)
        directory = self.root / ("native-" + snapshot_id)
        _directory(directory)
        before = _identity(directory.stat())
        manifest_data, manifest_stat = _read_file(
            directory / "manifest.json", MAX_ETL_METADATA_BYTES
        )
        if _sha(manifest_data) != snapshot_id:
            raise ValueError("ETL snapshot manifest integrity mismatch")
        manifest = json.loads(manifest_data)
        if not isinstance(manifest, dict):
            raise ValueError("Invalid ETL snapshot manifest")
        inventory = manifest.get("files")
        if (
            manifest.get("schema_version") != "etl-evidence-snapshot-v1"
            or not isinstance(inventory, dict)
            or not 4 <= len(inventory) <= 8
            or "evidence.json" not in inventory
            or "manifest.json" in inventory
        ):
            raise ValueError("Invalid ETL snapshot inventory")
        files = {"manifest.json": manifest_data}
        identities = {"manifest.json": _identity(manifest_stat)}
        for name, entry in inventory.items():
            if re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,99}", name) is None:
                raise ValueError("Unsafe ETL snapshot artifact name")
            if not isinstance(entry, dict) or type(entry.get("size_bytes")) is not int:
                raise ValueError("Invalid ETL snapshot artifact size")
            size = entry["size_bytes"]
            if size < 0 or size > MAX_ETL_SNAPSHOT_BYTES - sum(
                map(len, files.values())
            ):
                raise ValueError("ETL snapshot exceeds its byte limit")
            data, stat = _read_file(directory / name, size)
            if len(data) != size or _sha(data) != entry.get("sha256"):
                raise ValueError("ETL snapshot artifact integrity mismatch: " + name)
            files[name] = data
            identities[name] = _identity(stat)
        if manifest.get("record_sha256") != _sha(files["evidence.json"]):
            raise ValueError("ETL manifest record hash mismatch")
        if {p.name for p in islice(directory.iterdir(), len(files) + 1)} != set(files):
            raise ValueError("ETL snapshot inventory differs")
        for name, identity in identities.items():
            path = directory / name
            if path.is_symlink() or _identity(path.stat()) != identity:
                raise ValueError("ETL snapshot changed during verification")
        _directory(directory)
        if _identity(directory.stat()) != before:
            raise ValueError("ETL snapshot directory changed during verification")
        return files
