"""Shared native operation fields for runtime validation and schema discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NativeOperation = Literal[
    "contract",
    "contract_details",
    "schema",
    "register",
    "create",
    "list",
    "inspect",
    "project_workbook_table",
    "read_table_workspace",
    "apply_table_workspace",
    "create_workbook_from_table",
    "read_workbook",
    "create_workbook_rendition",
    "read_rendition",
    "update_worksheet_grid",
    "read_worksheet_layout",
    "update_worksheet_layout",
    "update_workbook_table",
    "add_workbook_table",
    "add_worksheets",
    "rename_worksheet",
    "reorder_worksheets",
    "delete_worksheets",
    "read_cell",
    "create_ods",
    "read_ods",
    "read_ods_cell",
    "update_ods",
    "create_delimited",
    "read_delimited",
    "read_delimited_cell",
    "update_delimited",
    "create_pdf",
    "create_image",
    "extract_image",
    "compose_images",
    "read_image",
    "read_image_frame",
    "render_image_frame",
    "read_image_region",
    "update_image",
    "read_pdf",
    "read_pdf_page",
    "read_pdf_region",
    "read_pdf_annotations",
    "read_pdf_annotation",
    "update_pdf_annotations",
    "render_pdf_page",
    "add_pdf_pages",
    "update_pdf",
    "delete_pdf_pages",
    "reorder_pdf_pages",
    "read_pptx_layouts",
    "render_pptx_slide",
    "add_pptx_slides",
    "delete_pptx_slides",
    "reorder_pptx_slides",
    "create_pptx",
    "add_pptx_pictures",
    "replace_pptx_pictures",
    "read_pptx_picture",
    "extract_pptx_picture",
    "read_pptx",
    "read_pptx_shape",
    "update_pptx",
    "add_pptx_tables",
    "update_pptx_table_grid",
    "add_pptx_shapes",
    "delete_pptx_shapes",
    "read_docx",
    "read_docx_notes",
    "read_docx_note",
    "update_docx_note",
    "update_docx_notes",
    "read_docx_stories",
    "read_docx_story",
    "update_docx_story",
    "read_docx_story_structure",
    "update_docx_story_structure",
    "render_docx_page",
    "create_docx",
    "add_docx_blocks",
    "delete_docx_blocks",
    "read_docx_block",
    "read_docx_table",
    "update_docx_table_grid",
    "update_docx",
    "verify",
    "read_selection",
    "record_derivation",
    "read_derivations",
    "retract_derivation",
    "verify_derivation",
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
    "contract_details": _fields("contract_sha256", "for_op text_offset text_limit"),
    "schema": _fields(optional="for_op schema_sha256 text_offset text_limit"),
    "register": _fields("source_path"),
    "create": _fields("workbook"),
    "list": _fields(optional="offset limit"),
    "inspect": _fields("asset_id", "sheet offset limit revision"),
    "read_cell": _fields("asset_id sheet cell", "revision text_offset text_limit"),
    "project_workbook_table": _fields("asset_id revision table_projection"),
    "read_table_workspace": _fields(
        "table_id", "table_sha256 workspace_reference text_offset text_limit"
    ),
    "apply_table_workspace": _fields(
        "asset_id expected_revision table_id expected_table_sha256", "worksheet_grid"
    ),
    "create_workbook_from_table": _fields(
        "table_id expected_table_sha256 table_workbook", "workspace_reference"
    ),
    "create_ods": _fields("ods_create"),
    "read_ods": _fields(
        "asset_id revision", "offset limit ods_text_sha256 text_offset text_limit"
    ),
    "read_ods_cell": _fields(
        "asset_id revision ods_locator", "ods_text_sha256 text_offset text_limit"
    ),
    "update_ods": _fields("asset_id expected_revision ods_update"),
    "create_delimited": _fields("delimited_create"),
    "read_delimited": _fields(
        "asset_id revision", "delimited_dialect text_offset text_limit"
    ),
    "read_delimited_cell": _fields(
        "asset_id revision delimited_row delimited_column",
        "delimited_dialect text_offset text_limit",
    ),
    "update_delimited": _fields(
        "asset_id expected_revision delimited_update", "delimited_dialect"
    ),
    "read_workbook": _fields(
        "asset_id", "revision workbook_view text_offset text_limit"
    ),
    "create_workbook_rendition": _fields("asset_id revision workbook_rendition"),
    "read_rendition": _fields("asset_id revision", "text_offset text_limit"),
    "read_worksheet_layout": _fields(
        "asset_id revision worksheet_key", "text_offset text_limit"
    ),
    "update_worksheet_layout": _fields("asset_id expected_revision worksheet_layout"),
    "update_worksheet_grid": _fields("asset_id expected_revision worksheet_grid"),
    "update_workbook_table": _fields("asset_id expected_revision table_update"),
    "add_workbook_table": _fields("asset_id expected_revision table_create"),
    "add_worksheets": _fields(
        "asset_id expected_revision worksheet_insert", "allow_3d_membership_change"
    ),
    "rename_worksheet": _fields("asset_id expected_revision worksheet_rename"),
    "reorder_worksheets": _fields(
        "asset_id expected_revision worksheet_order", "allow_3d_membership_change"
    ),
    "delete_worksheets": _fields("asset_id expected_revision worksheet_keys"),
    "create_pdf": _fields("pdf_create"),
    "create_image": _fields("image_create"),
    "extract_image": _fields("image_extract"),
    "compose_images": _fields("image_compose"),
    "read_image": _fields(
        "asset_id revision", "text_offset text_limit image_catalog_sha256"
    ),
    "read_image_frame": _fields(
        "asset_id revision image_locator", "text_offset text_limit reference"
    ),
    "render_image_frame": _fields("reference", "render_size image_color_policy"),
    "read_image_region": _fields(
        "reference", "image_region render_size image_color_policy"
    ),
    "update_image": _fields("asset_id expected_revision image_update"),
    "read_pdf": _fields("asset_id", "revision offset limit"),
    "read_pdf_page": _fields("asset_id pdf_locator", "revision text_offset text_limit"),
    "render_pdf_page": _fields("asset_id pdf_locator", "revision render_size"),
    "read_pdf_region": _fields("reference", "pdf_region render_size"),
    "read_pdf_annotations": _fields("asset_id revision", "text_offset text_limit"),
    "read_pdf_annotation": _fields(
        "asset_id revision pdf_annotation_locator", "text_offset text_limit"
    ),
    "update_pdf_annotations": _fields(
        "asset_id expected_revision pdf_annotations_update"
    ),
    "add_pdf_pages": _fields("asset_id expected_revision pdf_insert"),
    "update_pdf": _fields("asset_id expected_revision pdf_edits"),
    "delete_pdf_pages": _fields("asset_id expected_revision pdf_page_refs"),
    "reorder_pdf_pages": _fields("asset_id expected_revision pdf_order"),
    "read_pptx_layouts": _fields("asset_id", "revision offset limit"),
    "render_pptx_slide": _fields("asset_id revision pptx_slide_key", "render_size"),
    "add_pptx_slides": _fields("asset_id expected_revision pptx_slide_insert"),
    "delete_pptx_slides": _fields("asset_id expected_revision pptx_slide_keys"),
    "reorder_pptx_slides": _fields("asset_id expected_revision pptx_slide_order"),
    "create_pptx": _fields("presentation"),
    "add_pptx_pictures": _fields("asset_id expected_revision pptx_pictures"),
    "replace_pptx_pictures": _fields("asset_id expected_revision pptx_picture_edits"),
    "read_pptx_picture": _fields("asset_id pptx_locator", "revision render_size"),
    "extract_pptx_picture": _fields("asset_id pptx_locator", "revision"),
    "read_pptx": _fields("asset_id", "revision offset limit"),
    "read_pptx_shape": _fields(
        "asset_id pptx_locator", "revision text_offset text_limit"
    ),
    "update_pptx": _fields("asset_id expected_revision pptx_edits"),
    "add_pptx_tables": _fields("asset_id expected_revision pptx_tables"),
    "update_pptx_table_grid": _fields("asset_id expected_revision pptx_table_grid"),
    "add_pptx_shapes": _fields("asset_id expected_revision pptx_shapes"),
    "delete_pptx_shapes": _fields("asset_id expected_revision pptx_shape_refs"),
    "read_docx_notes": _fields("asset_id revision", "text_offset text_limit"),
    "read_docx_note": _fields(
        "asset_id revision docx_note_locator", "text_offset text_limit"
    ),
    "update_docx_note": _fields(
        "asset_id expected_revision docx_note_reference docx_note_update"
    ),
    "update_docx_notes": _fields("asset_id expected_revision docx_notes_update"),
    "read_docx_stories": _fields("asset_id revision", "text_offset text_limit"),
    "read_docx_story": _fields(
        "asset_id revision docx_story_part", "text_offset text_limit"
    ),
    "update_docx_story": _fields(
        "asset_id expected_revision docx_story_reference docx_story_update"
    ),
    "read_docx_story_structure": _fields("asset_id revision", "text_offset text_limit"),
    "update_docx_story_structure": _fields(
        "asset_id expected_revision docx_story_structure"
    ),
    "read_docx": _fields("asset_id", "revision text_offset text_limit offset limit"),
    "render_docx_page": _fields("asset_id revision docx_page_index", "render_size"),
    "create_docx": _fields("docx_create"),
    "add_docx_blocks": _fields("asset_id expected_revision docx_insert"),
    "delete_docx_blocks": _fields("asset_id expected_revision docx_block_refs"),
    "read_docx_block": _fields("asset_id block_id", "revision text_offset text_limit"),
    "read_docx_table": _fields(
        "asset_id revision docx_table_reference", "text_offset text_limit"
    ),
    "update_docx_table_grid": _fields("asset_id expected_revision docx_table_grid"),
    "update_docx": _fields("asset_id expected_revision docx_edit"),
    "verify": _fields("reference"),
    "read_selection": _fields("reference", "selection text_offset text_limit"),
    "record_derivation": _fields("asset_id expected_derivations_sha256 derivation"),
    "read_derivations": _fields(
        "asset_id", "derivations_sha256 text_offset text_limit"
    ),
    "retract_derivation": _fields("asset_id expected_derivations_sha256 retraction"),
    "verify_derivation": _fields(
        "asset_id derivation_id", "derivations_sha256 offset limit"
    ),
    "export_wiki": _fields(
        "asset_id output_dir",
        "revision citation_contract citation_metadata derivations_sha256 delimited_dialect image_color_policy image_catalog_sha256",
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
