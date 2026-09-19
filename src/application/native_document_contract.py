"""Public native operation capabilities without filesystem side effects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_schema import schema_discovery
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_operations import NATIVE_OPERATIONS

if TYPE_CHECKING:
    from src.domain.native_assets import NativeDocumentRequest, NativeFileAsset


def native_asset_summary(
    asset: NativeFileAsset,
    *,
    docx_enabled: bool = False,
    pptx_enabled: bool = False,
    pdf_enabled: bool = False,
) -> dict[str, Any]:
    return {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "format": asset.format,
        "media_type": asset.media_type,
        "revision": asset.revision,
        "file_reference": NativeFileReference(
            asset_id=asset.asset_id, revision=asset.revision
        ).model_dump(),
        "archived": asset.archived,
        "source": asset.source.model_dump() if asset.source else None,
        "revision_count": len(asset.history),
        "capabilities": {
            "verify_file_bytes": True,
            "read_pdf": asset.format == "pdf" and pdf_enabled,
            "edit_pdf_pages": asset.format == "pdf"
            and pdf_enabled
            and not asset.archived,
            "inspect_metadata": True,
            "immutable_history": True,
            "refresh_source": asset.source is not None and not asset.archived,
            "read_pptx": asset.format == "pptx" and pptx_enabled,
            "edit_pptx_slides": asset.format == "pptx"
            and pptx_enabled
            and not asset.archived,
            "verify_pptx_shapes": asset.format == "pptx" and pptx_enabled,
            "read_pptx_pictures": asset.format == "pptx" and pptx_enabled,
            "edit_pptx_pictures": asset.format == "pptx"
            and pptx_enabled
            and not asset.archived,
            "edit_pptx": asset.format == "pptx" and pptx_enabled and not asset.archived,
            "update_pptx_table_grid": asset.format == "pptx"
            and pptx_enabled
            and not asset.archived,
            "add_pptx_tables": asset.format == "pptx"
            and pptx_enabled
            and not asset.archived,
            "add_pptx_shapes": asset.format == "pptx"
            and pptx_enabled
            and not asset.archived,
            "delete_pptx_shapes": asset.format == "pptx"
            and pptx_enabled
            and not asset.archived,
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
    pdf_enabled: bool = False,
    derivations_enabled: bool = False,
    pptx_rendering_configured: bool = False,
    docx_structure_enabled: bool = False,
    docx_rendering_configured: bool = False,
) -> dict[str, Any]:
    for_op = request.for_op if request is not None else None
    return {
        "success": True,
        "contract_version": "native-contract-v2",
        "operations": list(NATIVE_OPERATIONS),
        **schema_discovery(for_op),
        "identity": "Stable asset IDs, SHA-256 revisions and revision-scoped locators.",
        "citation_policy": "citation_contract selects a display preset or custom inline/reference templates; it does not store source references or verification reports.",
        "derivations_enabled": derivations_enabled,
        "derivation_policy": "Read complete hash-pinned ledger before record/retract; endpoint integrity and caller-supplied agent review are separate. New file revisions never inherit old assertions automatically.",
        "pptx_slide_policy": "Discover destination layouts; insert, reorder or delete slides with current revision and exact slide IDs/parts. Dependencies may block edits. Deleted parts remain retained, not securely erased; review rendering and cached properties.",
        "pptx_rendering": {
            "configured": pptx_rendering_configured,
            "availability": "Checked per request; requires LibreOffice with Impress. Set LIBREOFFICE_BIN if needed.",
            "policy": "render_pptx_slide needs revision and exact pptx_slide_key. Returns an actual PNG of the whole slide. Static LibreOffice output is not a PowerPoint fidelity verdict.",
        },
        "docx_rendering": {
            "configured": docx_rendering_configured,
            "availability": "Checked per request; requires LibreOffice with Writer. Set LIBREOFFICE_BIN if needed.",
            "policy": "render_docx_page needs revision and zero-based docx_page_index. Returns an actual MCP PNG and rendered page count. Page indices belong to this rendition, not native DOCX block locators or Microsoft Word pagination.",
        },
        "pptx_grid_policy": "Sequential insert/delete/resize/merge/split with full shape references. Merge requires explicit content_policy; split retains anchor text. Read complete updated shapes and review rendering.",
        "file_reference_policy": "file_reference identifies exact immutable file bytes; verify does not assert source freshness or semantic meaning.",
        "formats": _formats(
            docx_enabled,
            pptx_enabled,
            pdf_enabled,
            pptx_rendering_configured,
            docx_structure_enabled,
            docx_rendering_configured,
        ),
        "verification": "MCP checks integrity; agents verify semantics, layout and calculated results.",
        "docx_policy": "Pin revision; assemble all DFM chunks with frontmatter/markers. Updates stage versions; writeback is explicit.",
        "docx_structure_enabled": docx_structure_enabled,
        "docx_structure_policy": "Create typed paragraphs/tables independently. Insert at body start/end or a full current block reference; delete complete body blocks with dependency checks. New block IDs are revision-scoped; old refs stay historical. Agents review page flow, styles, fields and rendering.",
        "archive_policy": "Archive retains history and the human source.",
        "wiki_policy": "Immutable snapshots; never replace existing notes. Citation fields go inside native_request.",
    }


def _edit_constraints(format_name: str) -> list[str]:
    if format_name == "pdf":
        return [
            "encrypted_or_signed_documents",
            "parser_repairs",
            "XFA_forms",
            "remaining_page_dependencies",
            "partial_or_conflicting_form_copies",
            "cross_document_tagged_layer_named_destination_integration",
            "semantic_text_replacement",
            "secure_redaction",
        ]
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
            "slide_structure",
            "non_table_non_picture_non_text_shape_creation",
            "linked_or_alternate_picture_representations",
            "shape_reference_dependencies",
            "zero_extent_group_insertion",
            "field_runs",
            "inherited_formatting",
        ]
    return []


def _formats(
    docx_enabled: bool,
    pptx_enabled: bool,
    pdf_enabled: bool,
    pptx_rendering_configured: bool = False,
    docx_structure_enabled: bool = False,
    docx_rendering_configured: bool = False,
) -> dict[str, list[str]]:
    return {
        "pdf": [
            "create_pdf",
            "read_pdf",
            "read_pdf_page",
            "render_pdf_page",
            "add_pdf_pages",
            "update_pdf",
            "delete_pdf_pages",
            "reorder_pdf_pages",
            "verify",
            "export_wiki",
        ]
        if pdf_enabled
        else [],
        "pptx": (["render_pptx_slide"] if pptx_rendering_configured else [])
        + [
            "read_pptx_layouts",
            "add_pptx_slides",
            "delete_pptx_slides",
            "reorder_pptx_slides",
            "add_pptx_pictures",
            "replace_pptx_pictures",
            "read_pptx_picture",
            "extract_pptx_picture",
            "create_pptx",
            "read_pptx",
            "read_pptx_shape",
            "update_pptx",
            "add_pptx_tables",
            "update_pptx_table_grid",
            "add_pptx_shapes",
            "delete_pptx_shapes",
            "verify",
            "export_wiki",
        ]
        if pptx_enabled
        else [],
        "docx": (["render_docx_page"] if docx_rendering_configured else [])
        + (
            ["create_docx", "add_docx_blocks", "delete_docx_blocks"]
            if docx_structure_enabled
            else []
        )
        + [
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
    }
