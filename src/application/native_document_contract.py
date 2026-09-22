"""Public native operation capabilities without filesystem side effects."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.application.native_contract_delivery import deliver_contract
from src.application.native_schema import schema_discovery
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_image import IMAGE_EXTENSIONS
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
    images_enabled: bool = False,
    ods_enabled: bool = False,
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
            "read_ods": asset.format == "ods" and ods_enabled,
            "edit_ods": asset.format == "ods" and ods_enabled and not asset.archived,
            "verify_ods_cells": asset.format == "ods" and ods_enabled,
            "read_image": asset.format in IMAGE_EXTENSIONS and images_enabled,
            "edit_image": asset.format in IMAGE_EXTENSIONS
            and images_enabled
            and not asset.archived,
            "verify_image_frames": asset.format in IMAGE_EXTENSIONS and images_enabled,
            "verify_file_bytes": True,
            "read_delimited": asset.format in {"csv", "tsv"} and delimited_enabled,
            "edit_delimited": asset.format in {"csv", "tsv"}
            and delimited_enabled
            and not asset.archived,
            "verify_delimited_fields": asset.format in {"csv", "tsv"}
            and delimited_enabled,
            "read_pdf": asset.format == "pdf" and pdf_enabled,
            "read_pdf_annotations": asset.format == "pdf" and pdf_enabled,
            "edit_pdf_annotations": asset.format == "pdf"
            and pdf_enabled
            and not asset.archived,
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
    docx_notes_enabled: bool = False,
    images_enabled: bool = False,
    ods_enabled: bool = False,
    image_evidence_retention_enabled: bool = False,
    ods_rendering_configured: bool = False,
) -> dict[str, Any]:
    for_op = request.for_op if request is not None else None
    result = {
        "success": True,
        "contract_version": "native-contract-v2",
        "ods_enabled": ods_enabled,
        "ods_table_rename_enabled": ods_enabled,
        "ods_dependency_policy": "read_ods_dependencies pins asset/revision and pages the complete native dependency inventory using ods_text_sha256. Its inventory_sha256 binds parsed XML, names, owners, namespaces and reference text. rename_ods_table requires expected_revision and ods_table_rename with exact table_index/table_name/new_name and dependencies_sha256. Rename preserves native rows, columns, styles, unrelated parts and historical references while mapping supported cell/named/conditional/chart/settings references and invalidating typed formula caches. Read full read_ods operation_result, then the new dependency inventory and current cell refs; render and inspect every actual page. Literal/INDIRECT arguments and chart appearance need Agent review/correction. Unresolved native owners, sources, aliases or protection fail before one managed commit; source writeback stays explicit. This operation does not provide table insertion/deletion/reorder or row/column lifecycle.",
        "ods_policy": "ODS reads pin revision. read_ods pages physical repeated ranges with offset/limit; assemble ALL text pages at one text_sha256 using ods_text_sha256 for continuation, then follow next_offset for ranges. read_ods_cell uses exact content.xml/table index/name/logical row/column and returns one full cell reference, including explicit absence. update_ods requires expected_revision and 1-100 full original cell refs with typed values and explicit replace_paragraphs_preserve_cell_style policy. Blank clears value only. Duplicate/stale/tampered refs fail before one commit. Read full operation_result and current refs; formula caches and display remain unverified. Wiki retains native .ods, physical ranges/anchor refs, full receipts and explicit derivation endpoints. MCP checks bytes/structure; Agent reviews meaning, rich text, formulas and actual Calc appearance. ODS row/table lifecycle and rendered recalculation are not provided by these cell operations.",
        "images_enabled": images_enabled,
        "image_evidence_retention_enabled": image_evidence_retention_enabled,
        "image_evidence_retention_policy": "When enabled, full frame records/catalogs and generated exact PNG preview recipes persist across restart and decoder changes. read_image/export_wiki may pin image_catalog_sha256; read_image_frame may pin a full frame reference matching asset/revision/locator. Verification checks immutable source bytes and retained representation integrity; retained projection/preview results explicitly do not re-run the current decoder. Uncaptured previews require matching current-decoder frame records. New unpinned reads and mutation preconditions use the current decoder. Retention does not certify decoding accuracy or semantic support; Agent reviews actual images.",
        "image_policy": "Pin source revision and read all image JSON pages at one text_sha256. Frame/region refs bind full decoder records; pixels are EXIF-oriented and animation-composited. Regions use displayed frame fractions rounded outward to pixels. Previews are RGBA8 with explicit ICC/unmanaged color policy. create_image creates PNG; extract_image creates PNG/TIFF, compose_images creates ordered TIFF, with required pixel and pixels_only metadata policies. update_image pins source catalog, exact candidate file ref and exhaustive old/new frame mappings with explicit pixel/metadata preservation or replacement. Source/history remain intact; read full receipts and actual PNGs. Agent reviews appearance, meaning, color, private fields and animation behavior. Decoder/version drift must not silently remap old evidence.",
        "delimited_enabled": delimited_enabled,
        "delimited_policy": "CSV/TSV strings; explicit dialect/encoding, no inferred headers/types. Pin revisions; assemble full JSON at one text_sha256. Cell edits need full refs; row/column edits preserve untouched bytes. Evidence/Wiki bind dialects.",
        "pdf_regions_enabled": pdf_enabled,
        "pdf_annotations_enabled": pdf_enabled,
        "pdf_annotations_policy": "Pin asset/revision and assemble complete read_pdf_annotations catalog and read_pdf_annotation records at one text_sha256. Locators bind page object, annotation array index and object/generation, never NM names alone. update_pdf_annotations accepts 1..32 create/update/delete edits, each existing target once, with full original-revision refs. Create requires a page_reference and typed appearance; Text uses point, FreeText/Square/Circle rect, Line/PolyLine/Polygon vertices, Ink strokes, text markers quads (UL/UR/LL/LR). All positions are displayed rotated CropBox fractions 0..1, top-left; font/border sizes are points. Read geometry retains out-of-crop values. Metadata omitted keys stay; null removes a key. Contents is annotation text, not text beneath markup. Page text extraction can include FreeText appearances; inspect annotation records to distinguish authored comments from the original body. FreeText content changes need replace_appearance of the same kind; it explicitly rebuilds geometry/style. Other metadata updates retain native appearance streams. Delete scope:annotation_and_owned_popup; replies must be explicitly included and outside dependencies, shared arrays, locks, signatures and Widget/standalone Popup edits are guarded. Rich comment formatting/unmodeled appearance features remain restricted. Source/history stay unchanged; deletion is not secure erasure. Read all paged receipts/current refs and all affected actual page PNGs; Agent reviews position, appearance, meaning and viewer behavior. Historical refs, selections, derivations and Wiki stay bound to original revisions.",
        "pdf_region_policy": "Full page ref + displayed CropBox fractions [x0,y0,x1,y1] (0..1, top-left, after rotation), or existing region ref. Actual PNG + source record; render_size changes detail, not identity. Agent checks coverage/transcription.",
        "operations": list(NATIVE_OPERATIONS),
        **schema_discovery(for_op),
        "workbook_structure_enabled": workbook_structure_enabled,
        "workbook_rendering": {
            "configured": workbook_rendering_configured or ods_rendering_configured,
            "source_formats": [
                *(["xlsx"] if workbook_rendering_configured else []),
                *(["ods"] if ods_rendering_configured else []),
            ],
            "availability": "Checked per request; requires LibreOffice Calc and optional LIBREOFFICE_BIN.",
            "policy": "create_workbook_rendition pins an exact revision in source_formats (XLSX/ODS), explicit print/whole_sheet and recalculate/prefer_cache policies. ODS uses its native package and ODF recalculation policy. New immutable PDF; read complete read_rendition receipt then every existing PDF page PNG. Agent reviews layout/results and omitted content; source bytes stay unchanged. Dynamic or external resources require a resource-aware preview. No visual/calculation verdict is inferred.",
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
            docx_notes_enabled,
            images_enabled,
            ods_enabled,
            ods_rendering_configured,
        ),
        "verification": "MCP checks structure/integrity and deterministic repairs. Read full operation receipts. Agents verify semantics, rendered layout, dynamic references and calculated results; sources/history stay intact.",
        "docx_notes_enabled": docx_notes_enabled,
        "docx_notes_policy": "Read complete read_docx_notes catalog and all read_docx_note records at a pinned revision/hash. Note locators bind actual part/kind/native ID, never displayed numbering. Content updates require full note refs and all_native_references scope. Definition creation/deletion pins expected_catalog_sha256 and definitions_and_native_body_references scope. Create anchors use full main-XML text_path, Unicode character_offset and expected_text_sha256; IDs allocate positively unless explicit. Delete requires exact note XML hash and literal_body_text:preserve; custom literal marks stay for explicit Agent correction. Explicit remap_ids supplies part, note_kind and mappings of note_id to new_note_id; it atomically changes normal definitions and all their editable main-body references, preserving definition order/content/styles. Collisions, special definitions and retained references outside that scope are rejected. Read complete new refs and mapping receipts; old refs stay historical. This can align IDs with body order when a target reader misbinds notes; actual page review is still required. All receipts are paged. Special definitions, revisions, fields, locked controls and retained external references have edit restrictions. Agent checks every affected actual page, placement, numbering and meaning. Historical notes and Wikis stay immutable; orphan media is retained.",
        "docx_stories_enabled": docx_stories_enabled,
        "docx_story_structure_enabled": docx_stories_enabled,
        "docx_story_structure_policy": "Read the complete read_docx_story_structure catalog and receipt at one text_sha256. update_docx_story_structure pins expected_revision and expected_catalog_sha256, explicit sections_and_following_inheritors scope, and sequential create/clone/bind/delete/first_page/even_pages edits. bind part:null resumes inheritance, not blank. Create a blank definition to suppress inherited content. Clone/delete require full part hash; known identity/incoming dependencies are checked. Read the complete new receipt and each affected story, then review all actual pages. Removed story dependencies remain as orphan media; no secure erasure. Source/history remain unchanged.",
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
    return deliver_contract(result, request)


def _edit_constraints(format_name: str) -> list[str]:
    if format_name == "ods":
        return [
            "full original logical cell references and expected revision",
            "explicit typed values and rich-display replacement policy",
            "signed/encrypted/protected/tracked content",
            "repeated objects/formulas/merges require mapping-aware edits",
            "Agent reviews formula recalculation, rich text and actual Calc layout",
        ]
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
    docx_notes_enabled: bool = False,
    images_enabled: bool = False,
    ods_enabled: bool = False,
    ods_rendering_configured: bool = False,
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
            "read_pdf_annotations",
            "read_pdf_annotation",
            "update_pdf_annotations",
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
            [
                "read_docx_notes",
                "read_docx_note",
                "update_docx_note",
                "update_docx_notes",
            ]
            if docx_notes_enabled
            else []
        )
        + (
            [
                "read_docx_stories",
                "read_docx_story",
                "update_docx_story",
                "read_docx_story_structure",
                "update_docx_story_structure",
            ]
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
        "ods": (
            [
                "create_ods",
                "read_ods",
                "read_ods_cell",
                "update_ods",
                "read_ods_dependencies",
                "rename_ods_table",
                "read_selection",
                "verify",
                "export_wiki",
            ]
            if ods_enabled
            else []
        )
        + (["create_workbook_rendition"] if ods_rendering_configured else []),
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
        **{
            kind: (
                [
                    "read_image",
                    "read_image_frame",
                    "render_image_frame",
                    "read_image_region",
                    "extract_image",
                    "compose_images",
                    "update_image",
                    "verify",
                    "read_selection",
                    "export_wiki",
                    *(["create_image"] if kind == "png" else []),
                ]
                if images_enabled
                else []
            )
            for kind in sorted(IMAGE_EXTENSIONS)
        },
        "other": [
            "register",
            "inspect_metadata",
            "history",
            "publish",
            "archive",
        ],
    }
