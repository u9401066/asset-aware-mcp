"""Serialize bundle publication and retain replaced trees for late external writes."""

from __future__ import annotations

import shutil
import uuid
from typing import TYPE_CHECKING, Any

from src.infrastructure.bundle_inventory import inspect_bundle
from src.infrastructure.native_file_io import operation_lock

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.bundle_publication import BundlePublicationPolicy


class FileBundlePublisher:
    def inspect(self, target: Path, policy: BundlePublicationPolicy) -> str | None:
        return inspect_bundle(target, policy)

    def publish(
        self,
        stage: Path,
        target: Path,
        policy: BundlePublicationPolicy,
        expected_token: str | None,
    ) -> dict[str, Any]:
        with operation_lock(target.parent):
            current = inspect_bundle(target, policy)
            if current != expected_token:
                raise ValueError(
                    "Bundle changed since export started; retry without replacing notes"
                )
            staged = inspect_bundle(stage, policy)
            if staged is None:
                raise ValueError("Bundle stage is missing")
            if current == staged:
                if inspect_bundle(target, policy) != current:
                    raise ValueError("Bundle changed before identical export reuse")
                shutil.rmtree(stage)
                return {"reused": True, "backup_path": None}
            return self._replace(stage, target, policy, expected_token, staged)

    @staticmethod
    def _replace(
        stage: Path,
        target: Path,
        policy: BundlePublicationPolicy,
        expected_token: str | None,
        staged_token: str,
    ) -> dict[str, Any]:
        backup = None
        if target.exists():
            backup = target.with_name(f".{target.name}.backup-{uuid.uuid4().hex}")
            target.rename(backup)
        try:
            if backup is not None and inspect_bundle(backup, policy) != expected_token:
                raise ValueError("Bundle changed during publication")
            if target.exists() or target.is_symlink():
                raise ValueError("Bundle output appeared during publication")
            stage.rename(target)
            if inspect_bundle(target, policy) != staged_token:
                raise ValueError("Published bundle changed during verification")
        except (OSError, ValueError) as exc:
            if backup is not None:
                if not target.exists() and not target.is_symlink():
                    backup.rename(target)
                else:
                    raise ValueError(
                        f"Publication conflict; previous files retained at {backup}"
                    ) from exc
            raise
        return {"reused": False, "backup_path": str(backup) if backup else None}
