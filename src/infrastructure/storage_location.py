"""Detect DATA_DIR locations where cross-machine file locking is unreliable.

DOCX concurrent editing serializes writers with an SQLite lock in each
document directory. That lock is reliable between processes on one computer,
but cloud-sync clients (Google Drive, OneDrive, Dropbox, iCloud) and network
shares do not carry it to other machines, and a sync client can upload a file
mid-write or create conflicted copies. Such locations still work; callers get
a warning explaining single-writer use. Detection is best effort and never
raises.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SYNC_FOLDER_MARKERS: tuple[tuple[str, str], ...] = (
    ("我的雲端硬碟", "Google Drive"),
    ("我的云端硬盘", "Google Drive"),
    ("共用雲端硬碟", "Google Drive (shared drive)"),
    ("google drive", "Google Drive"),
    ("googledrive", "Google Drive"),
    ("drivefs", "Google Drive (DriveFS)"),
    ("my drive", "Google Drive"),
    ("shared drives", "Google Drive (shared drive)"),
    ("onedrive", "OneDrive"),
    ("dropbox", "Dropbox"),
    ("iclouddrive", "iCloud Drive"),
    ("icloud drive", "iCloud Drive"),
    ("mobile documents/com~apple~clouddocs", "iCloud Drive"),
    ("library/cloudstorage", "a macOS cloud-storage provider folder"),
)
_ONEDRIVE_ENV = ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")
_NETWORK_FILESYSTEMS = frozenset(
    {
        "nfs",
        "nfs4",
        "cifs",
        "smbfs",
        "smb3",
        "sshfs",
        "fuse.sshfs",
        "fuse.rclone",
        "fuse.gcsfuse",
        "9p",
        "afs",
        "ceph",
        "glusterfs",
    }
)
_DRIVE_REMOTE = 4  # GetDriveTypeW


def _windows_drive_info(path: str) -> tuple[int | None, str]:
    """Return (drive type, volume label) for a Windows drive letter path."""
    if sys.platform != "win32" or len(path) < 2 or path[1] != ":":
        return None, ""
    try:
        import ctypes

        root = path[:2] + "\\"
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        drive_type = int(kernel32.GetDriveTypeW(ctypes.c_wchar_p(root)))
        label = ctypes.create_unicode_buffer(261)
        fs_name = ctypes.create_unicode_buffer(261)
        ok = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            label,
            len(label),
            None,
            None,
            None,
            fs_name,
            len(fs_name),
        )
        return drive_type, label.value if ok else ""
    except Exception:
        return None, ""


def _linux_mount_fstype(path: str) -> str | None:
    mounts = Path("/proc/mounts")
    if not sys.platform.startswith("linux") or not mounts.is_file():
        return None
    try:
        best = ("", "")
        for line in mounts.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            mount_point = parts[1].replace("\\040", " ")
            if (
                path == mount_point or path.startswith(mount_point.rstrip("/") + "/")
            ) and len(mount_point) > len(best[0]):
                best = (mount_point, parts[2])
        return best[1] or None
    except OSError:
        return None


def _location_kind(path: Path) -> str | None:
    text = str(path)
    lowered = text.replace("\\", "/").lower()
    if text.startswith(("\\\\", "//")):
        return "a network (UNC) share"
    for marker, kind in _SYNC_FOLDER_MARKERS:
        if marker in lowered:
            return f"inside a {kind} sync folder"
    for name in _ONEDRIVE_ENV:
        root = os.environ.get(name)
        if root and lowered.startswith(
            root.replace("\\", "/").lower().rstrip("/") + "/"
        ):
            return "inside a OneDrive sync folder"
    drive_type, label = _windows_drive_info(text)
    if label and "google drive" in label.lower():
        return "on the Google Drive (DriveFS) virtual drive"
    if drive_type == _DRIVE_REMOTE:
        return "on a mapped network drive"
    fstype = _linux_mount_fstype(text)
    if fstype and (fstype in _NETWORK_FILESYSTEMS or fstype.startswith("fuse.")):
        return f"on a network/FUSE file system ({fstype})"
    return None


def describe_storage_risk(path: Path | str) -> str | None:
    """Warning text when ``path`` is cloud-synced or remote, else ``None``."""
    try:
        resolved = Path(path).expanduser()
        kind = _location_kind(resolved)
    except Exception:
        return None
    if kind is None:
        return None
    return (
        f"DATA_DIR {resolved} appears to be {kind}. Concurrent DOCX editing is "
        "serialized by an SQLite lock that works between processes on this "
        "computer only; sync clients and network shares do not carry it to other "
        "machines and may upload files mid-write or create conflicted copies. "
        "Edit a document from one computer at a time (pause sync or keep other "
        "machines read-only), or move DATA_DIR to a local disk for heavy "
        "multi-agent use. Nothing is refused because of this warning."
    )
