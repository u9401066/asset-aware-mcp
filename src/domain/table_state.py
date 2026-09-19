"""Stable A2T persistence representation shared by storage and native projections."""

from __future__ import annotations

from typing import Any

from src.domain.table_entities import (
    CellCitation,
    ColumnDef,
    TableChangeLog,
    TableContext,
)


def table_state(context: TableContext) -> dict[str, Any]:
    state: dict[str, Any] = {
        "id": context.id,
        "schema_version": context.schema_version,
        "intent": context.intent,
        "title": context.title,
        "columns": [column.model_dump() for column in context.columns],
        "rows": context.rows,
        "row_ids": context.row_ids,
        "row_provenance": context.row_provenance,
        "source_description": context.source_description,
        "source_doc_id": context.source_doc_id,
        "source_block_id": context.source_block_id,
        "source_revision_id": context.source_revision_id,
        "source_block_hash": context.source_block_hash,
        "created_at": str(context.created_at),
    }
    if context.native_binding is not None:
        state["native_binding"] = context.native_binding.model_dump(mode="json")
    if context.citations:
        state["citations"] = {
            key: cite.to_dict() for key, cite in context.citations.items()
        }
    if context.change_log and context.change_log.entries:
        state["change_log"] = context.change_log.to_dict()
    return state


def table_from_state(data: dict[str, Any]) -> TableContext:
    return TableContext(
        id=data["id"],
        schema_version=data.get("schema_version", "a2t-table-v2"),
        intent=data["intent"],
        title=data["title"],
        columns=[ColumnDef(**column) for column in data["columns"]],
        rows=data["rows"],
        row_ids=data.get("row_ids", []),
        row_provenance=data.get("row_provenance", {}),
        source_description=data.get("source_description", ""),
        source_doc_id=data.get("source_doc_id", ""),
        source_block_id=data.get("source_block_id", ""),
        source_revision_id=data.get("source_revision_id", ""),
        source_block_hash=data.get("source_block_hash", ""),
        created_at=data.get("created_at", ""),
        native_binding=data.get("native_binding"),
        citations={
            key: CellCitation.from_dict(cite)
            for key, cite in data.get("citations", {}).items()
        },
        change_log=TableChangeLog.from_dict(data["change_log"])
        if "change_log" in data
        else None,
    )
