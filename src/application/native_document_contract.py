"""Public native operation capabilities without filesystem side effects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_schema import schema_discovery
from src.domain.native_operations import NATIVE_OPERATIONS

if TYPE_CHECKING:
    from src.domain.native_assets import NativeDocumentRequest, NativeFileAsset


def native_asset_summary(
    asset: NativeFileAsset, *, docx_enabled: bool = False, pptx_enabled: bool = False
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
            "read_pptx": asset.format == "pptx" and pptx_enabled,
            "verify_pptx_shapes": asset.format == "pptx" and pptx_enabled,
            "edit_pptx": asset.format == "pptx" and pptx_enabled and not asset.archived,
            "read_docx": asset.format == "docx" and docx_enabled,
            "verify_docx_blocks": asset.format == "docx" and docx_enabled,
            "edit_docx": asset.format == "docx" and docx_enabled and not asset.archived,
            "inspect_cells": asset.format in {"xlsx", "xlsm"},
            "verify_cells": asset.format in {"xlsx", "xlsm"},
            "edit_cells": asset.format in {"xlsx", "xlsm"} and not asset.archived,
            "writeback": asset.source is not None and not asset.archived,
            "rendered_verification": False,
            "formula_evaluation": False,
            "edit_constraints": _edit_constraints(asset.format),
        },
    }


def native_document_contract(
    request: NativeDocumentRequest | None = None,
    *,
    docx_enabled: bool = False,
    pptx_enabled: bool = False,
) -> dict[str, Any]:
    for_op = request.for_op if request is not None else None
    return {
        "success": True,
        "contract_version": "native-contract-v2",
        "operations": list(NATIVE_OPERATIONS),
        **schema_discovery(for_op),
        "identity": "Stable asset IDs, SHA-256 revisions and revision-scoped locators.",
        "formats": {
            "pptx": [
                "create_pptx",
                "read_pptx",
                "read_pptx_shape",
                "update_pptx",
                "verify",
                "export_wiki",
            ]
            if pptx_enabled
            else [],
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


def _edit_constraints(format_name: str) -> list[str]:
    if format_name in {"xlsx", "xlsm"}:
        return [
            "protected_sheets",
            "shared_array_formulas",
            "rich_text_runs",
            "table_headers_totals_calculated_columns",
            "digital_signatures",
        ]
    if format_name == "docx":
        return [
            "document_protection",
            "digital_signatures",
            "structural_edits",
            "document_style_design",
        ]
    if format_name == "pptx":
        return [
            "digital_signatures",
            "document_protection",
            "structural_edits",
            "field_runs",
            "inherited_formatting",
        ]
    return []
