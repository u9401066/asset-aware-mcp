"""Public native operation capabilities without filesystem side effects."""

from __future__ import annotations

import json
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
    delimited_enabled: bool = False,
    workbook_structure_enabled: bool = False,
    workbook_grid_enabled: bool = False,
    workbook_table_edit_enabled: bool = False,
    workbook_table_creation_enabled: bool = False,
    table_workspaces_enabled: bool = False,
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
            "read_delimited": asset.format in {"csv", "tsv"} and delimited_enabled,
            "edit_delimited": asset.format in {"csv", "tsv"}
            and delimited_enabled
            and not asset.archived,
            "verify_delimited_fields": asset.format in {"csv", "tsv"}
            and delimited_enabled,
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
            "read_workbook": asset.format in {"xlsx", "xlsm"}
            and workbook_structure_enabled,
            "edit_worksheets": asset.format in {"xlsx", "xlsm"}
            and workbook_structure_enabled
            and not asset.archived,
            "read_worksheet_layout": asset.format in {"xlsx", "xlsm"}
            and workbook_grid_enabled,
            "update_worksheet_layout": asset.format in {"xlsx", "xlsm"}
            and workbook_grid_enabled
            and not asset.archived,
            "update_worksheet_grid": asset.format in {"xlsx", "xlsm"}
            and workbook_grid_enabled
            and not asset.archived,
            "add_workbook_table": asset.format in {"xlsx", "xlsm"}
            and workbook_table_creation_enabled
            and not asset.archived,
            "update_workbook_table": asset.format in {"xlsx", "xlsm"}
            and workbook_table_edit_enabled
            and not asset.archived,
            "project_workbook_table": asset.format in {"xlsx", "xlsm"}
            and table_workspaces_enabled,
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
    delimited_enabled: bool = False,
    workbook_structure_enabled: bool = False,
    workbook_grid_enabled: bool = False,
    workbook_table_edit_enabled: bool = False,
    workbook_table_creation_enabled: bool = False,
    table_workspaces_enabled: bool = False,
    derivations_enabled: bool = False,
    pptx_rendering_configured: bool = False,
    docx_structure_enabled: bool = False,
    docx_rendering_configured: bool = False,
    workbook_rendering_configured: bool = False,
    docx_stories_enabled: bool = False,
) -> dict[str, Any]:
    for_op = request.for_op if request is not None else None
    result = {
        "success": True,
        "contract_version": "native-contract-v2",
        "delimited_enabled": delimited_enabled,
        "delimited_policy": "CSV/TSV strings; explicit dialect/encoding, no inferred headers/types. Pin revisions; assemble full JSON at one text_sha256. Cell edits need full refs; row/column edits preserve untouched bytes. Evidence/Wiki bind dialects.",
        "pdf_regions_enabled": pdf_enabled,
        "pdf_region_policy": "Full page ref + displayed CropBox fractions [x0,y0,x1,y1] (0..1, top-left, after rotation), or existing region ref. Actual PNG + source record; render_size changes detail, not identity. Agent checks coverage/transcription.",
        "operations": list(NATIVE_OPERATIONS),
        **schema_discovery(for_op),
        "workbook_structure_enabled": workbook_structure_enabled,
        "workbook_rendering": {
            "configured": workbook_rendering_configured,
            "availability": "Checked per request; requires LibreOffice Calc and optional LIBREOFFICE_BIN.",
            "policy": "create_workbook_rendition pins XLSX revision, explicit print/whole_sheet and recalculate/prefer_cache policies. New immutable PDF; read complete read_rendition receipt then existing PDF page PNGs. Agent reviews layout/results; source bytes stay unchanged.",
        },
        "workbook_grid_enabled": workbook_grid_enabled,
        "worksheet_layout_enabled": workbook_grid_enabled,
        "worksheet_layout_policy": "Pin revision/worksheet_key; read full dimensions. Set point heights/raw OOXML widths, reset_size or hidden. Anchors follow recorded metrics. Caches invalidate; render a new PDF for review.",
        "workbook_table_edit_enabled": workbook_table_edit_enabled,
        "table_totals_lifecycle_enabled": workbook_table_edit_enabled,
        "table_totals_lifecycle_policy": "Add needs blank reserved cells; optionally reuse definitions/styles. Remove clears or keeps cells; kept own-Table refs freeze old ranges. Correct kept current-row selectors; no worksheet rows move.",
        "workbook_table_creation_enabled": workbook_table_creation_enabled,
        "workbook_table_creation_policy": "Pin worksheet/range/unique columns. Match rich headers or fill blanks explicitly. Headerless Tables disable autofilter; totals need blanks. Calculated columns require blanks or replace_all; use built-in/existing styles.",
        "workbook_table_edit_policy": "Pin worksheet/part/ref/column IDs/names. Rich headers need matching header_runs; references follow renames. New formulas use final names; require_matching checks exceptions, replace_all replaces cells. Totals must exist.",
        "workbook_grid_policy": "Sequential edits use intermediate worksheet coordinates and exact sheet keys. Preserve modeled dependencies; read full operation receipt and geometry assumptions. Historical refs never migrate.",
        "table_expansion_enabled": workbook_grid_enabled,
        "table_workspaces_enabled": table_workspaces_enabled,
        "table_grid_apply_enabled": table_workspaces_enabled and workbook_grid_enabled,
        "table_workspace_policy": "Project exact ranges into tagged cells; no inferred headers/types. Pin table/file hashes. Changed correspondence needs structural_plan.worksheet_grid and stable row/column IDs; whole axes move. expand_tables selects part/expected_ref at each step. native_generated/null retains newly generated cells only. Unchanged formulas relocate; edited formulas use destination coordinates. Frozen inputs/bindings stay historical.",
        "workbook_policy": "Assemble full read_workbook JSON. Sheet edits need sheetId/part and revision. Preserve scopes/views; dependencies and default 3D membership changes may block edits. Detached parts remain; no secure erasure.",
        "identity": "Stable asset IDs, SHA-256 revisions and revision-scoped locators.",
        "citation_policy": "citation_contract is display only: presets/custom templates, not source refs or proof reports.",
        "derivations_enabled": derivations_enabled,
        "derivation_policy": "Read hash-pinned ledger before record/retract. Endpoint integrity and caller review are separate; new revisions never inherit assertions.",
        "pptx_slide_policy": "Discover layouts; use exact slide IDs/parts and revision. Dependencies may block edits. Deleted parts remain, not securely erased.",
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
        "pptx_grid_policy": "Sequential insert/delete/resize/merge/split uses full shape refs. Merge requires content_policy; split keeps anchor text. Read back and render.",
        "file_reference_policy": "Exact immutable bytes only; no semantic or live-source freshness verdict.",
        "selection_policy": "Full parsed reference + RFC6901 pointer (empty=whole record), optional Unicode range. Assemble at one text_sha256. Parsed offsets are not file bytes. No nested/opaque selections or automatic remapping.",
        "formats": _formats(
            docx_enabled,
            pptx_enabled,
            pdf_enabled,
            pptx_rendering_configured,
            docx_structure_enabled,
            docx_rendering_configured,
            workbook_structure_enabled,
            table_workspaces_enabled,
            workbook_grid_enabled,
            workbook_table_edit_enabled,
            workbook_table_creation_enabled,
            workbook_rendering_configured,
            delimited_enabled,
            docx_stories_enabled,
        ),
        "verification": "MCP checks structure/integrity and deterministic repairs. Read full operation receipts. Agents verify semantics, rendered layout, dynamic references and calculated results; sources/history stay intact.",
        "docx_stories_enabled": docx_stories_enabled,
        "docx_stories_policy": "Read full header/footer catalog and story JSON at a pinned revision. Bindings follow actual relationships and inheritance, including dormant/shared parts. update_docx_story requires full story ref and all_sections_using_part scope. Read complete receipts and review every affected actual page. Legacy DFM header/footer fields are abbreviated; use stories for exact content and bindings.",
        "docx_policy": "Pin revision; assemble all DFM chunks with frontmatter/markers. Updates stage versions; writeback is explicit.",
        "docx_structure_enabled": docx_structure_enabled,
        "docx_table_grid_enabled": docx_enabled and docx_structure_enabled,
        "docx_table_layout_enabled": docx_enabled and docx_structure_enabled,
        "docx_table_layout_policy": "Use set_header_rows for a contiguous repeated prefix; set_row_layout for explicit height and split policies. inherit removes direct properties; auto uses content height. Read full receipts and render all pages. Styles, oversized rows and Microsoft Word behavior require Agent review.",
        "docx_table_grid_policy": "Read full hash-pinned grid JSON at an exact revision. Sequential insert/delete/resize/merge/split requires full table refs. Merge needs explicit content_policy; retain native content and omitted positions. Read new refs and render for Agent review.",
        "docx_structure_policy": "Create typed paragraphs/tables; insert at body boundaries/current block refs. Delete complete blocks with dependency checks. Block IDs are revision-scoped; read back and render for review.",
        "archive_policy": "Archive retains history and the human source.",
        "wiki_policy": "Immutable snapshots; never replace existing notes. Citation fields go inside native_request.",
    }
    # Account for enabled-format inventory and policy text as well as the schema.
    # Keep the hash-pinned schema request when moving a large contract to pages.
    if (
        "schema" in result
        and len(json.dumps(result, ensure_ascii=False, indent=2)) > 10_000
    ):
        result.pop("schema")
        result["schema_delivery"] = "paged"
    return result


