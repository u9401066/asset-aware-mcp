"""Scoped ODS values, repetition splitting and output reopening, without calculation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_ods import NativeODSCellLocator
from src.infrastructure.native_odf_package import NS, q, xml_bytes
from src.infrastructure.native_ods_grid import ensure_cell, ensure_columns, guard_edit
from src.infrastructure.native_ods_reader import NativeODSReader, cells, rows
from src.infrastructure.native_ods_text import display_paragraph

if TYPE_CHECKING:
    from src.domain.native_ods import NativeODSCellEdit, NativeODSValue

VALUE_ATTRS = {
    q("office", key)
    for key in (
        "value-type",
        "value",
        "string-value",
        "boolean-value",
        "date-value",
        "time-value",
        "currency",
        "error",
    )
}
CALC_VALUE_TYPE = (
    "{urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0}value-type"
)


def _matches(record: dict[str, Any], value: NativeODSValue) -> bool:
    attrs = record["value_attributes"]
    if value.kind == "formula":
        formula = record["formula"]
        return bool(
            formula
            and formula["namespace"] == NS["of"]
            and formula["expression"] == value.value
        )
    if record["formula"] is not None:
        return False
    if value.kind == "blank":
        return not attrs and not record["display_paragraphs"]
    if record["value_type"] != value.kind:
        return False
    if value.kind == "string":
        return bool(
            attrs.get("string-value", "\n".join(record["display_paragraphs"]))
            == value.value
        )
    if value.kind == "boolean":
        return bool(attrs.get("boolean-value") == ("true" if value.value else "false"))
    key = {"date": "date-value", "time": "time-value"}.get(value.kind, "value")
    return attrs.get(key) == value.value and (
        value.kind != "currency" or attrs.get("currency") == value.currency
    )


def _set_value(cell: etree._Element, value: NativeODSValue) -> None:
    for key in VALUE_ATTRS | {CALC_VALUE_TYPE, q("table", "formula")}:
        cell.attrib.pop(key, None)
    for child in list(cell):
        if child.tag in {q("text", "p"), q("text", "h")}:
            cell.remove(child)
    if value.kind == "blank":
        return
    if value.kind == "formula":
        # No fabricated cached result. The default formula namespace is OpenFormula.
        cell.set(q("table", "formula"), str(value.value))
        return
    cell.set(q("office", "value-type"), value.kind)
    lexical = (
        ("true" if value.value else "false")
        if value.kind == "boolean"
        else str(value.value)
    )
    key = {
        "string": "string-value",
        "boolean": "boolean-value",
        "date": "date-value",
        "time": "time-value",
    }.get(value.kind, "value")
    cell.set(q("office", key), lexical)
    if value.currency:
        cell.set(q("office", "currency"), value.currency)
    cell.append(display_paragraph(lexical))


def edit_ods(
    data: bytes, edits: list[NativeODSCellEdit]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(edits) <= 256:
        raise ValueError("ODS cell transactions require 1-256 edits")
    identities = [
        (e.locator.table_index, e.locator.row, e.locator.column) for e in edits
    ]
    if len(set(identities)) != len(edits):
        raise ValueError("An ODS transaction cannot edit the same cell twice")
    book = NativeODSReader(data)
    if book.package.signed:
        raise ValueError("Signed ODF packages require a signature-aware workflow")
    changes: list[dict[str, Any]] = []
    original_records = [book.read_cell(edit.locator) for edit in edits]
    for edit, before in zip(edits, original_records, strict=True):
        if not _matches(before, edit.value):
            guard_edit(book, edit)
    for edit, before in zip(edits, original_records, strict=True):
        if _matches(before, edit.value):
            continue
        cell = ensure_cell(book, edit)
        attributes = {
            k: v
            for k, v in cell.attrib.items()
            if k not in VALUE_ATTRS | {CALC_VALUE_TYPE, q("table", "formula")}
        }
        _set_value(cell, edit.value)
        if attributes != {
            k: v
            for k, v in cell.attrib.items()
            if k not in VALUE_ATTRS | {CALC_VALUE_TYPE, q("table", "formula")}
        }:
            raise ValueError("ODS cell style/metadata preservation failed")
        changes.append(
            {
                "operation": "set_cell_value",
                "locator": edit.locator.model_dump(),
                "before": before,
                "display_policy": edit.display_policy,
            }
        )
    column_changes = []
    for index in sorted({change["locator"]["table_index"] for change in changes}):
        if growth := ensure_columns(book.tables[index]):
            column_changes.append(
                {
                    "operation": "extend_column_declarations",
                    "table_index": index,
                    "before_count": growth[0],
                    "after_count": growth[1],
                }
            )
    cache_changes = _invalidate_caches(book) if changes else []
    replacements = {"content.xml": xml_bytes(book.root)} if changes else {}
    result = book.package.replace(replacements)
    checked = NativeODSReader(result)
    if etree.tostring(checked.root, method="c14n") != etree.tostring(
        book.root, method="c14n"
    ):
        raise ValueError("ODS output XML differs from the edit plan")
    for edit in edits:
        if not _matches(checked.read_cell(edit.locator), edit.value):
            raise ValueError("ODS value read-back verification failed")
    for change in changes:
        locator = next(
            edit.locator
            for edit in edits
            if edit.locator.model_dump() == change["locator"]
        )
        change["after"] = checked.read_cell(locator)
    for change in cache_changes:
        change["after"] = checked.read_cell(
            NativeODSCellLocator.model_validate(change["locator"])
        )
    return result, NativeEditResult(
        changed_parts=list(replacements),
        preserved_parts=len(book.package.parts) - len(replacements),
        changes=changes + cache_changes + column_changes,
        checks=[
            "output_xml_matches_edit_plan",
            "cell_values_read_back",
            "cell_style_attributes_preserved",
            "untouched_package_members_byte_identical",
            "repetition_not_expanded",
        ],
        review_required=[
            "semantic_accuracy",
            "rendered_layout",
            "rich_text_replacement",
            "formula_recalculation_and_results",
        ],
        repairs=(["invalidated_typed_formula_caches"] if cache_changes else [])
        + (["extended_column_declarations"] if column_changes else []),
    )


def _invalidate_caches(book: NativeODSReader) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for index, table in enumerate(book.tables):
        for row_start, _, row in rows(table):
            for column_start, _, cell in cells(row):
                if q("table", "formula") not in cell.attrib or not (
                    set(cell.attrib) & (VALUE_ATTRS | {CALC_VALUE_TYPE})
                ):
                    continue
                if table.get(q("table", "protected")) in {"true", "1"} or cell.get(
                    q("table", "protected")
                ) in {"true", "1"}:
                    raise ValueError(
                        "Protected ODS formula caches require a protection-aware edit"
                    )
                locator = NativeODSCellLocator(
                    table_index=index,
                    table_name=table.get(q("table", "name")),
                    row=row_start,
                    column=column_start,
                )
                before = book.read_cell(locator)
                for key in VALUE_ATTRS | {CALC_VALUE_TYPE}:
                    cell.attrib.pop(key, None)
                changes.append(
                    {
                        "operation": "invalidate_typed_formula_cache",
                        "locator": locator.model_dump(),
                        "before": before,
                    }
                )
    return changes
