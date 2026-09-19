"""Read a fresh atomic A2T JSON snapshot independently of mutable service caches."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from src.domain.table_state import table_from_state
from src.infrastructure.native_file_io import _read_file

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.table_entities import TableContext


class FileTableWorkspaceReader:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def read_workspace(self, table_id: str) -> TableContext:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", table_id) or table_id in {
            ".",
            "..",
        }:
            raise ValueError("Invalid table workspace ID")
        path = self.root / f"{table_id}.json"
        data, _ = _read_file(path, 16 * 1024 * 1024)
        context = table_from_state(json.loads(data))
        if context.id != table_id:
            raise ValueError("Table workspace file identity mismatch")
        return context