def _edit_constraints(format_name: str) -> list[str]:
    if format_name in {"csv", "tsv"}:
        return [
            "explicit dialect and strict encoding",
            "strings only; logical rows/columns are zero-based",
            "full references for cell updates",
            "ragged rows never padded",
            "Agent reviews meaning and downstream interpretation",
        ]
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
    workbook_structure_enabled: bool = False,
    table_workspaces_enabled: bool = False,
    workbook_grid_enabled: bool = False,
    workbook_table_edit_enabled: bool = False,
    workbook_table_creation_enabled: bool = False,
    workbook_rendering_configured: bool = False,
    delimited_enabled: bool = False,
    docx_stories_enabled: bool = False,
) -> dict[str, list[str]]:
    workbook_ops = (
        [
            "read_workbook",
            "add_worksheets",
            "rename_worksheet",
            "reorder_worksheets",
            "delete_worksheets",
        ]
        if workbook_structure_enabled
        else []
    )
    if table_workspaces_enabled:
        workbook_ops.extend(
            [
                "project_workbook_table",
                "read_table_workspace",
                "apply_table_workspace",
                "create_workbook_from_table",
            ]
        )
    if workbook_structure_enabled and workbook_grid_enabled:
        workbook_ops.extend(
            [
                "update_worksheet_grid",
                "read_worksheet_layout",
                "update_worksheet_layout",
            ]
        )
    if workbook_structure_enabled and workbook_table_edit_enabled:
        workbook_ops.append("update_workbook_table")
    if workbook_structure_enabled and workbook_table_creation_enabled:
        workbook_ops.append("add_workbook_table")
    return {
        "pdf": [
            "read_rendition",
            "create_pdf",
            "read_pdf",
            "read_pdf_page",
            "read_pdf_region",
            "read_selection",
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
            "read_selection",
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
        "docx": (
            ["read_docx_stories", "read_docx_story", "update_docx_story"]
            if docx_stories_enabled
            else []
        )
        + (["render_docx_page"] if docx_rendering_configured else [])
        + (
            [
                "create_docx",
                "add_docx_blocks",
                "delete_docx_blocks",
                "read_docx_table",
                "update_docx_table_grid",
            ]
            if docx_structure_enabled
            else []
        )
        + [
            "read_docx",
            "read_docx_block",
            "read_selection",
            "update_docx",
            "verify",
            "export_wiki",
        ]
        if docx_enabled
        else [],
        "xlsx": [
            "create",
            "inspect_cells",
            "edit_cells",
            "read_selection",
            *workbook_ops,
            *(["create_workbook_rendition"] if workbook_rendering_configured else []),
        ],
        "xlsm": ["inspect_cells", "edit_cells", "read_selection", *workbook_ops],
        **{
            kind: (
                [
                    "create_delimited",
                    "read_delimited",
                    "read_delimited_cell",
                    "update_delimited",
                    "read_selection",
                    "verify",
                    "export_wiki",
                ]
                if delimited_enabled
                else []
            )
            for kind in ("csv", "tsv")
        },
        "other": [
            "register",
            "inspect_metadata",
            "history",
            "publish",
            "archive",
        ],
    }
