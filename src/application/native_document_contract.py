"""Public native operation capabilities without filesystem side effects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.native_assets import NativeDocumentRequest

if TYPE_CHECKING:
    from src.domain.native_assets import NativeFileAsset


def _compact_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Omit prose annotations/null defaults while preserving validation keywords."""
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in {"title", "description"} or (key == "default" and value is None):
            continue
        if key in {"properties", "$defs", "patternProperties", "dependentSchemas"}:
            result[key] = {name: _compact_schema(node) for name, node in value.items()}
        elif key in {"anyOf", "oneOf", "allOf", "prefixItems"}:
            result[key] = [_compact_schema(node) for node in value]
        elif key in {
            "items",
            "additionalProperties",
            "not",
            "if",
            "then",
            "else",
        } and isinstance(value, dict):
            result[key] = _compact_schema(value)
        else:
            result[key] = value
    return result


def native_asset_summary(
    asset: NativeFileAsset, *, docx_enabled: bool = False
) -> dict[str, Any]:
    return {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "format": asset.format,
        "media_type": asset.media_type,
        "revision": asset.revision,
        "archived": asset.archived,
        "source": asset.source.model_dump() if asset.source else None,
        "revision_count": len(asset.history),
        "capabilities": {
            "inspect_metadata": True,
            "immutable_history": True,
            "refresh_source": asset.source is not None and not asset.archived,
            "read_docx": asset.format == "docx" and docx_enabled,
            "verify_docx_blocks": asset.format == "docx" and docx_enabled,
            "edit_docx": asset.format == "docx" and docx_enabled and not asset.archived,
            "inspect_cells": asset.format in {"xlsx", "xlsm"},
            "verify_cells": asset.format in {"xlsx", "xlsm"},
            "edit_cells": asset.format in {"xlsx", "xlsm"} and not asset.archived,
            "writeback": asset.source is not None and not asset.archived,
            "rendered_verification": False,
            "formula_evaluation": False,
            "edit_constraints": (
                [
                    "protected_sheets",
                    "shared_array_formulas",
                    "rich_text_runs",
                    "table_headers_totals_calculated_columns",
                    "digital_signatures",
                ]
                if asset.format in {"xlsx", "xlsm"}
                else [
                    "document_protection",
                    "digital_signatures",
                    "structural_edits",
                    "document_style_design",
                ]
                if asset.format == "docx"
                else []
            ),
        },
    }


def native_document_contract(*, docx_enabled: bool = False) -> dict[str, Any]:
    return {
        "success": True,
        "schema": _compact_schema(NativeDocumentRequest.model_json_schema()),
        "identity": "Stable asset IDs, SHA-256 revisions and revision-scoped locators.",
        "formats": {
            "docx": [
                "read_docx",
                "read_docx_block",
                "update_docx",
                "verify",
                "export_wiki",
            ]
            if docx_enabled
            else [],
            "xlsx": ["create", "inspect_cells", "edit_cells"],
            "xlsm": ["inspect_cells", "edit_cells"],
            "other": [
                "register",
                "inspect_metadata",
                "history",
                "publish",
                "archive",
            ],
        },
        "verification": "MCP checks integrity; agents verify semantics, layout and calculated results.",
        "docx_policy": "Pin revision; assemble all DFM chunks with frontmatter/markers. Updates stage versions; writeback is explicit.",
        "archive_policy": "Archive retains history and the human source.",
        "wiki_policy": "Immutable snapshots; never replace existing notes. Citation fields go inside native_request.",
    }
