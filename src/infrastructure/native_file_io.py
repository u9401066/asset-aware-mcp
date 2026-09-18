"""Bounded native file IO, crash-released locks and explicit source publication."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.native_assets import MAX_NATIVE_BYTES, NativeSource

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_file(path: Path, limit: int) -> tuple[bytes, os.stat_result]:
    descriptor = os.open(
        path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("Expected a regular file within the byte limit")
        data = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
    if len(data) > limit or _identity(before) != _identity(after):
        raise ValueError("Source changed while being read")
    if path.is_symlink() or _identity(path.stat()) != _identity(after):
        raise ValueError("Source path changed while being read")
    return data, after


def _identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _source(path: Path, data: bytes, info: os.stat_result) -> NativeSource:
    return NativeSource(
        path=str(path),
        sha256=_digest(data),
        size_bytes=len(data),
        mtime_ns=info.st_mtime_ns,
        device=info.st_dev,
        inode=info.st_ino,
    )


def _write_atomic(path: Path, data: bytes, *, limit: int) -> None:
    if len(data) > limit:
        raise ValueError("Native asset output exceeds byte limit")
    descriptor, temp = tempfile.mkstemp(prefix=".native-stage-", dir=path.parent)
    stage = Path(temp)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        stage.replace(path)
    finally:
        stage.unlink(missing_ok=True)


@contextmanager
def operation_lock(directory: Path) -> Iterator[Path]:
    lock = directory / ".operation.lock"
    if lock.is_symlink():
        raise ValueError("Native operation lock cannot be a symlink")
    descriptor = os.open(
        lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    acquired = False
    try:
        if lock.is_symlink():
            raise ValueError("Native operation lock cannot be a symlink")
        if sys.platform == "win32":
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        yield directory
    except OSError as exc:
        if not acquired and exc.errno in {errno.EACCES, errno.EAGAIN}:
            raise ValueError(
                "Native asset is busy; retry after the active operation completes"
            ) from exc
        raise
    finally:
        try:
            if acquired:
                if sys.platform == "win32":
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def publish_new_file(
    target: Path, data: bytes, expected_revision: str
) -> dict[str, Any]:
    descriptor, temporary = tempfile.mkstemp(
        prefix=".native-publish-", dir=target.parent
    )
    stage = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(stage, target)
    finally:
        stage.unlink(missing_ok=True)
    written, _ = _read_file(target, MAX_NATIVE_BYTES)
    if _digest(written) != expected_revision:
        raise ValueError("Published file changed externally after creation")
    return {"success": True, "path": str(target), "sha256": expected_revision}


class NativeSourcePublication:
    def __init__(self, source: NativeSource, data: bytes):
        self.source = source
        self.data = data
        self.path = Path(source.path)
        self.backup = self.path.with_name(
            ".native-backup-" + uuid.uuid4().hex + self.path.suffix
        )
        self.source_written = False

    def execute(self, save_source: Callable[[NativeSource], None]) -> dict[str, Any]:
        before, info = _read_file(self.path, MAX_NATIVE_BYTES)
        if _source(self.path, before, info) != self.source:
            raise ValueError(
                "Source changed externally; refresh/reconcile it before writeback"
            )
        if before == self.data:
            return {
                "success": True,
                "path": str(self.path),
                "sha256": _digest(self.data),
                "changed": False,
            }
        try:
            self._replace(before, info)
            written, current = _read_file(self.path, MAX_NATIVE_BYTES)
            if written != self.data:
                raise ValueError(
                    "Source changed after writeback; original backup retained"
                )
            save_source(_source(self.path, written, current))
        except (OSError, ValueError) as exc:
            if not self.source_written:
                raise
            return self._failed_publication(exc)
        return {
            "success": True,
            "path": str(self.path),
            "sha256": _digest(self.data),
            "changed": True,
            "source_written": True,
            "backup_path": str(self.backup),
            "checks": ["source_hash_and_stat", "revision_hash", "written_bytes_match"],
            "concurrency_scope": "Service operations are serialized; external writers must coordinate and inspect the retained backup.",
        }

    def _replace(self, before: bytes, info: os.stat_result) -> None:
        descriptor, temporary = tempfile.mkstemp(
            prefix=".native-writeback-", dir=self.path.parent
        )
        stage = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(self.data)
                handle.flush()
                os.fsync(handle.fileno())
            stage.chmod(stat.S_IMODE(info.st_mode))
            # Retain the original inode, including late writes through another
            # application's already-open descriptor. Never auto-delete it.
            os.link(self.path, self.backup, follow_symlinks=False)
            checked, current = _read_file(self.path, MAX_NATIVE_BYTES)
            if checked != before or _identity(current) != _identity(info):
                raise ValueError(
                    "Source changed before writeback; original backup retained"
                )
            stage.replace(self.path)
            self.source_written = True
        finally:
            stage.unlink(missing_ok=True)

    def _failed_publication(self, error: Exception) -> dict[str, Any]:
        return {
            "success": False,
            "source_written": True,
            "path": str(self.path),
            "backup_path": str(self.backup),
            "error": str(error),
            "reconciliation_required": True,
            "guidance": "Inspect the source and retained backup before another writeback; source bytes changed but final verification/metadata publication failed.",
        }
