"""
Unit tests for TableService.
"""

import pytest

from src.application.table_service import TableService


@pytest.fixture
def table_service(tmp_path):
    # Use tmp_path for storage during tests
    from src.infrastructure.config import settings

    settings.table_output_dir = tmp_path
    return TableService()


def test_create_table(table_service, tmp_path):
    columns = [
        {"name": "Drug", "type": "text"},
        {"name": "Dose", "type": "number"},
        {"name": "Route", "type": "enum", "enum_values": ["IV", "IM"]},
    ]
    table_id = table_service.create_table(
        intent="comparison", title="Test Table", columns=columns
    )

    assert table_id.startswith("tbl_")
    context = table_service.get_table_context(table_id)
    assert context.title == "Test Table"
    assert len(context.columns) == 3

    # Check persistence
    assert (tmp_path / f"{table_id}.json").exists()
    assert (tmp_path / f"{table_id}.md").exists()


def test_add_rows_persistence(table_service, tmp_path):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)

    table_service.add_rows(table_id, [{"Drug": "Remimazolam"}])

    # Reload service to check persistence
    new_service = TableService()
    context = new_service.get_table_context(table_id)
    assert len(context.rows) == 1
    assert context.rows[0]["Drug"] == "Remimazolam"


def test_update_delete_row(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}, {"Drug": "B"}])

    # Update
    table_service.update_row(table_id, 0, {"Drug": "C"})
    assert table_service.get_table_context(table_id).rows[0]["Drug"] == "C"

    # Delete
    table_service.delete_row(table_id, 0)
    assert table_service.get_table_context(table_id).row_count == 1
    assert table_service.get_table_context(table_id).rows[0]["Drug"] == "B"


def test_delete_table(table_service, tmp_path):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    assert (tmp_path / f"{table_id}.json").exists()

    table_service.delete_table(table_id)
    assert not (tmp_path / f"{table_id}.json").exists()
    with pytest.raises(ValueError):
        table_service.get_table_context(table_id)


def test_add_rows_valid(table_service):
    columns = [{"name": "Drug", "type": "text"}, {"name": "Dose", "type": "number"}]
    table_id = table_service.create_table("comparison", "Test", columns)

    rows = [{"Drug": "Remimazolam", "Dose": 0.2}, {"Drug": "Propofol", "Dose": 2.0}]
    result = table_service.add_rows(table_id, rows)

    assert result["success"] is True
    assert result["added"] == 2
    assert table_service.get_table_context(table_id).row_count == 2


def test_add_rows_invalid_type(table_service):
    columns = [{"name": "Dose", "type": "number"}]
    table_id = table_service.create_table("comparison", "Test", columns)

    rows = [{"Dose": "high"}]  # Should be number
    result = table_service.add_rows(table_id, rows)

    assert result["success"] is False
    assert result["added"] == 0
    assert len(result["errors"]) == 1


def test_preview_table(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}, {"Drug": "B"}])

    preview = table_service.preview_table(table_id)
    assert "### Test" in preview
    assert "| Drug |" in preview
    assert "| A |" in preview
    assert "| B |" in preview


@pytest.mark.asyncio
async def test_render_table_excel(table_service, tmp_path):
    # Override output dir for test
    table_service._excel_renderer.output_dir = tmp_path

    columns = [{"name": "Drug", "type": "text"}, {"name": "Dose", "type": "number"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A", "Dose": 1}])

    result = await table_service.render_table(
        table_id, format="excel", filename="test_output"
    )
    assert result["success"] is True
    assert "test_output" in result["file_path"]
    assert result["file_path"].endswith(".xlsx")
