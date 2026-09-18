"""Deterministic MCP clients for the PDF CRUD matrix (no model invocation)."""

from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

from mcp import Client

from tests.codex_pdf.fixtures import COLUMNS, expected_rows


def unwrap(result: Any) -> Any:
    text = "\n".join(
        block.text
        for block in result.content
        if getattr(block, "text", None) is not None
    )
    assert not result.is_error, text
    assert "❌" not in text, text
    structured = result.structured_content
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    if structured is not None:
        return structured
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def call(client: Client, tool: str, **arguments: Any) -> Any:
    return unwrap(await client.call_tool(tool, arguments, read_timeout_seconds=90))


async def ingest(client: Client, source: Path) -> str:
    accepted = await call(
        client,
        "document",
        op="ingest",
        file_paths=[str(source)],
        extract_figures=True,
        index_knowledge_graph=False,
        ocr_enabled=False,
    )
    job_id = re.search(r"job_\d{8}_\d{6}_[a-f0-9]+", str(accepted))
    assert job_id, accepted
    deadline = time.monotonic() + 80
    while time.monotonic() < deadline:
        status = str(await call(client, "get_job_status", job_id=job_id.group()))
        assert not re.search(r"(?m)^# Job Status:.*\b(?:FAILED|CANCELLED)\b", status), (
            status
        )
        if re.search(r"(?m)^# Job Status:.*\bCOMPLETED\b", status):
            match = re.search(r"(?m)^  - `(doc_[A-Za-z0-9_.-]+)`\s*$", status)
            assert match, status
            return match.group(1)
        await asyncio.sleep(0.1)
    raise AssertionError("PDF ingestion did not complete")


def load_table(directory: Path, table_id: str) -> dict[str, Any]:
    return json.loads(
        (directory / "tables" / f"{table_id}.json").read_text(encoding="utf-8")
    )


async def create_table(client: Client, title: str) -> str:
    created = await call(
        client,
        "table_manage",
        operation="create",
        intent="citation",
        title=title,
        columns=[{"name": column, "type": "text"} for column in COLUMNS],
    )
    match = re.search(r"tbl_[a-f0-9]+", str(created))
    assert match, created
    return match.group()


def source_ref(manifest: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    page = {"A": 1, "B": 2, "C": 3}[row["Sample"][0]]
    candidates = [
        (kind[:-1], item)
        for kind in ("tables", "figures")
        for item in manifest["assets"][kind]
        if item["page"] == page
    ]
    assert candidates, f"No source asset on page {page}"
    kind, asset = candidates[0]
    return {
        "source_type": kind,
        "doc_id": manifest["doc_id"],
        "asset_id": asset["id"],
        "page": page,
    }


async def cite_rows(
    client: Client, table: dict[str, Any], manifest: dict[str, Any]
) -> None:
    for row, row_id in zip(table["rows"], table["row_ids"], strict=True):
        await call(
            client,
            "table_cite",
            operation="add",
            table_id=table["id"],
            row_id=row_id,
            column_name="Reading",
            refs=[source_ref(manifest, row)],
            notes="Mechanical fixture check; agent perception is evaluated separately.",
        )


async def edit_and_restore(client: Client, directory: Path, table_id: str) -> None:
    table = load_table(directory, table_id)
    row_id = table["row_ids"][3]
    common = {"table_id": table_id, "row_id": row_id, "column_name": "Reading"}
    await call(client, "table_data", operation="update_cell", value="13.0%", **common)
    updated = load_table(directory, table_id)
    assert updated["rows"][3]["Reading"] == "13.0%"
    assert f"rid:{row_id}:Reading" not in updated["citations"]
    assert "13.0%" in await call(client, "table_data", operation="get_cell", **common)
    await call(client, "table_data", operation="update_cell", value="12.5%", **common)
    assert "12.5%" in await call(client, "table_data", operation="get_cell", **common)
    assert load_table(directory, table_id)["row_ids"] == table["row_ids"]


async def delete_and_restore(client: Client, directory: Path, table_id: str) -> None:
    before = load_table(directory, table_id)
    await call(
        client,
        "table_data",
        operation="delete_row",
        table_id=table_id,
        row_id=before["row_ids"][0],
    )
    after = load_table(directory, table_id)
    assert after["row_ids"] == before["row_ids"][1:]
    assert f"rid:{before['row_ids'][0]}:Reading" not in after["citations"]
    assert after["rows"] == expected_rows()[1:]
    query = await call(client, "table_data", operation="query_rows", table_id=table_id)
    assert "A101" not in query and "**Rows:** 6" in query
    await call(
        client,
        "table_data",
        operation="add_rows",
        table_id=table_id,
        rows=[expected_rows()[0]],
    )


async def exercise_tables(
    client: Client, directory: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    table_id = await create_table(client, "SDK PDF fixture transcription")
    await call(
        client,
        "table_data",
        operation="add_rows",
        table_id=table_id,
        rows=expected_rows(),
    )
    await cite_rows(client, load_table(directory, table_id), manifest)
    await edit_and_restore(client, directory, table_id)
    await delete_and_restore(client, directory, table_id)
    await cite_rows(client, load_table(directory, table_id), manifest)
    await call(client, "table_cite", operation="get", table_id=table_id)
    await call(
        client,
        "table_manage",
        operation="render",
        table_id=table_id,
        format="excel",
        filename="sdk-transcription",
    )
    disposable = await create_table(client, "Disposable SDK CRUD check")
    await call(client, "table_manage", operation="delete", table_id=disposable)
    assert not (directory / "tables" / f"{disposable}.json").exists()
    assert disposable not in await call(client, "table_manage", operation="list")
    return load_table(directory, table_id)
