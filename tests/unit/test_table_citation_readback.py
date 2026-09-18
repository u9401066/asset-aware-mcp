"""Canonical MCP citation pages must preserve evidence and stable cell identity."""

from __future__ import annotations

import hashlib
import json

import pytest

from src.application.table_service import TableService
from src.infrastructure.excel_renderer import ExcelRenderer
from src.presentation.tools import table_tools


@pytest.fixture
def table(tmp_path, monkeypatch):
    service = TableService(tmp_path, ExcelRenderer(tmp_path))
    table_id = service.create_table(
        "citation", "Readback", [{"name": "Value", "type": "text"}]
    )
    service.add_rows(table_id, [{"Value": "µ μ 0007"}, {"Value": "other"}])
    monkeypatch.setattr(table_tools, "table_service", service)
    return service, table_id, tmp_path


async def read(table_id, **kwargs):
    response = await table_tools.table_cite(
        "read", table_id, column_name="Value", **kwargs
    )
    assert "❌" not in response, response
    return response, json.loads(response)


async def assemble(table_id, **kwargs):
    chunks, digest, offset = [], "", 0
    for _ in range(1000):
        raw, page = await read(
            table_id, text_offset=offset, citation_sha256=digest, **kwargs
        )
        digest = digest or page["citation_sha256"]
        assert page["citation_sha256"] == digest
        assert page["excerpt_char_range"] == [
            offset,
            offset + len(page["text_excerpt"]),
        ]
        chunks.append(page["text_excerpt"])
        assert len(raw) <= 12_000
        offset = page["next_text_offset"]
        if offset is None:
            text = "".join(chunks)
            assert len(text) == page["text_length"]
            assert hashlib.sha256(text.encode("utf-8")).hexdigest() == digest
            return json.loads(text)
    raise AssertionError("Citation paging made no progress")


async def test_read_preserves_every_locator_and_long_quote(table):
    service, table_id, directory = table
    quote = 'µ μ 繁體 "\\\n\x00' * 1000
    ref = {
        "source_type": "span",
        "doc_id": "doc_original",
        "asset_id": "sec_1",
        "span_id": "span_1",
        "block_id": "block_1",
        "page": 3,
        "line_range": [2, 4],
        "char_range": [10, 10 + len(quote)],
        "byte_range": [20, 20 + len(quote.encode("utf-8"))],
        "bbox": [1, 2, 300, 400],
        "source_revision_id": "rev_original",
        "locator_version": "v1",
        "locator_source_sha256": "a" * 64,
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "craap": {"evidence": "manually supplied; not verified"},
    }
    service.add_citation(
        table_id,
        0,
        "Value",
        [ref] + [{"source_type": "figure", "page": 2}] * 55,
        notes="Full notes " * 500,
        confidence=0.0,
    )
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in directory.glob("*.*")
    }
    snapshot = await assemble(table_id, row_index=0)
    persisted = json.loads((directory / f"{table_id}.json").read_text())
    row_id = persisted["row_ids"][0]
    assert snapshot == {
        "schema_version": "a2t-cell-citation-v1",
        "table_id": table_id,
        "row_id": row_id,
        "column_name": "Value",
        "value": "µ μ 0007",
        "citation": persisted["citations"][f"rid:{row_id}:Value"],
    }
    assert snapshot["citation"]["refs"][0] == ref
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in directory.glob("*.*")
    }


async def test_absent_citation_is_explicit_and_get_guides_to_read(table):
    service, table_id, _ = table
    snapshot = await assemble(table_id, row_index=1)
    assert snapshot["citation"] is None
    service.add_citation(
        table_id, 0, "Value", [{"source_type": "user_input", "excerpt": "source"}]
    )
    summary = await table_tools.table_cite(
        "get", table_id, row_index=0, column_name="Value"
    )
    assert "source" in summary and 'operation="read"' in summary


