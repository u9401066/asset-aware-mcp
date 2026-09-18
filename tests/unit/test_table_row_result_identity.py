"""Agent-visible operation targets must follow resolved stable IDs after reindexing."""

from __future__ import annotations

import pytest

from src.application.table_service import TableService
from src.infrastructure.excel_renderer import ExcelRenderer
from src.presentation.tools import table_tools


@pytest.fixture
def table(tmp_path, monkeypatch):
    service = TableService(tmp_path, ExcelRenderer(tmp_path))
    identity = service.create_table(
        "citation", "Stable rows", [{"name": "Value", "type": "text"}]
    )
    service.add_rows(
        identity, [{"Value": "first"}, {"Value": "target"}, {"Value": "last"}]
    )
    row_id = service.get_table_context(identity).row_ids[1]
    service.add_citation(
        identity, 1, "Value", [{"source_type": "user_input", "excerpt": "source"}]
    )
    service.delete_row(identity, 0)
    monkeypatch.setattr(table_tools, "table_service", service)
    return service, identity, row_id


@pytest.mark.parametrize(
    "operation",
    ["get_row", "get_cell", "update_cell", "update_row", "delete_row", "clear_cell"],
)
@pytest.mark.parametrize("input_index", [-1, 99])
async def test_data_results_name_resolved_target(table, operation, input_index):
    service, identity, row_id = table
    kwargs = {"column_name": "Value"} if "cell" in operation else {}
    if operation == "update_cell":
        kwargs["value"] = "updated"
    if operation == "update_row":
        kwargs["row"] = {"Value": "updated"}
    result = await table_tools.table_data(
        operation, identity, row_index=input_index, row_id=row_id, **kwargs
    )
    assert "❌" not in result
    assert row_id in result
    assert f"Row {input_index}" not in result and f"[{input_index}:" not in result
    if operation == "delete_row":
        assert service.get_table_context(identity).rows == [{"Value": "last"}]
    else:
        assert service.get_table_context(identity).row_ids[0] == row_id


@pytest.mark.parametrize("operation", ["remove", "cell_history"])
async def test_citation_results_name_stable_target(table, operation):
    _, identity, row_id = table
    result = await table_tools.table_cite(
        operation, identity, row_id=row_id, column_name="Value"
    )
    assert "❌" not in result and row_id in result and "[-1:" not in result


@pytest.mark.parametrize(
    "operation", ["update_row", "delete_row", "clear_cell", "remove_citation"]
)
def test_service_result_contains_resolved_identity(table, operation):
    service, identity, row_id = table
    positional = (
        [{"Value": "updated"}]
        if operation == "update_row"
        else ["Value"]
        if operation in {"clear_cell", "remove_citation"}
        else []
    )
    result = getattr(service, operation)(identity, -1, *positional, row_id=row_id)
    assert result["row_id"] == row_id and result["row_index"] == 0
