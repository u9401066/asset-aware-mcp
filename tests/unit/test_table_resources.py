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


class _FakeListTableService:
    def list_tables(self) -> list[dict[str, object]]:
        return [
            {
                "id": "tbl|1",
                "title": "Alpha | Beta",
                "intent": "compare | summarize",
                "rows": 2,
                "created_at": "2026-05-07",
            }
        ]

    def list_drafts(self) -> list[dict[str, object]]:
        return [
            {
                "id": "draft|1",
                "title": "Draft | Title",
                "intent": "extract | cite",
                "columns_planned": 3,
                "pending_rows": 1,
                "has_table": False,
            }
        ]


@pytest.mark.asyncio
async def test_table_list_resource_escapes_pipe_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.resources import table_resources

    monkeypatch.setattr(table_resources, "table_service", _FakeListTableService())

    result = await table_resources.resource_table_list()

    assert "`tbl\\|1`" in result
    assert "Alpha \\| Beta" in result
    assert "compare \\| summarize" in result


@pytest.mark.asyncio
async def test_draft_list_resource_escapes_pipe_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.resources import table_resources

    monkeypatch.setattr(table_resources, "table_service", _FakeListTableService())

    result = await table_resources.resource_draft_list()

    assert "`draft\\|1`" in result
    assert "Draft \\| Title" in result
    assert "extract \\| cite" in result