@pytest.mark.parametrize(
    "arguments",
    [
        {"row_index": -1},
        {"row_index": 2},
        {"row_id": "missing"},
        {"row_index": 0, "text_offset": -1},
        {"row_index": 0, "text_offset": 1},
        {"row_index": 0, "text_limit": 0},
        {"row_index": 0, "text_limit": 4001},
        {"row_index": 0, "citation_sha256": "not-a-hash"},
        {"row_index": 0, "citation_sha256": "a" * 64},
    ],
)
async def test_invalid_requests_fail(table, arguments):
    _, table_id, _ = table
    result = await table_tools.table_cite(
        "read", table_id, column_name="Value", **arguments
    )
    assert "❌" in result


@pytest.mark.parametrize("column", ["", "unknown"])
async def test_missing_column_fails(table, column):
    _, table_id, _ = table
    result = await table_tools.table_cite(
        "read", table_id, row_index=0, column_name=column
    )
    assert "❌" in result


async def test_stale_hash_rejects_value_citation_or_scope_changes(table):
    service, table_id, _ = table
    _, first = await read(table_id, row_index=0, text_limit=10)
    pinned = {"text_offset": 10, "citation_sha256": first["citation_sha256"]}
    wrong_cell = await table_tools.table_cite(
        "read", table_id, row_index=1, column_name="Value", **pinned
    )
    assert "changed or cell differs" in wrong_cell
    service.add_citation(table_id, 0, "Value", [{"source_type": "user_input"}])
    stale = await table_tools.table_cite(
        "read", table_id, row_index=0, column_name="Value", **pinned
    )
    assert "changed or cell differs" in stale
    _, second = await read(table_id, row_index=0)
    service.update_cell(table_id, 0, "Value", "new")
    stale = await table_tools.table_cite(
        "read",
        table_id,
        row_index=0,
        column_name="Value",
        citation_sha256=second["citation_sha256"],
    )
    assert "changed or cell differs" in stale


async def test_stable_row_identity_survives_reindexing(table):
    service, table_id, _ = table
    row_id = service.get_table_context(table_id).row_ids[1]
    _, first = await read(table_id, row_id=row_id, text_limit=20)
    service.delete_row(table_id, 0)
    _, second = await read(
        table_id,
        row_id=row_id,
        text_offset=20,
        citation_sha256=first["citation_sha256"],
    )
    assert second["citation_sha256"] == first["citation_sha256"]
    assert "row_index" not in await assemble(table_id, row_id=row_id)


async def test_small_response_cap_reduces_page_without_mutating_quote(
    table, monkeypatch
):
    service, table_id, _ = table
    service.add_citation(
        table_id, 0, "Value", [{"source_type": "user_input", "quote": '\x00"\\' * 100}]
    )
    monkeypatch.setenv("ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS", "700")
    raw, page = await read(table_id, row_index=0)
    assert len(raw) <= 700
    assert page["next_text_offset"] is not None
    assert page["representation_complete"] is False
    snapshot = await assemble(table_id, row_index=0)
    assert snapshot["citation"]["refs"][0]["quote"] == '\x00"\\' * 100
    monkeypatch.setenv("ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS", "100")
    response = await table_tools.table_cite(
        "read", table_id, row_index=0, column_name="Value"
    )
    assert "too small" in response


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object(), "\ud800"])
async def test_unrepresentable_legacy_values_fail_closed(table, value):
    service, table_id, _ = table
    service.get_table_context(table_id).rows[0]["Value"] = value
    response = await table_tools.table_cite(
        "read", table_id, row_index=0, column_name="Value"
    )
    assert "❌" in response


async def test_complete_representation_limit_is_enforced(table, monkeypatch):
    _, table_id, _ = table
    monkeypatch.setattr("src.application.table_citation_read.MAX_CITATION_BYTES", 10)
    response = await table_tools.table_cite(
        "read", table_id, row_index=0, column_name="Value"
    )
    assert "16 MiB limit" in response


async def test_offsets_beyond_end_fail_without_clamping(table):
    _, table_id, _ = table
    _, first = await read(table_id, row_index=0)
    response = await table_tools.table_cite(
        "read",
        table_id,
        row_index=0,
        column_name="Value",
        citation_sha256=first["citation_sha256"],
        text_offset=first["text_length"] + 1,
    )
    assert "beyond" in response
