"""
Unit tests for TableService.
"""

from pathlib import Path
from zipfile import ZipFile

import pytest

from src.application.table_service import TableService


@pytest.fixture
def table_service(tmp_path):
    # Use tmp_path for storage during tests
    from src.infrastructure.excel_renderer import ExcelRenderer

    renderer = ExcelRenderer(tmp_path)
    return TableService(table_output_dir=tmp_path, table_renderer=renderer)


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
    from src.infrastructure.excel_renderer import ExcelRenderer as _ER

    new_service = TableService(table_output_dir=tmp_path, table_renderer=_ER(tmp_path))
    context = new_service.get_table_context(table_id)
    assert len(context.rows) == 1
    assert context.rows[0]["Drug"] == "Remimazolam"


def test_load_existing_tables_includes_non_tbl_context_ids(tmp_path):
    from src.infrastructure.excel_renderer import ExcelRenderer

    table_id = "dfm_docx123_table1"
    (tmp_path / f"{table_id}.json").write_text(
        """{
  "id": "dfm_docx123_table1",
  "intent": "summary",
  "title": "DFM Table",
  "columns": [{"name": "Finding", "type": "text", "required": true}],
  "rows": [{"Finding": "A"}],
  "created_at": "2026-04-29"
}""",
        encoding="utf-8",
    )

    service = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )

    context = service.get_table_context(table_id)
    assert context.rows == [{"Finding": "A"}]


def test_load_existing_tables_preserves_docx_source_guards(tmp_path):
    from src.infrastructure.excel_renderer import ExcelRenderer

    table_id = "dfm_docx123_table1"
    (tmp_path / f"{table_id}.json").write_text(
        """{
  "id": "dfm_docx123_table1",
  "intent": "summary",
  "title": "DFM Table",
  "columns": [{"name": "Finding", "type": "text", "required": true}],
  "rows": [{"Finding": "A"}],
  "source_doc_id": "docx_123",
  "source_block_id": "t001",
  "source_revision_id": "rev-a",
  "source_block_hash": "hash-a",
  "created_at": "2026-04-29"
}""",
        encoding="utf-8",
    )

    service = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )

    context = service.get_table_context(table_id)
    assert context.source_revision_id == "rev-a"
    assert context.source_block_hash == "hash-a"


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


def test_update_cell_removes_stale_citation(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}])
    table_service.add_citation(
        table_id,
        0,
        "Drug",
        [{"source_type": "user_input", "excerpt": "A"}],
    )

    result = table_service.update_cell(table_id, 0, "Drug", "B")

    assert result["citation_removed"] is True
    assert table_service.get_cell(table_id, 0, "Drug")["citation"] is None


def test_update_row_removes_citations_only_for_changed_cells(table_service):
    columns = [{"name": "Drug", "type": "text"}, {"name": "Dose", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A", "Dose": "1 mg"}])
    table_service.add_citation(
        table_id,
        0,
        "Drug",
        [{"source_type": "user_input", "excerpt": "A"}],
    )
    table_service.add_citation(
        table_id,
        0,
        "Dose",
        [{"source_type": "user_input", "excerpt": "1 mg"}],
    )

    table_service.update_row(table_id, 0, {"Drug": "B", "Dose": "1 mg"})

    assert table_service.get_cell(table_id, 0, "Drug")["citation"] is None
    assert table_service.get_cell(table_id, 0, "Dose")["citation"] is not None


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
    # Output dir is already tmp_path from fixture
    columns = [{"name": "Drug", "type": "text"}, {"name": "Dose", "type": "number"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A", "Dose": 1}])

    result = await table_service.render_table(
        table_id, format="excel", filename="test_output"
    )
    assert result["success"] is True
    assert "test_output" in result["file_path"]
    assert result["file_path"].endswith(".xlsx")


@pytest.mark.asyncio
async def test_render_table_sanitizes_excel_filename(table_service, tmp_path):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}])

    result = await table_service.render_table(
        table_id, format="excel", filename="../evil report"
    )

    file_path = Path(result["file_path"])
    assert file_path.parent == tmp_path.resolve()
    assert file_path.name.startswith("evil_report_")


@pytest.mark.asyncio
async def test_render_table_disables_formula_injection(table_service):
    columns = [{"name": "Drug", "type": "text"}, {"name": "Reference", "type": "url"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(
        table_id,
        [
            {
                "Drug": '=HYPERLINK("https://evil.example","click")',
                "Reference": '=cmd|"/C calc"!A0',
            }
        ],
    )

    result = await table_service.render_table(
        table_id, format="excel", filename="formula_probe"
    )

    with ZipFile(result["file_path"]) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert "<f>" not in sheet_xml


@pytest.mark.asyncio
async def test_render_table_html(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test <Unsafe>", columns)
    table_service.add_rows(table_id, [{"Drug": "<script>"}])

    result = await table_service.render_table(table_id, format="html")

    assert result["success"] is True
    assert result["format"] == "html"
    assert "<table>" in result["content"]
    assert "&lt;script&gt;" in result["content"]
