"""Portable native evidence publication boundaries, independent of file IO."""

from __future__ import annotations

from typing import Any, Protocol

NATIVE_WIKI_VERSION = "native-wiki-v1"
MAX_WIKI_BYTES = 128 * 1024 * 1024
MAX_WIKI_CELLS = 20_000


class NativeWikiPublisher(Protocol):
    def publish(
        self,
        output_dir: str,
        snapshot_id: str,
        files: dict[str, bytes],
        *,
        source_path: str | None,
    ) -> dict[str, Any]: ...
