from __future__ import annotations

from pathlib import Path

import pytest


class _FakeTableService:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir

    def get_table_context(self, table_id: str) -> object:
        if table_id == "../secret":
            return object()
        raise ValueError(table_id)

    def preview_table(self, table_id: str, limit: int = 100) -> str:
        return f"preview:{table_id}:{limit}"


@pytest.mark.asyncio
async def test_table_content_resource_blocks_path_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "secret.md"
    secret_path.write_text("do not leak", encoding="utf-8")
    storage_dir = tmp_path / "tables"
    storage_dir.mkdir()

    from src.presentation.resources import table_resources

    monkeypatch.setattr(
        table_resources,
        "table_service",
        _FakeTableService(storage_dir),
    )

    result = await table_resources.resource_table_content("../secret")

    assert result == "Table not found: ../secret"
    assert "do not leak" not in result
