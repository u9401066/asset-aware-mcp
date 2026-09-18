"""Checked replacement of generated bundles, with explicit retained backups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class BundlePublicationPolicy:
    doc_id: str
    bundle_version: str
    max_bytes: int


class BundlePublisher(Protocol):
    def inspect(self, target: Path, policy: BundlePublicationPolicy) -> str | None: ...

    def publish(
        self,
        stage: Path,
        target: Path,
        policy: BundlePublicationPolicy,
        expected_token: str | None,
    ) -> dict[str, Any]: ...
