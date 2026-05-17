"""
Unit tests for TableService.
"""

import json
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
    assert context.row_ids[0].startswith("row_")


def test_legacy_table_backfills_and_persists_stable_row_ids(tmp_path):
    from src.infrastructure.excel_renderer import ExcelRenderer

    table_id = "tbl_legacy"
    (tmp_path / f"{table_id}.json").write_text(
        """{
  "id": "tbl_legacy",
  "intent": "summary",
  "title": "Legacy Table",
  "columns": [{"name": "Finding", "type": "text", "required": true}],
  "rows": [{"Finding": "A"}, {"Finding": "B"}],
  "created_at": "2026-04-29"
}""",
        encoding="utf-8",
    )
    service = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )

    context = service.get_table_context(table_id)
    first_ids = list(context.row_ids)
    service.add_rows(table_id, [{"Finding": "C"}])

    reloaded = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )
    assert reloaded.get_table_context(table_id).row_ids[:2] == first_ids
    persisted = json.loads((tmp_path / f"{table_id}.json").read_text("utf-8"))
    assert persisted["schema_version"] == "a2t-table-v2"
    assert persisted["row_ids"][:2] == first_ids


def test_legacy_table_replaces_unsafe_row_ids(tmp_path):
    from src.infrastructure.excel_renderer import ExcelRenderer

    table_id = "tbl_legacy_bad_row_id"
    (tmp_path / f"{table_id}.json").write_text(
        """{
  "id": "tbl_legacy_bad_row_id",
  "intent": "summary",
  "title": "Legacy Table",
  "columns": [{"name": "Finding", "type": "text", "required": true}],
  "rows": [{"Finding": "A"}],
  "row_ids": ["bad:id"],
  "created_at": "2026-04-29"
}""",
        encoding="utf-8",
    )
    service = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )

    context = service.get_table_context(table_id)

    assert context.row_ids[0].startswith("row_")
    assert ":" not in context.row_ids[0]


