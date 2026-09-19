"""Coordinate native column metadata and explicit calculated/totals cell intent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_table_edit import TOTAL_FUNCTIONS
from src.infrastructure.native_grid_formulas import translate_shared_formula
from src.infrastructure.native_grid_selectors import _encode
from src.infrastructure.native_grid_xml import address, tag
from src.infrastructure.native_spreadsheet_reader import NS, _decode_text, _encode_text
from src.infrastructure.native_workbook_formulas import formula_tokens

if TYPE_CHECKING:
    from src.domain.native_table_edit import NativeTableColumnEdit
    from src.infrastructure.native_grid_table_state import GridTableState
    from src.infrastructure.native_table_cells import TableCellWriter


def scalar_formula(column: etree._Element, name: str) -> etree._Element | None:
    nodes = column.findall(f"s:{name}", NS)
    if len(nodes) > 1 or any(
        node.get("array", "0") not in {"0", "false"}
        or set(node.attrib) - {"array"}
        or len(node)
        for node in nodes
    ):
        raise ValueError("Array/extended Table formulas need a dedicated edit")
    return nodes[0] if nodes else None


def set_formula(column: etree._Element, name: str, value: str | None) -> None:
    node = scalar_formula(column, name)
    if value is None:
        if node is not None:
            column.remove(node)
        return
    formula_tokens(value)  # Parse, without pretending to calculate or validate meaning.
    if node is None:
        node = etree.Element(tag(name))
        before = {tag("xmlColumnPr"), tag("extLst")}
        if name == "calculatedColumnFormula":
            before.add(tag("totalsRowFormula"))
        at = next(
            (i for i, item in enumerate(column) if item.tag in before), len(column)
        )
        column.insert(at, node)
    node.text = value.removeprefix("=")


def rename_header(
    state: GridTableState,
    column: etree._Element,
    position: int,
    edit: NativeTableColumnEdit,
    writer: TableCellWriter,
) -> None:
    if edit.name is None:
        return
    if state.headers:
        location = address(state.bounds.first_row, position)
        current = writer.value(location)
        if current["kind"] != "string" or current["value"] != edit.expected_name:
            raise ValueError("Table header cell disagrees with its column name")
        if edit.name != edit.expected_name or edit.header_runs is not None:
            writer.write(location, "string", edit.name, runs=edit.header_runs)
    elif edit.header_runs is not None:
        raise ValueError("A hidden header has no header runs to edit")
    column.set("name", _encode_text(edit.name))


def update_calculated(
    state: GridTableState,
    column: etree._Element,
    position: int,
    edit: NativeTableColumnEdit,
    writer: TableCellWriter,
) -> None:
    change = edit.calculated
    if change is None:
        return
    old = scalar_formula(column, "calculatedColumnFormula")
    if change.formula is None:
        set_formula(column, "calculatedColumnFormula", None)
        return
    first = state.bounds.first_row + state.headers
    last = state.bounds.last_row - state.totals
    if last - first + 1 > 20_000:
        raise ValueError("Calculated Table column exceeds the 20000-cell budget")
    formula_tokens(change.formula)
    for row in range(first, last + 1):
        location = address(row, position)
        previous = writer.value(location)
        expected = (
            "=" + translate_shared_formula(old.text or "", row - first, 0)
            if old is not None
            else None
        )
        if change.policy == "require_matching" and not (
            previous["kind"] == "blank"
            or (
                expected is not None
                and previous["kind"] == "formula"
                and previous["value"] == expected
            )
        ):
            raise ValueError(
                f"Calculated column exception at {location}; require explicit replace_all"
            )
        writer.write(
            location,
            "formula",
            "=" + translate_shared_formula(change.formula[1:], row - first, 0),
        )
    set_formula(column, "calculatedColumnFormula", change.formula)


def update_totals(
    state: GridTableState,
    column: etree._Element,
    position: int,
    edit: NativeTableColumnEdit,
    writer: TableCellWriter,
) -> None:
    change = edit.totals
    if change is None:
        return
    if not state.totals:
        raise ValueError("Table totals editing requires an existing totals row")
    set_formula(column, "totalsRowFormula", None)
    column.attrib.pop("totalsRowLabel", None)
    column.attrib.pop("totalsRowFunction", None)
    kind: str = change.kind
    value = change.value
    if kind == "label":
        assert value is not None
        column.set("totalsRowLabel", _encode_text(value))
        kind = "string"
    elif kind == "formula":
        assert value is not None
        column.set("totalsRowFunction", "custom")
        set_formula(column, "totalsRowFormula", value)
    elif kind == "function":
        assert value is not None
        column.set("totalsRowFunction", value)
        name = _encode(_decode_text(column.get("name", "")))
        value = f"=SUBTOTAL({TOTAL_FUNCTIONS[value]},[{name}])"
        kind = "formula"
    writer.write(address(state.bounds.last_row, position), kind, value)
