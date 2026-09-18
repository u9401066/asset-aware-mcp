"""Shared native operation fields for runtime validation and schema discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NativeOperation = Literal[
    "contract",
    "schema",
    "register",
    "create",
    "list",
    "inspect",
    "read_cell",
    "create_pptx",
    "read_pptx",
    "read_pptx_shape",
    "update_pptx",
    "read_docx",
    "read_docx_block",
    "update_docx",
    "verify",
    "export_wiki",
    "update",
    "history",
    "publish",
    "writeback",
    "refresh",
    "archive",
]


@dataclass(frozen=True)
class NativeOperationFields:
    required: frozenset[str]
    optional: frozenset[str]


def _fields(required: str = "", optional: str = "") -> NativeOperationFields:
    return NativeOperationFields(
        frozenset(required.split()), frozenset(optional.split())
    )


NATIVE_OPERATIONS = {
    "contract": _fields(optional="for_op"),
    "schema": _fields(optional="for_op schema_sha256 text_offset text_limit"),
    "register": _fields("source_path"),
    "create": _fields("workbook"),
    "list": _fields(optional="offset limit"),
    "inspect": _fields("asset_id", "sheet offset limit revision"),
    "read_cell": _fields("asset_id sheet cell", "revision text_offset text_limit"),
    "create_pptx": _fields("presentation"),
    "read_pptx": _fields("asset_id", "revision offset limit"),
    "read_pptx_shape": _fields(
        "asset_id pptx_locator", "revision text_offset text_limit"
    ),
    "update_pptx": _fields("asset_id expected_revision pptx_edits"),
    "read_docx": _fields("asset_id", "revision text_offset text_limit offset limit"),
    "read_docx_block": _fields("asset_id block_id", "revision text_offset text_limit"),
    "update_docx": _fields("asset_id expected_revision docx_edit"),
    "verify": _fields("reference"),
    "export_wiki": _fields(
        "asset_id output_dir", "revision citation_contract citation_metadata"
    ),
    "update": _fields("asset_id expected_revision edits"),
    "history": _fields("asset_id", "offset limit"),
    "publish": _fields("asset_id expected_revision output_path"),
    "writeback": _fields("asset_id expected_revision expected_source_sha256"),
    "refresh": _fields("asset_id expected_revision expected_source_sha256"),
    "archive": _fields("asset_id expected_revision"),
}


def operation_fields(operation: str) -> NativeOperationFields:
    try:
        return NATIVE_OPERATIONS[operation]
    except KeyError as exc:
        raise ValueError("Unknown native operation") from exc
