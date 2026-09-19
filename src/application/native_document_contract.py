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
    workbook_structure_enabled: bool = False,
    workbook_grid_enabled: bool = False,
    workbook_table_edit_enabled: bool = False,
    workbook_table_creation_enabled: bool = False,
    table_workspaces_enabled: bool = False,
    derivations_enabled: bool = False,
    pptx_rendering_configured: bool = False,
    docx_structure_enabled: bool = False,
    docx_rendering_configured: bool = False,
) -> dict[str, Any]:
    for_op = request.for_op if request is not None else None
    result = {
        "success": True,
        "contract_version": "native-contract-v2",
        "operations": list(NATIVE_OPERATIONS),
        **schema_discovery(for_op),
        "workbook_structure_enabled": workbook_structure_enabled,
        "workbook_grid_enabled": workbook_grid_enabled,
        "workbook_table_edit_enabled": workbook_table_edit_enabled,
        "table_totals_lifecycle_enabled": workbook_table_edit_enabled,
        "table_totals_lifecycle_policy": "update_workbook_table accepts table_update.totals_row to add/remove totals without worksheet row movement. Add requires blank cells below the Table; reuse hidden definitions or choose blanks, with optional last-data-row direct cell styles. Remove clears contents or keeps cells with own Table references frozen to pre-removal absolute ranges; definitions can be retained for reuse. Current-row selectors in kept totals formulas require explicit correction because they lack a data-row context. Other formulas keep structured references. Read complete cell receipts and source checks; Agent reviews meaning, future formula membership and rendering.",
        "workbook_table_creation_enabled": workbook_table_creation_enabled,
        "workbook_table_creation_policy": "add_workbook_table pins revision, worksheet and exact range. Unique ordered column names; header_policy requires matching strings or explicitly fills blanks, preserving rich runs. Headerless Tables disable autofilter. Explicit totals rows must start blank; no rows are inserted. Calculated columns require blank cells or explicit replace_all. Preserve ordinary data and cell styles; apply the requested built-in/existing Table style. Read complete references and creation receipt; Agent checks meaning, rendering and formula results. Historical evidence never migrates.",
        "workbook_table_edit_policy": "update_workbook_table pins worksheet/part/ref, file revision and column IDs/expected names. Rename headers and existing structured references together; rich headers require exact header_runs. New formulas use final names. Calculated require_matching preserves exceptions by rejecting; replace_all explicitly replaces ordinary values; null/keep_cells removes metadata only. Totals edits require an existing totals row. Read complete current references and operation receipt. Source schema dependencies may block edits. Agent reviews meaning, formula results and rendered formatting; old evidence and A2T bindings never migrate.",
        "workbook_grid_policy": "Sequential row/column insert/delete uses exact worksheet keys and revisions. Preserve native payloads, styles and modeled dependencies; read the complete operation receipt. Geometry uses declared metrics. Dynamic sources, rendered layout and recalculated results need Agent review; historical references never migrate.",
        "table_expansion_enabled": workbook_grid_enabled,
        "table_workspaces_enabled": table_workspaces_enabled,
        "table_grid_apply_enabled": table_workspaces_enabled and workbook_grid_enabled,
        "table_workspace_policy": "Project exact worksheet ranges into tagged A2T cells without header/type inference. Read complete hash-pinned workspaces/source records; preserve source bindings. Apply values at exact table/file revisions. When table_grid_apply_enabled, inspect structural_plan and pass its worksheet_grid explicitly for changed correspondence; MCP validates stable row/column identities before one native commit. Whole worksheet axes move. When table_expansion_enabled, insert edits may explicitly expand_tables using exact part/expected_ref at each intermediate data/column boundary; insert before totals. native_generated with null value resolves only cells generated by this structural operation; missing/blank remain blank. Read generated_table_cells and resolved values. Unchanged formulas follow native relocation; edited/new formulas use destination coordinates. Independent creation is a new workbook. Frozen workspace_reference snapshots and old bindings remain historical. Agent reviews meaning, table membership, formula results and layout.",
        "workbook_policy": "Read complete hash-pinned read_workbook JSON. Sheet changes need current revision and sheetId/part keys. Preserve explicit references, views and scopes; reject surviving deletion dependencies and default 3D membership changes. Dynamic strings, calculation results and rendering need Agent review. Detached parts remain; no secure erasure.",
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
        "selection_policy": "read_selection requires a full parsed cell/block/shape/page reference. An empty RFC6901 pointer reads its complete record without evidence metadata; an optional nonempty half-open Unicode character range selects within a JSON string. Assemble all pages at one text_sha256. verify and derivations accept selection refs; wiki attaches active selection records. Offsets are not source-file bytes; no nested or opaque-file selections or automatic remapping.",
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
        ),
        "verification": "MCP checks integrity; agents verify semantics, layout and calculated results.",
        "docx_policy": "Pin revision; assemble all DFM chunks with frontmatter/markers. Updates stage versions; writeback is explicit.",
        "docx_structure_enabled": docx_structure_enabled,
        "docx_structure_policy": "Create typed paragraphs/tables independently. Insert at body start/end or a full current block reference; delete complete body blocks with dependency checks. New block IDs are revision-scoped; old refs stay historical. Agents review page flow, styles, fields and rendering.",
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
        workbook_ops.append("update_worksheet_grid")
    if workbook_structure_enabled and workbook_table_edit_enabled:
        workbook_ops.append("update_workbook_table")
    if workbook_structure_enabled and workbook_table_creation_enabled:
        workbook_ops.append("add_workbook_table")
    return {
        "pdf": [
            "create_pdf",
            "read_pdf",
            "read_pdf_page",
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
        "docx": (["render_docx_page"] if docx_rendering_configured else [])
        + (
            ["create_docx", "add_docx_blocks", "delete_docx_blocks"]
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
        ],
        "xlsm": ["inspect_cells", "edit_cells", "read_selection", *workbook_ops],
        "other": [
            "register",
            "inspect_metadata",
            "history",
            "publish",
            "archive",
        ],
    }