def test_table_service_skips_large_table_files_on_startup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Large persisted table files should not be loaded during MCP startup."""
    from src.infrastructure.excel_renderer import ExcelRenderer

    table_path = tmp_path / "tbl_huge.json"
    table_path.write_text("x" * 200, encoding="utf-8")
    monkeypatch.setenv("ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES", "100")

    service = TableService(
        table_output_dir=tmp_path, table_renderer=ExcelRenderer(tmp_path)
    )

    tables = service.list_tables()
    assert tables[0]["id"] == "tbl_huge"
    assert tables[0]["load_status"] == "skipped_large"
    assert tables[0]["artifact_bytes"] == 200


def test_large_table_skip_uses_manifest_for_visible_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.infrastructure.excel_renderer import ExcelRenderer

    (tmp_path / "tbl_huge.json").write_text("x" * 200, encoding="utf-8")
    (tmp_path / "tbl_huge.manifest.json").write_text(
        json.dumps(
            {
                "table_id": "tbl_huge",
                "title": "Huge Table",
                "intent": "comparison",
                "row_count": 120000,
                "columns": ["Drug"],
                "citation_count": 3,
                "created_at": "2026-05-17",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES", "100")

    service = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )

    table = service.list_tables()[0]
    assert table["title"] == "Huge Table"
    assert table["rows"] == 120000
    assert table["columns"] == ["Drug"]


def test_skipped_large_table_status_and_delete_are_actionable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.infrastructure.excel_renderer import ExcelRenderer

    table_path = tmp_path / "tbl_huge.json"
    table_path.write_text("x" * 200, encoding="utf-8")
    (tmp_path / "tbl_huge.manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES", "100")
    service = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )

    with pytest.raises(ValueError, match="skipped_large"):
        service.get_table_context("tbl_huge")

    assert service.delete_table("tbl_huge") is True
    assert not table_path.exists()
    assert not (tmp_path / "tbl_huge.manifest.json").exists()


def test_table_citation_preserves_locator_source_hash(table_service, tmp_path):
    columns = [{"name": "Finding", "type": "text"}]
    table_id = table_service.create_table("citation", "Evidence", columns)
    table_service.add_rows(table_id, [{"Finding": "Signal"}])

    ref = {
        "source_type": "span",
        "doc_id": "doc_demo",
        "span_id": "span_1",
        "block_id": "blk_1",
        "source_revision_id": "rev-1",
        "locator_version": "blocks-v1",
        "locator_source_sha256": "abc123hash",
        "quote": "Signal",
        "quote_sha256": "quotehash",
    }

    table_service.add_citation(table_id, 0, "Finding", [ref])

    persisted = json.loads((tmp_path / f"{table_id}.json").read_text(encoding="utf-8"))
    citation_key = next(
        key for key in persisted["citations"] if key.endswith(":Finding")
    )
    assert citation_key.startswith("rid:row_")
    persisted_ref = persisted["citations"][citation_key]["refs"][0]
    assert persisted_ref["locator_source_sha256"] == "abc123hash"

    from src.infrastructure.excel_renderer import ExcelRenderer

    reloaded = TableService(
        table_output_dir=tmp_path,
        table_renderer=ExcelRenderer(tmp_path),
    )
    citation = reloaded.get_cell(table_id, 0, "Finding")["citation"]
    assert citation["refs"][0]["locator_source_sha256"] == "abc123hash"


def test_table_persistence_write_failure_preserves_existing_json(
    table_service, tmp_path, monkeypatch
):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "Remimazolam"}])
    json_path = tmp_path / f"{table_id}.json"
    markdown_path = tmp_path / f"{table_id}.md"
    original_json = json_path.read_text(encoding="utf-8")
    original_markdown = markdown_path.read_text(encoding="utf-8")
    original_dump = json.dump

    def fail_after_partial_write(payload, fp, *args, **kwargs):
        fp.write('{"partial"')
        raise OSError("simulated table persistence failure")

    monkeypatch.setattr(
        "src.application.table_service.json.dump", fail_after_partial_write
    )

    with pytest.raises(OSError, match="simulated table persistence failure"):
        table_service.add_rows(table_id, [{"Drug": "Propofol"}])

    monkeypatch.setattr("src.application.table_service.json.dump", original_dump)
    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert persisted == json.loads(original_json)
    assert markdown_path.read_text(encoding="utf-8") == original_markdown


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


def test_delete_row_preserves_row_id_citation_for_remaining_rows(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}, {"Drug": "B"}])
    context = table_service.get_table_context(table_id)
    b_row_id = context.row_id_for_index(1)
    table_service.add_citation(
        table_id,
        1,
        "Drug",
        [{"source_type": "user_input", "excerpt": "B"}],
    )

    table_service.delete_row(table_id, 0)

    assert table_service.get_table_context(table_id).row_id_for_index(0) == b_row_id
    assert "Drug" in table_service.get_citations(table_id, row_id=b_row_id)["citations"]
    assert table_service.get_citations(table_id, 0, "Drug")["citation"] is not None


def test_query_rows_supports_paging_search_filters_columns_and_coverage(table_service):
    columns = [{"name": "Drug", "type": "text"}, {"name": "Dose", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(
        table_id,
        [
            {"Drug": "Remimazolam", "Dose": "1 mg"},
            {"Drug": "Propofol", "Dose": "2 mg"},
            {"Drug": "Remimazolam", "Dose": "3 mg"},
        ],
    )
    table_service.add_citation(
        table_id,
        0,
        "Drug",
        [{"source_type": "user_input", "excerpt": "Remimazolam"}],
    )

    page = table_service.query_rows(
        table_id,
        offset=0,
        limit=1,
        search="Remimazolam",
        filters={"Drug": "Remimazolam"},
        columns=["Drug"],
        include_coverage=True,
    )

    assert page["matched_count"] == 2
    assert page["page"]["next_offset"] == 1
    assert page["rows"][0]["row_id"].startswith("row_")
    assert page["rows"][0]["data"] == {"Drug": "Remimazolam"}
    assert page["rows"][0]["coverage"] == {
        "cited_cells": 1,
        "total_cells": 2,
        "coverage_ratio": 0.5,
    }


def test_query_rows_rejects_unknown_columns(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}])

    with pytest.raises(ValueError, match="Unknown column"):
        table_service.query_rows(table_id, columns=["Missing"])

    with pytest.raises(ValueError, match="Unknown column"):
        table_service.query_rows(table_id, filters={"Missing": "A"})


def test_query_rows_pages_without_materializing_all_matches(table_service, monkeypatch):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(
        table_id,
        [{"Drug": f"Drug {index}"} for index in range(600)],
    )
    context = table_service.get_table_context(table_id)
    original_row_id_for_index = type(context).row_id_for_index
    requested_indices: list[int] = []

    def tracking_row_id_for_index(self, index: int) -> str:
        requested_indices.append(index)
        return original_row_id_for_index(self, index)

    monkeypatch.setattr(
        type(context),
        "row_id_for_index",
        tracking_row_id_for_index,
    )

    page = table_service.query_rows(table_id, offset=10, limit=5)

    assert page["matched_count"] == 600
    assert page["page"] == {"offset": 10, "limit": 5, "next_offset": 15}
    assert [row["row_index"] for row in page["rows"]] == [10, 11, 12, 13, 14]
    assert requested_indices == [10, 11, 12, 13, 14]


def test_unknown_row_id_does_not_fall_back_to_table_citations(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}])
    table_service.add_citation(
        table_id,
        0,
        "Drug",
        [{"source_type": "user_input", "excerpt": "A"}],
    )

    with pytest.raises(ValueError, match="Unknown row_id"):
        table_service.get_citations(table_id, row_id="row_missing")


def test_history_uses_stable_row_id_after_deleting_prior_row(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}, {"Drug": "B"}])
    b_row_id = table_service.get_table_context(table_id).row_id_for_index(1)

    table_service.update_cell(table_id, 1, "Drug", "B2")
    table_service.delete_row(table_id, 0)

    history = table_service.get_cell_history(
        table_id,
        -1,
        "Drug",
        row_id=b_row_id,
    )
    assert [entry["operation"] for entry in history] == ["update_cell"]


def test_clear_cell_accepts_row_id(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}])
    row_id = table_service.get_table_context(table_id).row_id_for_index(0)

    result = table_service.clear_cell(table_id, -1, "Drug", row_id=row_id)

    assert result["success"] is True
    assert table_service.get_cell(table_id, 0, "Drug")["value"] is None


def test_citation_coverage_ignores_stale_keys(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A"}])
    context = table_service.get_table_context(table_id)
    table_service.add_citation(
        table_id,
        0,
        "Drug",
        [{"source_type": "user_input", "excerpt": "A"}],
    )
    context.citations["99:Drug"] = context.citations[next(iter(context.citations))]
    context.citations["0:Missing"] = context.citations[next(iter(context.citations))]
    context.citations["malformed"] = context.citations[next(iter(context.citations))]
    context.citations["rid:broken"] = context.citations[next(iter(context.citations))]

    coverage = table_service.citation_coverage(table_id)

    assert coverage["cited_cells"] == 1
    assert coverage["stale_citation_count"] == 4


def test_citation_coverage_pages_rows_without_full_materialization(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(
        table_id,
        [{"Drug": f"Drug {index}"} for index in range(600)],
    )

    coverage = table_service.citation_coverage(table_id, offset=10, limit=5)

    assert coverage["page"] == {"offset": 10, "limit": 5, "next_offset": 15}
    assert len(coverage["rows"]) == 5
    assert coverage["rows"][0]["row_index"] == 10


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


def test_update_cell_rejects_values_that_violate_column_schema(table_service):
    columns = [
        {"name": "Dose", "type": "number"},
        {"name": "Route", "type": "enum", "enum_values": ["IV", "PO"]},
    ]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Dose": 1.0, "Route": "IV"}])

    with pytest.raises(ValueError, match="must be a number"):
        table_service.update_cell(table_id, 0, "Dose", "high")
    with pytest.raises(ValueError, match="Invalid value for enum column"):
        table_service.update_cell(table_id, 0, "Route", "IM")

    assert table_service.get_cell(table_id, 0, "Dose")["value"] == 1.0
    assert table_service.get_cell(table_id, 0, "Route")["value"] == "IV"


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


def test_rename_column_rejects_existing_column_name_preserves_data_and_citations(
    table_service,
):
    columns = [{"name": "Drug", "type": "text"}, {"name": "Dose", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(table_id, [{"Drug": "A", "Dose": "1 mg"}])
    table_service.add_citation(
        table_id,
        0,
        "Drug",
        [{"source_type": "user_input", "excerpt": "A"}],
    )

    result = table_service.rename_column(table_id, "Drug", "Dose")

    assert result == {"success": False, "error": "Column 'Dose' already exists"}
    context = table_service.get_table_context(table_id)
    assert context.column_names == ["Drug", "Dose"]
    assert context.rows == [{"Drug": "A", "Dose": "1 mg"}]
    assert context.get_citation(0, "Drug") is not None


def test_remove_last_citation_ref_removes_empty_cell_citation(table_service):
    columns = [{"name": "Finding", "type": "text"}]
    table_id = table_service.create_table("citation", "Evidence", columns)
    table_service.add_rows(table_id, [{"Finding": "Signal"}])
    table_service.add_citation(
        table_id,
        0,
        "Finding",
        [{"source_type": "user_input", "excerpt": "Signal"}],
    )

    result = table_service.remove_citation(table_id, 0, "Finding", ref_index=0)

    assert result["success"] is True
    assert table_service.get_cell(table_id, 0, "Finding")["citation"] is None
    assert table_service.get_table_status(table_id)["citation_count"] == 0


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


@pytest.mark.asyncio
async def test_render_table_artifact_only_writes_full_markdown_and_html(table_service):
    columns = [{"name": "Drug", "type": "text"}]
    table_id = table_service.create_table("comparison", "Test", columns)
    table_service.add_rows(
        table_id,
        [{"Drug": f"Drug {index}"} for index in range(1005)],
    )

    markdown = await table_service.render_table(
        table_id,
        format="markdown",
        artifact_only=True,
    )
    html = await table_service.render_table(
        table_id,
        format="html",
        artifact_only=True,
    )

    markdown_path = Path(markdown["file_path"])
    html_path = Path(html["file_path"])
    assert markdown_path.exists()
    assert html_path.exists()
    assert "Drug 1004" in markdown_path.read_text(encoding="utf-8")
    assert "Drug 1004" in html_path.read_text(encoding="utf-8")
    assert "sha256" in markdown
    assert "sha256" in html
    assert "content" not in markdown
    assert "content" not in html


def test_load_existing_drafts_preserves_last_updated(tmp_path):
    from src.infrastructure.excel_renderer import ExcelRenderer

    draft_dir = tmp_path / "drafts"
    draft_dir.mkdir(parents=True)
    (draft_dir / "draft_existing.json").write_text(
        """{
  "table_id": null,
  "intent": "summary",
  "title": "Existing Draft",
  "proposed_columns": [{"name": "Finding", "type": "text"}],
  "extraction_plan": [],
  "source_doc_ids": ["doc_a"],
  "source_sections": [],
  "pending_rows": [],
  "notes": "",
  "last_updated": "2026-04-29T12:34:56"
}""",
        encoding="utf-8",
    )

    service = TableService(
        table_output_dir=tmp_path, table_renderer=ExcelRenderer(tmp_path)
    )

    draft = service.get_draft("draft_existing")
    assert str(draft.last_updated) == "2026-04-29 12:34:56"
